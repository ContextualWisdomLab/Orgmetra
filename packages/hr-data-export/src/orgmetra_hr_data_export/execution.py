"""Purpose-bound HR export execution with immutable audit-before-egress evidence.

This module owns only the transition from one reviewed export request to one audited,
one-time delivery. It never grants employment-decision authority and never writes raw HR
field values into durable receipts. Hosts remain responsible for authoritative scope
resolution, protected field materialization, durable audit/outbox storage, and the concrete
one-time-delivery mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from threading import Lock
from typing import Callable, Protocol
import weakref

from .review import (
    HrDataExportReviewPacket,
    _freeze_timestamp,
    _validate_digest,
    _validate_frozen_timestamp,
    _validate_operational_uuid,
    _validate_reference,
    _validate_requested_fields,
    _validate_resource_kind,
    _validate_version,
)

_MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
_DESTINATION_KIND = "authenticated_one_time_download"
_AUDIT_STATE = "committed_before_delivery"
_EXPORT_STATE = "export_delivered"
_ISSUANCE_TOKEN = object()
_RECEIPT_SEALS_LOCK = Lock()


class HrDataExportExecutionError(ValueError):
    """Raised when governed HR export execution evidence fails closed."""


def _freeze_execution_time(value: object, field_name: str) -> datetime:
    """Normalize one host time into the package's exact built-in UTC representation."""
    try:
        return _freeze_timestamp(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a safe timezone-aware datetime") from exc


def _clock_now(now_provider: Callable[[], datetime]) -> datetime:
    """Read one host clock instant and normalize provider failures to an execution error."""
    try:
        value = now_provider()
    except Exception as exc:
        raise HrDataExportExecutionError("export execution clock failed") from exc
    try:
        return _freeze_execution_time(value, "execution clock")
    except ValueError as exc:
        raise HrDataExportExecutionError("export execution clock returned invalid time") from exc


def _require_current_authorization(
    verification: HrDataExportExecutionVerification,
    observed_at: datetime,
) -> None:
    """Require export authorization to be effective at one exact observed instant."""
    if observed_at < verification.verified_at or observed_at >= verification.authorization_expires_at:
        raise HrDataExportExecutionError("export authorization expired or is not yet valid")


def _expected_content_type(export_format_code: str) -> str:
    """Map the closed reviewed format vocabulary to one exact outbound media type."""
    return "application/json" if export_format_code == "json" else "text/csv"


@dataclass(frozen=True, slots=True, repr=False)
class HrDataExportExecutionVerification:
    """Authoritative current-scope evidence required before protected field materialization."""

    tenant_record_id: str
    export_execution_reference: str
    export_review_reference: str
    export_review_digest: str
    resource_kind: str
    resource_reference: str
    requested_fields: tuple[str, ...]
    export_format_code: str
    destination_kind: str
    execution_authorization_reference: str
    execution_authorization_digest: str
    authorization_policy_version_code: str
    human_approval_reference: str
    human_approval_digest: str
    retention_state: str
    legal_hold_state: str
    verified_at: datetime
    authorization_expires_at: datetime

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Prevent behavior-overriding verification subtypes at the trust boundary."""
        raise TypeError("HrDataExportExecutionVerification must not be subclassed")

    def __repr__(self) -> str:
        """Redact tenant, resource, authorization and approval correlation from routine logs."""
        return "HrDataExportExecutionVerification(<redacted>)"

    def __post_init__(self) -> None:
        """Validate exact scope primitives and detach both authorization chronology instants."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.export_execution_reference, "export_execution", "export_execution_reference")
        _validate_reference(self.export_review_reference, "export_review", "export_review_reference")
        _validate_digest(self.export_review_digest, "export_review_digest")
        _validate_resource_kind(self.resource_kind)
        _validate_reference(self.resource_reference, self.resource_kind, "resource_reference")
        _validate_requested_fields(self.requested_fields)
        if type(self.export_format_code) is not str or self.export_format_code not in {"json", "csv"}:
            raise ValueError("export_format_code must be json or csv")
        if type(self.destination_kind) is not str or self.destination_kind != _DESTINATION_KIND:
            raise ValueError("destination_kind must remain authenticated_one_time_download")
        _validate_reference(
            self.execution_authorization_reference,
            "export_authorization",
            "execution_authorization_reference",
        )
        _validate_digest(self.execution_authorization_digest, "execution_authorization_digest")
        _validate_version(self.authorization_policy_version_code)
        _validate_reference(self.human_approval_reference, "export_approval", "human_approval_reference")
        _validate_digest(self.human_approval_digest, "human_approval_digest")
        if type(self.retention_state) is not str or self.retention_state not in {
            "retention_permits_export",
            "retention_blocks_export",
        }:
            raise ValueError("retention_state must use the reviewed export policy vocabulary")
        if type(self.legal_hold_state) is not str or self.legal_hold_state not in {
            "no_legal_hold_block",
            "legal_hold_blocks_export",
        }:
            raise ValueError("legal_hold_state must use the reviewed export policy vocabulary")
        verified_at = _freeze_execution_time(self.verified_at, "verified_at")
        expires_at = _freeze_execution_time(self.authorization_expires_at, "authorization_expires_at")
        if expires_at <= verified_at:
            raise ValueError("authorization_expires_at must be later than verified_at")
        object.__setattr__(self, "verified_at", verified_at)
        object.__setattr__(self, "authorization_expires_at", expires_at)


@dataclass(frozen=True, slots=True, repr=False)
class HrDataExportArtifact:
    """Ephemeral bounded export bytes plus the exact reviewed field and media shape."""

    field_names: tuple[str, ...]
    content_type: str
    content: bytes

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Prevent artifact subtypes from redefining digest or size behavior."""
        raise TypeError("HrDataExportArtifact must not be subclassed")

    def __repr__(self) -> str:
        """Never emit protected export bytes through routine object representation."""
        return "HrDataExportArtifact(<redacted>)"

    def __post_init__(self) -> None:
        """Validate deterministic field scope, media type, exact bytes and the hard size budget."""
        _validate_requested_fields(self.field_names)
        if type(self.content_type) is not str or self.content_type not in {"application/json", "text/csv"}:
            raise ValueError("content_type must use the reviewed export media vocabulary")
        if type(self.content) is not bytes:
            raise ValueError("export content must be exact immutable bytes")
        if len(self.content) > _MAX_ARTIFACT_BYTES:
            raise ValueError("export content must not exceed 10 MiB")

    @property
    def byte_length(self) -> int:
        """Return the transient payload length without copying protected bytes."""
        return len(self.content)

    @property
    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact transient bytes destined for egress."""
        return sha256(self.content).hexdigest()


@dataclass(frozen=True, slots=True, repr=False)
class HrDataExportAuditReceipt:
    """Value-minimized immutable audit receipt committed before outbound delivery."""

    tenant_record_id: str
    export_execution_reference: str
    export_review_digest: str
    execution_authorization_digest: str
    human_approval_digest: str
    artifact_sha256_digest: str
    artifact_byte_length: int
    audit_event_reference: str
    recorded_at: datetime
    audit_state: str = _AUDIT_STATE

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Prevent audit receipt subtypes from spoofing exact evidence fields."""
        raise TypeError("HrDataExportAuditReceipt must not be subclassed")

    def __repr__(self) -> str:
        """Redact durable export correlations from routine logging."""
        return "HrDataExportAuditReceipt(<redacted>)"

    def __post_init__(self) -> None:
        """Validate pre-delivery audit identity, artifact binding, chronology and state."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.export_execution_reference, "export_execution", "export_execution_reference")
        _validate_digest(self.export_review_digest, "export_review_digest")
        _validate_digest(self.execution_authorization_digest, "execution_authorization_digest")
        _validate_digest(self.human_approval_digest, "human_approval_digest")
        _validate_digest(self.artifact_sha256_digest, "artifact_sha256_digest")
        if type(self.artifact_byte_length) is not int or not 0 <= self.artifact_byte_length <= _MAX_ARTIFACT_BYTES:
            raise ValueError("artifact_byte_length must be an exact integer within the 10 MiB budget")
        _validate_reference(self.audit_event_reference, "audit_event", "audit_event_reference")
        object.__setattr__(self, "recorded_at", _freeze_execution_time(self.recorded_at, "recorded_at"))
        if type(self.audit_state) is not str or self.audit_state != _AUDIT_STATE:
            raise ValueError("audit_state must remain committed_before_delivery")


@dataclass(frozen=True, slots=True, repr=False)
class HrDataExportEgressReceipt:
    """Host receipt proving the exact audited artifact entered one-time authenticated delivery."""

    tenant_record_id: str
    export_execution_reference: str
    artifact_sha256_digest: str
    artifact_byte_length: int
    audit_event_reference: str
    egress_reference: str
    destination_kind: str
    one_time_use_enforced: bool
    delivered_at: datetime

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Prevent egress receipt subtypes from redefining delivery evidence."""
        raise TypeError("HrDataExportEgressReceipt must not be subclassed")

    def __repr__(self) -> str:
        """Redact outbound correlation evidence from routine object representation."""
        return "HrDataExportEgressReceipt(<redacted>)"

    def __post_init__(self) -> None:
        """Validate exact one-time egress identity, artifact binding and delivery instant."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(self.export_execution_reference, "export_execution", "export_execution_reference")
        _validate_digest(self.artifact_sha256_digest, "artifact_sha256_digest")
        if type(self.artifact_byte_length) is not int or not 0 <= self.artifact_byte_length <= _MAX_ARTIFACT_BYTES:
            raise ValueError("artifact_byte_length must be an exact integer within the 10 MiB budget")
        _validate_reference(self.audit_event_reference, "audit_event", "audit_event_reference")
        _validate_reference(self.egress_reference, "one_time_download", "egress_reference")
        if type(self.destination_kind) is not str or self.destination_kind != _DESTINATION_KIND:
            raise ValueError("destination_kind must remain authenticated_one_time_download")
        if self.one_time_use_enforced is not True:
            raise ValueError("one_time_use_enforced must remain true")
        object.__setattr__(self, "delivered_at", _freeze_execution_time(self.delivered_at, "delivered_at"))


class HrDataExportExecutionAuthority(Protocol):
    """Host contract for fresh export-specific authorization and policy resolution."""

    def verify_export(
        self,
        *,
        review: HrDataExportReviewPacket,
        review_digest: str,
        requested_at: datetime,
    ) -> object:
        """Return current export-specific authorization and human-approval evidence."""


class HrDataExportMaterializer(Protocol):
    """Host contract that reads only the exact authorized HR field scope."""

    def materialize_export(self, *, verification: HrDataExportExecutionVerification) -> object:
        """Return bounded ephemeral export bytes for the verified scope."""


class HrDataExportAuditPort(Protocol):
    """Host contract for durable immutable audit/outbox evidence before delivery."""

    def append_pre_delivery_audit(
        self,
        *,
        verification: HrDataExportExecutionVerification,
        artifact: HrDataExportArtifact,
        recorded_at: datetime,
    ) -> object:
        """Commit one value-minimized audit receipt before outbound delivery."""


class HrDataExportEgressPort(Protocol):
    """Host contract for one-time authenticated delivery of already-audited bytes."""

    def publish_one_time_download(
        self,
        *,
        verification: HrDataExportExecutionVerification,
        artifact: HrDataExportArtifact,
        audit_receipt: HrDataExportAuditReceipt,
        published_at: datetime,
    ) -> object:
        """Publish the exact audited bytes and return one-time egress evidence."""


@dataclass(frozen=True, slots=True, weakref_slot=True, repr=False, init=False, eq=False)
class HrDataExportExecutionReceipt:
    """Value-minimized successful export receipt issued only by governed orchestration."""

    tenant_record_id: str
    export_execution_reference: str
    export_review_reference: str
    export_review_digest: str
    execution_authorization_reference: str
    execution_authorization_digest: str
    human_approval_reference: str
    human_approval_digest: str
    artifact_sha256_digest: str
    artifact_byte_length: int
    audit_event_reference: str
    egress_reference: str
    destination_kind: str
    one_time_use_enforced: bool
    audited_at: datetime
    delivered_at: datetime
    export_state: str
    contains_pii_values: bool

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Prevent receipt subtypes from redefining sealed canonical evidence."""
        raise TypeError("HrDataExportExecutionReceipt must not be subclassed")

    def __init__(
        self,
        *,
        tenant_record_id: str,
        export_execution_reference: str,
        export_review_reference: str,
        export_review_digest: str,
        execution_authorization_reference: str,
        execution_authorization_digest: str,
        human_approval_reference: str,
        human_approval_digest: str,
        artifact_sha256_digest: str,
        artifact_byte_length: int,
        audit_event_reference: str,
        egress_reference: str,
        destination_kind: str,
        one_time_use_enforced: bool,
        audited_at: datetime,
        delivered_at: datetime,
        _issuance_token: object | None = None,
    ) -> None:
        """Issue only from governed orchestration and seal the value-minimized payload externally."""
        if _issuance_token is not _ISSUANCE_TOKEN:
            raise TypeError("HrDataExportExecutionReceipt must be issued by governed export execution")
        object.__setattr__(self, "tenant_record_id", tenant_record_id)
        object.__setattr__(self, "export_execution_reference", export_execution_reference)
        object.__setattr__(self, "export_review_reference", export_review_reference)
        object.__setattr__(self, "export_review_digest", export_review_digest)
        object.__setattr__(self, "execution_authorization_reference", execution_authorization_reference)
        object.__setattr__(self, "execution_authorization_digest", execution_authorization_digest)
        object.__setattr__(self, "human_approval_reference", human_approval_reference)
        object.__setattr__(self, "human_approval_digest", human_approval_digest)
        object.__setattr__(self, "artifact_sha256_digest", artifact_sha256_digest)
        object.__setattr__(self, "artifact_byte_length", artifact_byte_length)
        object.__setattr__(self, "audit_event_reference", audit_event_reference)
        object.__setattr__(self, "egress_reference", egress_reference)
        object.__setattr__(self, "destination_kind", destination_kind)
        object.__setattr__(self, "one_time_use_enforced", one_time_use_enforced)
        object.__setattr__(self, "audited_at", audited_at)
        object.__setattr__(self, "delivered_at", delivered_at)
        object.__setattr__(self, "export_state", _EXPORT_STATE)
        object.__setattr__(self, "contains_pii_values", False)
        canonical = self._canonical_json_unsealed()
        with _RECEIPT_SEALS_LOCK:
            _RECEIPT_SEALS[self] = sha256(canonical.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        """Redact durable authorization, audit and egress correlations from routine logs."""
        return "HrDataExportExecutionReceipt(<redacted>)"

    def _payload(self) -> dict[str, object]:
        """Snapshot the value-minimized durable receipt payload from issued built-in primitives."""
        audited_at = _validate_frozen_timestamp(self.audited_at)
        delivered_at = _validate_frozen_timestamp(self.delivered_at)
        return {
            "artifact_byte_length": self.artifact_byte_length,
            "artifact_sha256_digest": self.artifact_sha256_digest,
            "audit_event_reference": self.audit_event_reference,
            "audited_at": audited_at.isoformat().replace("+00:00", "Z"),
            "contains_pii_values": self.contains_pii_values,
            "delivered_at": delivered_at.isoformat().replace("+00:00", "Z"),
            "destination_kind": self.destination_kind,
            "egress_reference": self.egress_reference,
            "execution_authorization_digest": self.execution_authorization_digest,
            "execution_authorization_reference": self.execution_authorization_reference,
            "export_execution_reference": self.export_execution_reference,
            "export_review_digest": self.export_review_digest,
            "export_review_reference": self.export_review_reference,
            "export_state": self.export_state,
            "human_approval_digest": self.human_approval_digest,
            "human_approval_reference": self.human_approval_reference,
            "one_time_use_enforced": self.one_time_use_enforced,
            "tenant_record_id": self.tenant_record_id,
        }

    def _canonical_json_unsealed(self) -> str:
        """Serialize one payload snapshot without consulting the external issuance seal."""
        return json.dumps(self._payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def canonical_json(self) -> str:
        """Return sealed deterministic JSON or fail closed after any post-issuance rewrite."""
        try:
            canonical = self._canonical_json_unsealed()
        except (AttributeError, TypeError, ValueError) as exc:
            raise HrDataExportExecutionError("export execution receipt is invalid or tampered") from exc
        with _RECEIPT_SEALS_LOCK:
            seal = _RECEIPT_SEALS.get(self)
        if seal is None or sha256(canonical.encode("utf-8")).hexdigest() != seal:
            raise HrDataExportExecutionError("export execution receipt was tampered after issuance")
        return canonical

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact sealed value-minimized receipt JSON."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


_RECEIPT_SEALS: weakref.WeakKeyDictionary[HrDataExportExecutionReceipt, str] = weakref.WeakKeyDictionary()


def _validate_authority_scope(
    verification: HrDataExportExecutionVerification,
    *,
    tenant_record_id: str,
    export_review_reference: str,
    review_digest: str,
    resource_kind: str,
    resource_reference: str,
    requested_fields: tuple[str, ...],
    export_format_code: str,
    destination_kind: str,
) -> None:
    """Require the authority result to bind exactly the pre-call reviewed scope snapshot."""
    if (
        verification.tenant_record_id != tenant_record_id
        or verification.export_review_reference != export_review_reference
        or verification.export_review_digest != review_digest
        or verification.resource_kind != resource_kind
        or verification.resource_reference != resource_reference
        or verification.requested_fields != requested_fields
        or verification.export_format_code != export_format_code
        or verification.destination_kind != destination_kind
    ):
        raise HrDataExportExecutionError("authoritative export verification scope does not match review")
    if verification.retention_state != "retention_permits_export" or verification.legal_hold_state != "no_legal_hold_block":
        raise HrDataExportExecutionError("authoritative export policy blocks egress")


def _validate_artifact_scope(
    artifact: HrDataExportArtifact,
    verification: HrDataExportExecutionVerification,
) -> None:
    """Require materialized bytes to match the exact reviewed field and media shape."""
    if artifact.field_names != verification.requested_fields:
        raise HrDataExportExecutionError("materialized export field scope does not match verification")
    if artifact.content_type != _expected_content_type(verification.export_format_code):
        raise HrDataExportExecutionError("materialized export content type does not match verification")


def _validate_audit_receipt(
    receipt: HrDataExportAuditReceipt,
    verification: HrDataExportExecutionVerification,
    artifact: HrDataExportArtifact,
    recorded_at: datetime,
) -> None:
    """Require pre-delivery audit evidence to bind the exact authorization and artifact."""
    if (
        receipt.tenant_record_id != verification.tenant_record_id
        or receipt.export_execution_reference != verification.export_execution_reference
        or receipt.export_review_digest != verification.export_review_digest
        or receipt.execution_authorization_digest != verification.execution_authorization_digest
        or receipt.human_approval_digest != verification.human_approval_digest
        or receipt.artifact_sha256_digest != artifact.sha256_digest
        or receipt.artifact_byte_length != artifact.byte_length
        or receipt.recorded_at != recorded_at
        or receipt.audit_state != _AUDIT_STATE
    ):
        raise HrDataExportExecutionError("pre-delivery audit receipt does not bind exact export evidence")


def _validate_egress_receipt(
    receipt: HrDataExportEgressReceipt,
    verification: HrDataExportExecutionVerification,
    artifact: HrDataExportArtifact,
    audit_receipt: HrDataExportAuditReceipt,
    published_at: datetime,
    observed_at: datetime,
) -> None:
    """Require one-time egress evidence to bind the exact audited artifact and authorization window."""
    if (
        receipt.tenant_record_id != verification.tenant_record_id
        or receipt.export_execution_reference != verification.export_execution_reference
        or receipt.artifact_sha256_digest != artifact.sha256_digest
        or receipt.artifact_byte_length != artifact.byte_length
        or receipt.audit_event_reference != audit_receipt.audit_event_reference
        or receipt.destination_kind != verification.destination_kind
        or receipt.one_time_use_enforced is not True
        or receipt.delivered_at < published_at
        or receipt.delivered_at < verification.verified_at
        or receipt.delivered_at >= verification.authorization_expires_at
        or receipt.delivered_at > observed_at
    ):
        raise HrDataExportExecutionError("egress receipt does not bind exact audited export evidence")


def execute_reviewed_hr_export(
    *,
    review: HrDataExportReviewPacket,
    authority: HrDataExportExecutionAuthority,
    materializer: HrDataExportMaterializer,
    audit_port: HrDataExportAuditPort,
    egress_port: HrDataExportEgressPort,
    now_provider: Callable[[], datetime],
) -> HrDataExportExecutionReceipt:
    """Freshly authorize, materialize, audit and one-time-deliver one reviewed HR export.

    Reviewed scope is snapshotted before authority work and checked again after that call.
    Authorization freshness is checked before protected materialization, after materialization,
    and immediately before host egress. The returned host receipt must prove that actual
    delivery occurred inside the same authorization window and no later than post-egress
    observation. Immutable audit evidence must validate before the egress port can receive
    bytes. Returned durable evidence contains no raw HR values.
    """
    if type(review) is not HrDataExportReviewPacket:
        raise TypeError("review must be the exact governed HrDataExportReviewPacket type")
    review_json = review.canonical_json()
    review_digest = sha256(review_json.encode("utf-8")).hexdigest()
    tenant_record_id = review.tenant_record_id
    export_review_reference = review.export_review_reference
    resource_kind = review.resource_kind
    resource_reference = review.resource_reference
    requested_fields = review.requested_fields
    export_format_code = review.export_format_code
    destination_kind = review.destination_kind

    requested_at = _clock_now(now_provider)
    verification_result = authority.verify_export(
        review=review,
        review_digest=review_digest,
        requested_at=requested_at,
    )
    if review.canonical_json() != review_json:
        raise HrDataExportExecutionError("review evidence changed across authoritative verification")
    if type(verification_result) is not HrDataExportExecutionVerification:
        raise HrDataExportExecutionError("authority returned invalid export verification evidence")
    verification = verification_result
    _validate_authority_scope(
        verification,
        tenant_record_id=tenant_record_id,
        export_review_reference=export_review_reference,
        review_digest=review_digest,
        resource_kind=resource_kind,
        resource_reference=resource_reference,
        requested_fields=requested_fields,
        export_format_code=export_format_code,
        destination_kind=destination_kind,
    )
    _require_current_authorization(verification, requested_at)

    artifact_result = materializer.materialize_export(verification=verification)
    if type(artifact_result) is not HrDataExportArtifact:
        raise HrDataExportExecutionError("materializer returned invalid export artifact")
    artifact = artifact_result
    _validate_artifact_scope(artifact, verification)
    audited_at = _clock_now(now_provider)
    _require_current_authorization(verification, audited_at)

    audit_result = audit_port.append_pre_delivery_audit(
        verification=verification,
        artifact=artifact,
        recorded_at=audited_at,
    )
    if type(audit_result) is not HrDataExportAuditReceipt:
        raise HrDataExportExecutionError("audit port returned invalid pre-delivery audit receipt")
    audit_receipt = audit_result
    _validate_audit_receipt(audit_receipt, verification, artifact, audited_at)
    published_at = _clock_now(now_provider)
    _require_current_authorization(verification, published_at)

    egress_result = egress_port.publish_one_time_download(
        verification=verification,
        artifact=artifact,
        audit_receipt=audit_receipt,
        published_at=published_at,
    )
    observed_at = _clock_now(now_provider)
    if type(egress_result) is not HrDataExportEgressReceipt:
        raise HrDataExportExecutionError("egress port returned invalid one-time-delivery receipt")
    egress_receipt = egress_result
    _validate_egress_receipt(
        egress_receipt,
        verification,
        artifact,
        audit_receipt,
        published_at,
        observed_at,
    )
    return HrDataExportExecutionReceipt(
        tenant_record_id=verification.tenant_record_id,
        export_execution_reference=verification.export_execution_reference,
        export_review_reference=verification.export_review_reference,
        export_review_digest=verification.export_review_digest,
        execution_authorization_reference=verification.execution_authorization_reference,
        execution_authorization_digest=verification.execution_authorization_digest,
        human_approval_reference=verification.human_approval_reference,
        human_approval_digest=verification.human_approval_digest,
        artifact_sha256_digest=artifact.sha256_digest,
        artifact_byte_length=artifact.byte_length,
        audit_event_reference=audit_receipt.audit_event_reference,
        egress_reference=egress_receipt.egress_reference,
        destination_kind=verification.destination_kind,
        one_time_use_enforced=True,
        audited_at=audit_receipt.recorded_at,
        delivered_at=egress_receipt.delivered_at,
        _issuance_token=_ISSUANCE_TOKEN,
    )
