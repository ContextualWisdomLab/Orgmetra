from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from orgmetra_candidate_document_disposition import (
    CandidateDocumentDisposition,
    build_candidate_document_disposition,
)


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


def _verified_return_evidence() -> dict:
    hiring_decision = _kwargs()["hiring_decision_finalized_at"]
    return {
        "return_request_reference": "candidate_return_request:00000000-0000-4000-a000-000000000050",
        "return_requested_at": hiring_decision + timedelta(hours=1),
        "return_request_verified_at": hiring_decision + timedelta(hours=2),
    }


class _ExecutableTimezone(tzinfo):
    def __init__(self) -> None:
        self.utcoffset_calls = 0

    def utcoffset(self, dt):
        self.utcoffset_calls += 1
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)


class _TextSubtype(str):
    pass


def test_custom_timezone_is_rejected_before_callback_execution():
    caller_timezone = _ExecutableTimezone()

    with pytest.raises(ValueError, match="timestamp"):
        _build(
            hiring_decision_finalized_at=datetime(
                2026,
                9,
                11,
                12,
                0,
                0,
                tzinfo=caller_timezone,
            )
        )

    assert caller_timezone.utcoffset_calls == 0


def test_builtin_fixed_offset_timezone_is_detached_to_utc():
    fixed_offset = timezone(timedelta(hours=9))
    packet = _build(
        hiring_decision_finalized_at=datetime(
            2026,
            9,
            11,
            21,
            0,
            0,
            tzinfo=fixed_offset,
        )
    )

    assert packet.hiring_decision_finalized_at == datetime(
        2026,
        9,
        11,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )
    assert packet.hiring_decision_finalized_at.tzinfo is timezone.utc


def test_legal_hold_must_be_exact_boolean():
    with pytest.raises(ValueError, match="legal_hold"):
        _build(legal_hold=1)


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
    evidence = {}
    if state == "return_destroyed":
        hiring_decision = _kwargs()["hiring_decision_finalized_at"]
        evidence.update(_verified_return_evidence())
        evidence["return_dispatched_at"] = hiring_decision + timedelta(days=1)
        evidence["return_delivered_at"] = hiring_decision + timedelta(days=2)
    with pytest.raises(ValueError, match="legal hold"):
        _build(legal_hold=True, state=state, **evidence)


@pytest.mark.parametrize(
    "state",
    [
        "return_requested",
        "return_request_verified",
        "return_dispatched",
        "return_delivered",
        "return_destroyed",
    ],
)
def test_return_request_lifecycle_requires_request_receipt(state):
    with pytest.raises(ValueError, match="return_request_reference"):
        _build(state=state)


@pytest.mark.parametrize(
    "state",
    [
        "return_requested",
        "return_request_verified",
        "return_dispatched",
        "return_delivered",
        "return_destroyed",
    ],
)
def test_return_request_lifecycle_requires_request_timestamp(state):
    evidence = _verified_return_evidence()
    evidence["return_requested_at"] = None
    with pytest.raises(ValueError, match="return_requested_at"):
        _build(state=state, **evidence)


def test_return_request_cannot_precede_hiring_decision():
    hiring_decision = _kwargs()["hiring_decision_finalized_at"]
    evidence = _verified_return_evidence()
    evidence["return_requested_at"] = hiring_decision - timedelta(seconds=1)
    with pytest.raises(ValueError, match="return_requested_at"):
        _build(state="return_requested", **evidence)


def test_verified_and_later_return_states_require_verification_timestamp():
    evidence = _verified_return_evidence()
    evidence["return_request_verified_at"] = None
    with pytest.raises(ValueError, match="return_request_verified_at"):
        _build(state="return_request_verified", **evidence)


def test_return_verification_cannot_precede_request():
    hiring_decision = _kwargs()["hiring_decision_finalized_at"]
    evidence = _verified_return_evidence()
    evidence["return_requested_at"] = hiring_decision + timedelta(hours=2)
    evidence["return_request_verified_at"] = hiring_decision + timedelta(hours=1)
    with pytest.raises(ValueError, match="return_request_verified_at"):
        _build(state="return_request_verified", **evidence)


def test_dispatch_cannot_precede_verified_request():
    hiring_decision = _kwargs()["hiring_decision_finalized_at"]
    evidence = _verified_return_evidence()
    evidence["return_request_verified_at"] = hiring_decision + timedelta(days=2)
    with pytest.raises(ValueError, match="return_dispatched_at"):
        _build(
            state="return_dispatched",
            return_dispatched_at=hiring_decision + timedelta(days=1),
            **evidence,
        )


@pytest.mark.parametrize(
    "state",
    ["return_dispatched", "return_delivered", "return_destroyed"],
)
def test_return_dispatch_states_require_dispatch_timestamp(state):
    evidence = _verified_return_evidence()
    with pytest.raises(ValueError, match="return_dispatched_at"):
        _build(state=state, return_dispatched_at=None, **evidence)


@pytest.mark.parametrize("offset", [timedelta(0), -timedelta(seconds=1)])
def test_return_dispatch_timestamp_must_follow_hiring_decision(offset):
    hiring_decision = _kwargs()["hiring_decision_finalized_at"]
    evidence = _verified_return_evidence()
    with pytest.raises(ValueError, match="return_dispatched_at"):
        _build(
            state="return_dispatched",
            return_dispatched_at=hiring_decision + offset,
            **evidence,
        )


@pytest.mark.parametrize("state", ["return_delivered", "return_destroyed"])
def test_return_completion_states_require_delivery_receipt(state):
    hiring_decision = _kwargs()["hiring_decision_finalized_at"]
    evidence = _verified_return_evidence()
    with pytest.raises(ValueError, match="return_delivered_at"):
        _build(
            state=state,
            return_dispatched_at=hiring_decision + timedelta(days=1),
            return_delivered_at=None,
            **evidence,
        )


def test_return_delivery_cannot_precede_dispatch():
    hiring_decision = _kwargs()["hiring_decision_finalized_at"]
    evidence = _verified_return_evidence()
    dispatched_at = hiring_decision + timedelta(days=2)
    with pytest.raises(ValueError, match="return_delivered_at"):
        _build(
            state="return_delivered",
            return_dispatched_at=dispatched_at,
            return_delivered_at=dispatched_at - timedelta(seconds=1),
            **evidence,
        )


def test_return_destroyed_accepts_verified_request_and_delivery_receipt():
    hiring_decision = _kwargs()["hiring_decision_finalized_at"]
    evidence = _verified_return_evidence()
    dispatched_at = hiring_decision + timedelta(days=1)
    delivered_at = dispatched_at + timedelta(days=1)
    packet = _build(
        state="return_destroyed",
        return_dispatched_at=dispatched_at,
        return_delivered_at=delivered_at,
        **evidence,
    )

    assert packet.return_request_reference == evidence["return_request_reference"]
    assert packet.return_request_verified_at == evidence["return_request_verified_at"]
    assert packet.return_dispatched_at == dispatched_at
    assert packet.return_delivered_at == delivered_at


def test_packet_state_cannot_be_rewritten_after_validation():
    packet = _build(legal_hold=True)

    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(packet, "state", "destroyed")

    assert packet.state == "created"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("tenant_record_id", "00000000-0000-4000-a000-000000000001"),
        ("document_reference", "document:00000000-0000-4000-a000-000000000020"),
        ("retention_policy_version", "v2026_09"),
        (
            "retention_policy_digest",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ),
    ],
)
def test_trust_bearing_text_rejects_string_subtypes(field_name, value):
    with pytest.raises(ValueError, match=field_name):
        _build(**{field_name: _TextSubtype(value)})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("review_state", "requires_human_disposition_review"),
        (
            "next_action",
            "Within tenant_record_id, verify the disposition event against the authoritative "
            "talent_acquisition or people_core record; confirm no conflicting legal hold, "
            "then request artifact lifecycle disposition from document_records.",
        ),
    ],
)
def test_governed_constant_text_rejects_string_subtypes(field_name, value):
    kwargs = _kwargs()
    kwargs[field_name] = _TextSubtype(value)

    with pytest.raises(ValueError, match=field_name):
        CandidateDocumentDisposition(**kwargs)
