"""Value-minimized external transport delivery receipt evidence for Orgmetra.

The provider receipt is untrusted evidence, not delivery-state mutation authority. Raw
provider payloads, destinations, credentials, and HR values remain outside this packet.
The authoritative host must match this evidence to one live leased outbox attempt before
it can consider a separately governed completion transaction.
"""
from __future__ import annotations

from collections import namedtuple
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RECEIPT_PREFIX = "transport_receipt"
_MAX_INT = 2_147_483_647

_DELIVERY_OUTCOME_CODE = "transport_reported_delivered"
_TRUST_STATE = "untrusted_transport_evidence"
_RECONCILIATION_STATE = "requires_exact_attempt_reconciliation"
_MUTATION_AUTHORITY = "not_authorized_to_mutate_delivery_state"
_NEXT_ACTION = (
    "Reconcile this normalized receipt to the exact live tenant/outbox/audit/target/attempt "
    "under the authoritative Orgmetra lease and purpose-bound authorization boundary; verify "
    "the external receipt artifact against transport_receipt_digest, then persist immutable "
    "audit/outbox evidence atomically before marking delivery complete."
)


def _validate_operational_uuid(value: object, field_name: str) -> str:
    """Return canonical built-in UUID text or fail closed."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be canonical UUID text")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be canonical UUID text") from exc
    if str(parsed) != value or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical operational UUID")
    return value


def _validate_code(value: object, field_name: str) -> str:
    """Return a bounded built-in two-or-more-word lower snake_case code."""
    if type(value) is not str or len(value) > 64 or not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be bounded two-or-more-word lower snake_case")
    return value


def _validate_positive_int(value: object, field_name: str) -> int:
    """Return a positive bounded integer while rejecting booleans."""
    if type(value) is not int or value < 1 or value > _MAX_INT:
        raise ValueError(f"{field_name} must be an integer from 1 through {_MAX_INT}")
    return value


def _validate_receipt_reference(value: object) -> str:
    """Require a built-in Orgmetra-normalized opaque UUIDv4 receipt reference."""
    message = "transport_receipt_reference must be an opaque transport_receipt: UUIDv4 reference"
    if type(value) is not str or len(value) > 160 or not value.startswith(f"{_RECEIPT_PREFIX}:"):
        raise ValueError(message)
    suffix = value.split(":", 1)[1]
    try:
        parsed = UUID(suffix)
    except ValueError as exc:
        raise ValueError(message) from exc
    if str(parsed) != suffix or parsed.version != 4 or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(message)
    return value


def _validate_digest(value: object) -> str:
    """Require built-in lowercase SHA-256 evidence for the external receipt artifact."""
    if type(value) is not str or not _DIGEST_PATTERN.fullmatch(value):
        raise ValueError("transport_receipt_digest must be lowercase SHA-256 hex")
    return value


def _freeze_timestamp(value: object, field_name: str) -> datetime:
    """Detach caller-owned timezone behavior into one built-in UTC datetime."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    try:
        if value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
        normalized = value.astimezone(timezone.utc)
    except Exception as exc:
        if isinstance(exc, ValueError) and str(exc) == f"{field_name} must be timezone-aware":
            raise
        raise ValueError(f"{field_name} must be safely normalizable to UTC") from exc
    return datetime(
        normalized.year,
        normalized.month,
        normalized.day,
        normalized.hour,
        normalized.minute,
        normalized.second,
        normalized.microsecond,
        tzinfo=timezone.utc,
    )


def _canonical_timestamp(value: object, field_name: str) -> str:
    """Return canonical text only for already-frozen built-in UTC evidence."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field_name} must be frozen built-in UTC datetime evidence")
    return value.isoformat().replace("+00:00", "Z")


def _validate_contract(
    *,
    tenant_record_id: object,
    outbox_delivery_record_id: object,
    audit_event_record_id: object,
    delivery_target_code: object,
    delivery_attempt_count: object,
    transport_provider_code: object,
    transport_receipt_reference: object,
    transport_receipt_digest: object,
    transport_delivered_at: object,
    observed_at: object,
    evidence_version: object,
    contains_hr_payload: object,
    contains_destination: object,
    contains_credentials: object,
    delivery_outcome_code: object,
    trust_state: object,
    reconciliation_state: object,
    mutation_authority: object,
    next_action: object,
) -> tuple[str, str]:
    """Revalidate every trust-bearing field, including copy/bypass-created instances."""
    _validate_operational_uuid(tenant_record_id, "tenant_record_id")
    _validate_operational_uuid(outbox_delivery_record_id, "outbox_delivery_record_id")
    _validate_operational_uuid(audit_event_record_id, "audit_event_record_id")
    _validate_code(delivery_target_code, "delivery_target_code")
    _validate_positive_int(delivery_attempt_count, "delivery_attempt_count")
    _validate_code(transport_provider_code, "transport_provider_code")
    _validate_receipt_reference(transport_receipt_reference)
    _validate_digest(transport_receipt_digest)
    transport_delivered_at_utc = _canonical_timestamp(
        transport_delivered_at, "transport_delivered_at"
    )
    observed_at_utc = _canonical_timestamp(observed_at, "observed_at")
    if observed_at < transport_delivered_at:
        raise ValueError("observed_at cannot precede transport_delivered_at")
    _validate_positive_int(evidence_version, "evidence_version")

    fixed_values = {
        "contains_hr_payload": (contains_hr_payload, False),
        "contains_destination": (contains_destination, False),
        "contains_credentials": (contains_credentials, False),
        "delivery_outcome_code": (delivery_outcome_code, _DELIVERY_OUTCOME_CODE),
        "trust_state": (trust_state, _TRUST_STATE),
        "reconciliation_state": (reconciliation_state, _RECONCILIATION_STATE),
        "mutation_authority": (mutation_authority, _MUTATION_AUTHORITY),
        "next_action": (next_action, _NEXT_ACTION),
    }
    for field_name, (actual, required) in fixed_values.items():
        if type(actual) is not type(required) or actual != required:
            raise ValueError(f"{field_name} must remain fixed by the governed receipt contract")
    return transport_delivered_at_utc, observed_at_utc


_BaseReceipt = namedtuple(
    "_BaseReceipt",
    [
        "tenant_record_id",
        "outbox_delivery_record_id",
        "audit_event_record_id",
        "delivery_target_code",
        "delivery_attempt_count",
        "transport_provider_code",
        "transport_receipt_reference",
        "transport_receipt_digest",
        "transport_delivered_at",
        "observed_at",
        "evidence_version",
        "contains_hr_payload",
        "contains_destination",
        "contains_credentials",
        "delivery_outcome_code",
        "trust_state",
        "reconciliation_state",
        "mutation_authority",
        "next_action",
    ],
)


class ExternalDeliveryReceiptEvidence(_BaseReceipt):
    """Structurally immutable evidence that an external transport reported delivery."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: str,
        outbox_delivery_record_id: str,
        audit_event_record_id: str,
        delivery_target_code: str,
        delivery_attempt_count: int,
        transport_provider_code: str,
        transport_receipt_reference: str,
        transport_receipt_digest: str,
        transport_delivered_at: datetime,
        observed_at: datetime,
        evidence_version: int = 1,
        contains_hr_payload: bool = False,
        contains_destination: bool = False,
        contains_credentials: bool = False,
        delivery_outcome_code: str = _DELIVERY_OUTCOME_CODE,
        trust_state: str = _TRUST_STATE,
        reconciliation_state: str = _RECONCILIATION_STATE,
        mutation_authority: str = _MUTATION_AUTHORITY,
        next_action: str = _NEXT_ACTION,
    ) -> "ExternalDeliveryReceiptEvidence":
        frozen_transport_delivered_at = _freeze_timestamp(
            transport_delivered_at, "transport_delivered_at"
        )
        frozen_observed_at = _freeze_timestamp(observed_at, "observed_at")
        _validate_contract(
            tenant_record_id=tenant_record_id,
            outbox_delivery_record_id=outbox_delivery_record_id,
            audit_event_record_id=audit_event_record_id,
            delivery_target_code=delivery_target_code,
            delivery_attempt_count=delivery_attempt_count,
            transport_provider_code=transport_provider_code,
            transport_receipt_reference=transport_receipt_reference,
            transport_receipt_digest=transport_receipt_digest,
            transport_delivered_at=frozen_transport_delivered_at,
            observed_at=frozen_observed_at,
            evidence_version=evidence_version,
            contains_hr_payload=contains_hr_payload,
            contains_destination=contains_destination,
            contains_credentials=contains_credentials,
            delivery_outcome_code=delivery_outcome_code,
            trust_state=trust_state,
            reconciliation_state=reconciliation_state,
            mutation_authority=mutation_authority,
            next_action=next_action,
        )

        instance = super().__new__(
            cls,
            tenant_record_id,
            outbox_delivery_record_id,
            audit_event_record_id,
            delivery_target_code,
            delivery_attempt_count,
            transport_provider_code,
            transport_receipt_reference,
            transport_receipt_digest,
            frozen_transport_delivered_at,
            frozen_observed_at,
            evidence_version,
            contains_hr_payload,
            contains_destination,
            contains_credentials,
            delivery_outcome_code,
            trust_state,
            reconciliation_state,
            mutation_authority,
            next_action,
        )
        return instance

    def __repr__(self) -> str:
        """Redact correlation identifiers from routine logs."""
        return "ExternalDeliveryReceiptEvidence(<redacted>)"

    @property
    def transport_delivered_at_utc(self) -> str:
        """Return the provider-reported delivery instant in canonical UTC text."""
        return _canonical_timestamp(self.transport_delivered_at, "transport_delivered_at")

    @property
    def observed_at_utc(self) -> str:
        """Return the host observation instant in canonical UTC text."""
        return _canonical_timestamp(self.observed_at, "observed_at")

    def canonical_json(self) -> str:
        """Return deterministic value-minimized JSON for immutable audit correlation."""
        transport_delivered_at_utc, observed_at_utc = _validate_contract(
            tenant_record_id=self.tenant_record_id,
            outbox_delivery_record_id=self.outbox_delivery_record_id,
            audit_event_record_id=self.audit_event_record_id,
            delivery_target_code=self.delivery_target_code,
            delivery_attempt_count=self.delivery_attempt_count,
            transport_provider_code=self.transport_provider_code,
            transport_receipt_reference=self.transport_receipt_reference,
            transport_receipt_digest=self.transport_receipt_digest,
            transport_delivered_at=self.transport_delivered_at,
            observed_at=self.observed_at,
            evidence_version=self.evidence_version,
            contains_hr_payload=self.contains_hr_payload,
            contains_destination=self.contains_destination,
            contains_credentials=self.contains_credentials,
            delivery_outcome_code=self.delivery_outcome_code,
            trust_state=self.trust_state,
            reconciliation_state=self.reconciliation_state,
            mutation_authority=self.mutation_authority,
            next_action=self.next_action,
        )
        payload = {
            "audit_event_record_id": self.audit_event_record_id,
            "contains_credentials": self.contains_credentials,
            "contains_destination": self.contains_destination,
            "contains_hr_payload": self.contains_hr_payload,
            "delivery_attempt_count": self.delivery_attempt_count,
            "delivery_outcome_code": self.delivery_outcome_code,
            "delivery_target_code": self.delivery_target_code,
            "evidence_version": self.evidence_version,
            "mutation_authority": self.mutation_authority,
            "next_action": self.next_action,
            "observed_at": observed_at_utc,
            "outbox_delivery_record_id": self.outbox_delivery_record_id,
            "reconciliation_state": self.reconciliation_state,
            "tenant_record_id": self.tenant_record_id,
            "transport_delivered_at": transport_delivered_at_utc,
            "transport_provider_code": self.transport_provider_code,
            "transport_receipt_digest": self.transport_receipt_digest,
            "transport_receipt_reference": self.transport_receipt_reference,
            "trust_state": self.trust_state,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 receipt evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_external_delivery_receipt_evidence(
    *,
    tenant_record_id: str,
    outbox_delivery_record_id: str,
    audit_event_record_id: str,
    delivery_target_code: str,
    delivery_attempt_count: int,
    transport_provider_code: str,
    transport_receipt_reference: str,
    transport_receipt_digest: str,
    transport_delivered_at: datetime,
    observed_at: datetime,
    evidence_version: int = 1,
) -> ExternalDeliveryReceiptEvidence:
    """Build one untrusted normalized receipt for later exact-attempt reconciliation."""
    return ExternalDeliveryReceiptEvidence(
        tenant_record_id=tenant_record_id,
        outbox_delivery_record_id=outbox_delivery_record_id,
        audit_event_record_id=audit_event_record_id,
        delivery_target_code=delivery_target_code,
        delivery_attempt_count=delivery_attempt_count,
        transport_provider_code=transport_provider_code,
        transport_receipt_reference=transport_receipt_reference,
        transport_receipt_digest=transport_receipt_digest,
        transport_delivered_at=transport_delivered_at,
        observed_at=observed_at,
        evidence_version=evidence_version,
    )


def verify_exact_delivery_attempt(
    evidence: ExternalDeliveryReceiptEvidence,
    *,
    tenant_record_id: str,
    outbox_delivery_record_id: str,
    audit_event_record_id: str,
    delivery_target_code: str,
    delivery_attempt_count: int,
) -> str:
    """Fail closed unless receipt evidence matches the exact authoritative attempt scope."""
    if type(evidence) is not ExternalDeliveryReceiptEvidence:
        raise TypeError("evidence must be ExternalDeliveryReceiptEvidence")

    evidence_digest = evidence.sha256_digest()
    expected = (
        _validate_operational_uuid(tenant_record_id, "tenant_record_id"),
        _validate_operational_uuid(outbox_delivery_record_id, "outbox_delivery_record_id"),
        _validate_operational_uuid(audit_event_record_id, "audit_event_record_id"),
        _validate_code(delivery_target_code, "delivery_target_code"),
        _validate_positive_int(delivery_attempt_count, "delivery_attempt_count"),
    )
    actual = (
        evidence.tenant_record_id,
        evidence.outbox_delivery_record_id,
        evidence.audit_event_record_id,
        evidence.delivery_target_code,
        evidence.delivery_attempt_count,
    )
    if actual != expected:
        raise ValueError("receipt evidence does not match the exact outbox delivery attempt")
    return evidence_digest
