from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_candidate_document_disposition import build_candidate_document_disposition


def _kwargs() -> dict:
    return {
        "tenant_record_id": "00000000-0000-4000-a000-000000000001",
        "disposition_reference": "candidate_document_disposition:00000000-0000-4000-a000-000000000010",
        "document_reference": "document:00000000-0000-4000-a000-000000000020",
        "candidate_reference": "candidate_profile:00000000-0000-4000-a000-000000000030",
        "hiring_decision_finalized_at": datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc),
        "return_eligibility": "eligible",
        "state": "created",
        "retention_policy_version": "v2026_09",
        "retention_policy_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "retention_anchor_event": "hiring_decision_finalized",
        "retain_until": datetime(2027, 9, 11, 12, 0, 0, tzinfo=timezone.utc),
        "legal_hold": False,
        "purpose_code": "candidate_document_disposition",
        "reason_code": "non_selected_applicant_return",
        "evidence_version": 1,
        "actor_reference": "actor:00000000-0000-4000-a000-000000000040",
    }


def _build(**overrides):
    kwargs = _kwargs()
    kwargs.update(overrides)
    return build_candidate_document_disposition(**kwargs)


@pytest.mark.parametrize("offset", [timedelta(0), -timedelta(seconds=1)])
def test_claim_window_must_follow_hiring_decision(offset):
    hiring_decision = _kwargs()["hiring_decision_finalized_at"]
    with pytest.raises(ValueError, match="claim_window_end"):
        _build(claim_window_end=hiring_decision + offset)


@pytest.mark.parametrize(
    "state",
    ["return_destroyed", "statutory_retention_expired_destroyed", "destroyed"],
)
def test_legal_hold_rejects_every_destruction_state(state):
    with pytest.raises(ValueError, match="legal hold"):
        _build(legal_hold=True, state=state)


def test_packet_state_cannot_be_rewritten_after_validation():
    packet = _build(legal_hold=True)

    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(packet, "state", "destroyed")

    assert packet.state == "created"
