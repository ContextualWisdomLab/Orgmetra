"""Runtime-integrity regressions for detached People mutation snapshots."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_people_api import mutations

TENANT = UUID("0198a412-b500-7000-8000-000000000001")
EMPLOYMENT = UUID("0198a412-b500-7000-8000-000000000030")
POSITION = UUID("0198a412-b500-7000-8000-000000000040")
ASSIGNMENT = UUID("0198a412-b500-7000-8000-000000000070")


def test_position_and_assignment_receipts_reject_non_string_replay_digest() -> None:
    """Receipt constructors must reject executable or otherwise non-string replay evidence."""
    with pytest.raises(ValueError, match="replay_command_digest must be a string"):
        mutations.PositionMutationResult(position_record_id=POSITION, replay_command_digest=object())
    with pytest.raises(ValueError, match="replay_command_digest must be a string"):
        mutations.AssignmentMutationResult(assignment_record_id=ASSIGNMENT, replay_command_digest=object())


def test_authorization_snapshot_rejects_noncanonical_runtime_type() -> None:
    """Persistence authorization snapshots must accept only the canonical decision runtime type."""
    with pytest.raises(TypeError, match="authorization must be an AuthorizationDecision"):
        mutations._snapshot_authorization(object())


def test_idempotency_identity_rejects_empty_command_route() -> None:
    """An empty route must never collapse otherwise valid tenant/idempotency identities."""
    with pytest.raises(ValueError, match="command_route_value must be a non-empty string"):
        mutations.idempotency_record_id(
            tenant_record_id=TENANT,
            command_route_value="",
            idempotency_key="snapshot-runtime-integrity-1",
        )


def test_result_snapshots_reject_post_construction_replay_digest_rewrite() -> None:
    """A port must not rewrite replay evidence after a valid receipt has been constructed."""
    cases = (
        (
            mutations._snapshot_employment_result,
            mutations.EmploymentMutationResult(employment_record_id=EMPLOYMENT),
        ),
        (
            mutations._snapshot_position_result,
            mutations.PositionMutationResult(position_record_id=POSITION),
        ),
        (
            mutations._snapshot_assignment_result,
            mutations.AssignmentMutationResult(assignment_record_id=ASSIGNMENT),
        ),
    )
    for snapshot, result in cases:
        object.__setattr__(result, "replay_command_digest", object())
        with pytest.raises(ValueError, match="replay_command_digest must be a string"):
            snapshot(result)
