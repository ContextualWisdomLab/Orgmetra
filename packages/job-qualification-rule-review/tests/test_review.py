"""Executable contract for governed Job qualification-rule review evidence."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from orgmetra_job_qualification_rule_review import (
    JobQualificationRuleReviewPacket,
    build_job_qualification_rule_review_packet,
)


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
TENANT_ID = "0198f1c0-7d6e-7f10-8a41-b1d9e2fe0199"
JOB_ID = str(uuid4())
SNAPSHOT_ID = str(uuid4())
RULE_ARTIFACT_ID = str(uuid4())
REQUESTER_ID = str(uuid4())
REVIEWER_ID = str(uuid4())
REVIEWED_AT = datetime(2026, 8, 23, 20, 0, tzinfo=timezone.utc)


def values() -> dict[str, object]:
    """Return one complete valid packet input for focused tests."""
    return {
        "tenant_record_id": TENANT_ID,
        "job_record_reference": f"job_record:{JOB_ID}",
        "job_analysis_snapshot_reference": f"job_analysis_snapshot:{SNAPSHOT_ID}",
        "job_analysis_snapshot_digest": DIGEST_A,
        "qualification_rule_artifact_reference": f"qualification_rule_artifact:{RULE_ARTIFACT_ID}",
        "qualification_rule_artifact_digest": DIGEST_B,
        "task_linkage_digest": DIGEST_C,
        "ksao_linkage_digest": DIGEST_D,
        "source_evidence_digest": "e" * 64,
        "rule_category": "knowledge_skill_ability_requirement",
        "effective_on": date(2026, 9, 1),
        "requester_actor_reference": f"actor:{REQUESTER_ID}",
        "reviewer_actor_reference": f"actor:{REVIEWER_ID}",
        "reason_code": "new_job_analysis",
        "evidence_version": 1,
        "reviewed_at": REVIEWED_AT,
    }


def test_builds_human_reviewed_non_authoritative_qualification_rule_evidence() -> None:
    """A valid packet binds reviewed job evidence without granting decision authority."""
    packet = build_job_qualification_rule_review_packet(**values())

    assert isinstance(packet, JobQualificationRuleReviewPacket)
    assert packet.purpose_code == "job_qualification_rule_review"
    assert packet.review_state == "reviewed_for_authoritative_resolution"
    assert packet.decision_authority == "not_authorized_for_candidate_or_employment_decision"
    assert packet.human_review_required is True
    assert packet.recorded_at >= packet.reviewed_at
    assert packet.recorded_at.tzinfo is timezone.utc
    assert "authoritative" in packet.next_action
    assert "audit/outbox" in packet.next_action
    assert repr(packet) == "JobQualificationRuleReviewPacket(<redacted>)"

    document = packet.canonical_document()
    assert document["rule_category"] == "knowledge_skill_ability_requirement"
    assert document["effective_on"] == "2026-09-01"
    assert document["reviewed_at"] == "2026-08-23T20:00:00Z"
    assert document["recorded_at"].endswith("Z")
    assert len(packet.sha256_digest()) == 64


def test_canonical_evidence_excludes_candidate_pii_rule_text_and_decision_values() -> None:
    """Durable evidence must remain minimized to correlations, categories, and digests."""
    encoded = JobQualificationRuleReviewPacket(**values()).canonical_json()

    for forbidden in (
        "candidate_profile",
        "person_record",
        "name",
        "email",
        "phone",
        "salary",
        "assessment_score",
        "cut_score",
        "rule_text",
        "qualification_text",
        "prompt",
        "model_output",
    ):
        assert forbidden not in encoded


@pytest.mark.parametrize(
    "field,value",
    [
        ("rule_category", "candidate_quality"),
        ("rule_category", "license:CPA"),
        ("reason_code", "manager_preference"),
        ("reason_code", "candidate_failed"),
    ],
)
def test_rejects_unreviewed_rule_categories_and_reasons(field: str, value: object) -> None:
    """Qualification metadata must stay inside reviewed non-sensitive vocabularies."""
    data = values()
    data[field] = value
    with pytest.raises(ValueError):
        JobQualificationRuleReviewPacket(**data)


def test_accepts_each_reviewed_rule_category_and_reason() -> None:
    """Every published controlled category and reason remains executable."""
    categories = (
        "credential_requirement",
        "education_training_requirement",
        "experience_requirement",
        "knowledge_skill_ability_requirement",
        "task_or_work_requirement",
    )
    reasons = (
        "new_job_analysis",
        "job_analysis_revision",
        "periodic_job_analysis_review",
        "source_evidence_change",
    )
    for category in categories:
        data = values()
        data["rule_category"] = category
        assert JobQualificationRuleReviewPacket(**data).rule_category == category
    for reason in reasons:
        data = values()
        data["reason_code"] = reason
        assert JobQualificationRuleReviewPacket(**data).reason_code == reason


def test_rejects_requester_reviewer_overlap() -> None:
    """The accountable human reviewer must not be the requesting actor correlation."""
    data = values()
    data["reviewer_actor_reference"] = data["requester_actor_reference"]
    with pytest.raises(ValueError, match="different actor"):
        JobQualificationRuleReviewPacket(**data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("tenant_record_id", "ffffffff-ffff-ffff-ffff-ffffffffffff"),
        ("tenant_record_id", "not-a-uuid"),
        ("job_record_reference", f"position_record:{JOB_ID}"),
        ("job_record_reference", "job_record:not-a-uuid"),
        ("job_record_reference", "job_record:00000000-0000-0000-0000-000000000000"),
        ("job_analysis_snapshot_reference", f"job_analysis:{SNAPSHOT_ID}"),
        ("qualification_rule_artifact_reference", f"qualification_rule:{RULE_ARTIFACT_ID}"),
        (
            "qualification_rule_artifact_reference",
            "qualification_rule_artifact:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        ),
    ],
)
def test_rejects_invalid_scope_and_evidence_references(field: str, value: object) -> None:
    """Authoritative scope and packet-owned evidence references must stay opaque and canonical."""
    data = values()
    data[field] = value
    with pytest.raises(ValueError):
        JobQualificationRuleReviewPacket(**data)


@pytest.mark.parametrize(
    "field",
    [
        "qualification_rule_artifact_reference",
        "requester_actor_reference",
        "reviewer_actor_reference",
    ],
)
def test_packet_owned_references_require_uuid4(field: str) -> None:
    """Packet-owned correlations reject UUIDv1 timestamp/node metadata."""
    data = values()
    prefix = str(data[field]).split(":", 1)[0]
    data[field] = f"{prefix}:6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    with pytest.raises(ValueError, match="UUIDv4"):
        JobQualificationRuleReviewPacket(**data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_analysis_snapshot_digest", "A" * 64),
        ("qualification_rule_artifact_digest", "abc"),
        ("task_linkage_digest", "g" * 64),
        ("ksao_linkage_digest", 7),
        ("source_evidence_digest", "f" * 63),
    ],
)
def test_rejects_noncanonical_sha256_evidence(field: str, value: object) -> None:
    """Every provenance digest must be exact lower-case SHA-256 text."""
    data = values()
    data[field] = value
    with pytest.raises(ValueError):
        JobQualificationRuleReviewPacket(**data)


class ForgedText(str):
    """Hostile string subtype that attempts to forge equality and hashing."""

    def __eq__(self, other: object) -> bool:
        """Pretend to equal any compared governance value."""
        return True

    def __hash__(self) -> int:
        """Return a forged stable hash."""
        return 0


@pytest.mark.parametrize(
    "field",
    [
        "tenant_record_id",
        "job_record_reference",
        "job_analysis_snapshot_reference",
        "qualification_rule_artifact_reference",
        "job_analysis_snapshot_digest",
        "task_linkage_digest",
        "rule_category",
        "requester_actor_reference",
        "reason_code",
    ],
)
def test_rejects_hostile_string_subclasses_before_governance_checks(field: str) -> None:
    """Trust-bearing text cannot execute caller-defined equality, hash, or parser behavior."""
    data = values()
    data[field] = ForgedText(str(data[field]))
    with pytest.raises(ValueError):
        JobQualificationRuleReviewPacket(**data)


class ForgedDate(date):
    """Hostile date subtype that must not enter the business-time boundary."""


def test_effective_date_requires_exact_builtin_date() -> None:
    """Business-effective time rejects datetime and caller-defined date behavior."""
    for value in (
        datetime(2026, 9, 1, tzinfo=timezone.utc),
        ForgedDate(2026, 9, 1),
        "2026-09-01",
    ):
        data = values()
        data["effective_on"] = value
        with pytest.raises(ValueError, match="effective_on"):
            JobQualificationRuleReviewPacket(**data)


class ForgedDateTime(datetime):
    """Hostile datetime subtype that must not enter accountable review time."""


def test_review_time_requires_exact_builtin_utc_datetime() -> None:
    """Human-review evidence rejects naive, offset, and caller-defined datetimes."""
    candidates = (
        datetime(2026, 8, 23, 20, 0),
        datetime(2026, 8, 24, 5, 0, tzinfo=timezone(timedelta(hours=9))),
        ForgedDateTime(2026, 8, 23, 20, 0, tzinfo=timezone.utc),
    )
    for value in candidates:
        data = values()
        data["reviewed_at"] = value
        with pytest.raises(ValueError, match="reviewed_at"):
            JobQualificationRuleReviewPacket(**data)


def test_future_human_review_cannot_precede_owner_generated_system_time() -> None:
    """A caller cannot claim a human review that occurs after owner-generated issuance."""
    data = values()
    data["reviewed_at"] = datetime.now(timezone.utc) + timedelta(days=1)
    with pytest.raises(ValueError, match="recorded_at"):
        JobQualificationRuleReviewPacket(**data)


@pytest.mark.parametrize("value", [True, 0, -1, 2_147_483_648, "1", Decimal("1")])
def test_evidence_version_requires_bounded_exact_integer(value: object) -> None:
    """High-impact evidence versioning rejects bool, non-int, nonpositive, and overflow values."""
    data = values()
    data["evidence_version"] = value
    with pytest.raises(ValueError, match="evidence_version"):
        JobQualificationRuleReviewPacket(**data)


def test_higher_valid_evidence_version_changes_canonical_evidence() -> None:
    """A reviewed evidence revision must be explicit in canonical audit correlation."""
    first = JobQualificationRuleReviewPacket(**values())
    data = values()
    data["evidence_version"] = 2
    second = JobQualificationRuleReviewPacket(**data)
    assert second.canonical_document()["evidence_version"] == 2
    assert first.sha256_digest() != second.sha256_digest()


@pytest.mark.parametrize(
    "field,value",
    [
        ("purpose_code", "candidate_screening"),
        ("review_state", "auto_approved"),
        ("decision_authority", "authorized_to_reject_candidate"),
        ("human_review_required", False),
        ("next_action", "reject candidate now"),
    ],
)
def test_direct_construction_cannot_weaken_fixed_governance(field: str, value: object) -> None:
    """Direct construction cannot convert review evidence into employment-decision authority."""
    data = values()
    data[field] = value
    with pytest.raises(ValueError):
        JobQualificationRuleReviewPacket(**data)


def test_recorded_at_is_owner_generated_and_not_a_public_constructor_input() -> None:
    """Callers cannot inject or backdate system-recorded issuance time."""
    data = values()
    data["recorded_at"] = REVIEWED_AT
    with pytest.raises(TypeError):
        JobQualificationRuleReviewPacket(**data)


def test_post_issuance_valid_field_mutation_invalidates_all_exports() -> None:
    """Even a syntactically valid field rewrite cannot create a second canonical truth."""
    packet = JobQualificationRuleReviewPacket(**values())
    object.__setattr__(packet, "rule_category", "experience_requirement")

    with pytest.raises(ValueError, match="modified after issuance"):
        packet.canonical_document()
    with pytest.raises(ValueError, match="modified after issuance"):
        packet.canonical_json()
    with pytest.raises(ValueError, match="modified after issuance"):
        packet.sha256_digest()


def test_post_issuance_hostile_runtime_mutation_fails_before_serialization() -> None:
    """Export revalidation rejects hostile runtime types before calling their text behavior."""
    packet = JobQualificationRuleReviewPacket(**values())
    object.__setattr__(packet, "rule_category", ForgedText("experience_requirement"))
    with pytest.raises(ValueError, match="exact string"):
        packet.canonical_json()


def test_replace_remains_non_authoritative_and_reissues_system_time() -> None:
    """A copied proposal is independently issued and never inherits employment authority."""
    first = JobQualificationRuleReviewPacket(**values())
    second = replace(first, rule_category="experience_requirement")

    assert second.decision_authority == "not_authorized_for_candidate_or_employment_decision"
    assert second.recorded_at >= first.recorded_at
    assert second.sha256_digest() != first.sha256_digest()


def test_subclass_cannot_override_the_trust_boundary() -> None:
    """Subclass forgery must fail closed at class definition, before any instance."""

    def bypass_validation(_self: object) -> dict[str, object]:
        return {}

    with pytest.raises(TypeError, match="must not be subclassed"):
        type(
            "ForgedPacket",
            (JobQualificationRuleReviewPacket,),
            {"_validated_payload": bypass_validation},
        )


def test_valid_packets_still_canonicalize_and_hash_deterministically() -> None:
    """Base-class construction keeps stable canonical evidence per issued instance."""
    first = build_job_qualification_rule_review_packet(**values())
    second_values = values()
    second_values["rule_category"] = "experience_requirement"
    second = build_job_qualification_rule_review_packet(**second_values)

    assert first.canonical_json() == first.canonical_json()
    assert first.sha256_digest() == first.sha256_digest()
    assert second.sha256_digest() != first.sha256_digest()
    assert len(first.canonical_json()) > 0
