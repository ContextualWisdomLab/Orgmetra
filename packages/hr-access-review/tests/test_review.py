"""Executable contract for value-minimized HR access-review evidence."""

from copy import copy
from datetime import datetime, timedelta, timezone
import json
from uuid import UUID

import pytest

from orgmetra_hr_access_review import HrAccessReviewPacket, build_hr_access_review_packet


TENANT = "018f2f65-9a8b-7c6d-8e5f-1234567890ab"
REVIEW = "access_review:12345678-1234-4234-8234-1234567890ab"
SUBJECT = "actor:11111111-1111-4111-8111-111111111111"
REQUESTER = "actor:22222222-2222-4222-8222-222222222222"
REVIEWER = "actor:33333333-3333-4333-8333-333333333333"
SCOPE_DIGEST = "1" * 64
POLICY_DIGEST = "2" * 64
ENTITLEMENT_DIGEST = "3" * 64
REVIEWER_IDENTITY_DIGEST = "4" * 64
REVIEWED_AT = datetime(2026, 8, 23, 0, 30, tzinfo=timezone.utc)
RECORDED_AT = datetime(2026, 8, 23, 0, 31, tzinfo=timezone.utc)


def values() -> dict[str, object]:
    """Return one valid access-review input set."""
    return {
        "tenant_record_id": TENANT,
        "access_review_reference": REVIEW,
        "subject_actor_reference": SUBJECT,
        "requester_actor_reference": REQUESTER,
        "reviewer_actor_reference": REVIEWER,
        "resource_scope_digest": SCOPE_DIGEST,
        "authorization_policy_digest": POLICY_DIGEST,
        "entitlement_snapshot_digest": ENTITLEMENT_DIGEST,
        "reviewer_identity_evidence_digest": REVIEWER_IDENTITY_DIGEST,
        "review_reason_code": "periodic_access_review",
        "review_recommendation_code": "retain_existing_access",
        "reviewed_at": REVIEWED_AT,
        "recorded_at": RECORDED_AT,
        "evidence_version": 1,
    }


def build(**overrides: object) -> HrAccessReviewPacket:
    """Build one packet with optional test overrides."""
    payload = values()
    payload.update(overrides)
    return build_hr_access_review_packet(**payload)


def test_builds_value_minimized_non_enforcing_access_review_evidence() -> None:
    """Bind reviewed access metadata without granting or revoking access."""
    packet = build()
    document = json.loads(packet.canonical_json())
    assert document["review_recommendation_code"] == "retain_existing_access"
    assert document["review_state"] == "human_review_recorded"
    assert document["enforcement_state"] == "not_authorized_to_modify_access"
    assert document["scope_verification_state"] == "requires_authoritative_resolution"
    assert document["contains_hr_data"] is False
    assert document["contains_credentials"] is False
    assert document["reviewed_at"] == "2026-08-23T00:30:00Z"
    assert document["recorded_at"] == "2026-08-23T00:31:00Z"
    assert len(packet.sha256_digest()) == 64
    assert repr(packet) == "HrAccessReviewPacket(<redacted>)"
    assert "password" not in packet.canonical_json().lower()
    assert "employee_name" not in packet.canonical_json().lower()


def test_binds_explicit_access_review_purpose() -> None:
    """Make the governance purpose explicit in immutable evidence rather than implicit in type."""
    document = build().canonical_document()
    assert document["purpose_code"] == "hr_access_recertification"


def test_binds_reviewer_identity_evidence_and_system_recorded_time() -> None:
    """Separate the human review instant from the later system-recorded evidence instant."""
    packet = build(
        reviewer_identity_evidence_digest=REVIEWER_IDENTITY_DIGEST,
        recorded_at=RECORDED_AT,
    )
    document = packet.canonical_document()
    assert document["reviewer_identity_evidence_digest"] == REVIEWER_IDENTITY_DIGEST
    assert document["recorded_at"] == "2026-08-23T00:31:00Z"
    with pytest.raises(ValueError, match="recorded_at"):
        build(recorded_at=REVIEWED_AT - timedelta(seconds=1))


def test_supports_reviewed_reduction_and_removal_without_execution_authority() -> None:
    """Represent least-privilege recommendations without executing them."""
    for recommendation in ("reduce_existing_access", "remove_existing_access"):
        packet = build(review_recommendation_code=recommendation)
        document = packet.canonical_document()
        assert document["review_recommendation_code"] == recommendation
        assert document["enforcement_state"] == "not_authorized_to_modify_access"


def test_requires_independent_reviewer() -> None:
    """Reject reviewer overlap with the requester or reviewed subject."""
    with pytest.raises(ValueError, match="reviewer_actor_reference"):
        build(reviewer_actor_reference=REQUESTER)
    with pytest.raises(ValueError, match="reviewer_actor_reference"):
        build(reviewer_actor_reference=SUBJECT)


@pytest.mark.parametrize(
    "reason",
    ["", "access_review", "salary_review", "PERIODIC_ACCESS_REVIEW"],
)
def test_rejects_unreviewed_reason_codes(reason: str) -> None:
    """Keep review reasons in the value-minimized governance vocabulary."""
    with pytest.raises(ValueError, match="review_reason_code"):
        build(review_reason_code=reason)


@pytest.mark.parametrize(
    "recommendation",
    ["grant_new_access", "approved", "", "REMOVE_EXISTING_ACCESS"],
)
def test_rejects_recommendations_that_expand_or_escape_review_scope(recommendation: str) -> None:
    """Prevent the review artifact from becoming an access-grant command."""
    with pytest.raises(ValueError, match="review_recommendation_code"):
        build(review_recommendation_code=recommendation)


@pytest.mark.parametrize("tenant", ["not-a-uuid", "00000000-0000-0000-0000-000000000000", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"])
def test_rejects_noncanonical_or_sentinel_tenants(tenant: str) -> None:
    """Require the authoritative tenant to be an operational canonical UUID."""
    with pytest.raises(ValueError, match="tenant_record_id"):
        build(tenant_record_id=tenant)


@pytest.mark.parametrize(
    "reference",
    [
        "wrong:12345678-1234-4234-8234-1234567890ab",
        "access_review:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "access_review:not-a-uuid",
    ],
)
def test_rejects_invalid_packet_owned_review_references(reference: str) -> None:
    """Require an opaque UUIDv4 reference owned by the review packet boundary."""
    with pytest.raises(ValueError, match="access_review_reference"):
        build(access_review_reference=reference)


@pytest.mark.parametrize(
    "actor",
    [
        "worker-123",
        "actor:",
        "actor:bad value",
        "other:worker-123",
        "actor:alice_smith",
        "actor:employee-123",
        "actor:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    ],
)
def test_rejects_malformed_or_identifying_actor_references(actor: str) -> None:
    """Keep durable actor correlation opaque rather than persisting names or employee IDs."""
    with pytest.raises(ValueError, match="subject_actor_reference"):
        build(subject_actor_reference=actor)


@pytest.mark.parametrize(
    "field",
    [
        "resource_scope_digest",
        "authorization_policy_digest",
        "entitlement_snapshot_digest",
        "reviewer_identity_evidence_digest",
    ],
)
def test_rejects_invalid_evidence_digests(field: str) -> None:
    """Require lowercase SHA-256 evidence for every reviewed scope snapshot."""
    with pytest.raises(ValueError, match=field):
        build(**{field: "not-a-digest"})


@pytest.mark.parametrize("version", [True, 0, 2_147_483_648])
def test_rejects_invalid_evidence_versions(version: object) -> None:
    """Reject booleans and out-of-range evidence versions."""
    with pytest.raises(ValueError, match="evidence_version"):
        build(evidence_version=version)


def test_requires_exact_utc_review_and_recorded_times() -> None:
    """Keep both human-review and system-recorded evidence on deterministic UTC primitives."""
    with pytest.raises(ValueError, match="reviewed_at"):
        build(reviewed_at=datetime(2026, 8, 23, 0, 30))
    with pytest.raises(ValueError, match="reviewed_at"):
        build(reviewed_at=datetime(2026, 8, 23, 9, 30, tzinfo=timezone(timedelta(hours=9))))
    with pytest.raises(ValueError, match="recorded_at"):
        build(recorded_at=datetime(2026, 8, 23, 0, 31))
    with pytest.raises(ValueError, match="recorded_at"):
        build(recorded_at=datetime(2026, 8, 23, 9, 31, tzinfo=timezone(timedelta(hours=9))))


class ForgedText(str):
    """Adversarial string whose equality and hashing can lie to governance checks."""

    def __eq__(self, other: object) -> bool:
        """Pretend to equal any compared governance value."""
        return True

    def __hash__(self) -> int:
        """Pretend to share the hash of a reviewed recommendation."""
        return hash("retain_existing_access")


def test_rejects_hostile_runtime_string_subclasses() -> None:
    """Validate canonical built-in text before equality, lookup, parsing, or serialization."""
    with pytest.raises(ValueError, match="review_recommendation_code"):
        build(review_recommendation_code=ForgedText("grant_new_access"))
    with pytest.raises(ValueError, match="subject_actor_reference"):
        build(subject_actor_reference=ForgedText(SUBJECT))
    with pytest.raises(ValueError, match="tenant_record_id"):
        build(tenant_record_id=ForgedText(TENANT))


def test_rejects_direct_governance_state_drift() -> None:
    """Keep high-impact fixed states fail-closed under direct construction."""
    payload = values()
    with pytest.raises(ValueError, match="purpose_code"):
        HrAccessReviewPacket(**payload, purpose_code="access_expansion")
    with pytest.raises(ValueError, match="enforcement_state"):
        HrAccessReviewPacket(**payload, enforcement_state="access_revoked")
    with pytest.raises(ValueError, match="contains_hr_data"):
        HrAccessReviewPacket(**payload, contains_hr_data=True)
    with pytest.raises(ValueError, match="contains_credentials"):
        HrAccessReviewPacket(**payload, contains_credentials=True)
    with pytest.raises(ValueError, match="scope_verification_state"):
        HrAccessReviewPacket(**payload, scope_verification_state="verified")


def test_detects_post_construction_evidence_rewrite_and_unregistered_copy() -> None:
    """Fail closed if frozen evidence is rewritten or copied outside issuance tracking."""
    packet = build()
    object.__setattr__(packet, "review_recommendation_code", "remove_existing_access")
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()

    original = build()
    copied = copy(original)
    with pytest.raises(ValueError, match="not registered"):
        copied.canonical_json()


def test_packet_runtime_is_final() -> None:
    """Governed review behavior cannot be replaced through subclass overrides."""
    with pytest.raises(TypeError, match="is final"):
        type("ForgedPacket", (HrAccessReviewPacket,), {})


def test_canonical_export_reuses_the_integrity_checked_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid rewrite after checking cannot change the emitted access-review evidence."""
    packet = build()
    original_assert_integrity = HrAccessReviewPacket._assert_integrity

    def rewrite_after_check(self: HrAccessReviewPacket) -> dict[str, object]:
        """Simulate a field rewrite immediately after the integrity check."""
        checked_snapshot = original_assert_integrity(self)
        object.__setattr__(self, "review_recommendation_code", "remove_existing_access")
        return checked_snapshot

    monkeypatch.setattr(HrAccessReviewPacket, "_assert_integrity", rewrite_after_check)

    document = json.loads(packet.canonical_json())
    assert document["review_recommendation_code"] == "retain_existing_access"
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()


def test_public_api_has_beginner_readable_docstrings() -> None:
    """Keep the buyer-facing evidence API understandable to new maintainers."""
    assert HrAccessReviewPacket.__doc__
    assert build_hr_access_review_packet.__doc__


def test_tenant_accepts_current_operational_uuid_versions() -> None:
    """Avoid imposing packet-owned UUIDv4 rules on authoritative tenant identity."""
    tenant_uuid = UUID(TENANT)
    assert tenant_uuid.version == 7
    packet = build(tenant_record_id=TENANT)
    assert packet.tenant_record_id == TENANT
