"""Executable contracts for purpose-bound bitemporal Employment history reads."""

from __future__ import annotations

from datetime import date, datetime, timezone
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.employment_history import (
    EmploymentHistoryIntegrityError,
    EmploymentHistoryRecord,
    read_employment_history,
)

TENANT = UUID("0198a412-7100-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a412-7100-7000-8000-000000000002")
PERSON = UUID("0198a412-7100-7000-8000-000000000010")
OTHER_PERSON = UUID("0198a412-7100-7000-8000-000000000011")
EMPLOYMENT_A = UUID("0198a412-7100-7000-8000-000000000020")
EMPLOYMENT_B = UUID("0198a412-7100-7000-8000-000000000021")
VERSION_A = UUID("0198a412-7100-7000-8000-000000000030")
VERSION_B = UUID("0198a412-7100-7000-8000-000000000031")
KNOWN_AT = datetime(2026, 8, 29, 0, 0, tzinfo=timezone.utc)
RECORDED_FROM = datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc)


class ForgedUUID(UUID):
    """Prove trust-bearing identities reject UUID subclasses."""


class ForgedField(str):
    """Prove authorization output cannot smuggle behavior in string subclasses."""


class ForgedStatus(str):
    """Prove controlled Employment codes require exact built-in strings."""


class FakeEmploymentHistoryPort:
    """Capture reads so tests prove authorization occurs before protected retrieval."""

    def __init__(self, records: object) -> None:
        self.records = records
        self.calls: list[tuple[UUID, UUID, datetime]] = []

    def read_employment_history(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        known_at: datetime,
    ) -> object:
        """Return configured persistence output after recording the exact scope."""
        self.calls.append((tenant_record_id, person_record_id, known_at))
        return self.records


def employment_record(
    *,
    employment_record_id: UUID = EMPLOYMENT_A,
    employment_record_version_id: UUID = VERSION_A,
    tenant_record_id: UUID = TENANT,
    person_record_id: UUID = PERSON,
    employment_status_code: str = "active",
    employment_concurrency_code: str = "exclusive",
    effective_from: date = date(2025, 1, 1),
    effective_to: date | None = None,
    recorded_from: datetime = RECORDED_FROM,
    recorded_to: datetime | None = None,
) -> EmploymentHistoryRecord:
    """Build one persisted Employment version for service-contract tests."""
    return EmploymentHistoryRecord(
        tenant_record_id=tenant_record_id,
        person_record_id=person_record_id,
        employment_record_id=employment_record_id,
        employment_record_version_id=employment_record_version_id,
        employment_status_code=employment_status_code,
        employment_concurrency_code=employment_concurrency_code,
        effective_from=effective_from,
        effective_to=effective_to,
        recorded_from=recorded_from,
        recorded_to=recorded_to,
    )


class EmploymentHistoryReadTests(unittest.TestCase):
    """Prove Employment history remains purpose-bound, bitemporal, and deterministic."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:hr-operator",
            granted_scope_codes=frozenset({"orgmetra.people.employment_history.read"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="employee-profile-employment-history-v1",
            resource_kind="person_employment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.employment_history.read",
            permitted_fields=frozenset(
                {
                    "employment_record_id",
                    "employment_record_version_id",
                    "employment_status_code",
                    "employment_concurrency_code",
                    "effective_from",
                    "effective_to",
                    "recorded_from",
                    "recorded_to",
                }
            ),
        )

    def test_returns_authorized_history_in_deterministic_effective_order(self) -> None:
        later = employment_record(
            employment_record_id=EMPLOYMENT_B,
            employment_record_version_id=VERSION_B,
            employment_status_code="leave",
            employment_concurrency_code="concurrent",
            effective_from=date(2026, 7, 1),
        )
        earlier = employment_record(
            employment_status_code="terminated",
            effective_from=date(2025, 1, 1),
            effective_to=date(2026, 6, 30),
            recorded_to=datetime(2026, 8, 30, 0, 0, tzinfo=timezone.utc),
        )
        port = FakeEmploymentHistoryPort((later, earlier))

        view = read_employment_history(
            principal=self.principal,
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            known_at=KNOWN_AT,
            purpose_code="employee_profile_review",
            requested_fields=self.policy.permitted_fields,
            policy=self.policy,
            read_port=port,
        )

        self.assertEqual(view.resource_reference, f"person_employment_history:{PERSON.hex}")
        self.assertEqual(port.calls, [(TENANT, PERSON, KNOWN_AT)])
        rows = tuple(dict(entry.field_values) for entry in view.entries)
        self.assertEqual(tuple(row["employment_record_id"] for row in rows), (str(EMPLOYMENT_A), str(EMPLOYMENT_B)))
        self.assertEqual(rows[0]["employment_record_version_id"], str(VERSION_A))
        self.assertEqual(rows[0]["employment_status_code"], "terminated")
        self.assertEqual(rows[0]["employment_concurrency_code"], "exclusive")
        self.assertEqual(rows[0]["effective_to"], "2026-06-30")
        self.assertEqual(rows[0]["recorded_to"], "2026-08-30T00:00:00Z")
        self.assertEqual(rows[1]["employment_status_code"], "leave")
        self.assertIsNone(rows[1]["effective_to"])
        self.assertIsNone(rows[1]["recorded_to"])

    def test_field_minimization_never_leaks_employment_identity(self) -> None:
        limited_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="minimal-v1",
            resource_kind="person_employment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.employment_history.read",
            permitted_fields=frozenset({"employment_status_code"}),
        )
        view = read_employment_history(
            principal=self.principal,
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            known_at=KNOWN_AT,
            purpose_code="employee_profile_review",
            requested_fields=frozenset({"employment_status_code"}),
            policy=limited_policy,
            read_port=FakeEmploymentHistoryPort((employment_record(),)),
        )
        self.assertEqual(view.entries[0].field_values, (("employment_status_code", "active"),))

    def test_denied_field_never_reaches_employment_repository(self) -> None:
        port = FakeEmploymentHistoryPort((employment_record(),))
        limited_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="limited-v1",
            resource_kind="person_employment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.employment_history.read",
            permitted_fields=frozenset({"effective_from"}),
        )
        with self.assertRaises(AuthorizationDeniedError):
            read_employment_history(
                principal=self.principal,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                known_at=KNOWN_AT,
                purpose_code="employee_profile_review",
                requested_fields=frozenset({"employment_status_code"}),
                policy=limited_policy,
                read_port=port,
            )
        self.assertEqual(port.calls, [])

    def test_repository_scope_or_recorded_visibility_mismatch_fails_closed(self) -> None:
        cases = (
            employment_record(tenant_record_id=OTHER_TENANT),
            employment_record(person_record_id=OTHER_PERSON),
            employment_record(recorded_from=datetime(2026, 8, 30, 0, 0, tzinfo=timezone.utc)),
            employment_record(recorded_to=KNOWN_AT),
        )
        for record in cases:
            with self.subTest(record=record), self.assertRaises(EmploymentHistoryIntegrityError):
                read_employment_history(
                    principal=self.principal,
                    tenant_record_id=TENANT,
                    person_record_id=PERSON,
                    known_at=KNOWN_AT,
                    purpose_code="employee_profile_review",
                    requested_fields=frozenset({"effective_from"}),
                    policy=self.policy,
                    read_port=FakeEmploymentHistoryPort((record,)),
                )

    def test_repository_container_or_row_type_drift_fails_closed(self) -> None:
        for records, message in (
            ([employment_record()], "immutable tuple"),
            ((object(),), "unsupported row type"),
        ):
            with self.subTest(records=records), self.assertRaisesRegex(EmploymentHistoryIntegrityError, message):
                read_employment_history(
                    principal=self.principal,
                    tenant_record_id=TENANT,
                    person_record_id=PERSON,
                    known_at=KNOWN_AT,
                    purpose_code="employee_profile_review",
                    requested_fields=frozenset({"effective_from"}),
                    policy=self.policy,
                    read_port=FakeEmploymentHistoryPort(records),
                )

    def test_low_level_invalid_row_reconstruction_fails_runtime_integrity(self) -> None:
        record = employment_record()
        raw_values = list(record)
        raw_values[4] = "forged"
        forged = tuple.__new__(EmploymentHistoryRecord, tuple(raw_values))
        self.assertIs(type(forged), EmploymentHistoryRecord)
        with self.assertRaisesRegex(EmploymentHistoryIntegrityError, "runtime integrity"):
            read_employment_history(
                principal=self.principal,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                known_at=KNOWN_AT,
                purpose_code="employee_profile_review",
                requested_fields=frozenset({"employment_status_code"}),
                policy=self.policy,
                read_port=FakeEmploymentHistoryPort((forged,)),
            )

    def test_duplicate_version_identity_or_overlapping_effective_truth_fails_closed(self) -> None:
        duplicate_version = employment_record(effective_from=date(2026, 7, 1))
        overlap = employment_record(
            employment_record_version_id=VERSION_B,
            effective_from=date(2025, 6, 1),
            effective_to=date(2025, 12, 1),
        )
        base = employment_record(effective_to=date(2026, 1, 1))
        for records, message in (
            ((base, duplicate_version), "duplicate Employment version identity"),
            ((base, overlap), "overlapping Employment business-time truth"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(EmploymentHistoryIntegrityError, message):
                read_employment_history(
                    principal=self.principal,
                    tenant_record_id=TENANT,
                    person_record_id=PERSON,
                    known_at=KNOWN_AT,
                    purpose_code="employee_profile_review",
                    requested_fields=frozenset({"effective_from"}),
                    policy=self.policy,
                    read_port=FakeEmploymentHistoryPort(records),
                )

    def test_adjacent_versions_for_one_employment_are_valid_history(self) -> None:
        first = employment_record(effective_to=date(2026, 1, 1))
        second = employment_record(
            employment_record_version_id=VERSION_B,
            employment_status_code="leave",
            effective_from=date(2026, 1, 1),
        )
        view = read_employment_history(
            principal=self.principal,
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            known_at=KNOWN_AT,
            purpose_code="employee_profile_review",
            requested_fields=frozenset({"employment_status_code", "effective_from"}),
            policy=self.policy,
            read_port=FakeEmploymentHistoryPort((second, first)),
        )
        self.assertEqual(tuple(dict(item.field_values)["employment_status_code"] for item in view.entries), ("active", "leave"))

    def test_policy_schema_drift_or_forged_field_fails_closed(self) -> None:
        for field in ("future_sensitive_field", ForgedField("effective_from")):
            policy = PurposeBoundAccessPolicy(
                tenant_record_id=TENANT,
                policy_version_code="drifted-v1",
                resource_kind="person_employment_history",
                purpose_code="employee_profile_review",
                operation_code="read_record",
                required_scope_code="orgmetra.people.employment_history.read",
                permitted_fields=frozenset({field}),
            )
            with self.subTest(field_type=type(field).__name__), self.assertRaisesRegex(
                EmploymentHistoryIntegrityError, "unsupported Employment-history field"
            ):
                read_employment_history(
                    principal=self.principal,
                    tenant_record_id=TENANT,
                    person_record_id=PERSON,
                    known_at=KNOWN_AT,
                    purpose_code="employee_profile_review",
                    requested_fields=frozenset({field}),
                    policy=policy,
                    read_port=FakeEmploymentHistoryPort((employment_record(),)),
                )

    def test_invalid_request_shape_fails_before_repository_access(self) -> None:
        port = FakeEmploymentHistoryPort(())
        invalid = (
            ("tenant_record_id", UUID(int=0)),
            ("tenant_record_id", ForgedUUID(str(TENANT))),
            ("person_record_id", UUID(int=(1 << 128) - 1)),
            ("known_at", datetime(2026, 8, 29, 0, 0)),
        )
        for field_name, value in invalid:
            kwargs = {
                "principal": self.principal,
                "tenant_record_id": TENANT,
                "person_record_id": PERSON,
                "known_at": KNOWN_AT,
                "purpose_code": "employee_profile_review",
                "requested_fields": frozenset({"effective_from"}),
                "policy": self.policy,
                "read_port": port,
            }
            kwargs[field_name] = value
            with self.subTest(field_name=field_name), self.assertRaises(ValueError):
                read_employment_history(**kwargs)
        self.assertEqual(port.calls, [])

    def test_record_rejects_noncanonical_identity_code_business_or_system_time(self) -> None:
        invalid_overrides = (
            {"employment_record_id": "employment"},
            {"employment_record_version_id": ForgedUUID(str(VERSION_A))},
            {"employment_status_code": "unknown"},
            {"employment_status_code": ForgedStatus("active")},
            {"employment_concurrency_code": "shared"},
            {"employment_concurrency_code": ForgedStatus("exclusive")},
            {"effective_from": datetime(2025, 1, 1, tzinfo=timezone.utc)},
            {"effective_to": date(2025, 1, 1)},
            {"recorded_from": datetime(2026, 8, 20, 0, 0)},
            {"recorded_to": datetime(2026, 8, 21, 0, 0)},
            {"recorded_to": RECORDED_FROM},
        )
        for override in invalid_overrides:
            with self.subTest(override=override), self.assertRaises(ValueError):
                employment_record(**override)


if __name__ == "__main__":
    unittest.main()
