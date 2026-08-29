"""Value-minimized, human-reviewed control evidence for HR data exports.

This module deliberately does not read protected HR fields or construct an export.
It records the exact tenant/resource/field scope that a human reviewer may ask the
authoritative People boundary to re-resolve. Keyverse remains the identity owner;
Orgmetra remains the HR authorization and export-control owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from threading import Lock
from uuid import UUID
import weakref

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_PURPOSE_CODE = "hr_data_export_review"
_ALLOWED_REASON_CODES = frozenset(
    {
        "employee_access_request",
        "regulatory_disclosure",
        "contractual_hr_export",
    }
)
_ALLOWED_FORMAT_CODES = frozenset({"csv", "json"})
_DESTINATION_KIND = "authenticated_one_time_download"
_SCOPE_VERIFICATION_STATE = "requires_authoritative_resolution"
_EXPORT_STATE = "not_authorized_to_export"
_NEXT_ACTION = (
    "Re-resolve the authenticated actor, exact HR resource, purpose-bound policy, and requested "
    "field subset through the authoritative Orgmetra People authorization boundary; record "
    "accountable human approval and immutable audit evidence before constructing a one-time "
    "authenticated export, and do not export after the reviewed authorization expires or drifts."
)
_MAX_UUID_INT = (1 << 128) - 1
_PACKET_SEALS_LOCK = Lock()


def _validate_operational_uuid(value: object, field_name: str) -> None:
    """Require canonical non-sentinel built-in UUID text for authoritative identities."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical operational UUID text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field_name} must be canonical operational UUID text") from exc
    if str(parsed) != value or parsed.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be canonical non-sentinel operational UUID text")


def _validate_reference(value: object, expected_namespace: str, field_name: str) -> None:
    """Require an exact namespace followed by one canonical opaque UUIDv4."""
    message = f"{field_name} must be an opaque {expected_namespace}: UUIDv4 reference"
    if type(value) is not str:
        raise ValueError(message)
    namespace, separator, suffix = value.partition(":")
    if separator != ":" or namespace != expected_namespace or not suffix:
        raise ValueError(message)
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(message) from exc
    if str(parsed) != suffix or parsed.version != 4:
        raise ValueError(message)


def _validate_code(value: object, field_name: str) -> None:
    """Require exact built-in descriptive lower snake_case governance text."""
    if type(value) is not str or _CODE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be descriptive lower snake_case built-in text")


def _validate_resource_kind(value: object) -> None:
    """Require a bounded descriptive resource namespace."""
    if type(value) is not str or len(value) > 64 or _CODE_PATTERN.fullmatch(value) is None:
        raise ValueError("resource_kind must be bounded two-or-more-word lower snake_case")


def _validate_digest(value: object, field_name: str) -> None:
    """Require exact lowercase SHA-256 evidence text."""
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_version(value: object) -> None:
    """Require a bounded immutable authorization-policy version token."""
    if (
        type(value) is not str
        or len(value) > 128
        or _VERSION_PATTERN.fullmatch(value) is None
    ):
        raise ValueError(
            "authorization_policy_version_code must be a bounded whitespace-free version token"
        )


def _validate_requested_fields(values: object) -> None:
    """Require one deterministic, bounded, explicit tuple of field names."""
    if type(values) is not tuple:
        raise ValueError("requested_fields must be an exact tuple")
    if not values:
        raise ValueError("requested_fields must not be empty")
    if len(values) > 64:
        raise ValueError("requested_fields must contain at most 64 fields")
    for value in values:
        if type(value) is not str or _CODE_PATTERN.fullmatch(value) is None:
            raise ValueError("requested_fields must contain explicit lower snake_case built-in text")
    if tuple(sorted(values)) != values:
        raise ValueError("requested_fields must be sorted for deterministic review evidence")
    if len(set(values)) != len(values):
        raise ValueError("requested_fields must not contain duplicates")


def _freeze_timestamp(value: object) -> datetime:
    """Detach one exact datetime from caller-controlled timezone-provider behavior."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("generated_at must be an exact timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise ValueError("generated_at timezone offset could not be resolved safely") from exc
    if type(offset) is not timedelta:
        raise ValueError("generated_at must provide one concrete UTC offset")
    naive_value = value.replace(tzinfo=None)
    return (naive_value - offset).replace(tzinfo=timezone.utc)


def _validate_frozen_timestamp(value: object) -> None:
    """Require the stored audit instant to be the detached built-in UTC representation."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("generated_at must remain the canonical built-in UTC datetime")


def _validate_evidence_version(value: object) -> None:
    """Require a bounded positive exact integer evidence version."""
    if type(value) is not int or value < 1 or value > 2_147_483_647:
        raise ValueError("evidence_version must be an integer from 1 through 2147483647")


def _validate_allowed_text(
    value: object,
    allowed_values: frozenset[str],
    field_name: str,
) -> None:
    """Require exact built-in text from one closed reviewed vocabulary."""
    if type(value) is not str or value not in allowed_values:
        raise ValueError(f"{field_name} must use the reviewed export-control vocabulary")


def _validate_fixed_text(value: object, expected_value: str, field_name: str) -> None:
    """Require one exact built-in fixed governance value."""
    if type(value) is not str or value != expected_value:
        raise ValueError(f"{field_name} must remain {expected_value}")


@dataclass(frozen=True, slots=True, weakref_slot=True, repr=False, eq=False)
class HrDataExportReviewPacket:
    """Immutable, value-minimized pre-export review evidence.

    The packet is deliberately not an export authorization. It carries only
    correlation, reviewed field names, provenance, and human-review metadata.
    The authoritative People boundary must re-resolve scope before any HR value
    leaves its owning service. A process-local external creation seal prevents
    low-level mutation from turning one reviewed correlation into a second truth;
    durable cross-process uniqueness remains the persistence/audit owner's job.
    """

    tenant_record_id: str
    export_review_reference: str
    resource_kind: str
    resource_reference: str
    authorization_evidence_reference: str
    authorization_evidence_digest: str
    authorization_policy_version_code: str
    requester_reference: str
    reviewer_reference: str
    purpose_code: str
    reason_code: str
    requested_fields: tuple[str, ...]
    export_format_code: str
    destination_kind: str
    generated_at: datetime
    evidence_version: int = 1
    contains_pii_values: bool = False
    human_review_required: bool = True
    scope_verification_state: str = _SCOPE_VERIFICATION_STATE
    export_state: str = _EXPORT_STATE
    next_action: str = _NEXT_ACTION

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Prevent validation-bypassing runtime subtypes at the export-control boundary."""
        raise TypeError("HrDataExportReviewPacket must not be subclassed")

    def __repr__(self) -> str:
        """Never emit correlating HR export evidence through routine object representation."""
        return "HrDataExportReviewPacket(<redacted>)"

    def __post_init__(self) -> None:
        """Validate every trust-bearing field, freeze time, and seal creation evidence."""
        self._assert_integrity(normalize_timestamp=True)
        canonical = self._canonical_json_unsealed()
        with _PACKET_SEALS_LOCK:
            _PACKET_SEALS[self] = sha256(canonical.encode("utf-8")).hexdigest()

    def _assert_integrity(self, *, normalize_timestamp: bool) -> None:
        """Fail closed before construction or canonical audit serialization."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.export_review_reference,
            "export_review",
            "export_review_reference",
        )
        _validate_resource_kind(self.resource_kind)
        _validate_reference(
            self.resource_reference,
            self.resource_kind,
            "resource_reference",
        )
        _validate_reference(
            self.authorization_evidence_reference,
            "authorization_decision",
            "authorization_evidence_reference",
        )
        _validate_digest(
            self.authorization_evidence_digest,
            "authorization_evidence_digest",
        )
        _validate_version(self.authorization_policy_version_code)
        _validate_reference(self.requester_reference, "actor", "requester_reference")
        _validate_reference(self.reviewer_reference, "actor", "reviewer_reference")
        if self.requester_reference == self.reviewer_reference:
            raise ValueError("reviewer_reference must identify a different accountable actor")
        _validate_code(self.purpose_code, "purpose_code")
        _validate_fixed_text(self.purpose_code, _PURPOSE_CODE, "purpose_code")
        _validate_code(self.reason_code, "reason_code")
        _validate_allowed_text(self.reason_code, _ALLOWED_REASON_CODES, "reason_code")
        _validate_requested_fields(self.requested_fields)
        _validate_allowed_text(
            self.export_format_code,
            _ALLOWED_FORMAT_CODES,
            "export_format_code",
        )
        _validate_fixed_text(
            self.destination_kind,
            _DESTINATION_KIND,
            "destination_kind",
        )
        if normalize_timestamp:
            object.__setattr__(self, "generated_at", _freeze_timestamp(self.generated_at))
        else:
            _validate_frozen_timestamp(self.generated_at)
        if self.generated_at > datetime.now(timezone.utc):
            raise ValueError("generated_at cannot be in the future")
        _validate_evidence_version(self.evidence_version)
        if self.contains_pii_values is not False:
            raise ValueError("HR data export review packet must not contain PII values")
        if self.human_review_required is not True:
            raise ValueError("human review is mandatory before HR data export")
        _validate_fixed_text(
            self.scope_verification_state,
            _SCOPE_VERIFICATION_STATE,
            "scope_verification_state",
        )
        _validate_fixed_text(self.export_state, _EXPORT_STATE, "export_state")
        _validate_fixed_text(self.next_action, _NEXT_ACTION, "next_action")

    def _payload(self) -> dict[str, object]:
        """Return the exact value-minimized payload after current-field validation."""
        self._assert_integrity(normalize_timestamp=False)
        return {
            "authorization_evidence_digest": self.authorization_evidence_digest,
            "authorization_evidence_reference": self.authorization_evidence_reference,
            "authorization_policy_version_code": self.authorization_policy_version_code,
            "contains_pii_values": self.contains_pii_values,
            "destination_kind": self.destination_kind,
            "evidence_version": self.evidence_version,
            "export_format_code": self.export_format_code,
            "export_review_reference": self.export_review_reference,
            "export_state": self.export_state,
            "generated_at": self.generated_at.isoformat().replace("+00:00", "Z"),
            "human_review_required": self.human_review_required,
            "next_action": self.next_action,
            "purpose_code": self.purpose_code,
            "reason_code": self.reason_code,
            "requested_fields": self.requested_fields,
            "requester_reference": self.requester_reference,
            "resource_kind": self.resource_kind,
            "resource_reference": self.resource_reference,
            "reviewer_reference": self.reviewer_reference,
            "scope_verification_state": self.scope_verification_state,
            "tenant_record_id": self.tenant_record_id,
        }

    def _canonical_json_unsealed(self) -> str:
        """Serialize one current validated payload without consulting the creation seal."""
        return json.dumps(self._payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def canonical_json(self) -> str:
        """Return deterministic PII-value-free JSON only for the originally issued evidence."""
        canonical = self._canonical_json_unsealed()
        with _PACKET_SEALS_LOCK:
            seal = _PACKET_SEALS.get(self)
        if seal is None or sha256(canonical.encode("utf-8")).hexdigest() != seal:
            raise ValueError("HR data export review evidence was altered after issuance")
        return canonical

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 export-review evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


_PACKET_SEALS: weakref.WeakKeyDictionary[HrDataExportReviewPacket, str] = weakref.WeakKeyDictionary()
