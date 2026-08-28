"""Executable contract for governed Job Analysis model-assisted drafts."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import pytest

from orgmetra_job_analysis_model_draft import (
    DraftModelResult,
    HumanDraftReview,
    JobAnalysisDraftRequest,
    JobAnalysisDraftScopeVerification,
    JobAnalysisModelDraftError,
    SemanticUnit,
    generate_job_analysis_model_draft,
)


def digest(text: str) -> str:
    """Return a lowercase SHA-256 hex digest for a UTF-8 string."""
    return sha256(text.encode("utf-8")).hexdigest()


def ref(prefix: str) -> str:
    """Return a namespaced opaque UUIDv4 reference."""
    return f"{prefix}:{uuid4()}"


def request() -> JobAnalysisDraftRequest:
    """Return one valid purpose-bound model-draft request."""
    units = tuple(
        sorted(
            (
                SemanticUnit("task", ref("semantic_unit"), "Handle escalations", digest("Handle escalations"), digest("task-source")),
                SemanticUnit("fja", ref("semantic_unit"), "Reasoning complexity 4", digest("Reasoning complexity 4"), digest("fja-source")),
                SemanticUnit("ksao", ref("semantic_unit"), "Conflict resolution", digest("Conflict resolution"), digest("ksao-source")),
            ),
            key=lambda unit: unit.semantic_unit_reference,
        )
    )
    return JobAnalysisDraftRequest(
        tenant_record_id=str(uuid4()),
        job_analysis_reference=ref("job_analysis"),
        job_analysis_snapshot_digest_sha256=digest("snapshot"),
        draft_request_reference=ref("job_analysis_draft_request"),
        requester_actor_reference=ref("actor"),
        semantic_units=units,
        requested_at=datetime(2026, 8, 25, 12, tzinfo=timezone.utc),
    )


def scope(req: JobAnalysisDraftRequest) -> JobAnalysisDraftScopeVerification:
    """Return exact-scope authority evidence for a request."""
    return JobAnalysisDraftScopeVerification(
        tenant_record_id=req.tenant_record_id,
        job_analysis_reference=req.job_analysis_reference,
        job_analysis_snapshot_digest_sha256=req.job_analysis_snapshot_digest_sha256,
        purpose_code=req.purpose_code,
        requester_actor_reference=req.requester_actor_reference,
        authority_evidence_digest_sha256=digest("authority"),
        authorized=True,
    )


def model_result(text: str = "Draft Task/FJA/KSAO synthesis") -> DraftModelResult:
    """Return one digest-bound untrusted model result."""
    return DraftModelResult(
        draft_text=text,
        draft_digest_sha256=digest(text),
        orchestration_revision="a" * 40,
        orchestration_evidence_digest_sha256=digest("orchestration"),
        route_reference=ref("model_route"),
    )


def human_review(req: JobAnalysisDraftRequest, *, decision: str = "confirm_for_authoritative_review") -> HumanDraftReview:
    """Return a distinct-human review of an untrusted draft."""
    return HumanDraftReview(
        reviewer_actor_reference=ref("actor"),
        decision_code=decision,
        reason_code="content_supported" if decision == "confirm_for_authoritative_review" else "needs_revision",
        reviewed_at=req.requested_at + timedelta(minutes=3),
        review_evidence_digest_sha256=digest("human-review"),
    )


def test_happy_path_binds_semantic_units_and_human_review_without_authorizing_persistence() -> None:
    """A confirmed draft remains non-authoritative and omits raw draft/unit text from durable evidence."""
    req = request()
    calls: list[str] = []

    def resolve(actual: JobAnalysisDraftRequest) -> JobAnalysisDraftScopeVerification:
        """Record authority ordering and return exact scope evidence."""
        calls.append("authority")
        return scope(actual)

    def orchestrate(actual: JobAnalysisDraftRequest) -> DraftModelResult:
        """Record model ordering and verify semantic content is available only at runtime."""
        calls.append("model")
        assert {unit.semantic_kind for unit in actual.semantic_units} == {"task", "fja", "ksao"}
        return model_result()

    def review(actual: JobAnalysisDraftRequest, result: DraftModelResult) -> HumanDraftReview:
        """Record human-review ordering after model output exists."""
        calls.append("human")
        assert result.draft_text.startswith("Draft")
        return human_review(actual)

    outcome = generate_job_analysis_model_draft(req, resolve, orchestrate, review)
    assert calls == ["authority", "model", "human"]
    assert outcome.draft_text == "Draft Task/FJA/KSAO synthesis"
    document = outcome.receipt.canonical_document()
    encoded = outcome.receipt.canonical_json()
    assert document["review_state"] == "human_confirmed_draft"
    assert document["decision_authority"] == "not_authorized_for_job_analysis_persistence"
    assert document["next_action"] == "submit through the authoritative Job Analysis persistence boundary"
    assert document["purpose_code"] == "job_analysis_model_draft"
    assert document["authority_evidence_digest_sha256"] == digest("authority")
    assert document["semantic_unit_evidence_digest_sha256"] == req.semantic_unit_evidence_digest_sha256()
    assert "Draft Task/FJA/KSAO synthesis" not in encoded
    assert "Handle escalations" not in encoded


def test_authority_rejection_prevents_model_and_human_work() -> None:
    """Protected model work never begins when authoritative scope verification rejects the request."""
    req = request()
    touched = {"model": False, "human": False}

    def reject(actual: JobAnalysisDraftRequest) -> JobAnalysisDraftScopeVerification:
        """Return scope-matching but unauthorized evidence."""
        return replace(scope(actual), authorized=False)

    def model(_: JobAnalysisDraftRequest) -> DraftModelResult:
        """Fail the test if model work occurs before authorization."""
        touched["model"] = True
        return model_result()

    def review(_: JobAnalysisDraftRequest, __: DraftModelResult) -> HumanDraftReview:
        """Fail the test if human review occurs after an unauthorized request."""
        touched["human"] = True
        return human_review(req)

    with pytest.raises(JobAnalysisModelDraftError, match="not authorized"):
        generate_job_analysis_model_draft(req, reject, model, review)
    assert touched == {"model": False, "human": False}


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: replace(value, tenant_record_id=str(uuid4())),
        lambda value: replace(value, job_analysis_reference=ref("job_analysis")),
        lambda value: replace(value, job_analysis_snapshot_digest_sha256=digest("other")),
        lambda value: replace(value, requester_actor_reference=ref("actor")),
    ],
)
def test_scope_verification_must_match_exact_request(mutator) -> None:
    """Authority evidence cannot authorize a neighboring tenant, snapshot, purpose, or actor."""
    req = request()
    with pytest.raises(JobAnalysisModelDraftError, match="not authorized for exact Job Analysis scope"):
        generate_job_analysis_model_draft(req, lambda actual: mutator(scope(actual)), lambda _: model_result(), lambda actual, __: human_review(actual))


def test_request_requires_task_fja_and_ksao_semantic_units() -> None:
    """The model workflow cannot draft from a partial Job Analysis evidence family."""
    req = request()
    with pytest.raises(ValueError, match="task, fja, and ksao"):
        replace(req, semantic_units=tuple(unit for unit in req.semantic_units if unit.semantic_kind != "ksao"))


def test_semantic_units_are_digest_bound_and_canonically_ordered() -> None:
    """Runtime semantic text and provenance must match digests and deterministic reference ordering."""
    req = request()
    unit = req.semantic_units[0]
    with pytest.raises(ValueError, match="content digest"):
        replace(unit, semantic_text="rewritten")
    with pytest.raises(ValueError, match="sorted and unique"):
        replace(req, semantic_units=tuple(reversed(req.semantic_units)))
    with pytest.raises(ValueError, match="sorted and unique"):
        replace(req, semantic_units=(unit, unit, *req.semantic_units[1:]))


def test_model_result_is_digest_bound_and_revision_pinned() -> None:
    """Untrusted output is accepted only with exact draft bytes and a pinned lowercase commit revision."""
    with pytest.raises(ValueError, match="draft digest"):
        replace(model_result(), draft_text="rewritten")
    with pytest.raises(ValueError, match="orchestration_revision"):
        replace(model_result(), orchestration_revision="latest")


def test_human_reviewer_must_be_distinct_and_reason_compatible() -> None:
    """Human confirmation requires actor separation and a reason compatible with the review decision."""
    req = request()
    review = human_review(req)
    with pytest.raises(JobAnalysisModelDraftError, match="reviewer must differ"):
        generate_job_analysis_model_draft(req, scope, lambda _: model_result(), lambda *_: replace(review, reviewer_actor_reference=req.requester_actor_reference))
    with pytest.raises(ValueError, match="reason_code"):
        replace(review, decision_code="reject_draft", reason_code="content_supported")


def test_rejected_draft_is_auditable_but_never_persistence_authority() -> None:
    """A rejected draft remains durable evidence without becoming authoritative Job Analysis truth."""
    req = request()
    outcome = generate_job_analysis_model_draft(req, scope, lambda _: model_result(), lambda actual, __: human_review(actual, decision="reject_draft"))
    document = outcome.receipt.canonical_document()
    assert document["review_state"] == "human_rejected_draft"
    assert document["decision_authority"] == "not_authorized_for_job_analysis_persistence"


def test_request_mutation_during_authority_call_fails_before_model_work() -> None:
    """Authority code cannot rewrite an otherwise frozen request and authorize the rewritten evidence."""
    req = request()
    called = False

    def mutate(actual: JobAnalysisDraftRequest) -> JobAnalysisDraftScopeVerification:
        """Mutate the request after capturing authority evidence to simulate hostile host code."""
        verification = scope(actual)
        object.__setattr__(actual, "job_analysis_snapshot_digest_sha256", digest("rewritten"))
        return verification

    def model(_: JobAnalysisDraftRequest) -> DraftModelResult:
        """Record whether a tampered request reaches the model."""
        nonlocal called
        called = True
        return model_result()

    with pytest.raises(JobAnalysisModelDraftError, match="request changed during authority verification"):
        generate_job_analysis_model_draft(req, mutate, model, lambda actual, __: human_review(actual))
    assert called is False


def test_model_result_mutation_during_human_review_fails_closed() -> None:
    """Human-review code cannot rewrite model output after the workflow snapshots the draft evidence."""
    req = request()
    result = model_result()

    def review(actual: JobAnalysisDraftRequest, current: DraftModelResult) -> HumanDraftReview:
        """Mutate the model result while returning otherwise valid human evidence."""
        object.__setattr__(current, "draft_text", "other valid draft")
        object.__setattr__(current, "draft_digest_sha256", digest("other valid draft"))
        return human_review(actual)

    with pytest.raises(JobAnalysisModelDraftError, match="model result changed during human review"):
        generate_job_analysis_model_draft(req, scope, lambda _: result, review)


def test_receipt_rejects_direct_replacement_and_post_issuance_mutation() -> None:
    """Only the workflow may issue receipt evidence, and emitted evidence is tamper-evident afterwards."""
    req = request()
    receipt = generate_job_analysis_model_draft(req, scope, lambda _: model_result(), lambda actual, __: human_review(actual)).receipt
    with pytest.raises(TypeError, match="issued only"):
        replace(receipt, _canonical_json=receipt.canonical_json())
    original = receipt.canonical_json()
    object.__setattr__(receipt, "_canonical_json", original.replace("human_confirmed_draft", "human_rejected_draft"))
    with pytest.raises(JobAnalysisModelDraftError, match="issued receipt changed"):
        receipt.canonical_json()
    assert "human_confirmed_draft" in original


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("tenant_record_id", "not-a-uuid", "tenant_record_id"),
        ("job_analysis_reference", "job_analysis:not-a-uuid", "job_analysis_reference"),
        ("draft_request_reference", "job_analysis_draft_request:not-a-uuid", "draft_request_reference"),
        ("requester_actor_reference", "actor:not-a-uuid", "requester_actor_reference"),
        ("job_analysis_snapshot_digest_sha256", "xyz", "job_analysis_snapshot_digest_sha256"),
        ("purpose_code", "selection_decision", "purpose_code"),
        ("evidence_version", True, "evidence_version"),
    ],
)
def test_request_rejects_malformed_governance_primitives(field: str, value: object, message: str) -> None:
    """Trust-bearing request primitives reject malformed or coercible values."""
    with pytest.raises((TypeError, ValueError), match=message):
        replace(request(), **{field: value})


def test_requested_at_must_be_exact_timezone_aware_datetime() -> None:
    """System chronology rejects naive timestamps and caller-defined datetime subclasses."""
    req = request()
    with pytest.raises(ValueError, match="requested_at"):
        replace(req, requested_at=datetime(2026, 8, 25, 12))

    class ForgedDateTime(datetime):
        """Represent a caller-defined datetime subtype."""

    forged = ForgedDateTime(2026, 8, 25, 12, tzinfo=timezone.utc)
    with pytest.raises(TypeError, match="requested_at"):
        replace(req, requested_at=forged)


def test_review_chronology_must_follow_request() -> None:
    """Human review evidence cannot predate the model-draft request."""
    req = request()
    review = human_review(req)
    with pytest.raises(JobAnalysisModelDraftError, match="reviewed_at cannot predate"):
        generate_job_analysis_model_draft(req, scope, lambda _: model_result(), lambda *_: replace(review, reviewed_at=req.requested_at - timedelta(seconds=1)))


def test_exact_text_uuid_and_reference_edge_rejections() -> None:
    """Canonical identity helpers reject subclasses, empty text, sentinels, wrong namespaces, and non-v4 references."""
    req = request()

    class ForgedStr(str):
        """Represent caller-controlled string behavior."""

    with pytest.raises(TypeError, match="job_analysis_reference"):
        replace(req, job_analysis_reference=ForgedStr(req.job_analysis_reference))
    with pytest.raises(ValueError, match="semantic_text"):
        replace(req.semantic_units[0], semantic_text="", content_digest_sha256=digest(""))
    with pytest.raises(ValueError, match="tenant_record_id"):
        replace(req, tenant_record_id="00000000-0000-0000-0000-000000000000")
    with pytest.raises(ValueError, match="job_analysis_reference"):
        replace(req, job_analysis_reference=ref("wrong_namespace"))
    with pytest.raises(ValueError, match="job_analysis_reference"):
        replace(req, job_analysis_reference="job_analysis:6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def test_timestamp_provider_failures_are_stable_validation_errors() -> None:
    """Exact datetime values fail closed when caller-controlled timezone providers are unusable."""
    from datetime import tzinfo

    class RaisingTimezone(tzinfo):
        """Raise when asked for the UTC offset."""

        def utcoffset(self, dt):
            """Raise to simulate a hostile or broken timezone provider."""
            raise RuntimeError("boom")

        def dst(self, dt):
            """Return no daylight-saving adjustment."""
            return None

    class OffsetlessTimezone(tzinfo):
        """Return no concrete UTC offset."""

        def utcoffset(self, dt):
            """Return None to represent an offsetless timezone."""
            return None

        def dst(self, dt):
            """Return no daylight-saving adjustment."""
            return None

    req = request()
    with pytest.raises(ValueError, match="timezone is unusable"):
        replace(req, requested_at=datetime(2026, 8, 25, 12, tzinfo=RaisingTimezone()))
    with pytest.raises(ValueError, match="timezone is unusable"):
        replace(req, requested_at=datetime(2026, 8, 25, 12, tzinfo=OffsetlessTimezone()))


def test_semantic_collection_and_kind_runtime_guards() -> None:
    """Semantic evidence rejects non-tuples, empty collections, wrong element types, and unknown kinds."""
    req = request()
    with pytest.raises(TypeError, match="semantic_units"):
        replace(req, semantic_units=list(req.semantic_units))
    with pytest.raises(TypeError, match="non-empty exact tuple"):
        replace(req, semantic_units=())
    with pytest.raises(TypeError, match="exact SemanticUnit"):
        replace(req, semantic_units=(object(),))
    unit = req.semantic_units[0]
    with pytest.raises(ValueError, match="kind must be task"):
        replace(unit, semantic_kind="other")


def test_scope_verification_rejects_invalid_fixed_fields_and_bool_subclasses() -> None:
    """Authority evidence itself must use fixed purpose and exact boolean authorization."""
    req = request()
    valid = scope(req)
    with pytest.raises(ValueError, match="purpose_code"):
        replace(valid, purpose_code="shadow_decision")
    with pytest.raises(TypeError, match="authorized"):
        replace(valid, authorized=1)


def test_human_review_rejects_unknown_decision_code() -> None:
    """Human review uses a closed decision vocabulary before reason lookup."""
    req = request()
    with pytest.raises(ValueError, match="decision_code"):
        replace(human_review(req), decision_code="approve_employment", reason_code="content_supported")


def test_exact_callback_result_types_are_required() -> None:
    """Duck-typed authority, model, and human-review results are rejected at trust boundaries."""
    req = request()
    with pytest.raises(JobAnalysisModelDraftError, match="authority must return exact"):
        generate_job_analysis_model_draft(req, lambda _: object(), lambda _: model_result(), lambda actual, __: human_review(actual))
    with pytest.raises(JobAnalysisModelDraftError, match="orchestrator must return exact"):
        generate_job_analysis_model_draft(req, scope, lambda _: object(), lambda actual, __: human_review(actual))
    with pytest.raises(JobAnalysisModelDraftError, match="human reviewer must return exact"):
        generate_job_analysis_model_draft(req, scope, lambda _: model_result(), lambda *_: object())
    with pytest.raises(JobAnalysisModelDraftError, match="request must be exact"):
        generate_job_analysis_model_draft(object(), scope, lambda _: model_result(), lambda actual, __: human_review(actual))


def test_request_mutation_during_model_orchestration_fails_before_human_review() -> None:
    """Model adapter code cannot rewrite request evidence before the human-review boundary."""
    req = request()
    human_called = False

    def mutate(actual: JobAnalysisDraftRequest) -> DraftModelResult:
        """Mutate one request field after producing otherwise valid model evidence."""
        result = model_result()
        object.__setattr__(actual, "job_analysis_snapshot_digest_sha256", digest("model-mutated"))
        return result

    def review(actual: JobAnalysisDraftRequest, result: DraftModelResult) -> HumanDraftReview:
        """Record whether a tampered request reaches human review."""
        nonlocal human_called
        human_called = True
        return human_review(actual)

    with pytest.raises(JobAnalysisModelDraftError, match="request changed during model orchestration"):
        generate_job_analysis_model_draft(req, scope, mutate, review)
    assert human_called is False


def test_request_mutation_during_human_review_fails_before_receipt_issuance() -> None:
    """Human-review code cannot rewrite request evidence and still obtain a durable receipt."""
    req = request()

    def review(actual: JobAnalysisDraftRequest, result: DraftModelResult) -> HumanDraftReview:
        """Mutate request evidence while returning an otherwise valid human review."""
        evidence = human_review(actual)
        object.__setattr__(actual, "job_analysis_snapshot_digest_sha256", digest("human-mutated"))
        return evidence

    with pytest.raises(JobAnalysisModelDraftError, match="request changed during human review"):
        generate_job_analysis_model_draft(req, scope, lambda _: model_result(), review)
