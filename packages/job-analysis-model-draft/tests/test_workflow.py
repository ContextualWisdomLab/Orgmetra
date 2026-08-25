"""Executable contract for governed Job Analysis model-assisted drafts."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from orgmetra_job_analysis_model_draft import (
    DraftModelResult,
    HumanDraftReview,
    JobAnalysisDraftRequest,
    JobAnalysisDraftScopeVerification,
    SemanticUnit,
    generate_job_analysis_model_draft,
)


def digest(text: str) -> str:
    """Return a SHA-256 digest for test evidence."""
    return sha256(text.encode("utf-8")).hexdigest()


def ref(prefix: str) -> str:
    """Return an opaque namespaced UUIDv4 reference."""
    return f"{prefix}:{uuid4()}"


def test_model_draft_requires_scope_model_and_human_review() -> None:
    """Bind Task/FJA/KSAO evidence and keep confirmed model output non-authoritative."""
    units = tuple(sorted((
        SemanticUnit("task", ref("semantic_unit"), "Task evidence", digest("Task evidence"), digest("task-source")),
        SemanticUnit("fja", ref("semantic_unit"), "FJA evidence", digest("FJA evidence"), digest("fja-source")),
        SemanticUnit("ksao", ref("semantic_unit"), "KSAO evidence", digest("KSAO evidence"), digest("ksao-source")),
    ), key=lambda unit: unit.semantic_unit_reference))
    request = JobAnalysisDraftRequest(
        tenant_record_id=str(uuid4()),
        job_analysis_reference=ref("job_analysis"),
        job_analysis_snapshot_digest_sha256=digest("snapshot"),
        draft_request_reference=ref("job_analysis_draft_request"),
        requester_actor_reference=ref("actor"),
        semantic_units=units,
        requested_at=datetime(2026, 8, 25, 12, tzinfo=timezone.utc),
    )
    scope = JobAnalysisDraftScopeVerification(
        tenant_record_id=request.tenant_record_id,
        job_analysis_reference=request.job_analysis_reference,
        job_analysis_snapshot_digest_sha256=request.job_analysis_snapshot_digest_sha256,
        purpose_code=request.purpose_code,
        requester_actor_reference=request.requester_actor_reference,
        authority_evidence_digest_sha256=digest("authority"),
        authorized=True,
    )
    text = "Untrusted Task/FJA/KSAO draft"
    model = DraftModelResult(
        draft_text=text,
        draft_digest_sha256=digest(text),
        orchestration_revision="a" * 40,
        orchestration_evidence_digest_sha256=digest("orchestration"),
        route_reference=ref("model_route"),
    )
    review = HumanDraftReview(
        reviewer_actor_reference=ref("actor"),
        decision_code="confirm_for_authoritative_review",
        reason_code="content_supported",
        reviewed_at=datetime(2026, 8, 25, 12, 5, tzinfo=timezone.utc),
        review_evidence_digest_sha256=digest("human-review"),
    )
    outcome = generate_job_analysis_model_draft(request, lambda _: scope, lambda _: model, lambda *_: review)
    assert outcome.draft_text == text
    document = outcome.receipt.canonical_document()
    assert document["review_state"] == "human_confirmed_draft"
    assert document["decision_authority"] == "not_authorized_for_job_analysis_persistence"
    assert text not in outcome.receipt.canonical_json()
