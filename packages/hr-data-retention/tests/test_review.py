"""Executable contract for value-minimized HR data-retention review evidence."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from copy import copy, deepcopy
import pickle
from uuid import uuid1
import weakref

import pytest

from orgmetra_hr_data_retention.review import HrDataRetentionReviewPacket
import orgmetra_hr_data_retention.review as review_module


TENANT = "0198f0a1-7b2c-7abc-8def-0123456789ab"
REVIEW = "retention_review:550e8400-e29b-41d4-a716-446655440003"
RESOURCE = "candidate_profile:550e8400-e29b-41d4-a716-446655440000"
POLICY = "retention_policy:550e8400-e29b-41d4-a716-446655440001"
REQUESTER = "actor:550e8400-e29b-41d4-a716-446655440002"
REVIEWER = "actor:550e8400-e29b-41d4-a716-446655440005"
HOLD = "legal_hold:550e8400-e29b-41d4-a716-446655440004"
DIGEST = "a" * 64
HOLD_DIGEST = "b" * 64


def values() -> dict[str, object]:
    """Return one ordinary retention review that is still inside its retention window."""
    return {
        "tenant_record_id": TENANT,
        "retention_review_reference": REVIEW,
        "resource_kind": "candidate_profile",
        "resource_reference": RESOURCE,
        "record_category_code": "candidate_employment_record",
        "retention_policy_reference": POLICY,
        "retention_policy_digest": DIGEST,
        "retention_due_on": date(2026, 8, 31),
        "reviewed_on": date(2026, 8, 22),
        "legal_hold_state": "clear",
        "legal_hold_reference": None,
        "legal_hold_digest": None,
        "requester_actor_reference": REQUESTER,
        "reviewer_actor_reference": REVIEWER,
        "evidence_version": 1,
        "recorded_at": datetime(2026, 8, 22, 6, 0, tzinfo=timezone.utc),
    }


def packet(**overrides: object) -> HrDataRetentionReviewPacket:
    """Build a packet while keeping every unrelated governed field stable."""
    data = values()
    data.update(overrides)
    return HrDataRetentionReviewPacket(**data)


def test_retention_window_requires_continued_retention_and_never_authorizes_deletion() -> None:
    """Keep records while the reviewed retention due date has not passed."""
    review = packet()
    assert review.retention_window_state == "retain_until_due"
    assert review.disposition_authorization_state == "not_authorized_to_delete"
    assert review.scope_verification_state == "requires_authoritative_resolution"
    assert review.human_review_required is True
    assert review.purpose_code == "hr_data_retention_review"
    assert review.requested_action == "review_disposition_eligibility"
    assert "Retain the record" in review.next_action


def test_elapsed_retention_date_requires_authoritative_disposition_review() -> None:
    """A passed policy date is only a review trigger, never deletion authority."""
    review = packet(retention_due_on=date(2026, 8, 21))
    assert review.retention_window_state == "requires_authoritative_disposition_review"
    assert "Re-resolve the authoritative retention policy" in review.next_action
    assert review.disposition_authorization_state == "not_authorized_to_delete"


def test_active_legal_hold_overrides_elapsed_retention_date() -> None:
    """An active hold keeps the packet fail-closed even after a policy due date."""
    review = packet(
        retention_due_on=date(2026, 8, 1),
        legal_hold_state="active",
        legal_hold_reference=HOLD,
        legal_hold_digest=HOLD_DIGEST,
    )
    assert review.retention_window_state == "retain_legal_hold"
    assert "legal hold" in review.next_action


def test_canonical_evidence_is_deterministic_value_minimized_and_redacted() -> None:
    """Canonical evidence contains governed references and states but no HR payload values."""
    review = packet()
    document = review.canonical_document()
    assert document["tenant_record_id"] == TENANT
    assert document["retention_policy_digest"] == DIGEST
    assert document["human_review_required"] is True
    assert document["disposition_authorization_state"] == "not_authorized_to_delete"
    assert document["retention_window_state"] == "retain_until_due"
    assert review.canonical_json() == review.canonical_json()
    assert len(review.evidence_digest()) == 64
    assert repr(review) == "HrDataRetentionReviewPacket(<redacted>)"
    serialized = review.canonical_json()
    for prohibited in ("name", "email", "salary", "assessment_score"):
        assert prohibited not in serialized


def test_correlation_digest_changes_when_governed_policy_evidence_changes() -> None:
    """Bind the exact reviewed policy evidence into the immutable correlation digest."""
    left = packet()
    right = replace(left, retention_policy_digest="c" * 64)
    assert left.evidence_digest() != right.evidence_digest()


class ForgedText(str):
    """Represent caller-controlled text with forged comparison behavior."""

    def __eq__(self, other: object) -> bool:
        """Pretend to equal any compared value."""
        return True

    def __hash__(self) -> int:
        """Return a stable hash that could otherwise influence set membership."""
        return hash("candidate_profile")


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("tenant_record_id", ForgedText(TENANT)),
        ("tenant_record_id", ""),
        ("tenant_record_id", "x" * 201),
        ("tenant_record_id", "not-a-uuid"),
        ("tenant_record_id", TENANT.upper()),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("resource_kind", "shadow_record"),
        ("record_category_code", "free_form_candidate_notes"),
        ("legal_hold_state", "unknown"),
        ("retention_policy_digest", ForgedText(DIGEST)),
        ("retention_policy_digest", "A" * 64),
        ("evidence_version", True),
        ("evidence_version", 0),
        ("evidence_version", 2_147_483_648),
        ("reviewed_on", datetime(2026, 8, 22, tzinfo=timezone.utc)),
        ("retention_due_on", datetime(2026, 8, 31, tzinfo=timezone.utc)),
        ("recorded_at", date(2026, 8, 22)),
        ("recorded_at", datetime(2026, 8, 22, 6, 0)),
        ("recorded_at", datetime(2026, 8, 22, 15, 0, tzinfo=timezone(timedelta(hours=9)))),
        ("recorded_at", datetime(2099, 8, 22, 6, 0, tzinfo=timezone.utc)),
    ],
)
def test_rejects_noncanonical_or_unreviewable_governance_values(
    field_name: str, bad_value: object
) -> None:
    """Reject polymorphic, malformed, unbounded, or noncanonical trust-bearing values."""
    with pytest.raises(ValueError):
        packet(**{field_name: bad_value})


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("retention_review_reference", "wrong:550e8400-e29b-41d4-a716-446655440003"),
        ("resource_reference", "person_record:550e8400-e29b-41d4-a716-446655440000"),
        ("retention_policy_reference", "retention_policy:not-a-uuid"),
        ("requester_actor_reference", f"actor:{uuid1()}"),
        ("reviewer_actor_reference", "actor:550E8400-E29B-41D4-A716-446655440005"),
    ],
)
def test_rejects_wrong_namespace_malformed_or_non_uuid4_references(
    field_name: str, bad_value: str
) -> None:
    """Keep packet-owned references opaque, canonical, namespace-bound UUIDv4 values."""
    with pytest.raises(ValueError):
        packet(**{field_name: bad_value})


def test_rejects_same_requester_and_reviewer() -> None:
    """Require accountable separation between the disposition requester and reviewer."""
    with pytest.raises(ValueError, match="must differ"):
        packet(reviewer_actor_reference=REQUESTER)


@pytest.mark.parametrize(
    ("hold_reference", "hold_digest"),
    [(None, HOLD_DIGEST), (HOLD, None), (None, None)],
)
def test_active_hold_requires_complete_versioned_hold_evidence(
    hold_reference: str | None, hold_digest: str | None
) -> None:
    """Reject an asserted legal hold that lacks either opaque reference or exact digest."""
    with pytest.raises(ValueError, match="active legal hold"):
        packet(
            legal_hold_state="active",
            legal_hold_reference=hold_reference,
            legal_hold_digest=hold_digest,
        )


@pytest.mark.parametrize(
    ("hold_reference", "hold_digest"),
    [(HOLD, None), (None, HOLD_DIGEST), (HOLD, HOLD_DIGEST)],
)
def test_clear_hold_state_rejects_hidden_hold_evidence(
    hold_reference: str | None, hold_digest: str | None
) -> None:
    """Prevent contradictory clear-state evidence from carrying an undisclosed hold binding."""
    with pytest.raises(ValueError, match="clear legal hold"):
        packet(legal_hold_reference=hold_reference, legal_hold_digest=hold_digest)


def test_rejects_recording_before_the_human_review_business_date() -> None:
    """Do not record a review as system evidence before its claimed business review date."""
    with pytest.raises(ValueError, match="recorded_at"):
        packet(recorded_at=datetime(2026, 8, 21, 23, 59, tzinfo=timezone.utc))


def test_replace_revalidates_governed_invariants() -> None:
    """Dataclass replacement cannot bypass requester-reviewer separation or hold consistency."""
    review = packet()
    with pytest.raises(ValueError):
        replace(review, reviewer_actor_reference=REQUESTER)
    with pytest.raises(ValueError):
        replace(review, legal_hold_reference=HOLD)


def test_equivalent_packets_compare_equal_and_keep_separate_seals() -> None:
    """Value equality remains public while identity seals remain independently addressable."""
    first = packet()
    second = packet()
    assert first == second
    object.__setattr__(first, "retention_policy_digest", "c" * 64)
    with pytest.raises(ValueError, match="changed after construction"):
        first.canonical_json()
    assert second.canonical_json() == packet().canonical_json()


def test_copy_and_pickle_rebuild_a_governed_packet_with_a_fresh_seal() -> None:
    """Supported copies preserve valid evidence and reject later mutation independently."""
    original = packet()
    copies = (copy(original), deepcopy(original), pickle.loads(pickle.dumps(original)))
    for clone in copies:
        assert clone == original
        assert clone.canonical_json() == original.canonical_json()
        object.__setattr__(clone, "retention_policy_digest", "c" * 64)
        with pytest.raises(ValueError, match="changed after construction"):
            clone.canonical_json()


def test_missing_or_mismatched_registry_seals_fail_closed() -> None:
    """An identity collision or missing lifecycle entry cannot authorize evidence."""
    review = packet()
    review_module._remove_packet_seal(weakref.ref(review), id(review))
    assert review.canonical_json() == packet().canonical_json()
    with review_module._PACKET_SEALS_LOCK:
        review_module._PACKET_SEALS.pop(id(review))
    with pytest.raises(ValueError, match="retention review evidence changed after construction"):
        review.canonical_json()
