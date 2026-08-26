"""Static contract regressions for TEPP retry-comparison helper annotations."""

from typing import get_type_hints

from orgmetra_tepp_adapter import TeppAnalysisRequestPacket


def test_retry_comparison_accepts_arbitrary_runtime_objects_in_its_type_contract() -> None:
    """Keep annotations aligned with the exact-type fail-closed runtime boundary."""
    retry_hints = get_type_hints(TeppAnalysisRequestPacket.is_idempotent_retry_of)
    conflict_hints = get_type_hints(TeppAnalysisRequestPacket.idempotency_conflicts_with)

    assert retry_hints["other"] is object
    assert conflict_hints["other"] is object
