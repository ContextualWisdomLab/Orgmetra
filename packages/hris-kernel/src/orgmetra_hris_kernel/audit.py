"""Governed CloudEvents-compatible audit/outbox envelopes for Orgmetra writes.

The module creates a PII-minimized event envelope that carries only opaque
resource references plus the actor, purpose, reason, evidence version, and
human-confirmation metadata needed to explain a write later. Persistence is a
separate boundary: callers store the canonical envelope and digest in the
Orgmetra-owned transactional outbox/audit store in the same transaction as the
business mutation.
"""

from __future__ import annotations

from collections import namedtuple
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

_SOURCE_SERVICE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_EVENT_TYPE_PATTERN = re.compile(r"^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$")
_OPAQUE_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_VERSION_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_MAX_UUID_INT = (1 << 128) - 1
_REQUIRED_TEXT_FIELDS = (
    "resource_reference",
    "actor_reference",
    "purpose_code",
    "reason_code",
    "evidence_version_code",
    "result_code",
)
_ALL_REQUIRED_TEXT_FIELDS = ("source_service", "event_type", *_REQUIRED_TEXT_FIELDS)
_AUDIT_EVENT_FIELDS = (
    "event_id",
    "tenant_record_id",
    "source_service",
    "event_type",
    "resource_reference",
    "actor_reference",
    "purpose_code",
    "reason_code",
    "evidence_version_code",
    "result_code",
    "occurred_at",
    "high_impact",
    "confirmation_reference",
)


def _freeze_timestamp(value: datetime) -> datetime:
    """Detach caller-controlled timezone behavior as one immutable UTC instant."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("occurred_at must be an exact timezone-aware datetime.")
    try:
        offset = value.utcoffset()
    except Exception as exc:  # noqa: BLE001 - normalize provider behavior at trust boundary.
        raise ValueError("occurred_at must resolve to a UTC offset.") from exc
    if offset is None or type(offset) is not timedelta:
        raise ValueError("occurred_at must resolve to a UTC offset.")
    try:
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except OverflowError as exc:
        raise ValueError("occurred_at must be a representable timezone-aware datetime.") from exc


def _canonical_timestamp(value: datetime) -> str:
    """Render only a previously detached built-in UTC instant as RFC 3339 text."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("occurred_at must be an exact timezone-aware datetime.")
    return value.isoformat().replace("+00:00", "Z")


def _validate_event_snapshot(
    *,
    event_id: object,
    tenant_record_id: object,
    source_service: object,
    event_type: object,
    resource_reference: object,
    actor_reference: object,
    purpose_code: object,
    reason_code: object,
    evidence_version_code: object,
    result_code: object,
    occurred_at: object,
    high_impact: object,
    confirmation_reference: object,
) -> None:
    """Validate one captured audit value set without executing untrusted coercions."""
    if type(event_id) is not UUID:
        raise ValueError("event_id must be a UUID.")
    if type(tenant_record_id) is not UUID:
        raise ValueError("tenant_record_id must be a UUID.")
    if event_id.int == 0:
        raise ValueError("event_id must not be the reserved nil UUID.")
    if tenant_record_id.int == 0:
        raise ValueError("tenant_record_id must not be the reserved nil UUID.")
    if event_id.int == _MAX_UUID_INT:
        raise ValueError("event_id must not be the reserved max UUID.")
    if tenant_record_id.int == _MAX_UUID_INT:
        raise ValueError("tenant_record_id must not be the reserved max UUID.")
    if type(occurred_at) is not datetime:
        raise ValueError("occurred_at must be a datetime.")
    if type(high_impact) is not bool:
        raise ValueError("high_impact must be a boolean.")
    text_values = {
        "source_service": source_service,
        "event_type": event_type,
        "resource_reference": resource_reference,
        "actor_reference": actor_reference,
        "purpose_code": purpose_code,
        "reason_code": reason_code,
        "evidence_version_code": evidence_version_code,
        "result_code": result_code,
    }
    for field_name in _ALL_REQUIRED_TEXT_FIELDS:
        if type(text_values[field_name]) is not str:
            raise ValueError(f"{field_name} must be a string.")
    if confirmation_reference is not None and type(confirmation_reference) is not str:
        raise ValueError("confirmation_reference must be a string when supplied.")

    if _SOURCE_SERVICE_PATTERN.fullmatch(source_service) is None:
        raise ValueError("source_service must contain two or more lower snake_case words.")
    if _EVENT_TYPE_PATTERN.fullmatch(event_type) is None:
        raise ValueError(
            "event_type must use a canonical lower-case orgmetra.<context>.<event> namespace."
        )
    for field_name in _REQUIRED_TEXT_FIELDS:
        value = text_values[field_name]
        if not value.strip():
            raise ValueError(f"{field_name} must not be blank.")
    for field_name in ("resource_reference", "actor_reference"):
        if _OPAQUE_REFERENCE_PATTERN.fullmatch(text_values[field_name]) is None:
            raise ValueError(f"{field_name} must be a namespaced opaque reference.")
    for field_name in ("purpose_code", "reason_code", "result_code"):
        if _CODE_PATTERN.fullmatch(text_values[field_name]) is None:
            raise ValueError(f"{field_name} must be lower snake_case code data.")
    if _VERSION_CODE_PATTERN.fullmatch(evidence_version_code) is None:
        raise ValueError("evidence_version_code must be a whitespace-free version token.")
    if confirmation_reference is not None:
        if not confirmation_reference.strip():
            raise ValueError("confirmation_reference must not be blank when supplied.")
        if _OPAQUE_REFERENCE_PATTERN.fullmatch(confirmation_reference) is None:
            raise ValueError("confirmation_reference must be a namespaced opaque reference.")
    if high_impact and confirmation_reference is None:
        raise ValueError("high-impact events require confirmation_reference.")


_AuditOutboxEventTuple = namedtuple(
    "_AuditOutboxEventTuple",
    _AUDIT_EVENT_FIELDS,
    module=__name__,
)


class AuditOutboxEvent(_AuditOutboxEventTuple):
    """One structurally immutable governance envelope for an Orgmetra mutation.

    High-impact employment decisions require ``confirmation_reference``. The
    emitted CloudEvent intentionally excludes mutable HR payload fields so the
    audit/outbox record can be retained and shared without becoming a shadow
    system of record for names, compensation, or other necessary PII. Reserved
    Nil and Max UUID sentinels are rejected before persistence.

    Canonical evidence is held directly by the tuple value object. There is no
    process-local mutable issuance registry to reset or overwrite. Persistence
    authorization remains a separate service/port responsibility.
    """

    __slots__ = ()

    def __new__(
        cls,
        event_id: UUID,
        tenant_record_id: UUID,
        source_service: str,
        event_type: str,
        resource_reference: str,
        actor_reference: str,
        purpose_code: str,
        reason_code: str,
        evidence_version_code: str,
        result_code: str,
        occurred_at: datetime,
        high_impact: bool,
        confirmation_reference: str | None = None,
    ) -> AuditOutboxEvent:
        """Validate, detach time-provider behavior, and construct one immutable value."""
        if cls is not AuditOutboxEvent:
            raise TypeError("AuditOutboxEvent must be constructed as the exact canonical type.")
        _validate_event_snapshot(
            event_id=event_id,
            tenant_record_id=tenant_record_id,
            source_service=source_service,
            event_type=event_type,
            resource_reference=resource_reference,
            actor_reference=actor_reference,
            purpose_code=purpose_code,
            reason_code=reason_code,
            evidence_version_code=evidence_version_code,
            result_code=result_code,
            occurred_at=occurred_at,
            high_impact=high_impact,
            confirmation_reference=confirmation_reference,
        )
        frozen_occurred_at = _freeze_timestamp(occurred_at)
        return super().__new__(
            cls,
            event_id,
            tenant_record_id,
            source_service,
            event_type,
            resource_reference,
            actor_reference,
            purpose_code,
            reason_code,
            evidence_version_code,
            result_code,
            frozen_occurred_at,
            high_impact,
            confirmation_reference,
        )

    def __post_init__(self) -> None:
        """Reject compatibility-style re-entry; tuple construction already issued evidence."""
        raise ValueError("audit event identity has already issued canonical evidence.")

    def to_cloudevent(self) -> dict[str, object]:
        """Return the canonical structured CloudEvent 1.0 envelope.

        Returns:
            A JSON-serializable mapping carrying governance extensions and a
            PII-minimized result body. Persist this mapping atomically with the
            owning business write before asynchronous delivery.
        """
        if type(self) is not AuditOutboxEvent:
            raise ValueError("audit event must be the exact canonical type.")
        event_id = self.event_id
        tenant_record_id = self.tenant_record_id
        source_service = self.source_service
        event_type = self.event_type
        resource_reference = self.resource_reference
        actor_reference = self.actor_reference
        purpose_code = self.purpose_code
        reason_code = self.reason_code
        evidence_version_code = self.evidence_version_code
        result_code = self.result_code
        occurred_at = self.occurred_at
        high_impact = self.high_impact
        confirmation_reference = self.confirmation_reference
        _validate_event_snapshot(
            event_id=event_id,
            tenant_record_id=tenant_record_id,
            source_service=source_service,
            event_type=event_type,
            resource_reference=resource_reference,
            actor_reference=actor_reference,
            purpose_code=purpose_code,
            reason_code=reason_code,
            evidence_version_code=evidence_version_code,
            result_code=result_code,
            occurred_at=occurred_at,
            high_impact=high_impact,
            confirmation_reference=confirmation_reference,
        )
        canonical_time = _canonical_timestamp(occurred_at)
        envelope: dict[str, object] = {
            "specversion": "1.0",
            "id": str(event_id),
            "source": f"urn:orgmetra:{source_service}",
            "type": event_type,
            "subject": resource_reference,
            "time": canonical_time,
            "datacontenttype": "application/json",
            "orgmetratenant": str(tenant_record_id),
            "orgmetraactor": actor_reference,
            "orgmetrapurpose": purpose_code,
            "orgmetrareason": reason_code,
            "orgmetraevidence": evidence_version_code,
            "data": {
                "result_code": result_code,
                "high_impact": high_impact,
            },
        }
        if confirmation_reference is not None:
            envelope["orgmetraconfirmation"] = confirmation_reference
        return envelope

    def canonical_json(self) -> str:
        """Return the exact deterministic UTF-8 JSON text persisted and digested.

        The database verifies the SHA-256 digest over these exact bytes. Callers
        must therefore persist this string directly instead of independently
        serializing :meth:`to_cloudevent` with library-specific defaults.
        """
        return json.dumps(
            self.to_cloudevent(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def content_digest(self) -> str:
        """Return a deterministic SHA-256 digest of the canonical event envelope."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()
