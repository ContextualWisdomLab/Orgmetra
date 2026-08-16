"""Governed CloudEvents-compatible audit/outbox envelopes for Orgmetra writes.

The module creates a PII-minimized event envelope that carries only opaque
resource references plus the actor, purpose, reason, evidence version, and
human-confirmation metadata needed to explain a write later. Persistence is a
separate boundary: callers store the canonical envelope and digest in the
Orgmetra-owned transactional outbox/audit store in the same transaction as the
business mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

_SOURCE_SERVICE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_EVENT_TYPE_PATTERN = re.compile(r"^orgmetra(?:\.[a-z][a-z0-9_]*){2,}$")
_OPAQUE_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_VERSION_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_REQUIRED_TEXT_FIELDS = (
    "resource_reference",
    "actor_reference",
    "purpose_code",
    "reason_code",
    "evidence_version_code",
    "result_code",
)


@dataclass(frozen=True, slots=True)
class AuditOutboxEvent:
    """One immutable governance envelope for an Orgmetra domain mutation.

    High-impact employment decisions require ``confirmation_reference``. The
    emitted CloudEvent intentionally excludes mutable HR payload fields so the
    audit/outbox record can be retained and shared without becoming a shadow
    system of record for names, compensation, or other necessary PII.
    """

    event_id: UUID
    tenant_record_id: UUID
    source_service: str
    event_type: str
    resource_reference: str
    actor_reference: str
    purpose_code: str
    reason_code: str
    evidence_version_code: str
    result_code: str
    occurred_at: datetime
    high_impact: bool
    confirmation_reference: str | None = None

    def __post_init__(self) -> None:
        """Reject envelopes that cannot provide accountable, portable audit evidence."""
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware.")
        if self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must resolve to a UTC offset.")
        if _SOURCE_SERVICE_PATTERN.fullmatch(self.source_service) is None:
            raise ValueError("source_service must contain two or more lower snake_case words.")
        if _EVENT_TYPE_PATTERN.fullmatch(self.event_type) is None:
            raise ValueError("event_type must use a canonical lower-case orgmetra.<context>.<event> namespace.")
        for field_name in _REQUIRED_TEXT_FIELDS:
            value = getattr(self, field_name)
            if not value.strip():
                raise ValueError(f"{field_name} must not be blank.")
        for field_name in ("resource_reference", "actor_reference"):
            if _OPAQUE_REFERENCE_PATTERN.fullmatch(getattr(self, field_name)) is None:
                raise ValueError(f"{field_name} must be a namespaced opaque reference.")
        for field_name in ("purpose_code", "reason_code", "result_code"):
            if _CODE_PATTERN.fullmatch(getattr(self, field_name)) is None:
                raise ValueError(f"{field_name} must be lower snake_case code data.")
        if _VERSION_CODE_PATTERN.fullmatch(self.evidence_version_code) is None:
            raise ValueError("evidence_version_code must be a whitespace-free version token.")
        if self.confirmation_reference is not None:
            if not self.confirmation_reference.strip():
                raise ValueError("confirmation_reference must not be blank when supplied.")
            if _OPAQUE_REFERENCE_PATTERN.fullmatch(self.confirmation_reference) is None:
                raise ValueError("confirmation_reference must be a namespaced opaque reference.")
        if self.high_impact and self.confirmation_reference is None:
            raise ValueError("high-impact events require confirmation_reference.")

    def to_cloudevent(self) -> dict[str, object]:
        """Return the canonical structured CloudEvent 1.0 envelope.

        Returns:
            A JSON-serializable mapping carrying governance extensions and a
            PII-minimized result body. Persist this mapping atomically with the
            owning business write before asynchronous delivery.
        """
        occurred_utc = self.occurred_at.astimezone(timezone.utc)
        envelope: dict[str, object] = {
            "specversion": "1.0",
            "id": str(self.event_id),
            "source": f"urn:orgmetra:{self.source_service}",
            "type": self.event_type,
            "subject": self.resource_reference,
            "time": occurred_utc.isoformat().replace("+00:00", "Z"),
            "datacontenttype": "application/json",
            "orgmetratenant": str(self.tenant_record_id),
            "orgmetraactor": self.actor_reference,
            "orgmetrapurpose": self.purpose_code,
            "orgmetrareason": self.reason_code,
            "orgmetraevidence": self.evidence_version_code,
            "data": {
                "result_code": self.result_code,
                "high_impact": self.high_impact,
            },
        }
        if self.confirmation_reference is not None:
            envelope["orgmetraconfirmation"] = self.confirmation_reference
        return envelope

    def content_digest(self) -> str:
        """Return a deterministic SHA-256 digest of the canonical event envelope."""
        canonical = json.dumps(
            self.to_cloudevent(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return sha256(canonical).hexdigest()
