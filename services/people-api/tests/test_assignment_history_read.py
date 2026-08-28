"""Executable contracts for purpose-bound bitemporal assignment history reads."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.assignment_history import (
    AssignmentHistoryIntegrityError,
    AssignmentHistoryRecord,
    read_assignment_history,
)

TENANT = UUID("0198a412-7000-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a412-7000-7000-8000-000000000002")
PERSON = UUID("0198a412-7000-7000-8000-000000000010")
OTHER_PERSON = UUID("0198a412-7000-7000-8000-000000000011")
EMPLOYMENT = UUID("0198a412-7000-7000-8000-000000000020")
POSITION_A = UUID("0198a412-7000-7000-8000-000000000030")
POSITION_B = UUID("0198a412-7000-7000-8000-000000000031")
ASSIGNMENT_A = UUID("0198a412-7000-7000-8000-000000000040")
ASSIGNMENT_B = UUID("0198a412-7000-7000-8000-000000000041")
KNOWN_AT = datetime(2026, 8, 28, 3, 0, tzinfo=timezone.utc)
RECORDED_FROM = datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc)


class ForgedUUID(UUID):
    """Prove trust-bearing identity validators reject subclass behavior."""


class ForgedField(str):
    """Prove authorization output cannot smuggle behavior in a string subclass."""


class FakeAssignmentHistoryPort:
    """Capture read calls so tests can prove authorization-before-retrieval ordering."""

    def __init__(self, records: object) -> None:
        self.records = records
        self.calls: list[tuple[UUID, UUID, datetime]] = []

    def read_assignment_history(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        known_at: datetime,
    ) -> object:
        """Return configured persistence output after recording the exact read scope."""
        self.calls.append((tenant_record_id, person_record_id, known_at))
        return self.records


def assignment_record(
    *,
    assignment_record_id: UUID = ASSIGNMENT_A,
    tenant_record_id: UUID = TENANT,
    person_record_id: UUID = PERSON,
    position_record_id: UUID = POSITION_A,
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = date(2026, 7, 1),
    recorded_from: datetime = RECORDED_FROM,
    recorded_to: datetime | None = None,
    allocation_ratio: Decimal = Decimal("1.0000"),
) -> AssignmentHistoryRecord:
    """Build one persisted assignment-history row for service-contract tests."""
    return AssignmentHistoryRecord(
        tenant_record_id=tenant_record_id,
        assignment_record_id=assignment_record_id,
        employment_record_id=EMPLOYMENT,
        person_record_id=person_record_id,
        position_record_id=position_record_id,
        allocation_ratio=allocation_ratio,
        effective_from=effective_from,
        effective_to=effective_to,
        recorded_from=recorded_from,
        recorded_to=recorded_to,
    )


class AssignmentHistoryReadTests(unittest.TestCase):
    """Prove employee-profile history remains authorized, bitemporal, and deterministic."""

    def setUp(self) -> None:
        self.principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:hr-operator",
            granted_scope_codes=frozenset({"orgmetra.people.assignment_history.read"}),
        )
        self.policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="employee-profile-assignment-history-v1",
            resource_kind="person_assignment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.assignment_history.read",
            permitted_fields=frozenset(
                {
                    "assignment_record_id",
                    "employment_record_id",
                    "position_record_id",
                    "allocation_ratio",
                    "effective_from",
                    "effective_to",
                    "recorded_from",
                    "recorded_to",
                }
            ),
        )

    def test_returns_authorized_history_in_deterministic_effective_order(self) -> None:
        later = assignment_record(
            assignment_record_id=ASSIGNMENT_B,
            position_record_id=POSITION_B,
            effective_from=date(2026, 7, 1),
            effective_to=None,
            allocation_ratio=Decimal("0.5000"),
        )
        earlier = assignment_record(recorded_to=KNOWN_AT.replace(day=30))
        port = FakeAssignmentHistoryPort((later, earlier))

        view = read_assignment_history(
            principal=self.principal,
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            known_at=KNOWN_AT,
            purpose_code="employee_profile_review",
            requested_fields=self.policy.permitted_fields,
            policy=self.policy,
            read_port=port,
        )

        self.assertEqual(view.resource_reference, f"person_assignment_history:{PERSON.hex}")
        self.assertEqual(port.calls, [(TENANT, PERSON, KNOWN_AT)])
        rows = tuple(dict(entry.field_values) for entry in view.entries)
        self.assertEqual(tuple(row["assignment_record_id"] for row in rows), (str(ASSIGNMENT_A), str(ASSIGNMENT_B)))
        self.assertEqual(rows[0]["effective_from"], "2026-01-01")
        self.assertEqual(rows[0]["effective_to"], "2026-07-01")
        self.assertEqual(rows[0]["allocation_ratio"], "1.0000")
        self.assertEqual(rows[0]["recorded_to"], "2026-08-30T03:00:00Z")
        self.assertIsNone(rows[1]["effective_to"])
        self.assertIsNone(rows[1]["recorded_to"])

    def test_field_minimization_never_leaks_assignment_identity(self) -> None:
        port = FakeAssignmentHistoryPort((assignment_record(),))
        limited_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="minimal-v1",
            resource_kind="person_assignment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.assignment_history.read",
            permitted_fields=frozenset({"effective_from"}),
        )

        view = read_assignment_history(
            principal=self.principal,
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            known_at=KNOWN_AT,
            purpose_code="employee_profile_review",
            requested_fields=frozenset({"effective_from"}),
            policy=limited_policy,
            read_port=port,
        )

        self.assertEqual(view.entries[0].field_values, (("effective_from", "2026-01-01"),))

    def test_denied_field_never_reaches_assignment_repository(self) -> None:
        port = FakeAssignmentHistoryPort((assignment_record(),))
        limited_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="limited-v1",
            resource_kind="person_assignment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.assignment_history.read",
            permitted_fields=frozenset({"effective_from"}),
        )

        with self.assertRaises(AuthorizationDeniedError):
            read_assignment_history(
                principal=self.principal,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                known_at=KNOWN_AT,
                purpose_code="employee_profile_review",
                requested_fields=frozenset({"position_record_id"}),
                policy=limited_policy,
                read_port=port,
            )

        self.assertEqual(port.calls, [])

    def test_repository_scope_or_recorded_visibility_mismatch_fails_closed(self) -> None:
        future_recorded = KNOWN_AT.replace(day=29)
        cases = (
            assignment_record(tenant_record_id=OTHER_TENANT),
            assignment_record(person_record_id=OTHER_PERSON),
            assignment_record(recorded_from=future_recorded),
            assignment_record(recorded_to=KNOWN_AT),
        )
        for record in cases:
            with self.subTest(record=record):
                with self.assertRaises(AssignmentHistoryIntegrityError):
                    read_assignment_history(
                        principal=self.principal,
                        tenant_record_id=TENANT,
                        person_record_id=PERSON,
                        known_at=KNOWN_AT,
                        purpose_code="employee_profile_review",
                        requested_fields=frozenset({"effective_from"}),
                        policy=self.policy,
                        read_port=FakeAssignmentHistoryPort((record,)),
                    )

    def test_repository_container_or_row_type_drift_fails_closed(self) -> None:
        for records, message in (
            ([assignment_record()], "immutable tuple"),
            ((object(),), "unsupported row type"),
        ):
            with self.subTest(records=records), self.assertRaisesRegex(AssignmentHistoryIntegrityError, message):
                read_assignment_history(
                    principal=self.principal,
                    tenant_record_id=TENANT,
                    person_record_id=PERSON,
                    known_at=KNOWN_AT,
                    purpose_code="employee_profile_review",
                    requested_fields=frozenset({"effective_from"}),
                    policy=self.policy,
                    read_port=FakeAssignmentHistoryPort(records),
                )

    def test_post_construction_row_mutation_fails_runtime_integrity(self) -> None:
        record = assignment_record()
        object.__setattr__(record, "allocation_ratio", Decimal("NaN"))

        with self.assertRaisesRegex(AssignmentHistoryIntegrityError, "runtime integrity"):
            read_assignment_history(
                principal=self.principal,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                known_at=KNOWN_AT,
                purpose_code="employee_profile_review",
                requested_fields=frozenset({"allocation_ratio"}),
                policy=self.policy,
                read_port=FakeAssignmentHistoryPort((record,)),
            )

    def test_duplicate_visible_assignment_identity_fails_closed(self) -> None:
        duplicate = assignment_record(effective_from=date(2026, 2, 1), effective_to=None)
        with self.assertRaisesRegex(AssignmentHistoryIntegrityError, "duplicate visible assignment"):
            read_assignment_history(
                principal=self.principal,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                known_at=KNOWN_AT,
                purpose_code="employee_profile_review",
                requested_fields=frozenset({"effective_from"}),
                policy=self.policy,
                read_port=FakeAssignmentHistoryPort((assignment_record(), duplicate)),
            )

    def test_policy_schema_drift_fails_closed_after_authorization(self) -> None:
        drifted_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="drifted-v1",
            resource_kind="person_assignment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.assignment_history.read",
            permitted_fields=frozenset({"future_sensitive_field"}),
        )
        with self.assertRaisesRegex(AssignmentHistoryIntegrityError, "unsupported assignment-history field"):
            read_assignment_history(
                principal=self.principal,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                known_at=KNOWN_AT,
                purpose_code="employee_profile_review",
                requested_fields=frozenset({"future_sensitive_field"}),
                policy=drifted_policy,
                read_port=FakeAssignmentHistoryPort((assignment_record(),)),
            )

    def test_field_name_subclass_from_authorization_fails_closed(self) -> None:
        forged_field = ForgedField("effective_from")
        forged_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="forged-field-v1",
            resource_kind="person_assignment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.assignment_history.read",
            permitted_fields=frozenset({forged_field}),
        )

        with self.assertRaisesRegex(AssignmentHistoryIntegrityError, "unsupported assignment-history field"):
            read_assignment_history(
                principal=self.principal,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                known_at=KNOWN_AT,
                purpose_code="employee_profile_review",
                requested_fields=frozenset({forged_field}),
                policy=forged_policy,
                read_port=FakeAssignmentHistoryPort((assignment_record(),)),
            )

    def test_invalid_request_shape_fails_before_repository_access(self) -> None:
        port = FakeAssignmentHistoryPort(())
        invalid = (
            ("tenant_record_id", UUID(int=0)),
            ("tenant_record_id", ForgedUUID(str(TENANT))),
            ("person_record_id", UUID(int=(1 << 128) - 1)),
            ("known_at", datetime(2026, 8, 28, 3, 0)),
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
            with self.subTest(field_name=field_name, value_type=type(value).__name__), self.assertRaises(ValueError):
                read_assignment_history(**kwargs)
        self.assertEqual(port.calls, [])

    def test_record_rejects_noncanonical_business_or_time_values(self) -> None:
        invalid_overrides = (
            {"assignment_record_id": "assignment"},
            {"assignment_record_id": ForgedUUID(str(ASSIGNMENT_A))},
            {"allocation_ratio": Decimal("NaN")},
            {"allocation_ratio": Decimal("1.00000")},
            {"allocation_ratio": Decimal("0.0000")},
            {"allocation_ratio": Decimal("1.0001")},
            {"effective_from": datetime(2026, 1, 1, tzinfo=timezone.utc)},
            {"effective_to": date(2026, 1, 1)},
            {"recorded_from": datetime(2026, 8, 20, 0, 0)},
            {"recorded_to": datetime(2026, 8, 21, 0, 0)},
            {"recorded_to": RECORDED_FROM},
        )
        for override in invalid_overrides:
            with self.subTest(override=override), self.assertRaises(ValueError):
                assignment_record(**override)


if __name__ == "__main__":
    unittest.main()
