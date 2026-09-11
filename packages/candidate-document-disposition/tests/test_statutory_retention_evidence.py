from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_candidate_document_disposition import build_candidate_document_disposition


def _build(**overrides):
    hiring_decision = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    kwargs = {
        "tenant_record_id": "00000000-0000-4000-a000-000000000001",
        "disposition_reference": "candidate_document_disposition:00000000-0000-4000-a000-000000000010",
        "document_reference": "document:00000000-0000-4000-a000-000000000020",
        "candidate_reference": "candidate_profile:00000000-0000-4000-a000-000000000030",
        "hiring_decision_finalized_at": hiring_decision,
        "return_eligibility": "eligible",
        "state": "statutory_retained",
        "retention_policy_version": "v2026_09",
        "retention_policy_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "retention_anchor_event": "statutory_period_start",
        "retain_until": None,
        "legal_hold": False,
        "purpose_code": "candidate_document_disposition",
        "reason_code": "statutory_retention_expiry",
        "evidence_version": 1,
        "actor_reference": "actor:00000000-0000-4000-a000-000000000040",
    }
    kwargs.update(overrides)
    return build_candidate_document_disposition(**kwargs)


@pytest.mark.parametrize(
    "state",
    ["statutory_retained", "statutory_retention_expired_destroyed"],
)
def test_statutory_retention_states_require_policy_deadline(state):
    with pytest.raises(ValueError, match="statutory_retain_until"):
        _build(state=state, statutory_retain_until=None)


def test_statutory_retention_state_keeps_explicit_policy_deadline():
    deadline = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)

    packet = _build(statutory_retain_until=deadline)

    assert packet.statutory_retain_until == deadline
