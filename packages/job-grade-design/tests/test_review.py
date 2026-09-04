"""Executable contract for governed Job grade and band design evidence."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from orgmetra_job_grade_design import (
    JobGradeDesignReviewPacket,
    build_job_grade_design_review_packet,
)


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
TENANT_ID = "0198f1c0-7d6e-7f10-8a41-b1d9e2fe0199"
JOB_ID = str(uuid4())
SNAPSHOT_ID = str(uuid4())
REQUESTER_ID = str(uuid4())
REVIEWER_ID = str(uuid4())
REVIEWED_AT = datetime(2026, 8, 24, 0, 10, tzinfo=timezone.utc)
RECORDED_AT = datetime(2026, 8, 24, 0, 11, tzinfo=timezone.utc)


def values() -> dict[str, object]:
    """Return one complete valid review-packet input for focused tests."""
    return {
        "tenant_record_id": TENANT_ID,
        "job_record_reference": f"job_record:{JOB_ID}",
        "job_analysis_snapshot_reference": f"job_analysis_snapshot:{SNAPSHOT_ID}",
        "job_analysis_snapshot_digest": DIGEST_A,
        "job_evaluation_method_code": "factor_based_job_evaluation",
        "job_evaluation_method_digest": DIGEST_B,
        "grade_code": "G07",
        "band_code": "P3",
        "grade_band_definition_digest": DIGEST_C,
        "requester_actor_reference": f"actor:{REQUESTER_ID}",
        "reviewer_actor_reference": f"actor:{REVIEWER_ID}",
        "reason_code": "job_architecture_alignment",
        "reviewed_at": REVIEWED_AT,
        "recorded_at": RECORDED_AT,
    }


def test_builds_human_reviewed_non_authoritative_job_grade_evidence() -> None:
    """A valid packet must bind reviewed evidence without granting mutation authority."""
    packet = build_job_grade_design_review_packet(**values())

    assert isinstance(packet, JobGradeDesignReviewPacket)
    assert packet.purpose_code == "job_grade_design_review"
    assert packet.review_state == "reviewed_for_authoritative_resolution"
    assert packet.decision_authority == "not_authorized_to_assign_grade_or_compensation"
    assert packet.human_review_required is True
    assert "authoritative" in packet.next_action
    assert "audit/outbox" in packet.next_action
    assert repr(packet) == "JobGradeDesignReviewPacket(<redacted>)"

    document = packet.canonical_document()
    assert document["grade_code"] == "G07"
    assert document["band_code"] == "P3"
    assert document["reviewed_at"] == "2026-08-24T00:10:00Z"
    assert document["recorded_at"] == "2026-08-24T00:11:00Z"
    assert len(packet.sha256_digest()) == 64


def test_canonical_evidence_excludes_sensitive_or_free_form_hr_content() -> None:
    """Canonical evidence must contain only minimized governance correlations and digests."""
    packet = JobGradeDesignReviewPacket(**values())
    encoded = packet.canonical_json()

    for forbidden in (
        "person_record_id",
        "candidate",
        "salary",
        "compensation_amount",
        "job_title",
        "task_statement",
        "free_text",
        "prompt",
        "model_output",
    ):
        assert forbidden not in encoded


def test_rejects_requester_reviewer_overlap_and_unreviewed_reason() -> None:
    """Accountable review requires separated actors and a controlled non-sensitive reason."""
    same_actor = values()
    same_actor["reviewer_actor_reference"] = same_actor["requester_actor_reference"]
    with pytest.raises(ValueError, match="different actor"):
        JobGradeDesignReviewPacket(**same_actor)

    bad_reason = values()
    bad_reason["reason_code"] = "manager_says_so"
    with pytest.raises(ValueError, match="reason_code"):
        JobGradeDesignReviewPacket(**bad_reason)


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("tenant_record_id", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"),
        ("tenant_record_id", "not-a-uuid"),
        ("job_record_reference", f"position_record:{JOB_ID}"),
        ("job_record_reference", "job_record:00000000-0000-0000-0000-000000000000"),
        ("job_analysis_snapshot_reference", f"job_analysis:{SNAPSHOT_ID}"),
        (
            "job_analysis_snapshot_reference",
            "job_analysis_snapshot:ffffffff-ffff-ffff-ffff-ffffffffffff",
        ),
    ],
)
def test_rejects_invalid_authoritative_scope_identifiers(field: str, value: object) -> None:
    """Tenant, Job and snapshot scope must use canonical non-sentinel operational UUIDs."""
    data = values()
    data[field] = value
    with pytest.raises(ValueError):
        JobGradeDesignReviewPacket(**data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_analysis_snapshot_digest", "A" * 64),
        ("job_evaluation_method_digest", "abc"),
        ("grade_band_definition_digest", "g" * 64),
    ],
)
def test_rejects_noncanonical_sha256_evidence(field: str, value: object) -> None:
    """Malformed text evidence digests must fail the lower-case SHA-256 shape check."""
    data = values()
    data[field] = value
    with pytest.raises(ValueError, match="SHA-256"):
        JobGradeDesignReviewPacket(**data)


def test_rejects_non_text_sha256_evidence_before_digest_shape_validation() -> None:
    """Non-text digest evidence must fail the exact runtime-type boundary first."""
    data = values()
    data["job_analysis_snapshot_digest"] = 7
    with pytest.raises(
        ValueError,
        match="job_analysis_snapshot_digest must be an exact string",
    ):
        JobGradeDesignReviewPacket(**data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_evaluation_method_code", "singleword"),
        ("job_evaluation_method_code", "Factor_Based"),
        ("job_evaluation_method_code", 3),
        ("grade_code", "grade seven"),
        ("grade_code", "g07"),
        ("band_code", "p 3"),
        ("band_code", "P" * 33),
        ("band_code", 3),
    ],
)
def test_rejects_unbounded_or_noncanonical_job_architecture_codes(
    field: str, value: object
) -> None:
    """Method, grade and band codes must remain bounded enterprise-local tokens."""
    data = values()
    data[field] = value
    with pytest.raises(ValueError):
        JobGradeDesignReviewPacket(**data)


class ForgedText(str):
    """Hostile string subtype that attempts to forge equality and hashing."""

    def __eq__(self, other: object) -> bool:
        """Pretend to equal any compared governance value."""
        return True

    def __hash__(self) -> int:
        """Return a stable forged hash independent of the underlying text."""
        return 0


@pytest.mark.parametrize(
    "field",
    [
        "tenant_record_id",
        "job_record_reference",
        "job_analysis_snapshot_digest",
        "job_evaluation_method_code",
        "grade_code",
        "band_code",
        "requester_actor_reference",
        "reason_code",
    ],
)
def test_rejects_hostile_string_subclasses_before_governance_checks(field: str) -> None:
    """Trust-bearing text must be an exact built-in string before comparisons or parsing."""
    data = values()
    data[field] = ForgedText(str(data[field]))
    with pytest.raises(ValueError):
        JobGradeDesignReviewPacket(**data)


@pytest.mark.parametrize("field", ["requester_actor_reference", "reviewer_actor_reference"])
def test_actor_references_require_canonical_uuid4(field: str) -> None:
    """Packet-owned accountable actor correlations must use opaque UUIDv4 references."""
    data = values()
    uuid1_text = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    data[field] = f"actor:{uuid1_text}"
    with pytest.raises(ValueError, match="UUIDv4"):
        JobGradeDesignReviewPacket(**data)


@pytest.mark.parametrize("field", ["reviewed_at", "recorded_at"])
def test_timestamps_require_exact_builtin_utc_datetime(field: str) -> None:
    """Evidence time must reject naive, non-UTC and caller-defined datetime behavior."""
    naive = values()
    naive[field] = datetime(2026, 8, 24, 0, 10)
    with pytest.raises(ValueError, match="UTC datetime"):
        JobGradeDesignReviewPacket(**naive)

    offset = values()
    offset[field] = datetime(
        2026, 8, 24, 9, 10, tzinfo=timezone(timedelta(hours=9))
    )
    with pytest.raises(ValueError, match="UTC datetime"):
        JobGradeDesignReviewPacket(**offset)

    class ForgedDateTime(datetime):
        """Hostile datetime subtype that must not execute inside the trust boundary."""

    forged = values()
    forged[field] = ForgedDateTime(2026, 8, 24, 0, 10, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="UTC datetime"):
        JobGradeDesignReviewPacket(**forged)


def test_rejects_system_recording_before_human_review() -> None:
    """System-recorded evidence cannot predate the accountable human review instant."""
    data = values()
    data["recorded_at"] = REVIEWED_AT - timedelta(seconds=1)
    with pytest.raises(ValueError, match="recorded_at"):
        JobGradeDesignReviewPacket(**data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("purpose_code", "shadow_decision"),
        ("review_state", "auto_approved"),
        ("decision_authority", "authorized_to_assign_grade"),
        ("human_review_required", False),
        ("next_action", "apply grade immediately"),
    ],
)
def test_direct_construction_cannot_weaken_fixed_governance(
    field: str, value: object
) -> None:
    """Direct dataclass construction cannot convert review evidence into decision authority."""
    data = values()
    data[field] = value
    with pytest.raises(ValueError):
        JobGradeDesignReviewPacket(**data)


def test_post_issuance_mutation_cannot_change_exported_evidence() -> None:
    """Mutation through object internals must invalidate later canonical evidence exports."""
    packet = JobGradeDesignReviewPacket(**values())
    object.__setattr__(packet, "grade_code", "G99")

    with pytest.raises(ValueError, match="modified after issuance"):
        packet.canonical_document()
    with pytest.raises(ValueError, match="modified after issuance"):
        packet.canonical_json()
    with pytest.raises(ValueError, match="modified after issuance"):
        packet.sha256_digest()


def test_replace_creates_a_distinct_review_proposal_not_a_reused_authority() -> None:
    """A changed dataclass replacement may exist only as a new independently hashed proposal."""
    original = JobGradeDesignReviewPacket(**values())
    changed = replace(original, grade_code="G08", reason_code="job_content_change")

    assert changed.sha256_digest() != original.sha256_digest()
    assert changed.decision_authority == "not_authorized_to_assign_grade_or_compensation"
