"""Regressions for persistence-held Employment-history row aliases.

A persistence adapter may retain a reference to a row after returning it. The
People boundary therefore uses structurally immutable tuple storage for accepted
rows and reconstructs each row through the validating constructor before use.
Low-level tuple construction remains untrusted and must fail closed when invalid.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch
from uuid import UUID

import pytest

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


def _principal() -> AuthenticatedPrincipal:
    """Return an authorized HR operator for Employment-history regressions."""
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:hr-operator",
        granted_scope_codes=frozenset({"orgmetra.people.employment_history.read"}),
    )


def _policy(*fields: str) -> PurposeBoundAccessPolicy:
    """Return one purpose-bound Employment-history read policy."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="employee-profile-employment-history-v1",
        resource_kind="person_employment_history",
        purpose_code="employee_profile_review",
        operation_code="read_record",
        required_scope_code="orgmetra.people.employment_history.read",
        permitted_fields=frozenset(fields),
    )


def _record() -> employment_history_module.EmploymentHistoryRecord:
    """Return one valid immutable Employment-history record."""
    return employment_history_module.EmploymentHistoryRecord(
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


def test_persistence_record_is_structurally_immutable_against_object_setattr() -> None:
    """A retained persistence alias must not support low-level in-place field rewriting."""
    record = _record()

    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(record, "employment_status_code", "leave")

    assert record.employment_status_code == "active"


def test_persistence_alias_cannot_rewrite_authorized_value_after_validation() -> None:
    """A post-validation alias rewrite attempt must fail before response serialization."""
    record = _record()
    policy = _policy("employment_status_code")
    original_overlap_check = employment_history_module._reject_effective_overlap

    def reject_retained_alias_rewrite(
        records: list[employment_history_module.EmploymentHistoryRecord],
    ) -> None:
        """Attempt the retained-alias attack after all row validation has completed."""
        original_overlap_check(records)
        with pytest.raises((AttributeError, TypeError)):
            object.__setattr__(record, "employment_status_code", "leave")

    with patch.object(
        employment_history_module,
        "_reject_effective_overlap",
        side_effect=reject_retained_alias_rewrite,
    ):
        view = employment_history_module.read_employment_history(
            principal=_principal(),
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            known_at=KNOWN_AT,
            purpose_code="employee_profile_review",
            requested_fields=policy.permitted_fields,
            policy=policy,
            read_port=AliasHoldingPort(record),
        )

    assert record.employment_status_code == "active"
    assert view.entries[0].field_values == (("employment_status_code", "active"),)


def test_low_level_invalid_tuple_reconstruction_fails_runtime_integrity() -> None:
    """Bypassing the public constructor must not make forged persistence evidence trusted."""
    record = _record()
    raw_values = list(record)
    raw_values[4] = "forged"
    forged = tuple.__new__(
        employment_history_module.EmploymentHistoryRecord,
        tuple(raw_values),
    )
    policy = _policy("employment_status_code", "employment_concurrency_code")

    assert type(forged) is employment_history_module.EmploymentHistoryRecord
    assert forged.employment_status_code == "forged"
    with pytest.raises(
        employment_history_module.EmploymentHistoryIntegrityError,
        match="runtime integrity",
    ):
        employment_history_module.read_employment_history(
            principal=_principal(),
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            known_at=KNOWN_AT,
            purpose_code="employee_profile_review",
            requested_fields=policy.permitted_fields,
            policy=policy,
            read_port=AliasHoldingPort(forged),
        )
