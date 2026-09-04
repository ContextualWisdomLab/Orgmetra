"""Purpose-bound, human-reviewed model drafting for Job Analysis evidence."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from typing import Callable
from uuid import UUID
from weakref import WeakKeyDictionary

PURPOSE = "job_analysis_model_draft"
KINDS = frozenset({"task", "fja", "ksao"})
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")
_TOKEN = object()
_SEALS: WeakKeyDictionary[object, str] = WeakKeyDictionary()
_LOCK = RLock()

class JobAnalysisModelDraftError(ValueError):
    """Signal a fail-closed Job Analysis model-draft governance violation."""

def _text(value: object, name: str, limit: int) -> str:
    """Require bounded exact built-in text."""
    if type(value) is not str:
        raise TypeError(f"{name} must be exact str")
    if not value or len(value) > limit:
        raise ValueError(f"{name} is empty or too long")
    return value

def _digest(value: object, name: str) -> str:
    """Require canonical lowercase SHA-256 evidence."""
    text = _text(value, name, 64)
    if HEX64.fullmatch(text) is None:
        raise ValueError(f"{name} must be SHA-256")
    return text

def _operational_uuid(value: object, name: str) -> str:
    """Require a canonical non-sentinel operational UUID."""
    text = _text(value, name, 36)
    try:
        parsed = UUID(text)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"{name} must be canonical UUID") from exc
    if str(parsed) != text or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{name} must be non-sentinel canonical UUID")
    return text

def _ref(value: object, name: str, prefix: str) -> str:
    """Require a namespaced canonical UUIDv4 reference."""
    text = _text(value, name, 160)
    marker = f"{prefix}:"
    if not text.startswith(marker):
        raise ValueError(f"{name} must use {marker}")
    try:
        parsed = UUID(text[len(marker):])
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"{name} must end in UUIDv4") from exc
    if str(parsed) != text[len(marker):] or parsed.version != 4:
        raise ValueError(f"{name} must end in canonical UUIDv4")
    return text

def _time(value: object, name: str) -> datetime:
    """Require exact timezone-aware datetime and normalize it to UTC."""
    if type(value) is not datetime:
        raise TypeError(f"{name} must be exact datetime")
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError(f"{name} timezone is unusable") from exc
    if offset is None:
        raise ValueError(f"{name} timezone is unusable")
    return value.astimezone(timezone.utc)

def _json(value: object) -> str:
    """Encode deterministic UTF-8 JSON."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _sha(text: str) -> str:
    """Hash deterministic UTF-8 text."""
    return sha256(text.encode("utf-8")).hexdigest()

@dataclass(frozen=True, slots=True)
class SemanticUnit:
    """One Task/FJA/KSAO semantic unit; raw text is runtime-only."""
    semantic_kind: str
    semantic_unit_reference: str
    semantic_text: str = field(repr=False)
    content_digest_sha256: str
    source_provenance_digest_sha256: str
    def __post_init__(self) -> None:
        """Bind bounded raw text to kind, reference, content, and source provenance."""
        if _text(self.semantic_kind, "semantic_kind", 8) not in KINDS:
            raise ValueError("kind must be task, fja, or ksao")
        _ref(self.semantic_unit_reference, "semantic_unit_reference", "semantic_unit")
        raw = _text(self.semantic_text, "semantic_text", 4000)
        if _sha(raw) != _digest(self.content_digest_sha256, "content_digest_sha256"):
            raise ValueError("text does not match content digest")
        _digest(self.source_provenance_digest_sha256, "source_provenance_digest_sha256")
    def evidence(self) -> dict[str, str]:
        """Return value-minimized evidence without raw semantic text."""
        self.__post_init__()
        return {"kind": self.semantic_kind, "reference": self.semantic_unit_reference, "content_digest_sha256": self.content_digest_sha256, "provenance_digest_sha256": self.source_provenance_digest_sha256}

@dataclass(frozen=True, slots=True)
class JobAnalysisDraftRequest:
    """Authorized request to draft against one exact Job Analysis snapshot."""
    tenant_record_id: str
    job_analysis_reference: str
    job_analysis_snapshot_digest_sha256: str
    draft_request_reference: str
    requester_actor_reference: str
    semantic_units: tuple[SemanticUnit, ...]
    requested_at: datetime
    purpose_code: str = PURPOSE
    evidence_version: int = 1
    def __post_init__(self) -> None:
        """Validate exact scope, semantic families, chronology, purpose, and version."""
        _operational_uuid(self.tenant_record_id, "tenant_record_id")
        _ref(self.job_analysis_reference, "job_analysis_reference", "job_analysis")
        _digest(self.job_analysis_snapshot_digest_sha256, "job_analysis_snapshot_digest_sha256")
        _ref(self.draft_request_reference, "draft_request_reference", "job_analysis_draft_request")
        _ref(self.requester_actor_reference, "requester_actor_reference", "actor")
        if type(self.semantic_units) is not tuple or not self.semantic_units:
            raise TypeError("semantic_units must be non-empty exact tuple")
        if any(type(unit) is not SemanticUnit for unit in self.semantic_units):
            raise TypeError("semantic_units must contain exact SemanticUnit")
        evidence = [unit.evidence() for unit in self.semantic_units]
        refs = [item["reference"] for item in evidence]
        if refs != sorted(set(refs)):
            raise ValueError("semantic_units must be sorted and unique")
        if {item["kind"] for item in evidence} != KINDS:
            raise ValueError("semantic_units must include task, fja, and ksao")
        if type(self.purpose_code) is not str or self.purpose_code != PURPOSE:
            raise ValueError("purpose_code must be job_analysis_model_draft")
        if type(self.evidence_version) is not int or self.evidence_version != 1:
            raise ValueError("evidence_version must be exact integer 1")
        _time(self.requested_at, "requested_at")
    def semantic_unit_evidence_digest_sha256(self) -> str:
        """Return a deterministic digest for value-minimized semantic-unit evidence."""
        self.__post_init__()
        return _sha(_json([unit.evidence() for unit in self.semantic_units]))
    def document(self) -> dict[str, object]:
        """Return durable request evidence without raw Task/FJA/KSAO text."""
        self.__post_init__()
        unit_digest = self.semantic_unit_evidence_digest_sha256()
        return {"tenant_record_id": self.tenant_record_id, "job_analysis_reference": self.job_analysis_reference, "job_analysis_snapshot_digest_sha256": self.job_analysis_snapshot_digest_sha256, "draft_request_reference": self.draft_request_reference, "requester_actor_reference": self.requester_actor_reference, "semantic_unit_evidence_digest_sha256": unit_digest, "requested_at": _time(self.requested_at, "requested_at").isoformat().replace("+00:00", "Z"), "purpose_code": self.purpose_code, "evidence_version": self.evidence_version}
    def digest(self) -> str:
        """Return the deterministic digest of durable request evidence."""
        return _sha(_json(self.document()))

@dataclass(frozen=True, slots=True)
class JobAnalysisDraftScopeVerification:
    """Authoritative scope evidence required before model work."""
    tenant_record_id: str
    job_analysis_reference: str
    job_analysis_snapshot_digest_sha256: str
    purpose_code: str
    requester_actor_reference: str
    authority_evidence_digest_sha256: str
    authorized: bool
    def __post_init__(self) -> None:
        """Validate authoritative evidence primitives."""
        _operational_uuid(self.tenant_record_id, "tenant_record_id")
        _ref(self.job_analysis_reference, "job_analysis_reference", "job_analysis")
        _digest(self.job_analysis_snapshot_digest_sha256, "job_analysis_snapshot_digest_sha256")
        if type(self.purpose_code) is not str or self.purpose_code != PURPOSE:
            raise ValueError("purpose_code must be job_analysis_model_draft")
        _ref(self.requester_actor_reference, "requester_actor_reference", "actor")
        _digest(self.authority_evidence_digest_sha256, "authority_evidence_digest_sha256")
        if type(self.authorized) is not bool:
            raise TypeError("authorized must be exact bool")

@dataclass(frozen=True, slots=True)
class DraftModelResult:
    """Untrusted model text with pinned orchestration provenance."""
    draft_text: str = field(repr=False)
    draft_digest_sha256: str
    orchestration_revision: str
    orchestration_evidence_digest_sha256: str
    route_reference: str
    def __post_init__(self) -> None:
        """Bind model bytes to exact digest, revision, route, and provenance."""
        text = _text(self.draft_text, "draft_text", 20000)
        if _sha(text) != _digest(self.draft_digest_sha256, "draft_digest_sha256"):
            raise ValueError("draft_text does not match draft digest")
        if HEX40.fullmatch(_text(self.orchestration_revision, "orchestration_revision", 40)) is None:
            raise ValueError("orchestration_revision must be lowercase 40-hex")
        _digest(self.orchestration_evidence_digest_sha256, "orchestration_evidence_digest_sha256")
        _ref(self.route_reference, "route_reference", "model_route")
    def evidence_digest(self) -> str:
        """Return a digest of model provenance without raw draft text."""
        self.__post_init__()
        return _sha(_json({"draft_digest_sha256": self.draft_digest_sha256, "orchestration_revision": self.orchestration_revision, "orchestration_evidence_digest_sha256": self.orchestration_evidence_digest_sha256, "route_reference": self.route_reference}))

@dataclass(frozen=True, slots=True)
class HumanDraftReview:
    """Distinct-human confirmation or rejection of an untrusted draft."""
    reviewer_actor_reference: str
    decision_code: str
    reason_code: str
    reviewed_at: datetime
    review_evidence_digest_sha256: str
    def __post_init__(self) -> None:
        """Validate reviewer, closed decision/reason vocabulary, time, and evidence."""
        _ref(self.reviewer_actor_reference, "reviewer_actor_reference", "actor")
        allowed = {"confirm_for_authoritative_review": {"content_supported"}, "reject_draft": {"needs_revision", "insufficient_evidence"}}
        decision = _text(self.decision_code, "decision_code", 40)
        if decision not in allowed:
            raise ValueError("decision_code is unsupported")
        if _text(self.reason_code, "reason_code", 40) not in allowed[decision]:
            raise ValueError("reason_code is incompatible")
        _time(self.reviewed_at, "reviewed_at")
        _digest(self.review_evidence_digest_sha256, "review_evidence_digest_sha256")

@dataclass(frozen=True, slots=True, eq=False, weakref_slot=True)
class JobAnalysisModelDraftReceipt:
    """Workflow-issued, tamper-evident, value-minimized durable draft evidence."""
    _canonical_json: str = field(repr=False)
    _issuance_token: object = field(repr=False, compare=False)
    def __post_init__(self) -> None:
        """Reject direct receipt construction without the internal issuance capability."""
        _text(self._canonical_json, "canonical_json", 12000)
        if self._issuance_token is not _TOKEN:
            raise TypeError("receipt is issued only by governed workflow")
    def canonical_json(self) -> str:
        """Return exact issued evidence only while its process-local seal remains valid."""
        with _LOCK:
            expected = _SEALS.get(self)
        if expected is None or expected != _sha(self._canonical_json):
            raise JobAnalysisModelDraftError("issued receipt changed after review")
        return self._canonical_json
    def canonical_document(self) -> dict[str, object]:
        """Return the exact verified evidence document."""
        return json.loads(self.canonical_json())

@dataclass(frozen=True, slots=True)
class JobAnalysisModelDraftOutcome:
    """Runtime draft text paired with matching non-authoritative durable evidence."""
    _draft_text: str = field(repr=False)
    receipt: JobAnalysisModelDraftReceipt
    def __post_init__(self) -> None:
        """Require the runtime draft bytes to match the issued receipt digest."""
        text = _text(self._draft_text, "draft_text", 20000)
        if type(self.receipt) is not JobAnalysisModelDraftReceipt:
            raise TypeError("receipt must be exact JobAnalysisModelDraftReceipt")
        document = self.receipt.canonical_document()
        if _sha(text) != document.get("draft_digest_sha256"):
            raise JobAnalysisModelDraftError("runtime draft does not match issued receipt")
    @property
    def draft_text(self) -> str:
        """Return runtime draft text only while it still matches the issued receipt."""
        self.__post_init__()
        return self._draft_text

def generate_job_analysis_model_draft(request: JobAnalysisDraftRequest, scope_resolver: Callable[[JobAnalysisDraftRequest], JobAnalysisDraftScopeVerification], orchestrator: Callable[[JobAnalysisDraftRequest], DraftModelResult], human_reviewer: Callable[[JobAnalysisDraftRequest, DraftModelResult], HumanDraftReview]) -> JobAnalysisModelDraftOutcome:
    """Authorize, draft, human-review, and issue evidence without persisting Job Analysis truth."""
    if type(request) is not JobAnalysisDraftRequest:
        raise JobAnalysisModelDraftError("request must be exact JobAnalysisDraftRequest")
    request_digest = request.digest()
    verification = scope_resolver(request)
    if request.digest() != request_digest:
        raise JobAnalysisModelDraftError("request changed during authority verification")
    if type(verification) is not JobAnalysisDraftScopeVerification:
        raise JobAnalysisModelDraftError("authority must return exact scope verification")
    verification.__post_init__()
    scope = (request.tenant_record_id, request.job_analysis_reference, request.job_analysis_snapshot_digest_sha256, request.purpose_code, request.requester_actor_reference)
    verified = (verification.tenant_record_id, verification.job_analysis_reference, verification.job_analysis_snapshot_digest_sha256, verification.purpose_code, verification.requester_actor_reference)
    if not verification.authorized or verified != scope:
        raise JobAnalysisModelDraftError("request is not authorized for exact Job Analysis scope")
    result = orchestrator(request)
    if request.digest() != request_digest:
        raise JobAnalysisModelDraftError("request changed during model orchestration")
    if type(result) is not DraftModelResult:
        raise JobAnalysisModelDraftError("orchestrator must return exact DraftModelResult")
    model_digest = result.evidence_digest()
    review = human_reviewer(request, result)
    if result.evidence_digest() != model_digest:
        raise JobAnalysisModelDraftError("model result changed during human review")
    if request.digest() != request_digest:
        raise JobAnalysisModelDraftError("request changed during human review")
    if type(review) is not HumanDraftReview:
        raise JobAnalysisModelDraftError("human reviewer must return exact HumanDraftReview")
    review.__post_init__()
    if review.reviewer_actor_reference == request.requester_actor_reference:
        raise JobAnalysisModelDraftError("reviewer must differ from requester")
    if _time(review.reviewed_at, "reviewed_at") < _time(request.requested_at, "requested_at"):
        raise JobAnalysisModelDraftError("reviewed_at cannot predate requested_at")
    confirmed = review.decision_code == "confirm_for_authoritative_review"
    document = request.document() | {"authority_evidence_digest_sha256": verification.authority_evidence_digest_sha256, "draft_digest_sha256": result.draft_digest_sha256, "model_evidence_digest_sha256": model_digest, "orchestration_revision": result.orchestration_revision, "route_reference": result.route_reference, "reviewer_actor_reference": review.reviewer_actor_reference, "review_evidence_digest_sha256": review.review_evidence_digest_sha256, "reviewed_at": _time(review.reviewed_at, "reviewed_at").isoformat().replace("+00:00", "Z"), "review_state": "human_confirmed_draft" if confirmed else "human_rejected_draft", "review_reason_code": review.reason_code, "decision_authority": "not_authorized_for_job_analysis_persistence", "next_action": "submit through the authoritative Job Analysis persistence boundary" if confirmed else "revise draft evidence before authoritative submission"}
    receipt = JobAnalysisModelDraftReceipt(_json(document), _TOKEN)
    with _LOCK:
        _SEALS[receipt] = _sha(receipt._canonical_json)
    object.__setattr__(receipt, "_issuance_token", None)
    return JobAnalysisModelDraftOutcome(result.draft_text, receipt)
