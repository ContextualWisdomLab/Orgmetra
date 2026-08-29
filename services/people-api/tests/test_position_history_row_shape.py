"""Regression for malformed low-level Position-history row reconstruction."""

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
VERSION = UUID("0198a413-7000-7000-8000-000000000020")
ORGANIZATION = UUID("0198a413-7000-7000-8000-000000000030")
JOB = UUID("0198a413-7000-7000-8000-000000000040")
KNOWN_AT = datetime(2026, 8, 30, 2, 0, tzinfo=timezone.utc)


class ShortRowPort:
    """Return a malformed Position row reconstructed below the public constructor."""

    def __init__(self, row: PositionHistoryRecord) -> None:
        self.row = row

    def read_position_history(
        self,
        *,
        tenant_record_id: UUID,
        position_record_id: UUID,
        known_at: datetime,
    ) -> tuple[PositionHistoryRecord, ...]:
        return (self.row,)


def test_short_low_level_row_fails_closed_at_runtime_boundary() -> None:
    """A tuple-level reconstruction missing a field must never reach serialization."""
    valid = PositionHistoryRecord(
        tenant_record_id=TENANT,
        position_record_id=POSITION,
        position_record_version_id=VERSION,
        organization_unit_id=ORGANIZATION,
        job_profile_id=JOB,
        position_status_code="active",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        recorded_from=datetime(2026, 8, 20, 0, 0, tzinfo=timezone.utc),
        recorded_to=None,
    )
    short_row = tuple.__new__(PositionHistoryRecord, tuple(valid)[:-1])
    principal = AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:hr-operator",
        granted_scope_codes=frozenset({"orgmetra.people.position_history.read"}),
    )
    policy = PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="position-history-v1",
        resource_kind="position_history",
        purpose_code="workforce_position_review",
        operation_code="read_record",
        required_scope_code="orgmetra.people.position_history.read",
        permitted_fields=frozenset({"position_status_code"}),
    )

    with pytest.raises(PositionHistoryIntegrityError, match="runtime integrity"):
        read_position_history(
            principal=principal,
            tenant_record_id=TENANT,
            position_record_id=POSITION,
            known_at=KNOWN_AT,
            purpose_code="workforce_position_review",
            requested_fields=frozenset({"position_status_code"}),
            policy=policy,
            read_port=ShortRowPort(short_row),
        )
