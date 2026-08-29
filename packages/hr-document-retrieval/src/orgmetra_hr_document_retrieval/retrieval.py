"""Purpose-bound, fail-closed execution for retrieving one governed HR document artifact.

This module deliberately separates authorization, authoritative metadata resolution,
artifact storage, and immutable audit. It never queries another service's tables and
never treats an opaque identifier, cached UI state, or review packet as access authority.
Document bytes are returned only after exact-scope authorization, artifact integrity
verification, and successful immutable audit recording.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from typing import Protocol
from uuid import UUID

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_MEDIA_TYPE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*$")
_MAX_UUID_INT = (1 << 128) - 1
_MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
_SCHEMA_VERSION = "orgmetra.hr_document_retrieval_receipt.v1"
_RETRIEVAL_STATE = "retrieved_after_authorization_and_audit"
_DECISION_AUTHORITY_STATE = "not_authorized_for_employment_decision"
_DELIVERY_CONTEXT_CODE = "authenticated_hr_session"


class HrDocumentRetrievalError(RuntimeError):
    """Stable public failure for a denied or invalid HR document retrieval."""


def _fail(message: str) -> HrDocumentRetrievalError:
    """Build one stable retrieval failure without leaking protected values."""
    return HrDocumentRetrievalError(message)


def _validate_operational_uuid(value: object, field_name: str) -> str:
    """Return canonical non-sentinel UUID text for an Orgmetra authoritative identity."""
    if type(value) is not str:
        raise _fail(f"{field_name} must be canonical operational UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise _fail(f"{field_name} must be canonical operational UUID text") from exc
    if str(parsed) != value or parsed.int in (0, _MAX_UUID_INT):
        raise _fail(f"{field_name} must be canonical operational UUID text")
    return value


def _validate_reference(value: object, namespace: str, field_name: str) -> str:
    """Return one exact namespaced UUIDv4 correlation reference."""
    message = f"{field_name} must be an opaque {namespace}: UUIDv4 reference"
    if type(value) is not str or len(value) > 160:
        raise _fail(message)
    prefix, separator, suffix = value.partition(":")
    if separator != ":" or prefix != namespace or not suffix:
        raise _fail(message)
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise _fail(message) from exc
    if str(parsed) != suffix or parsed.version != 4:
        raise _fail(message)
    return value


def _validate_digest(value: object, field_name: str) -> str:
    """Return exact lowercase SHA-256 text."""
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise _fail(f"{field_name} must be lowercase SHA-256 hex")
    return value


def _validate_code(value: object, field_name: str) -> str:
    """Return bounded descriptive lower-snake-case policy text."""
    if (
        type(value) is not str
        or len(value) > 64
        or _CODE_PATTERN.fullmatch(value) is None
    ):
        raise _fail(f"{field_name} must be bounded descriptive lower snake_case")
    return value


def _validate_media_type(value: object) -> str:
    """Return a bounded lower-case media type without parameters or control text."""
    if (
        type(value) is not str
        or len(value) > 127
        or _MEDIA_TYPE_PATTERN.fullmatch(value) is None
    ):
        raise _fail("media_type must be a bounded lower-case media type without parameters")
    return value


def _freeze_utc(value: object, field_name: str) -> datetime:
    """Detach one timezone-aware built-in datetime from caller timezone code."""
    if type(value) is not datetime or value.tzinfo is None:
        raise _fail(f"{field_name} must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise _fail(f"{field_name} timezone offset could not be resolved safely") from exc
    if type(offset) is not timedelta:
        raise _fail(f"{field_name} must provide one concrete UTC offset")
    return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)


def _now_utc() -> datetime:
    """Return one owner-generated built-in UTC system instant."""
    return datetime.now(timezone.utc)


def _validate_positive_bound(value: object, field_name: str, maximum: int) -> int:
    """Return one exact positive built-in integer within a reviewed bound."""
    if type(value) is not int or value < 1 or value > maximum:
        raise _fail(f"{field_name} must be an integer from 1 through {maximum}")
    return value


def _require_method(value: object, method_name: str, field_name: str) -> None:
    """Fail before protected resolution if a required host capability is absent."""
    method = getattr(value, method_name, None)
    if not callable(method):
        raise _fail(f"{field_name} must provide callable {method_name}()")


@dataclass(frozen=True, slots=True, repr=False)
class DocumentRetrievalQuery:
    """Caller request for one purpose-bound document read.

    This is not authorization. The authoritative metadata and policy owners are
    re-resolved on every invocation before any artifact bytes are requested.
    """

    tenant_record_id: str
    document_record_reference: str
    requester_reference: str
    purpose_code: str
    reason_code: str
    max_bytes: int = _MAX_DOCUMENT_BYTES

    def __repr__(self) -> str:
        """Avoid emitting HR document correlations in routine logs."""
        return "DocumentRetrievalQuery(<redacted>)"

    def __post_init__(self) -> None:
        """Validate the initial request value."""
        _query_snapshot(self)


@dataclass(frozen=True, slots=True, repr=False)
class DocumentRetrievalScope:
    """Fresh authoritative metadata needed to resolve one artifact."""

    tenant_record_id: str
    document_record_reference: str
    person_record_reference: str
    employment_record_reference: str
    artifact_reference: str
    artifact_digest_sha256: str
    media_type: str
    retention_state: str
    classification_code: str

    def __repr__(self) -> str:
        """Avoid emitting HR subject correlations in routine logs."""
        return "DocumentRetrievalScope(<redacted>)"

    def __post_init__(self) -> None:
        """Validate authoritative metadata at construction."""
        _scope_snapshot(self)


@dataclass(frozen=True, slots=True, repr=False)
class DocumentRetrievalAuthorization:
    """Human-accountable authorization for one exact fresh document scope."""

    tenant_record_id: str
    document_record_reference: str
    person_record_reference: str
    employment_record_reference: str
    artifact_reference: str
    artifact_digest_sha256: str
    retention_state: str
    classification_code: str
    authorized_max_bytes: int
    delivery_context_code: str
    requester_reference: str
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    authorization_evidence_digest_sha256: str
    reviewed_at: datetime
    expires_at: datetime
    permitted: bool

    def __repr__(self) -> str:
        """Avoid exposing governed access correlations in routine logs."""
        return "DocumentRetrievalAuthorization(<redacted>)"

    def __post_init__(self) -> None:
        """Validate the initial authorization value."""
        _authorization_snapshot(self)


@dataclass(frozen=True, slots=True, repr=False)
class DocumentArtifact:
    """Bounded artifact bytes returned by the configured Orgmetra storage port."""

    content: bytes
    digest_sha256: str

    def __repr__(self) -> str:
        """Never print document content or digest through routine object representation."""
        return f"DocumentArtifact(<redacted>, byte_count={len(self.content)})"

    def __post_init__(self) -> None:
        """Validate the initial artifact value."""
        _artifact_snapshot(self, _MAX_DOCUMENT_BYTES)


@dataclass(frozen=True, slots=True, repr=False)
class DocumentRetrievalResult:
    """Successfully retrieved bytes plus non-authorizing receipt correlation."""

    content: bytes
    media_type: str
    receipt_digest_sha256: str
    retrieval_state: str = _RETRIEVAL_STATE
    decision_authority_state: str = _DECISION_AUTHORITY_STATE

    def __repr__(self) -> str:
        """Never print retrieved HR document content."""
        return f"DocumentRetrievalResult(<redacted>, byte_count={len(self.content)})"

    def __post_init__(self) -> None:
        """Keep returned result metadata canonical even after direct construction."""
        if type(self.content) is not bytes or not self.content:
            raise _fail("result content must be non-empty built-in bytes")
        _validate_media_type(self.media_type)
        _validate_digest(self.receipt_digest_sha256, "receipt_digest_sha256")
        if type(self.retrieval_state) is not str or self.retrieval_state != _RETRIEVAL_STATE:
            raise _fail("retrieval_state must remain retrieved_after_authorization_and_audit")
        if (
            type(self.decision_authority_state) is not str
            or self.decision_authority_state != _DECISION_AUTHORITY_STATE
        ):
            raise _fail(
                "decision_authority_state must remain not_authorized_for_employment_decision"
            )


class DocumentMetadataResolver(Protocol):
    """Host port that resolves fresh Orgmetra-owned document metadata."""

    def resolve_document_scope(self, query: DocumentRetrievalQuery) -> DocumentRetrievalScope:
        """Resolve one exact current document scope."""


class DocumentRetrievalAuthority(Protocol):
    """Host port that authorizes one exact purpose-bound document scope."""

    def authorize_document_retrieval(
        self,
        query: DocumentRetrievalQuery,
        scope: DocumentRetrievalScope,
    ) -> DocumentRetrievalAuthorization:
        """Return one human-accountable exact-scope authorization decision."""


class DocumentArtifactReader(Protocol):
    """Host port for a bounded read from Orgmetra's configured artifact store."""

    def read_document_artifact(self, artifact_reference: str, max_bytes: int) -> DocumentArtifact:
        """Read at most ``max_bytes`` for the reviewed artifact reference."""


class ImmutableRetrievalAuditWriter(Protocol):
    """Host port that durably records canonical retrieval evidence before release."""

    def append_document_retrieval_receipt(self, canonical_receipt_json: str) -> None:
        """Persist one immutable canonical retrieval receipt or raise."""


def _query_snapshot(value: DocumentRetrievalQuery) -> DocumentRetrievalQuery:
    """Validate and return a detached query without re-entering public construction."""
    if type(value) is not DocumentRetrievalQuery:
        raise _fail("query must be an exact DocumentRetrievalQuery")
    tenant = _validate_operational_uuid(value.tenant_record_id, "tenant_record_id")
    document = _validate_reference(
        value.document_record_reference, "document_record", "document_record_reference"
    )
    requester = _validate_reference(value.requester_reference, "actor", "requester_reference")
    purpose = _validate_code(value.purpose_code, "purpose_code")
    reason = _validate_code(value.reason_code, "reason_code")
    max_bytes = _validate_positive_bound(value.max_bytes, "max_bytes", _MAX_DOCUMENT_BYTES)
    snapshot = object.__new__(DocumentRetrievalQuery)
    object.__setattr__(snapshot, "tenant_record_id", tenant)
    object.__setattr__(snapshot, "document_record_reference", document)
    object.__setattr__(snapshot, "requester_reference", requester)
    object.__setattr__(snapshot, "purpose_code", purpose)
    object.__setattr__(snapshot, "reason_code", reason)
    object.__setattr__(snapshot, "max_bytes", max_bytes)
    return snapshot


def _scope_snapshot(value: DocumentRetrievalScope) -> DocumentRetrievalScope:
    """Validate and return a detached authoritative metadata snapshot."""
    if type(value) is not DocumentRetrievalScope:
        raise _fail("metadata resolver must return an exact DocumentRetrievalScope")
    snapshot = object.__new__(DocumentRetrievalScope)
    object.__setattr__(snapshot, "tenant_record_id", _validate_operational_uuid(value.tenant_record_id, "tenant_record_id"))
    object.__setattr__(snapshot, "document_record_reference", _validate_reference(value.document_record_reference, "document_record", "document_record_reference"))
    object.__setattr__(snapshot, "person_record_reference", _validate_reference(value.person_record_reference, "person_record", "person_record_reference"))
    object.__setattr__(snapshot, "employment_record_reference", _validate_reference(value.employment_record_reference, "employment_record", "employment_record_reference"))
    object.__setattr__(snapshot, "artifact_reference", _validate_reference(value.artifact_reference, "document_artifact", "artifact_reference"))
    object.__setattr__(snapshot, "artifact_digest_sha256", _validate_digest(value.artifact_digest_sha256, "artifact_digest_sha256"))
    object.__setattr__(snapshot, "media_type", _validate_media_type(value.media_type))
    retention = _validate_code(value.retention_state, "retention_state")
    if retention not in {"retained_record", "legal_hold_record"}:
        raise _fail("retention_state must be retained_record or legal_hold_record")
    object.__setattr__(snapshot, "retention_state", retention)
    classification = _validate_code(value.classification_code, "classification_code")
    if classification != "restricted_hr":
        raise _fail("classification_code must remain restricted_hr")
    object.__setattr__(snapshot, "classification_code", classification)
    return snapshot


def _authorization_snapshot(
    value: DocumentRetrievalAuthorization,
) -> DocumentRetrievalAuthorization:
    """Validate and return a detached authorization snapshot."""
    if type(value) is not DocumentRetrievalAuthorization:
        raise _fail("authority must return an exact DocumentRetrievalAuthorization")
    snapshot = object.__new__(DocumentRetrievalAuthorization)
    object.__setattr__(snapshot, "tenant_record_id", _validate_operational_uuid(value.tenant_record_id, "tenant_record_id"))
    object.__setattr__(snapshot, "document_record_reference", _validate_reference(value.document_record_reference, "document_record", "document_record_reference"))
    object.__setattr__(snapshot, "person_record_reference", _validate_reference(value.person_record_reference, "person_record", "person_record_reference"))
    object.__setattr__(snapshot, "employment_record_reference", _validate_reference(value.employment_record_reference, "employment_record", "employment_record_reference"))
    object.__setattr__(snapshot, "artifact_reference", _validate_reference(value.artifact_reference, "document_artifact", "artifact_reference"))
    object.__setattr__(snapshot, "artifact_digest_sha256", _validate_digest(value.artifact_digest_sha256, "artifact_digest_sha256"))
    retention = _validate_code(value.retention_state, "retention_state")
    if retention not in {"retained_record", "legal_hold_record"}:
        raise _fail("retention_state must be retained_record or legal_hold_record")
    object.__setattr__(snapshot, "retention_state", retention)
    classification = _validate_code(value.classification_code, "classification_code")
    if classification != "restricted_hr":
        raise _fail("classification_code must remain restricted_hr")
    object.__setattr__(snapshot, "classification_code", classification)
    object.__setattr__(snapshot, "authorized_max_bytes", _validate_positive_bound(value.authorized_max_bytes, "authorized_max_bytes", _MAX_DOCUMENT_BYTES))
    delivery = _validate_code(value.delivery_context_code, "delivery_context_code")
    if delivery != _DELIVERY_CONTEXT_CODE:
        raise _fail("delivery_context_code must remain authenticated_hr_session")
    object.__setattr__(snapshot, "delivery_context_code", delivery)
    object.__setattr__(snapshot, "requester_reference", _validate_reference(value.requester_reference, "actor", "requester_reference"))
    object.__setattr__(snapshot, "reviewer_reference", _validate_reference(value.reviewer_reference, "actor", "reviewer_reference"))
    if snapshot.requester_reference == snapshot.reviewer_reference:
        raise _fail("reviewer_reference must identify a different accountable actor")
    object.__setattr__(snapshot, "purpose_code", _validate_code(value.purpose_code, "purpose_code"))
    object.__setattr__(snapshot, "reason_code", _validate_code(value.reason_code, "reason_code"))
    object.__setattr__(snapshot, "authorization_evidence_digest_sha256", _validate_digest(value.authorization_evidence_digest_sha256, "authorization_evidence_digest_sha256"))
    object.__setattr__(snapshot, "reviewed_at", _freeze_utc(value.reviewed_at, "reviewed_at"))
    object.__setattr__(snapshot, "expires_at", _freeze_utc(value.expires_at, "expires_at"))
    if type(value.permitted) is not bool:
        raise _fail("permitted must be an exact boolean")
    object.__setattr__(snapshot, "permitted", value.permitted)
    return snapshot


def _artifact_snapshot(value: DocumentArtifact, max_bytes: int) -> DocumentArtifact:
    """Validate one artifact and detach immutable built-in bytes before audit."""
    if type(value) is not DocumentArtifact:
        raise _fail("artifact reader must return an exact DocumentArtifact")
    if type(value.content) is not bytes or not value.content:
        raise _fail("document artifact content must be non-empty built-in bytes")
    if len(value.content) > max_bytes:
        raise _fail("document artifact exceeded the authorized byte limit")
    digest = _validate_digest(value.digest_sha256, "artifact digest_sha256")
    snapshot = object.__new__(DocumentArtifact)
    object.__setattr__(snapshot, "content", bytes(value.content))
    object.__setattr__(snapshot, "digest_sha256", digest)
    return snapshot


def _canonical_receipt(
    *,
    query: DocumentRetrievalQuery,
    scope: DocumentRetrievalScope,
    authorization: DocumentRetrievalAuthorization,
    artifact: DocumentArtifact,
    recorded_at: datetime,
) -> str:
    """Build value-minimized immutable audit evidence for one completed retrieval."""
    payload = {
        "artifact_digest_sha256": artifact.digest_sha256,
        "authorization_evidence_digest_sha256": authorization.authorization_evidence_digest_sha256,
        "byte_count": len(artifact.content),
        "classification_code": scope.classification_code,
        "decision_authority_state": _DECISION_AUTHORITY_STATE,
        "delivery_context_code": authorization.delivery_context_code,
        "document_record_reference": scope.document_record_reference,
        "employment_record_reference": scope.employment_record_reference,
        "media_type": scope.media_type,
        "person_record_reference": scope.person_record_reference,
        "purpose_code": query.purpose_code,
        "reason_code": query.reason_code,
        "recorded_at": recorded_at.isoformat().replace("+00:00", "Z"),
        "requester_reference": query.requester_reference,
        "retention_state": scope.retention_state,
        "retrieval_state": _RETRIEVAL_STATE,
        "reviewer_reference": authorization.reviewer_reference,
        "schema_version": _SCHEMA_VERSION,
        "tenant_record_id": query.tenant_record_id,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def retrieve_hr_document(
    *,
    query: DocumentRetrievalQuery,
    metadata_resolver: DocumentMetadataResolver,
    authority: DocumentRetrievalAuthority,
    artifact_reader: DocumentArtifactReader,
    audit_writer: ImmutableRetrievalAuditWriter,
) -> DocumentRetrievalResult:
    """Retrieve one HR document only after fresh exact-scope authorization and immutable audit.

    The execution order is security-significant: host capability validation → request
    snapshot → authoritative metadata resolution → exact-scope human authorization →
    bounded artifact read and digest verification → authorization freshness recheck →
    immutable audit append → byte release.
    """
    _require_method(metadata_resolver, "resolve_document_scope", "metadata_resolver")
    _require_method(authority, "authorize_document_retrieval", "authority")
    _require_method(artifact_reader, "read_document_artifact", "artifact_reader")
    _require_method(audit_writer, "append_document_retrieval_receipt", "audit_writer")

    request = _query_snapshot(query)

    resolver_request = _query_snapshot(request)
    scope = _scope_snapshot(metadata_resolver.resolve_document_scope(resolver_request))
    if (
        scope.tenant_record_id != request.tenant_record_id
        or scope.document_record_reference != request.document_record_reference
    ):
        raise _fail("resolved document metadata does not match the requested tenant/document scope")

    authority_request = _query_snapshot(request)
    authority_scope = _scope_snapshot(scope)
    authorization = _authorization_snapshot(
        authority.authorize_document_retrieval(authority_request, authority_scope)
    )
    if (
        authorization.tenant_record_id != request.tenant_record_id
        or authorization.document_record_reference != scope.document_record_reference
        or authorization.person_record_reference != scope.person_record_reference
        or authorization.employment_record_reference != scope.employment_record_reference
        or authorization.artifact_reference != scope.artifact_reference
        or authorization.artifact_digest_sha256 != scope.artifact_digest_sha256
        or authorization.retention_state != scope.retention_state
        or authorization.classification_code != scope.classification_code
        or authorization.authorized_max_bytes != request.max_bytes
        or authorization.delivery_context_code != _DELIVERY_CONTEXT_CODE
        or authorization.requester_reference != request.requester_reference
        or authorization.purpose_code != request.purpose_code
        or authorization.reason_code != request.reason_code
    ):
        raise _fail("authorization evidence does not match the exact retrieval scope")
    if authorization.permitted is not True:
        raise _fail("document retrieval is not authorized")

    authorization_checked_at = _now_utc()
    if authorization.reviewed_at > authorization_checked_at:
        raise _fail("authorization review time cannot be later than the retrieval instant")
    if authorization.expires_at <= authorization_checked_at:
        raise _fail("document retrieval authorization is expired or chronologically invalid")

    artifact = _artifact_snapshot(
        artifact_reader.read_document_artifact(scope.artifact_reference, request.max_bytes),
        request.max_bytes,
    )
    actual_digest = sha256(artifact.content).hexdigest()
    if actual_digest != artifact.digest_sha256 or actual_digest != scope.artifact_digest_sha256:
        raise _fail("document artifact digest does not match reviewed metadata")

    release_time = _now_utc()
    if authorization.expires_at <= release_time:
        raise _fail("document retrieval authorization expired before byte release")

    receipt_json = _canonical_receipt(
        query=request,
        scope=scope,
        authorization=authorization,
        artifact=artifact,
        recorded_at=release_time,
    )
    audit_writer.append_document_retrieval_receipt(receipt_json)
    if authorization.expires_at <= _now_utc():
        raise _fail("document retrieval authorization expired before byte release")
    receipt_digest = sha256(receipt_json.encode("utf-8")).hexdigest()
    return DocumentRetrievalResult(
        content=artifact.content,
        media_type=scope.media_type,
        receipt_digest_sha256=receipt_digest,
    )
