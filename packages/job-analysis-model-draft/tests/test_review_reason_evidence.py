"""Regression for preserving accountable human-review reason evidence."""

from datetime import datetime, timedelta, timezone
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


def _digest(text: str) -> str:
    """Return a lowercase SHA-256 digest for UTF-8 text."""
    return sha256(text.encode("utf-8")).hexdigest()


def _ref(prefix: str) -> str:
    """Return one opaque namespaced UUIDv4 reference."""
    return f"{prefix}:{uuid4()}"


def _request() -> JobAnalysisDraftRequest:
    """Return one complete Task/FJA/KSAO draft request."""
    units = tuple(
        sorted(
            (
                SemanticUnit("task", _ref("semantic_unit"), "Resolve escalations", _digest("Resolve escalations"), _digest("task-source")),
                SemanticUnit("fja", _ref("semantic_unit"), "Reasoning complexity 4", _digest("Reasoning complexity 4"), _digest("fja-source")),
                SemanticUnit("ksao", _ref("semantic_unit"), "Conflict resolution", _digest("Conflict resolution"), _digest("ksao-source")),
            ),
            key=lambda unit: unit.semantic_unit_reference,
        )
    )
    return JobAnalysisDraftRequest(
        tenant_record_id=str(uuid4()),
        job_analysis_reference=_ref("job_analysis"),
        job_analysis_snapshot_digest_sha256=_digest("snapshot"),
        draft_request_reference=_ref("job_analysis_draft_request"),
        requester_actor_reference=_ref("actor"),
        semantic_units=units,
        requested_at=datetime(2026, 8, 25, 12, tzinfo=timezone.utc),
    )


def _scope(request: JobAnalysisDraftRequest) -> JobAnalysisDraftScopeVerification:
    """Return exact-scope authorization evidence for the request."""
    return JobAnalysisDraftScopeVerification(
        tenant_record_id=request.tenant_record_id,
        job_analysis_reference=request.job_analysis_reference,
        job_analysis_snapshot_digest_sha256=request.job_analysis_snapshot_digest_sha256,
        purpose_code=request.purpose_code,
        requester_actor_reference=request.requester_actor_reference,
        authority_evidence_digest_sha256=_digest("authority"),
        authorized=True,
    )


def _model() -> DraftModelResult:
    """Return one digest-bound untrusted draft result."""
    text = "Draft Task/FJA/KSAO synthesis"
    return DraftModelResult(
        draft_text=text,
        draft_digest_sha256=_digest(text),
        orchestration_revision="a" * 40,
        orchestration_evidence_digest_sha256=_digest("orchestration"),
        route_reference=_ref("model_route"),
    )


def test_rejected_draft_preserves_controlled_human_reason_in_durable_evidence() -> None:
    """A rejected draft must retain its reason and direct the next actor to revise, not persist."""
    request = _request()

    def review(actual: JobAnalysisDraftRequest, _: DraftModelResult) -> HumanDraftReview:
        """Reject the draft because the supporting evidence is insufficient."""
        return HumanDraftReview(
            reviewer_actor_reference=_ref("actor"),
            decision_code="reject_draft",
            reason_code="insufficient_evidence",
            reviewed_at=actual.requested_at + timedelta(minutes=3),
            review_evidence_digest_sha256=_digest("human-review"),
        )

    outcome = generate_job_analysis_model_draft(request, _scope, lambda _: _model(), review)
    document = outcome.receipt.canonical_document()
    assert document["review_state"] == "human_rejected_draft"
    assert document["review_reason_code"] == "insufficient_evidence"
    assert document["next_action"] == "revise draft evidence before authoritative submission"
