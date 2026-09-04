"""Regression for checked-versus-consumed runtime draft evidence."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import pytest

from orgmetra_job_analysis_model_draft import (
    DraftModelResult,
    HumanDraftReview,
    JobAnalysisDraftRequest,
    JobAnalysisDraftScopeVerification,
    JobAnalysisModelDraftError,
    JobAnalysisModelDraftOutcome,
    SemanticUnit,
    generate_job_analysis_model_draft,
)


def _digest(text: str) -> str:
    """Return a SHA-256 digest for test evidence."""
    return sha256(text.encode("utf-8")).hexdigest()


def _ref(prefix: str) -> str:
    """Return one opaque UUIDv4 reference."""
    return f"{prefix}:{uuid4()}"


def _issued_outcome() -> JobAnalysisModelDraftOutcome:
    """Issue one valid reviewed model-draft outcome."""
    units = tuple(sorted((
        SemanticUnit("task", _ref("semantic_unit"), "Task", _digest("Task"), _digest("task-source")),
        SemanticUnit("fja", _ref("semantic_unit"), "FJA", _digest("FJA"), _digest("fja-source")),
        SemanticUnit("ksao", _ref("semantic_unit"), "KSAO", _digest("KSAO"), _digest("ksao-source")),
    ), key=lambda unit: unit.semantic_unit_reference))
    request = JobAnalysisDraftRequest(
        tenant_record_id=str(uuid4()),
        job_analysis_reference=_ref("job_analysis"),
        job_analysis_snapshot_digest_sha256=_digest("snapshot"),
        draft_request_reference=_ref("job_analysis_draft_request"),
        requester_actor_reference=_ref("actor"),
        semantic_units=units,
        requested_at=datetime(2026, 8, 25, 12, tzinfo=timezone.utc),
    )
    verification = JobAnalysisDraftScopeVerification(
        tenant_record_id=request.tenant_record_id,
        job_analysis_reference=request.job_analysis_reference,
        job_analysis_snapshot_digest_sha256=request.job_analysis_snapshot_digest_sha256,
        purpose_code=request.purpose_code,
        requester_actor_reference=request.requester_actor_reference,
        authority_evidence_digest_sha256=_digest("authority"),
        authorized=True,
    )
    text = "Reviewed runtime draft"
    model = DraftModelResult(text, _digest(text), "a" * 40, _digest("orchestration"), _ref("model_route"))
    review = HumanDraftReview(_ref("actor"), "confirm_for_authoritative_review", "content_supported", datetime(2026, 8, 25, 12, 5, tzinfo=timezone.utc), _digest("human-review"))
    return generate_job_analysis_model_draft(request, lambda _: verification, lambda _: model, lambda *_: review)


def test_runtime_outcome_cannot_detach_draft_text_from_receipt() -> None:
    """Runtime consumers cannot pair or mutate draft text away from the reviewed receipt digest."""
    outcome = _issued_outcome()
    assert outcome.draft_text == "Reviewed runtime draft"
    with pytest.raises(JobAnalysisModelDraftError, match="runtime draft does not match"):
        JobAnalysisModelDraftOutcome("different draft", outcome.receipt)
    with pytest.raises(TypeError, match="receipt must be exact"):
        JobAnalysisModelDraftOutcome(outcome.draft_text, object())
    object.__setattr__(outcome, "_draft_text", "different draft")
    with pytest.raises(JobAnalysisModelDraftError, match="runtime draft does not match"):
        _ = outcome.draft_text
