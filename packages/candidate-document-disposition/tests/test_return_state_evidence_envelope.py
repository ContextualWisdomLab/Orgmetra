from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_candidate_document_disposition import build_candidate_document_disposition


_HIRING_DECISION = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
_REQUESTED_AT = _HIRING_DECISION + timedelta(hours=1)
_CLAIM_WINDOW_END = _HIRING_DECISION + timedelta(days=30)
_VERIFIED_AT = _HIRING_DECISION + timedelta(hours=2)
_DUE_AT = _VERIFIED_AT + timedelta(days=14)
_DISPATCHED_AT = _HIRING_DECISION + timedelta(days=1)
_DELIVERED_AT = _HIRING_DECISION + timedelta(days=2)
_REQUEST_REFERENCE = "candidate_return_request:00000000-0000-4000-a000-000000000050"


def _build(state: str, **overrides):
    kwargs = {
        "tenant_record_id": "00000000-0000-4000-a000-000000000001",
        "disposition_reference": "candidate_document_disposition:00000000-0000-4000-a000-000000000010",
        "document_reference": "document:00000000-0000-4000-a000-000000000020",
        "candidate_reference": "candidate_profile:00000000-0000-4000-a000-000000000030",
        "hiring_decision_finalized_at": _HIRING_DECISION,
        "return_eligibility": "eligible",
        "state": state,
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
    kwargs.update(overrides)
    return build_candidate_document_disposition(**kwargs)


@pytest.mark.parametrize("state", ["created", "return_claim_window_open"])
def test_pre_request_state_rejects_return_request_evidence(state):
    extra = {}
    if state == "return_claim_window_open":
        extra["claim_window_end"] = _HIRING_DECISION + timedelta(days=30)

    with pytest.raises(ValueError, match="return request evidence"):
        _build(
            state,
            return_request_reference=_REQUEST_REFERENCE,
            return_requested_at=_REQUESTED_AT,
            **extra,
        )


@pytest.mark.parametrize("state", ["created", "return_claim_window_open"])
@pytest.mark.parametrize(
    "future_evidence",
    [
        {"return_dispatched_at": _DISPATCHED_AT},
        {
            "return_dispatched_at": _DISPATCHED_AT,
            "return_delivered_at": _DELIVERED_AT,
        },
    ],
)
def test_pre_request_state_rejects_dispatch_or_delivery_evidence(state, future_evidence):
    extra = dict(future_evidence)
    if state == "return_claim_window_open":
        extra["claim_window_end"] = _HIRING_DECISION + timedelta(days=30)

    with pytest.raises(ValueError, match="return request evidence"):
        _build(state, **extra)


def test_return_requested_state_rejects_verification_evidence():
    with pytest.raises(ValueError, match="verification evidence"):
        _build(
            "return_requested",
            claim_window_end=_CLAIM_WINDOW_END,
            return_request_reference=_REQUEST_REFERENCE,
            return_requested_at=_REQUESTED_AT,
            return_request_verified_at=_VERIFIED_AT,
            return_due_at=_DUE_AT,
        )


def test_return_requested_state_rejects_dispatch_evidence():
    with pytest.raises(ValueError, match="verification evidence"):
        _build(
            "return_requested",
            claim_window_end=_CLAIM_WINDOW_END,
            return_request_reference=_REQUEST_REFERENCE,
            return_requested_at=_REQUESTED_AT,
            return_dispatched_at=_DISPATCHED_AT,
        )


def test_return_requested_state_rejects_delivery_evidence():
    with pytest.raises(ValueError, match="verification evidence"):
        _build(
            "return_requested",
            claim_window_end=_CLAIM_WINDOW_END,
            return_request_reference=_REQUEST_REFERENCE,
            return_requested_at=_REQUESTED_AT,
            return_dispatched_at=_DISPATCHED_AT,
            return_delivered_at=_DELIVERED_AT,
        )


def test_return_verified_state_rejects_dispatch_evidence():
    with pytest.raises(ValueError, match="dispatch evidence"):
        _build(
            "return_request_verified",
            claim_window_end=_CLAIM_WINDOW_END,
            return_request_reference=_REQUEST_REFERENCE,
            return_requested_at=_REQUESTED_AT,
            return_request_verified_at=_VERIFIED_AT,
            return_due_at=_DUE_AT,
            return_dispatched_at=_DISPATCHED_AT,
        )


def test_return_dispatched_state_rejects_delivery_evidence():
    with pytest.raises(ValueError, match="delivery evidence"):
        _build(
            "return_dispatched",
            claim_window_end=_CLAIM_WINDOW_END,
            return_request_reference=_REQUEST_REFERENCE,
            return_requested_at=_REQUESTED_AT,
            return_request_verified_at=_VERIFIED_AT,
            return_due_at=_DUE_AT,
            return_dispatched_at=_DISPATCHED_AT,
            return_delivered_at=_DELIVERED_AT,
        )


def test_eligible_return_request_requires_claim_window_evidence():
    with pytest.raises(ValueError, match="claim_window_end"):
        _build(
            "return_requested",
            return_request_reference=_REQUEST_REFERENCE,
            return_requested_at=_REQUESTED_AT,
        )


def test_return_verification_timestamp_requires_request_timestamp():
    with pytest.raises(ValueError, match="requires return_requested_at"):
        _build(
            "talent_pool_retained",
            return_request_verified_at=_VERIFIED_AT,
        )


def test_return_due_timestamp_requires_verification_timestamp():
    with pytest.raises(ValueError, match="requires return_request_verified_at"):
        _build(
            "talent_pool_retained",
            return_due_at=_DUE_AT,
        )


def test_return_delivery_timestamp_requires_dispatch_timestamp():
    with pytest.raises(ValueError, match="requires return_dispatched_at"):
        _build(
            "talent_pool_retained",
            return_delivered_at=_DELIVERED_AT,
        )
