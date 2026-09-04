"""Adversarial edge cases for Job grade design review validation."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from orgmetra_job_grade_design import JobGradeDesignReviewPacket


DIGEST = "d" * 64
TENANT_ID = "0198f1c0-7d6e-7f10-8a41-b1d9e2fe0199"
REVIEWED_AT = datetime(2026, 8, 24, 1, 0, tzinfo=timezone.utc)
RECORDED_AT = datetime(2026, 8, 24, 1, 1, tzinfo=timezone.utc)


def valid_values() -> dict[str, object]:
    """Return independently constructed valid data for validation-edge tests."""
    return {
        "tenant_record_id": TENANT_ID,
        "job_record_reference": f"job_record:{uuid4()}",
        "job_analysis_snapshot_reference": f"job_analysis_snapshot:{uuid4()}",
        "job_analysis_snapshot_digest": DIGEST,
        "job_evaluation_method_code": "factor_based_job_evaluation",
        "job_evaluation_method_digest": DIGEST,
        "grade_code": "G07",
        "band_code": "P3",
        "grade_band_definition_digest": DIGEST,
        "requester_actor_reference": f"actor:{uuid4()}",
        "reviewer_actor_reference": f"actor:{uuid4()}",
        "reason_code": "periodic_job_review",
        "reviewed_at": REVIEWED_AT,
        "recorded_at": RECORDED_AT,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_record_id", "ffffffff-ffff-ffff-ffff-ffffffffffff"),
        ("job_record_reference", "job_record:not-a-uuid"),
        ("job_record_reference", "job_record:" + "1" * 170),
        (
            "job_analysis_snapshot_reference",
            "job_analysis_snapshot:550E8400-E29B-41D4-A716-446655440000",
        ),
        ("requester_actor_reference", f"reviewer:{uuid4()}"),
        ("reviewer_actor_reference", "actor:not-a-uuid"),
        ("reviewer_actor_reference", "actor:00000000-0000-0000-0000-000000000000"),
    ],
)
def test_references_fail_closed_at_every_parser_boundary(field: str, value: object) -> None:
    """Malformed, noncanonical, sentinel, oversized and wrong-namespace references fail."""
    data = valid_values()
    data[field] = value
    with pytest.raises(ValueError):
        JobGradeDesignReviewPacket(**data)


def test_method_code_rejects_oversized_text_before_accepting_pattern_shape() -> None:
    """A syntactically plausible method code cannot exceed its transport bound."""
    data = valid_values()
    data["job_evaluation_method_code"] = "factor_" + "a" * 64
    with pytest.raises(ValueError, match="bounded"):
        JobGradeDesignReviewPacket(**data)


class ForgedText(str):
    """String subtype used to prove exact-runtime checks on fixed governance fields."""


def test_fixed_governance_rejects_string_subclasses_even_with_expected_text() -> None:
    """Fixed governance cannot be supplied by caller-defined string behavior."""
    for field, expected in (
        ("purpose_code", "job_grade_design_review"),
        ("review_state", "reviewed_for_authoritative_resolution"),
        ("decision_authority", "not_authorized_to_assign_grade_or_compensation"),
    ):
        data = valid_values()
        data[field] = ForgedText(expected)
        with pytest.raises(ValueError):
            JobGradeDesignReviewPacket(**data)


def test_next_action_rejects_string_subclass_and_human_review_rejects_integer_truthiness() -> None:
    """Instruction and mandatory-human-review flags use exact immutable governance values."""
    packet = JobGradeDesignReviewPacket(**valid_values())

    data = valid_values()
    data["next_action"] = ForgedText(packet.next_action)
    with pytest.raises(ValueError, match="next_action"):
        JobGradeDesignReviewPacket(**data)

    data = valid_values()
    data["human_review_required"] = 1
    with pytest.raises(ValueError, match="human review"):
        JobGradeDesignReviewPacket(**data)


def test_all_review_reason_codes_are_executable_contract_values() -> None:
    """Every reviewed reason code can be represented without free-form explanation."""
    for reason in (
        "job_architecture_alignment",
        "new_job_design",
        "job_content_change",
        "periodic_job_review",
    ):
        data = valid_values()
        data["reason_code"] = reason
        assert JobGradeDesignReviewPacket(**data).reason_code == reason
