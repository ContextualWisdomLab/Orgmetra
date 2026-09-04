"""Regression for open Position business intervals at Python's maximum date."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.position_history import (
    PositionHistoryIntegrityError,
    PositionHistoryRecord,
    read_position_history,
)

TENANT = UUID("0198a413-7000-7000-8000-000000000001")
POSITION = UUID("0198a413-7000-7000-8000-000000000010")
VERSION_A = UUID("0198a413-7000-7000-8000-000000000020")
VERSION_B = UUID("0198a413-7000-7000-8000-000000000021")
ORGANIZATION = UUID("0198a413-7000-7000-8000-000000000030")
JOB = UUID("0198a413-7000-7000-8000-000000000040")
KNOWN_AT = datetime(2026, 8, 30, 2, 0, tzinfo=timezone.utc)
RECORDED_FROM = datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc)


class ExtremeDatePort:
    """Return two exact Position rows whose open business intervals overlap."""

    def read_position_history(
        self,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        known_at: datetime,
    ) -> tuple[PositionHistoryRecord, ...]:
        return (
            PositionHistoryRecord(
                tenant_record_id=TENANT,
                position_record_id=POSITION,
                position_record_version_id=VERSION_A,
                organization_unit_id=ORGANIZATION,
                job_profile_id=JOB,
                position_status_code="active",
                effective_from=date(9999, 1, 1),
                effective_to=None,
                recorded_from=RECORDED_FROM,
                recorded_to=None,
            ),
            PositionHistoryRecord(
                tenant_record_id=TENANT,
                position_record_id=POSITION,
                position_record_version_id=VERSION_B,
                organization_unit_id=ORGANIZATION,
                job_profile_id=JOB,
                position_status_code="frozen",
                effective_from=date.max,
                effective_to=None,
                recorded_from=RECORDED_FROM,
                recorded_to=None,
            ),
        )


def test_open_interval_starting_at_date_max_still_overlaps_prior_open_truth() -> None:
    """Open-endedness must not be approximated with ``date.max`` as an exclusive end."""
    principal = AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:hr-operator",
        granted_scope_codes=frozenset({"orgmetra.people.position_history.read"}),
    )
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="position-history-extreme-date-v1",
        resource_kind="position_history",
        purpose_code="workforce_position_review",
        operation_code="read_record",
        required_scope_code="orgmetra.people.position_history.read",
        permitted_fields=frozenset({"position_status_code"}),
    )

    with pytest.raises(PositionHistoryIntegrityError, match="overlapping visible Position truth"):
        read_position_history(
            principal=principal,
            tenant_record_id=TENANT,
            position_record_id=POSITION,
            known_at=KNOWN_AT,
            purpose_code="workforce_position_review",
            requested_fields=frozenset({"position_status_code"}),
            policy=policy,
            read_port=ExtremeDatePort(),
        )
