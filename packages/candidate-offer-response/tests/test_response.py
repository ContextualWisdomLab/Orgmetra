"""Executable contract for candidate-originated offer response evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
import json
from uuid import UUID

import pytest

from orgmetra_candidate_offer_response.response import (
    CandidateOfferResponsePacket,
    build_candidate_offer_response,
)

TENANT_ID = "018f6e2a-4f7c-7a1b-9c20-1f3a7d8e5b60"
OFFER_RESPONSE = "candidate_offer_response:6ba7b810-9dad-4b11-80b4-00c04fd430c8"
CANDIDATE = "candidate_profile:6ba7b811-9dad-4b11-80b4-00c04fd430c8"
OFFER_APPROVAL = "offer_approval:6ba7b812-9dad-4b11-80b4-00c04fd430c8"
OFFER_TERMS = "offer_terms:6ba7b813-9dad-4b11-80b4-00c04fd430c8"
CANDIDATE_ACTOR = "candidate:6ba7b814-9dad-4b11-80b4-00c04fd430c8"
IDENTITY_RESOLUTION = "identity_resolution:6ba7b815-9dad-4b11-80b4-00c04fd430c8"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
RESPONDED_AT = datetime(2026, 8, 22, 9, 30, 15, 123456, tzinfo=timezone.utc)
RECORDED_AT = datetime(2026, 8, 22, 9, 30, 16, 123456, tzinfo=timezone.utc)


def _kwargs() -> dict[str, object]:
    """Return one valid, value-minimized accepted-offer evidence fixture."""
    return {
        "tenant_record_id": TENANT_ID,
        "offer_response_reference": OFFER_RESPONSE,
        "candidate_profile_reference": CANDIDATE,
        "offer_approval_reference": OFFER_APPROVAL,
        "offer_approval_digest": DIGEST_A,
        "offer_terms_reference": OFFER_TERMS,
        "offer_terms_digest": DIGEST_B,
        "candidate_actor_reference": CANDIDATE_ACTOR,
        "identity_resolution_reference": IDENTITY_RESOLUTION,
        "identity_resolution_digest": DIGEST_C,
        "response_code": "offer_accepted",
        "responded_at": RESPONDED_AT,
        "recorded_at": RECORDED_AT,
        "evidence_version": 1,
    }


def _build(**overrides: object) -> CandidateOfferResponsePacket:
    """Build a packet while allowing one test to replace selected inputs."""
    values = _kwargs()
    values.update(overrides)
    return build_candidate_offer_response(**values)  # type: ignore[arg-type]


def test_candidate_acceptance_is_value_minimized_and_non_authorizing() -> None:
    packet = _build()
    document = json.loads(packet.canonical_json())

    assert document["response_code"] == "offer_accepted"
    assert document["candidate_confirmation_required"] is True
    assert document["scope_verification_state"] == "requires_authoritative_resolution"
    assert document["employment_effect"] == "not_authorized_to_hire"
    assert document["decision_authority"] == "candidate_response_only"
    assert document["contains_candidate_pii"] is False
    assert document["contains_compensation_values"] is False
    assert document["contains_free_form_reason"] is False
    assert document["responded_at"] == "2026-08-22T09:30:15.123456Z"
    assert document["recorded_at"] == "2026-08-22T09:30:16.123456Z"
    assert "re-resolve" in document["next_action"]
    assert "offer" in document["next_action"]
    assert "hire" in document["next_action"]
    assert len(packet.sha256_digest()) == 64
    assert packet.sha256_digest() == packet.sha256_digest()
    assert repr(packet) == "CandidateOfferResponsePacket(<redacted>)"


def test_candidate_decline_uses_the_same_candidate_originated_boundary() -> None:
    packet = _build(response_code="offer_declined")
    assert json.loads(packet.canonical_json())["response_code"] == "offer_declined"
    assert packet.employment_effect == "not_authorized_to_hire"


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("tenant_record_id", "not-a-uuid", "tenant_record_id"),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000", "operational UUID"),
        ("tenant_record_id", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF", "canonical"),
        ("offer_response_reference", "candidate_offer_response:not-uuid", "offer_response_reference"),
        ("candidate_profile_reference", "candidate_profile:not-uuid", "candidate_profile_reference"),
        ("offer_approval_reference", "offer_approval:not-uuid", "offer_approval_reference"),
        ("offer_terms_reference", "offer_terms:not-uuid", "offer_terms_reference"),
        ("candidate_actor_reference", "staff:6ba7b814-9dad-4b11-80b4-00c04fd430c8", "candidate_actor_reference"),
        ("identity_resolution_reference", "identity_resolution:not-uuid", "identity_resolution_reference"),
        ("offer_approval_digest", "A" * 64, "offer_approval_digest"),
        ("offer_terms_digest", "b" * 63, "offer_terms_digest"),
        ("identity_resolution_digest", "not-a-digest", "identity_resolution_digest"),
        ("response_code", "offer_pending", "response_code"),
        ("evidence_version", 0, "evidence_version"),
        ("evidence_version", 2_147_483_648, "evidence_version"),
    ],
)
def test_invalid_trust_evidence_fails_closed(field_name: str, value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _build(**{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("offer_response_reference", "offer_response:6ba7b810-9dad-4b11-80b4-00c04fd430c8"),
        ("candidate_profile_reference", "candidate:6ba7b811-9dad-4b11-80b4-00c04fd430c8"),
        ("offer_approval_reference", "offer_terms:6ba7b812-9dad-4b11-80b4-00c04fd430c8"),
        ("offer_terms_reference", "offer_approval:6ba7b813-9dad-4b11-80b4-00c04fd430c8"),
        ("identity_resolution_reference", "candidate:6ba7b815-9dad-4b11-80b4-00c04fd430c8"),
    ],
)
def test_reference_namespaces_are_not_interchangeable(field_name: str, value: str) -> None:
    with pytest.raises(ValueError):
        _build(**{field_name: value})


def test_packet_owned_references_require_uuid4_suffixes() -> None:
    version_one = "candidate_offer_response:6ba7b810-9dad-1b11-80b4-00c04fd430c8"
    with pytest.raises(ValueError, match="offer_response_reference"):
        _build(offer_response_reference=version_one)


class _ForgedText(str):
    def __eq__(self, other: object) -> bool:
        return True

    def __hash__(self) -> int:
        return hash("offer_accepted")

    def __len__(self) -> int:
        return 1


class _ForgedInt(int):
    def __lt__(self, other: object) -> bool:
        return False

    def __le__(self, other: object) -> bool:
        return True

    def __gt__(self, other: object) -> bool:
        return False

    def __ge__(self, other: object) -> bool:
        return True


class _ForgedDatetime(datetime):
    pass


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("tenant_record_id", _ForgedText(TENANT_ID)),
        ("offer_response_reference", _ForgedText(OFFER_RESPONSE)),
        ("candidate_profile_reference", _ForgedText(CANDIDATE)),
        ("offer_approval_reference", _ForgedText(OFFER_APPROVAL)),
        ("offer_approval_digest", _ForgedText(DIGEST_A)),
        ("offer_terms_reference", _ForgedText(OFFER_TERMS)),
        ("offer_terms_digest", _ForgedText(DIGEST_B)),
        ("candidate_actor_reference", _ForgedText(CANDIDATE_ACTOR)),
        ("identity_resolution_reference", _ForgedText(IDENTITY_RESOLUTION)),
        ("identity_resolution_digest", _ForgedText(DIGEST_C)),
        ("response_code", _ForgedText("shadow_rejection")),
        ("evidence_version", _ForgedInt(0)),
        ("responded_at", _ForgedDatetime(2026, 8, 22, tzinfo=timezone.utc)),
        ("recorded_at", _ForgedDatetime(2026, 8, 22, tzinfo=timezone.utc)),
    ],
)
def test_caller_controlled_runtime_subclasses_are_rejected(field_name: str, value: object) -> None:
    with pytest.raises(ValueError):
        _build(**{field_name: value})


def test_recorded_time_cannot_precede_candidate_response() -> None:
    with pytest.raises(ValueError, match="recorded_at must not precede responded_at"):
        _build(recorded_at=RESPONDED_AT - timedelta(microseconds=1))


class _MutableTimezone(tzinfo):
    def __init__(self, offset: timedelta) -> None:
        self.offset = offset

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return self.offset

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return "mutable"


class _NoOffsetTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None

    def tzname(self, dt: datetime | None) -> str:
        return "none"


class _BrokenTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta:
        raise RuntimeError("provider secret")

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return "broken"


def test_timezone_behavior_is_detached_at_construction() -> None:
    tz = _MutableTimezone(timedelta(hours=9))
    responded = datetime(2026, 8, 22, 18, 30, 15, 123456, tzinfo=tz)
    recorded = datetime(2026, 8, 22, 18, 30, 16, 123456, tzinfo=tz)
    packet = _build(responded_at=responded, recorded_at=recorded)
    before = packet.canonical_json()

    tz.offset = timedelta(hours=-7)

    assert packet.canonical_json() == before
    assert packet.responded_at.tzinfo is timezone.utc
    assert packet.recorded_at.tzinfo is timezone.utc
    assert json.loads(before)["responded_at"] == "2026-08-22T09:30:15.123456Z"


@pytest.mark.parametrize("field_name", ["responded_at", "recorded_at"])
def test_offsetless_timestamp_fails_closed(field_name: str) -> None:
    bad = datetime(2026, 8, 22, 9, 30, tzinfo=_NoOffsetTimezone())
    with pytest.raises(ValueError, match=field_name):
        _build(**{field_name: bad})


@pytest.mark.parametrize("field_name", ["responded_at", "recorded_at"])
def test_timezone_provider_exception_is_normalized(field_name: str) -> None:
    bad = datetime(2026, 8, 22, 9, 30, tzinfo=_BrokenTimezone())
    with pytest.raises(ValueError, match=field_name) as exc_info:
        _build(**{field_name: bad})
    assert "provider secret" not in str(exc_info.value)


def test_valid_value_replacement_after_issuance_invalidates_evidence() -> None:
    packet = _build()
    object.__setattr__(packet, "response_code", "offer_declined")
    with pytest.raises(ValueError, match="offer response evidence changed after construction"):
        packet.canonical_json()


def test_invalid_value_replacement_after_issuance_fails_validation() -> None:
    packet = _build()
    object.__setattr__(packet, "offer_approval_digest", "A" * 64)
    with pytest.raises(ValueError, match="offer_approval_digest"):
        packet.sha256_digest()


def test_canonicalization_rejects_post_construction_timestamp_reinjection() -> None:
    packet = _build()
    object.__setattr__(packet, "recorded_at", datetime(2026, 8, 22, 9, 30, 16, tzinfo=timezone(timedelta(hours=1))))
    with pytest.raises(ValueError, match="recorded_at"):
        packet.canonical_json()


def test_packet_runtime_is_final() -> None:
    with pytest.raises(TypeError, match="final"):
        type("ForgedPacket", (CandidateOfferResponsePacket,), {})


def test_direct_construction_cannot_weaken_fixed_governance() -> None:
    values = _kwargs()
    values["candidate_confirmation_required"] = False
    with pytest.raises(ValueError, match="candidate confirmation"):
        CandidateOfferResponsePacket(**values)  # type: ignore[arg-type]

    values = _kwargs()
    values["employment_effect"] = "authorized_to_hire"
    with pytest.raises(ValueError, match="employment_effect"):
        CandidateOfferResponsePacket(**values)  # type: ignore[arg-type]

    values = _kwargs()
    values["scope_verification_state"] = "verified"
    with pytest.raises(ValueError, match="scope_verification_state"):
        CandidateOfferResponsePacket(**values)  # type: ignore[arg-type]


def test_direct_construction_cannot_claim_sensitive_payloads_or_model_authority() -> None:
    for field_name in (
        "contains_candidate_pii",
        "contains_compensation_values",
        "contains_free_form_reason",
    ):
        values = _kwargs()
        values[field_name] = True
        with pytest.raises(ValueError):
            CandidateOfferResponsePacket(**values)  # type: ignore[arg-type]

    values = _kwargs()
    values["decision_authority"] = "model_decided"
    with pytest.raises(ValueError, match="decision_authority"):
        CandidateOfferResponsePacket(**values)  # type: ignore[arg-type]


def test_direct_construction_cannot_rewrite_next_action() -> None:
    values = _kwargs()
    values["next_action"] = "Hire immediately"
    with pytest.raises(ValueError, match="next_action"):
        CandidateOfferResponsePacket(**values)  # type: ignore[arg-type]


def test_operational_tenant_accepts_uuid7() -> None:
    packet = _build()
    assert UUID(packet.tenant_record_id).version == 7


@pytest.mark.parametrize("field_name", ["responded_at", "recorded_at"])
def test_offset_overflow_normalizes_to_governed_value_error(field_name: str) -> None:
    """Normalize range overflow during UTC detachment to the governed error."""
    extreme = datetime(1, 1, 1, 0, 0, tzinfo=_MutableTimezone(timedelta(hours=23, minutes=59)))
    with pytest.raises(ValueError, match=f"{field_name} must have a valid timezone offset"):
        _build(**{field_name: extreme})
