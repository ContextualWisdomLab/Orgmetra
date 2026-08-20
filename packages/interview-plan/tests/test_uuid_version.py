"""Regression coverage for tenant interoperability and UUIDv4 trust references."""

from datetime import datetime, timezone

import pytest

from orgmetra_interview_plan import build_structured_interview_plan

_UUID1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
_UUID7_TENANT = "10000000-0000-7000-8000-000000000001"


def _plan_kwargs() -> dict[str, object]:
    """Return one valid structured-interview plan input mapping."""
    return {
        "tenant_record_id": "12345678-1234-4234-8234-123456789abc",
        "interview_plan_reference": "interview_plan:11111111-1111-4111-8111-111111111111",
        "requisition_reference": "requisition:22222222-2222-4222-8222-222222222222",
        "job_profile_reference": "job_profile:33333333-3333-4333-8333-333333333333",
        "job_analysis_reference": "job_analysis:44444444-4444-4444-8444-444444444444",
        "job_analysis_digest": "a" * 64,
        "question_set_reference": "question_set:55555555-5555-4555-8555-555555555555",
        "question_set_digest": "b" * 64,
        "question_competency_map_reference": "question_competency_map:66666666-6666-4666-8666-666666666666",
        "question_competency_map_digest": "c" * 64,
        "rating_anchor_reference": "rating_anchor:77777777-7777-4777-8777-777777777777",
        "rating_anchor_digest": "d" * 64,
        "competency_references": ("competency:88888888-8888-4888-8888-888888888888",),
        "panel_actor_references": (
            "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        ),
        "question_count": 2,
        "purpose_code": "structured_interview_plan",
        "reason_code": "approved_requisition_interview",
        "generated_at": datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc),
        "evidence_version": 1,
    }


def test_authoritative_uuid7_tenant_identity_is_accepted() -> None:
    """Accept the canonical UUIDv7 tenant identity already valid in Orgmetra core."""
    data = _plan_kwargs()
    data["tenant_record_id"] = _UUID7_TENANT

    plan = build_structured_interview_plan(**data)

    assert plan.tenant_record_id == _UUID7_TENANT


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("job_profile_reference", f"job_profile:{_UUID1}"),
        ("competency_references", (f"competency:{_UUID1}",)),
        (
            "panel_actor_references",
            (f"actor:{_UUID1}", "actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        ),
    ],
)
def test_uuid1_trust_references_fail_closed(field: str, value: object) -> None:
    """Reject time/node-bearing UUIDv1 suffixes across scalar and collection references."""
    data = _plan_kwargs()
    data[field] = value
    with pytest.raises(ValueError, match="canonical-uuid"):
        build_structured_interview_plan(**data)
