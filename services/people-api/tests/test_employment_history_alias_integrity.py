"""Regression for persistence-held Employment-history row aliases.

A persistence adapter may retain a reference to a row after returning it.  Frozen
``dataclass`` syntax alone is not an integrity boundary because Python's
``object.__setattr__`` can still rewrite a frozen instance.  The People service
must therefore use a validated local snapshot rather than the persistence-owned
object when producing an authorized response.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch
from uuid import UUID

import orgmetra_people_api.employment_history as employment_history_module
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal

TENANT = UUID("0198a412-7100-7000-8000-000000000001")
PERSON = UUID("0198a412-7100-7000-8000-000000000010")
EMPLOYMENT = UUID("0198a412-7100-7000-8000-000000000020")
VERSION = UUID("0198a412-7100-7000-8000-000000000030")
KNOWN_AT = datetime(2026, 8, 29, 0, 0, tzinfo=timezone.utc)


class AliasHoldingPort:
    """Return a row while deliberately retaining the persistence-side alias."""

    def __init__(self, record: employment_history_module.EmploymentHistoryRecord) -> None:
        self.record = record

    def read_employment_history(
        self,
        *,
        tenant_record_id: UUID,
        person_record_id: UUID,
        known_at: datetime,
    ) -> tuple[employment_history_module.EmploymentHistoryRecord, ...]:
        """Return the retained row exactly as an in-process adapter could."""
        return (self.record,)


def test_persistence_alias_cannot_rewrite_authorized_value_after_validation() -> None:
    """A post-validation alias rewrite must not change the authorized response."""
    record = employment_history_module.EmploymentHistoryRecord(
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
    principal = AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:hr-operator",
        granted_scope_codes=frozenset({"orgmetra.people.employment_history.read"}),
    )
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="employee-profile-employment-history-v1",
        resource_kind="person_employment_history",
        purpose_code="employee_profile_review",
        operation_code="read_record",
        required_scope_code="orgmetra.people.employment_history.read",
        permitted_fields=frozenset({"employment_status_code"}),
    )

    original_overlap_check = employment_history_module._reject_effective_overlap

    def mutate_retained_alias_after_validation(
        records: list[employment_history_module.EmploymentHistoryRecord],
    ) -> None:
        """Deterministically model a concurrent persistence-side alias rewrite."""
        original_overlap_check(records)
        object.__setattr__(record, "employment_status_code", "leave")

    with patch.object(
        employment_history_module,
        "_reject_effective_overlap",
        side_effect=mutate_retained_alias_after_validation,
    ):
        view = employment_history_module.read_employment_history(
            principal=principal,
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            known_at=KNOWN_AT,
            purpose_code="employee_profile_review",
            requested_fields=frozenset({"employment_status_code"}),
            policy=policy,
            read_port=AliasHoldingPort(record),
        )

    assert view.entries[0].field_values == (("employment_status_code", "active"),)
