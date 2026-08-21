"""Regression coverage for high-impact offer-review evidence versioning."""

from dataclasses import replace
from datetime import datetime, timezone
import json

import pytest

from orgmetra_offer_approval import build_offer_approval_packet


def _build(evidence_version: object = 1):
    """Build a valid offer-review packet while varying only its evidence version."""
    return build_offer_approval_packet(
        tenant_record_id="11111111-1111-4111-8111-111111111111",
        offer_approval_reference="offer_approval:10000000-0000-4000-8000-000000000001",
        candidate_profile_reference="candidate_profile:10000000-0000-4000-8000-000000000002",
        requisition_reference="requisition:10000000-0000-4000-8000-000000000003",
        job_profile_reference="job_profile:10000000-0000-4000-8000-000000000004",
        position_record_reference="position_record:10000000-0000-4000-8000-000000000005",
        selection_decision_reference="selection_decision:10000000-0000-4000-8000-000000000006",
        selection_decision_digest="a" * 64,
        compensation_package_reference="compensation_package:10000000-0000-4000-8000-000000000007",
        compensation_package_digest="b" * 64,
        offer_terms_reference="offer_terms:10000000-0000-4000-8000-000000000008",
        offer_terms_digest="c" * 64,
        requester_reference="actor:10000000-0000-4000-8000-000000000009",
        approver_reference="actor:10000000-0000-4000-8000-00000000000a",
        purpose_code="offer_approval_review",
        reason_code="selected_candidate_offer_review",
        generated_at=datetime(2026, 8, 19, 5, 10, 0, 123456, tzinfo=timezone.utc),
        evidence_version=evidence_version,
    )


def test_evidence_version_is_bound_to_offer_correlation_evidence() -> None:
    """Changing evidence version must change canonical JSON and its correlation digest."""
    first = _build(1)
    second = _build(2)

    assert first.evidence_version == 1
    assert json.loads(first.canonical_json())["evidence_version"] == 1
    assert second.evidence_version == 2
    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()


@pytest.mark.parametrize("evidence_version", [0, -1, True, "1", 2_147_483_648])
def test_evidence_version_fails_closed(evidence_version: object) -> None:
    """Reject non-integer, non-positive, or overflow evidence versions."""
    with pytest.raises(ValueError, match="evidence_version"):
        _build(evidence_version)


def test_replace_cannot_bypass_evidence_version_validation() -> None:
    """Mutation-by-copy must revalidate the immutable evidence version invariant."""
    with pytest.raises(ValueError, match="evidence_version"):
        replace(_build(), evidence_version=False)
