from datetime import datetime, timezone

import pytest

from orgmetra_candidate_document_disposition import build_candidate_document_disposition


def _build(*, legal_hold: bool):
    return build_candidate_document_disposition(
        tenant_record_id="00000000-0000-4000-a000-000000000001",
        disposition_reference="candidate_document_disposition:00000000-0000-4000-a000-000000000010",
        document_reference="document:00000000-0000-4000-a000-000000000020",
        candidate_reference="candidate_profile:00000000-0000-4000-a000-000000000030",
        hiring_decision_finalized_at=datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc),
        return_eligibility="eligible",
        state="legal_hold_suspended",
        retention_policy_version="v2026_09",
        retention_policy_digest="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        retention_anchor_event="hiring_decision_finalized",
        retain_until=datetime(2027, 9, 11, 12, 0, 0, tzinfo=timezone.utc),
        legal_hold=legal_hold,
        purpose_code="candidate_document_disposition",
        reason_code="legal_hold_release",
        evidence_version=1,
        actor_reference="actor:00000000-0000-4000-a000-000000000040",
    )


def test_legal_hold_suspended_rejects_inactive_hold():
    with pytest.raises(ValueError, match="legal_hold_suspended"):
        _build(legal_hold=False)


def test_legal_hold_suspended_accepts_active_hold():
    packet = _build(legal_hold=True)
    assert packet.state == "legal_hold_suspended"
    assert packet.legal_hold is True
