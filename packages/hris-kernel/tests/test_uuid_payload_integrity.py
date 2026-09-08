"""Regressions for nested exact-UUID payload integrity in Job Analysis evidence."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_hris_kernel.job_analysis import TaskKSAOLink


class _ExecutableUUIDPayload:
    """Trip if sentinel validation executes caller-controlled UUID payload behavior."""

    def __init__(self) -> None:
        self.equality_calls = 0

    def __eq__(self, other: object) -> bool:
        del other
        self.equality_calls += 1
        raise AssertionError("caller-controlled UUID payload equality executed")


def _forged_exact_uuid() -> tuple[UUID, _ExecutableUUIDPayload]:
    """Return an exact UUID whose internal scalar was replaced without subclassing."""
    value = UUID("00000000-0000-4000-8000-000000000123")
    payload = _ExecutableUUIDPayload()
    object.__setattr__(value, "int", payload)
    return value, payload


def test_job_analysis_rejects_exact_uuid_with_executable_internal_payload_without_calling_it() -> None:
    """Outer exact type cannot authorize executable storage hidden in UUID.int."""
    forged, payload = _forged_exact_uuid()

    with pytest.raises(ValueError, match="task_record_id must contain a built-in UUID integer"):
        TaskKSAOLink(
            task_record_id=forged,
            ksao_record_id=UUID("00000000-0000-4000-8000-000000000124"),
            relationship_strength=5,
            essential_for_task=True,
        )

    assert payload.equality_calls == 0


@pytest.mark.parametrize("identity", [-1, 1 << 128])
def test_job_analysis_rejects_exact_uuid_with_out_of_range_internal_integer(identity: int) -> None:
    """A forged exact UUID cannot carry an integer outside the canonical 128-bit range."""
    forged = UUID("00000000-0000-4000-8000-000000000123")
    object.__setattr__(forged, "int", identity)

    with pytest.raises(ValueError, match="task_record_id must contain a 128-bit UUID integer"):
        TaskKSAOLink(
            task_record_id=forged,
            ksao_record_id=UUID("00000000-0000-4000-8000-000000000124"),
            relationship_strength=5,
            essential_for_task=True,
        )


def test_job_analysis_detaches_accepted_uuid_from_caller_alias() -> None:
    """Frozen job-analysis evidence owns its identity rather than retaining caller UUID storage."""
    task_id = UUID("00000000-0000-4000-8000-000000000123")
    link = TaskKSAOLink(
        task_record_id=task_id,
        ksao_record_id=UUID("00000000-0000-4000-8000-000000000124"),
        relationship_strength=5,
        essential_for_task=True,
    )
    expected = UUID(int=task_id.int)

    object.__setattr__(task_id, "int", UUID("00000000-0000-4000-8000-000000000999").int)

    assert link.task_record_id == expected
    assert link.task_record_id is not task_id
