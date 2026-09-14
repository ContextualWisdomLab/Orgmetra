"""Regression contracts for Employment-history persistence and schema integrity."""

from __future__ import annotations

from datetime import date, datetime, timezone
import unittest
from unittest.mock import patch
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields as real_authorize_resource_fields
from orgmetra_people_api.employment_history import (
    EmploymentHistoryIntegrityError,
    EmploymentHistoryRecord,
    read_employment_history,
)

TENANT = UUID("0198a412-7100-7000-8000-000000000001")
PERSON = UUID("0198a412-7100-7000-8000-000000000010")
EMPLOYMENT = UUID("0198a412-7100-7000-8000-000000000020")
VERSION = UUID("0198a412-7100-7000-8000-000000000030")
KNOWN_AT = datetime(2026, 8, 29, 0, 0, tzinfo=timezone.utc)


class FakeEmploymentHistoryPort:
    """Expose configured rows and capture whether protected persistence was read."""

    def __init__(self, records: tuple[object, ...]) -> None:
        self.records = records
        self.calls = 0

    def read_employment_history(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        known_at: datetime,
    ) -> tuple[object, ...]:
        """Return configured persistence evidence after recording the read."""
        del tenant_record_id, person_record_id, known_at
        self.calls += 1
        return self.records


class DynamicLookupTrapPort(FakeEmploymentHistoryPort):
    """Reject a fresh instance lookup of the repository capability."""

    def __getattribute__(self, name: str) -> object:
        if name == "read_employment_history":
            raise AttributeError("dynamic repository lookup is forbidden")
        return super().__getattribute__(name)


def _record() -> EmploymentHistoryRecord:
    """Build one canonical row before exercising low-level tuple forgery."""
    return EmploymentHistoryRecord(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=VERSION,
        employment_status_code="active",
        employment_concurrency_code="exclusive",
        effective_from=date(2025, 1, 1),
        effective_to=None,
        recorded_from=datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc),
        recorded_to=None,
    )


def _principal() -> AuthenticatedPrincipal:
    """Return a principal authorized for the Employment-history read scope."""
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:hr-operator",
        granted_scope_codes=frozenset({"orgmetra.people.employment_history.read"}),
    )


def _read(*, policy: PurposeBoundAccessPolicy, port: FakeEmploymentHistoryPort) -> None:
    """Execute the public service through the exact authorization boundary."""
    read_employment_history(
        principal=_principal(),
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        known_at=KNOWN_AT,
        purpose_code="employee_profile_review",
        requested_fields=policy.permitted_fields,
        policy=policy,
        read_port=port,
    )


class EmploymentHistoryReviewRegressionTests(unittest.TestCase):
    """Pin review findings to public fail-closed service behavior."""

    def test_repository_capability_is_bound_before_authorization(self) -> None:
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="capability-binding-v1",
            resource_kind="person_employment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.employment_history.read",
            permitted_fields=frozenset({"employment_status_code"}),
        )
        port = DynamicLookupTrapPort((_record(),))

        _read(policy=policy, port=port)

        self.assertEqual(port.calls, 1)

    def test_authorization_cannot_replace_the_bound_repository_capability(self) -> None:
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="capability-swap-v1",
            resource_kind="person_employment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.employment_history.read",
            permitted_fields=frozenset({"employment_status_code"}),
        )
        port = FakeEmploymentHistoryPort((_record(),))

        def substituted_read(
            self: FakeEmploymentHistoryPort,
            *,
            tenant_record_id: UUID,
            person_record_id: UUID,
            known_at: datetime,
        ) -> tuple[object, ...]:
            del self, tenant_record_id, person_record_id, known_at
            raise AssertionError("authorization replaced the repository capability")

        method_patcher = patch.object(
            FakeEmploymentHistoryPort,
            "read_employment_history",
            substituted_read,
        )

        def authorize_and_replace(**kwargs: object) -> object:
            decision = real_authorize_resource_fields(**kwargs)
            method_patcher.start()
            return decision

        try:
            with patch(
                "orgmetra_people_api.employment_history.authorize_resource_fields",
                side_effect=authorize_and_replace,
            ):
                _read(policy=policy, port=port)
        finally:
            method_patcher.stop()

        self.assertEqual(port.calls, 1)

    def test_low_level_tuple_shape_drift_is_rejected_before_field_access(self) -> None:
        canonical = _record()
        raw = tuple(canonical)
        malformed = (
            tuple.__new__(EmploymentHistoryRecord, raw[:-1]),
            tuple.__new__(EmploymentHistoryRecord, raw + ("unexpected",)),
        )
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="shape-v1",
            resource_kind="person_employment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.employment_history.read",
            permitted_fields=frozenset({"effective_from"}),
        )

        for forged in malformed:
            port = FakeEmploymentHistoryPort((forged,))
            with self.subTest(row_length=len(forged)), self.assertRaisesRegex(
                EmploymentHistoryIntegrityError,
                "invalid row shape",
            ):
                _read(policy=policy, port=port)
            self.assertEqual(port.calls, 1)

    def test_unsupported_authorized_field_is_rejected_even_when_history_is_empty(self) -> None:
        policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="schema-drift-v1",
            resource_kind="person_employment_history",
            purpose_code="employee_profile_review",
            operation_code="read_record",
            required_scope_code="orgmetra.people.employment_history.read",
            permitted_fields=frozenset({"future_sensitive_field"}),
        )
        port = FakeEmploymentHistoryPort(())

        with self.assertRaisesRegex(
            EmploymentHistoryIntegrityError,
            "unsupported Employment-history field",
        ):
            _read(policy=policy, port=port)
        self.assertEqual(port.calls, 0)


if __name__ == "__main__":
    unittest.main()
