"""Executable contracts for purpose-bound bitemporal Position history reads."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.position_history import (
    PositionHistoryIntegrityError,
    PositionHistoryRecord,
    read_position_history,
)

TENANT = UUID("0198a413-7000-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a413-7000-7000-8000-000000000002")
POSITION = UUID("0198a413-7000-7000-8000-000000000010")
OTHER_POSITION = UUID("0198a413-7000-7000-8000-000000000011")
VERSION_A = UUID("0198a413-7000-7000-8000-000000000020")
VERSION_B = UUID("0198a413-7000-7000-8000-000000000021")
ORGANIZATION = UUID("0198a413-7000-7000-8000-000000000030")
JOB = UUID("0198a413-7000-7000-8000-000000000040")
KNOWN_AT = datetime(2026, 8, 30, 2, 0, tzinfo=timezone.utc)
RECORDED_FROM = datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc)


class ForgedUUID(UUID):
    """Prove trust-bearing identity validators reject UUID subclasses."""


class ForgedField(str):
    """Prove authorization output cannot smuggle string subclass behavior."""


class ZeroOffsetTimezone(tzinfo):
    """Caller-controlled timezone that merely looks like UTC."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return timedelta(0)

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)


class FakePositionHistoryPort:
    """Capture protected reads so authorization-before-retrieval is observable."""

    def __init__(self, records: object) -> None:
        self.records = records
        self.calls: list[tuple[UUID, UUID, datetime]] = []

    def read_position_history(
        self,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        known_at: datetime,
    ) -> object:
        self.calls.append((tenant_record_id, position_record_id, known_at))
        return self.records


def position_record(
    *,
    tenant_record_id: UUID = TENANT,
    position_record_id: UUID = POSITION,
    position_record_version_id: UUID = VERSION_A,
    organization_unit_id: UUID = ORGANIZATION,
    job_profile_id: UUID = JOB,
    position_status_code: str = "active",
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = date(2026, 7, 1),
    recorded_from: datetime = RECORDED_FROM,
    recorded_to: datetime | None = None,
) -> PositionHistoryRecord:
    """Build one Position history row crossing the injected persistence boundary."""
    return PositionHistoryRecord(
        tenant_record_id=tenant_record_id,
        position_record_id=position_record_id,
        position_record_version_id=position_record_version_id,
        organization_unit_id=organization_unit_id,
        job_profile_id=job_profile_id,
        position_status_code=position_status_code,
        effective_from=effective_from,
        effective_to=effective_to,
        recorded_from=recorded_from,
        recorded_to=recorded_to,
    )


class PositionHistoryReadTests(unittest.TestCase):
    """Prove Position history stays purpose-bound, bitemporal, and fail-closed."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:hr-operator",
            granted_scope_codes=frozenset({"orgmetra.people.position_history.read"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="position-history-v1",
            resource_kind="position_history",
            purpose_code="workforce_position_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.position_history.read",
            permitted_fields=frozenset(
                {
                    "position_record_version_id",
                    "organization_unit_id",
                    "job_profile_id",
                    "position_status_code",
                    "effective_from",
                    "effective_to",
                    "recorded_from",
                    "recorded_to",
                }
            ),
        )

    def read(self, records: object, requested_fields: frozenset[str] | None = None):
        port = FakePositionHistoryPort(records)
        view = read_position_history(
            principal=self.principal,
            tenant_record_id=TENANT,
            position_record_id=POSITION,
            known_at=KNOWN_AT,
            purpose_code="workforce_position_review",
            requested_fields=self.policy.permitted_fields if requested_fields is None else requested_fields,
            policy=self.policy,
            read_port=port,
        )
        return view, port

    def test_returns_authorized_versions_in_deterministic_effective_order(self) -> None:
        later = position_record(
            position_record_version_id=VERSION_B,
            position_status_code="frozen",
            effective_from=date(2026, 7, 1),
            effective_to=None,
        )
        earlier = position_record(recorded_to=datetime(2026, 8, 31, 0, 0, tzinfo=timezone.utc))

        view, port = self.read((later, earlier))

        self.assertEqual(view.resource_reference, f"position_history:{POSITION.hex}")
        self.assertEqual(port.calls, [(TENANT, POSITION, KNOWN_AT)])
        rows = tuple(dict(entry.field_values) for entry in view.entries)
        self.assertEqual(tuple(row["position_record_version_id"] for row in rows), (str(VERSION_A), str(VERSION_B)))
        self.assertEqual(rows[0]["organization_unit_id"], str(ORGANIZATION))
        self.assertEqual(rows[0]["job_profile_id"], str(JOB))
        self.assertEqual(rows[0]["position_status_code"], "active")
        self.assertEqual(rows[0]["effective_from"], "2026-01-01")
        self.assertEqual(rows[0]["effective_to"], "2026-07-01")
        self.assertEqual(rows[0]["recorded_from"], "2026-08-20T00:00:00Z")
        self.assertEqual(rows[0]["recorded_to"], "2026-08-31T00:00:00Z")
        self.assertIsNone(rows[1]["effective_to"])
        self.assertIsNone(rows[1]["recorded_to"])

    def test_field_minimization_never_adds_position_identity(self) -> None:
        limited = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="position-history-minimal-v1",
            resource_kind="position_history",
            purpose_code="workforce_position_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.position_history.read",
            permitted_fields=frozenset({"position_status_code"}),
        )
        port = FakePositionHistoryPort((position_record(),))

        view = read_position_history(
            principal=self.principal,
            tenant_record_id=TENANT,
            position_record_id=POSITION,
            known_at=KNOWN_AT,
            purpose_code="workforce_position_review",
            requested_fields=frozenset({"position_status_code"}),
            policy=limited,
            read_port=port,
        )

        self.assertEqual(view.entries[0].field_values, (("position_status_code", "active"),))

    def test_denied_field_never_reaches_protected_repository(self) -> None:
        limited = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="position-history-limited-v1",
            resource_kind="position_history",
            purpose_code="workforce_position_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.position_history.read",
            permitted_fields=frozenset({"position_status_code"}),
        )
        port = FakePositionHistoryPort((position_record(),))

        with self.assertRaises(AuthorizationDeniedError):
            read_position_history(
                principal=self.principal,
                tenant_record_id=TENANT,
                position_record_id=POSITION,
                known_at=KNOWN_AT,
                purpose_code="workforce_position_review",
                requested_fields=frozenset({"job_profile_id"}),
                policy=limited,
                read_port=port,
            )
        self.assertEqual(port.calls, [])

    def test_scope_or_system_visibility_mismatch_fails_closed(self) -> None:
        cases = (
            position_record(tenant_record_id=OTHER_TENANT),
            position_record(position_record_id=OTHER_POSITION),
            position_record(recorded_from=datetime(2026, 8, 31, 0, 0, tzinfo=timezone.utc)),
            position_record(recorded_to=KNOWN_AT),
        )
        for record in cases:
            with self.subTest(record=record), self.assertRaises(PositionHistoryIntegrityError):
                self.read((record,))

    def test_container_row_and_low_level_forgery_fail_closed(self) -> None:
        valid = position_record()
        forged_values = tuple(valid)
        forged_values = forged_values[:5] + ("NOT_CANONICAL",) + forged_values[6:]
        forged = tuple.__new__(PositionHistoryRecord, forged_values)
        cases = (
            ([valid], "immutable tuple"),
            ((object(),), "unsupported row type"),
            ((forged,), "runtime integrity"),
        )
        for records, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(PositionHistoryIntegrityError, message):
                self.read(records)

    def test_record_is_structurally_immutable(self) -> None:
        record = position_record()
        with self.assertRaises(AttributeError):
            object.__setattr__(record, "position_status_code", "closed")
        self.assertEqual(record.position_status_code, "active")

    def test_duplicate_version_identity_or_overlapping_business_truth_fails_closed(self) -> None:
        duplicate = position_record(
            effective_from=date(2026, 7, 1),
            effective_to=None,
            position_status_code="frozen",
        )
        with self.assertRaisesRegex(PositionHistoryIntegrityError, "duplicate visible Position version"):
            self.read((position_record(), duplicate))

        overlapping = position_record(
            position_record_version_id=VERSION_B,
            effective_from=date(2026, 6, 1),
            effective_to=None,
            position_status_code="frozen",
        )
        with self.assertRaisesRegex(PositionHistoryIntegrityError, "overlapping visible Position truth"):
            self.read((position_record(), overlapping))

    def test_policy_schema_or_field_subclass_drift_fails_closed(self) -> None:
        for field in ("future_sensitive_field", ForgedField("position_status_code")):
            policy = PurposeBoundAccessPolicy(
                tenant_record_id=TENANT,
                policy_version_code="position-history-drift-v1",
                resource_kind="position_history",
                purpose_code="workforce_position_review",
                operation_code="read_record",
                required_scope_code="orgmetra.people.position_history.read",
                permitted_fields=frozenset({field}),
            )
            with self.subTest(field=field), self.assertRaisesRegex(PositionHistoryIntegrityError, "unsupported Position-history field"):
                read_position_history(
                    principal=self.principal,
                    tenant_record_id=TENANT,
                    position_record_id=POSITION,
                    known_at=KNOWN_AT,
                    purpose_code="workforce_position_review",
                    requested_fields=frozenset({field}),
                    policy=policy,
                    read_port=FakePositionHistoryPort((position_record(),)),
                )

    def test_invalid_request_shape_fails_before_repository_access(self) -> None:
        port = FakePositionHistoryPort(())
        invalid = (
            ("tenant_record_id", UUID(int=0)),
            ("tenant_record_id", ForgedUUID(str(TENANT))),
            ("position_record_id", UUID(int=(1 << 128) - 1)),
            ("known_at", datetime(2026, 8, 30, 2, 0)),
            ("known_at", datetime(2026, 8, 30, 2, 0, tzinfo=ZeroOffsetTimezone())),
        )
        for field_name, value in invalid:
            kwargs = {
                "principal": self.principal,
                "tenant_record_id": TENANT,
                "position_record_id": POSITION,
                "known_at": KNOWN_AT,
                "purpose_code": "workforce_position_review",
                "requested_fields": frozenset({"position_status_code"}),
                "policy": self.policy,
                "read_port": port,
            }
            kwargs[field_name] = value
            with self.subTest(field_name=field_name, value_type=type(value).__name__), self.assertRaises(ValueError):
                read_position_history(**kwargs)
        self.assertEqual(port.calls, [])

    def test_record_rejects_noncanonical_identity_status_and_time_values(self) -> None:
        invalid_overrides = (
            {"position_record_version_id": UUID(int=0)},
            {"organization_unit_id": ForgedUUID(str(ORGANIZATION))},
            {"position_status_code": "NOT_CANONICAL"},
            {"position_status_code": ForgedField("active")},
            {"effective_from": datetime(2026, 1, 1, tzinfo=timezone.utc)},
            {"effective_to": date(2026, 1, 1)},
            {"recorded_from": datetime(2026, 8, 20, 0, 0)},
            {"recorded_from": datetime(2026, 8, 20, 0, 0, tzinfo=ZeroOffsetTimezone())},
            {"recorded_to": datetime(2026, 8, 21, 0, 0)},
            {"recorded_to": RECORDED_FROM},
        )
        for override in invalid_overrides:
            with self.subTest(override=override), self.assertRaises(ValueError):
                position_record(**override)


if __name__ == "__main__":
    unittest.main()
