"""Regression coverage for assignment-history timezone-provider integrity."""

from __future__ import annotations

from datetime import datetime, timedelta, tzinfo
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.assignment_history import AssignmentHistoryRecord, read_assignment_history

TENANT = UUID("0198a412-7000-7000-8000-000000000001")
PERSON = UUID("0198a412-7000-7000-8000-000000000010")
EMPLOYMENT = UUID("0198a412-7000-7000-8000-000000000020")
POSITION = UUID("0198a412-7000-7000-8000-000000000030")
ASSIGNMENT = UUID("0198a412-7000-7000-8000-000000000040")


class CallerControlledUtc(tzinfo):
    """Model a caller-defined timezone provider that currently reports UTC."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        """Return zero offset while retaining caller-controlled behavior."""
        del dt
        return timedelta(0)

    def dst(self, dt: datetime | None) -> timedelta | None:
        """Return no daylight-saving adjustment."""
        del dt
        return None

    def tzname(self, dt: datetime | None) -> str:
        """Present the forged provider as UTC-like text."""
        del dt
        return "UTC"


class EmptyPort:
    """Capture whether protected persistence was reached."""

    def __init__(self) -> None:
        """Start with no protected reads."""
        self.calls = 0

    def read_assignment_history(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        known_at: datetime,
    ) -> tuple[AssignmentHistoryRecord, ...]:
        """Record protected access and return no assignment rows."""
        del tenant_record_id, person_record_id, known_at
        self.calls += 1
        return ()


class AssignmentHistoryTimezoneIntegrityTests(unittest.TestCase):
    """Prove trust-bearing instants cannot retain caller-controlled tzinfo behavior."""

    def setUp(self) -> None:
        """Build the minimum authorized read context."""
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
            permitted_fields=frozenset({"effective_from"}),
        )

    def test_caller_controlled_known_at_fails_before_protected_retrieval(self) -> None:
        """Reject a UTC-looking custom tzinfo before any repository call."""
        port = EmptyPort()
        known_at = datetime(2026, 8, 28, 3, 0, tzinfo=CallerControlledUtc())

        with self.assertRaisesRegex(ValueError, "known_at must be a timezone-aware UTC datetime"):
            read_assignment_history(
                principal=self.principal,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                known_at=known_at,
                purpose_code="employee_profile_review",
                requested_fields=frozenset({"effective_from"}),
                policy=self.policy,
                read_port=port,
            )

        self.assertEqual(port.calls, 0)

    def test_persisted_record_rejects_caller_controlled_recorded_timezone(self) -> None:
        """Reject UTC-looking custom tzinfo before it becomes persisted read evidence."""
        recorded_from = datetime(2026, 8, 20, 0, 0, tzinfo=CallerControlledUtc())

        with self.assertRaisesRegex(ValueError, "recorded_from must be a timezone-aware UTC datetime"):
            AssignmentHistoryRecord(
                tenant_record_id=TENANT,
                assignment_record_id=ASSIGNMENT,
                employment_record_id=EMPLOYMENT,
                person_record_id=PERSON,
                position_record_id=POSITION,
                allocation_ratio=Decimal("1.0000"),
                effective_from=datetime(2026, 1, 1).date(),
                effective_to=None,
                recorded_from=recorded_from,
                recorded_to=None,
            )


if __name__ == "__main__":
    unittest.main()
