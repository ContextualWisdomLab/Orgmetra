"""Executable contract for governed release-readiness review evidence."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_release_readiness_review import (
    ReleaseReadinessReviewPacket,
    build_release_readiness_review_packet,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
REQUESTER = "actor:123e4567-e89b-42d3-a456-426614174000"
REVIEWER = "actor:123e4567-e89b-42d3-b456-426614174001"
REVIEWED_AT = datetime(2020, 1, 1, tzinfo=timezone.utc)


def valid_kwargs() -> dict[str, object]:
    """Return one fully valid, value-minimized review fixture."""
    return {
        "candidate_revision_sha": "a" * 40,
        "source_artifact_digest_sha256": DIGEST_A,
        "sbom_digest_sha256": DIGEST_A,
        "provenance_digest_sha256": DIGEST_A,
        "test_evidence_digest_sha256": DIGEST_A,
        "coverage_evidence_digest_sha256": DIGEST_A,
        "security_evidence_digest_sha256": DIGEST_A,
        "sast_evidence_digest_sha256": DIGEST_A,
        "recovery_evidence_digest_sha256": DIGEST_A,
        "operability_evidence_digest_sha256": DIGEST_A,
        "accessibility_evidence_digest_sha256": DIGEST_A,
        "migration_rollback_evidence_digest_sha256": DIGEST_A,
        "package_reproducibility_evidence_digest_sha256": DIGEST_A,
        "requester_actor_reference": REQUESTER,
        "reviewer_actor_reference": REVIEWER,
        "reviewed_at": REVIEWED_AT,
    }


def build_valid() -> ReleaseReadinessReviewPacket:
    """Build one valid packet through the public factory."""
    return build_release_readiness_review_packet(**valid_kwargs())


def test_canonical_evidence_is_value_minimized_and_deterministic() -> None:
    """Canonical evidence binds reviewed gates without release authority or free-form data."""
    packet = build_valid()
    document = packet.canonical_document()
    assert document["candidate_revision_sha"] == "a" * 40
    assert document["review_state"] == "requires_human_review"
    assert document["integration_state"] == "requires_protected_head_verification"
    assert document["release_authority"] == "not_authorized_to_release"
    assert document["human_review_required"] is True
    assert "tags" not in document
    assert "credentials" not in document
    assert "artifact_bytes" not in document
    assert packet.canonical_json() == packet.canonical_json()
    assert len(packet.sha256_digest()) == 64
    assert repr(packet) == "ReleaseReadinessReviewPacket(<redacted>)"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("candidate_revision_sha", "A" * 40),
        ("candidate_revision_sha", "a" * 39),
        ("candidate_revision_sha", "0" * 40),
        ("source_artifact_digest_sha256", "g" * 64),
        ("requester_actor_reference", "actor:not-a-uuid"),
        ("reviewer_actor_reference", "actor:123e4567-e89b-12d3-a456-426614174000"),
    ],
)
def test_malformed_trust_evidence_fails_closed(field_name: str, value: object) -> None:
    """Malformed revision, digest, or actor correlation cannot become reviewed evidence."""
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError):
        build_release_readiness_review_packet(**kwargs)


class ForgedText(str):
    """Caller-defined text subtype that must never control trust validation."""


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("candidate_revision_sha", ForgedText("a" * 40)),
        ("source_artifact_digest_sha256", ForgedText(DIGEST_A)),
        ("requester_actor_reference", ForgedText(REQUESTER)),
    ],
)
def test_text_subclasses_fail_before_parser_or_serialization(
    field_name: str, value: object
) -> None:
    """Trust-bearing text requires exact built-in strings."""
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match="exact string"):
        build_release_readiness_review_packet(**kwargs)


def test_requester_and_reviewer_must_be_distinct() -> None:
    """One actor cannot self-review release-readiness evidence."""
    kwargs = valid_kwargs()
    kwargs["reviewer_actor_reference"] = REQUESTER
    with pytest.raises(ValueError, match="different actor"):
        build_release_readiness_review_packet(**kwargs)


def test_timestamp_runtime_and_chronology_fail_closed() -> None:
    """Human review time is exact UTC and cannot postdate system issuance."""
    kwargs = valid_kwargs()
    kwargs["reviewed_at"] = "2020-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="exact built-in datetime"):
        build_release_readiness_review_packet(**kwargs)

    kwargs = valid_kwargs()
    kwargs["reviewed_at"] = datetime(2020, 1, 1)
    with pytest.raises(ValueError, match=r"timezone\.utc"):
        build_release_readiness_review_packet(**kwargs)

    kwargs = valid_kwargs()
    kwargs["reviewed_at"] = datetime.now(timezone.utc) + timedelta(days=1)
    with pytest.raises(ValueError, match="cannot precede reviewed_at"):
        build_release_readiness_review_packet(**kwargs)


def test_evidence_version_is_exactly_one() -> None:
    """Evidence schema version cannot be coerced or silently widened."""
    kwargs = valid_kwargs()
    kwargs["evidence_version"] = True
    with pytest.raises(ValueError, match="exact integer 1"):
        build_release_readiness_review_packet(**kwargs)

    kwargs = valid_kwargs()
    kwargs["evidence_version"] = 2
    with pytest.raises(ValueError, match="exact integer 1"):
        build_release_readiness_review_packet(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "unsafe_value", "message"),
    [
        ("purpose_code", "other", "purpose_code"),
        ("review_state", "reviewed", "review_state"),
        ("integration_state", "integrated", "integration_state"),
        ("release_authority", "authorized", "release_authority"),
        ("human_review_required", False, "human review"),
        ("next_action", "release now", "next_action"),
    ],
)
def test_fixed_governance_cannot_be_rewritten(
    field_name: str, unsafe_value: object, message: str
) -> None:
    """Post-issuance changes to derived authority state fail before export."""
    packet = build_valid()
    object.__setattr__(packet, field_name, unsafe_value)
    with pytest.raises(ValueError, match=message):
        packet.canonical_json()


def test_fixed_governance_rejects_text_subclasses() -> None:
    """Derived fixed text cannot be replaced with equality-compatible subclasses."""
    packet = build_valid()
    object.__setattr__(packet, "purpose_code", ForgedText("release_readiness_review"))
    with pytest.raises(ValueError, match="purpose_code"):
        packet.canonical_document()


def test_post_issuance_payload_mutation_fails_closed() -> None:
    """A different valid digest cannot create a second canonical truth."""
    packet = build_valid()
    object.__setattr__(packet, "security_evidence_digest_sha256", DIGEST_B)
    with pytest.raises(ValueError, match="modified after issuance"):
        packet.canonical_json()


def test_post_issuance_digest_subclass_fails_before_canonical_export() -> None:
    """Equality-compatible digest subtypes cannot escape as canonical evidence."""
    packet = build_valid()
    object.__setattr__(packet, "security_evidence_digest_sha256", ForgedText(DIGEST_A))
    with pytest.raises(ValueError, match=r"security_evidence_digest_sha256.*exact string"):
        packet.canonical_document()


def test_post_issuance_identity_and_time_mutation_fail_closed() -> None:
    """Identity, time, and version integrity are revalidated before export."""
    packet = build_valid()
    object.__setattr__(packet, "candidate_revision_sha", "bad")
    with pytest.raises(ValueError, match="candidate_revision_sha"):
        packet.canonical_document()

    packet = build_valid()
    object.__setattr__(packet, "requester_actor_reference", "bad")
    with pytest.raises(ValueError, match="requester_actor_reference"):
        packet.canonical_document()

    packet = build_valid()
    object.__setattr__(packet, "reviewed_at", "bad")
    with pytest.raises(ValueError, match="reviewed_at"):
        packet.canonical_document()

    packet = build_valid()
    object.__setattr__(packet, "recorded_at", datetime(2020, 1, 1))
    with pytest.raises(ValueError, match="recorded_at"):
        packet.canonical_document()

    packet = build_valid()
    object.__setattr__(packet, "evidence_version", 2)
    with pytest.raises(ValueError, match="evidence_version"):
        packet.canonical_document()


def test_copy_or_replacement_does_not_inherit_issuance_authority() -> None:
    """Dataclass replacement creates a separately sealed packet rather than copying a seal."""
    packet = build_valid()
    replacement = replace(packet, security_evidence_digest_sha256=DIGEST_B)
    assert replacement.sha256_digest() != packet.sha256_digest()


def test_packet_type_is_final() -> None:
    """Subtype-based overrides cannot cross the trust-bearing packet boundary."""
    with pytest.raises(TypeError, match="final trust-bearing"):
        type("ForgedPacket", (ReleaseReadinessReviewPacket,), {})


def test_all_digest_fields_are_validated() -> None:
    """Each required release evidence digest independently participates in validation."""
    digest_fields = [key for key in valid_kwargs() if key.endswith("_digest_sha256")]
    for field_name in digest_fields:
        kwargs = valid_kwargs()
        kwargs[field_name] = "0" * 63
        with pytest.raises(ValueError, match=field_name):
            build_release_readiness_review_packet(**kwargs)
