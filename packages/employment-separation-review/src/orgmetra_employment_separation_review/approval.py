"""Authoritative human-approval boundary for reviewed Employment separations.

The pre-mutation review packet is deliberately non-authorizing. This module adds
one accountable approval step that is still not permission to mutate Employment,
Assignment, identity, payroll, benefits, or any foreign-owner system. The host
authority must re-resolve the exact reviewed scope and approval instant before a
value-minimized receipt can be issued.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
import hmac
import json
import secrets
from threading import RLock
from typing import Protocol
from weakref import finalize

from .packet import (
    EmploymentSeparationReviewPacket,
    _canonical_timestamp,
    _freeze_timestamp,
    _validate_digest,
    _validate_evidence_version,
    _validate_operational_uuid,
    _validate_reference,
)

_PURPOSE_CODE = "employment_separation_approval"
_APPROVAL_REASON_CODE = "human_approved_employment_separation"
_APPROVAL_STATE = "human_approved_for_authoritative_resolution"
_MUTATION_STATE = "not_authorized_to_apply"
_EXTERNAL_EXECUTION_STATE = "not_authorized_to_execute"
_RECEIPT_ISSUANCE_TOKEN = object()
_NEW_ISSUANCE_MARKER = object()
_USED_ISSUANCE_MARKER = object()
_PROCESS_SEAL_KEY = secrets.token_bytes(32)
_CREATION_SEALS: dict[int, str] = {}
_CREATION_SEALS_LOCK = RLock()


def _discard_creation_seal(receipt_id: int) -> None:
    """Discard process-local issuance evidence when its receipt is collected."""
    with _CREATION_SEALS_LOCK:
        _CREATION_SEALS.pop(receipt_id, None)


def _register_creation_seal(receipt: object, seal: str) -> None:
    """Bind one live receipt identity to evidence outside receipt-writable slots."""
    receipt_id = id(receipt)
    with _CREATION_SEALS_LOCK:
        _CREATION_SEALS[receipt_id] = seal
    finalize(receipt, _discard_creation_seal, receipt_id)


def _authoritative_creation_seal(receipt: object) -> str | None:
    """Return process-local issuance evidence without trusting receipt-owned state."""
    with _CREATION_SEALS_LOCK:
        return _CREATION_SEALS.get(id(receipt))


def _seal(payload_json: str) -> str:
    """Bind one process-local issuance to its exact canonical payload bytes."""
    return hmac.new(_PROCESS_SEAL_KEY, payload_json.encode("utf-8"), "sha256").hexdigest()


def _freeze_approved_at(value: object) -> datetime:
    """Freeze one caller approval instant while keeping diagnostics field-specific."""
    try:
        return _freeze_timestamp(value)  # type: ignore[arg-type]
    except ValueError as error:
        raise ValueError("approved_at must be a valid non-future timezone-aware datetime") from error


def _canonical_approved_at(value: object) -> str:
    """Render one governed approval instant with field-specific diagnostics."""
    try:
        return _canonical_timestamp(value)  # type: ignore[arg-type]
    except ValueError as error:
        raise ValueError("approved_at must be an exact built-in UTC datetime") from error


@dataclass(frozen=True, slots=True, repr=False)
class EmploymentSeparationApprovalVerification:
    """Host evidence returned only after authoritative separation checks succeed."""

    tenant_record_id: str
    separation_review_reference: str
    review_digest: str
    person_record_reference: str
    employment_record_reference: str
    approving_actor_reference: str
    authority_evidence_reference: str
    authority_evidence_digest: str

    def __repr__(self) -> str:
        """Avoid emitting worker or approval correlation in routine logs."""
        return "EmploymentSeparationApprovalVerification(<redacted>)"


class EmploymentSeparationApprovalAuthority(Protocol):
    """Host contract that fail-closes unless the reviewed separation is still valid."""

    def verify_approval(
        self,
        *,
        packet: EmploymentSeparationReviewPacket,
        approving_actor_reference: str,
        approved_at: datetime,
    ) -> EmploymentSeparationApprovalVerification:
        """Return exact-scope evidence after authoritative review of the approval instant."""


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
class EmploymentSeparationApprovalReceipt:
    """Immutable human-approval evidence that still grants no mutation authority."""

    tenant_record_id: str
    separation_review_reference: str
    review_digest: str
    person_record_reference: str
    employment_record_reference: str
    approving_actor_reference: str
    authority_evidence_reference: str
    authority_evidence_digest: str
    approved_at: datetime
    purpose_code: str = _PURPOSE_CODE
    approval_reason_code: str = _APPROVAL_REASON_CODE
    evidence_version: int = 1
    human_confirmation: bool = True
    approval_state: str = _APPROVAL_STATE
    mutation_state: str = _MUTATION_STATE
    external_execution_state: str = _EXTERNAL_EXECUTION_STATE
    _creation_seal: str | None = field(default=None, repr=False, compare=False)
    _issuance_marker: object = field(default=_NEW_ISSUANCE_MARKER, repr=False, compare=False)
    _issuance_token: object = field(default=None, repr=False, compare=False)

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep the trust-bearing receipt runtime type final."""
        raise TypeError("EmploymentSeparationApprovalReceipt is final")

    def __post_init__(self) -> None:
        """Validate exact evidence, require factory issuance, and seal creation state."""
        if self._issuance_token is not _RECEIPT_ISSUANCE_TOKEN:
            raise TypeError(
                "EmploymentSeparationApprovalReceipt can only be issued by "
                "approve_employment_separation"
            )
        if self._issuance_marker is not _NEW_ISSUANCE_MARKER or self._creation_seal is not None:
            raise ValueError("employment separation approval changed during issuance")
        self._validate_fields()
        seal = _seal(self._canonical_payload_json())
        object.__setattr__(self, "_creation_seal", seal)
        object.__setattr__(self, "_issuance_marker", _USED_ISSUANCE_MARKER)
        _register_creation_seal(self, seal)

    def _validate_fields(self) -> None:
        """Fail closed on approval scope, evidence provenance, and non-authorizing state."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_reference(
            self.separation_review_reference,
            "employment_separation_review",
            "separation_review_reference",
        )
        _validate_digest(self.review_digest, "review_digest")
        _validate_reference(self.person_record_reference, "person_record", "person_record_reference")
        _validate_reference(
            self.employment_record_reference,
            "employment_record",
            "employment_record_reference",
        )
        _validate_reference(self.approving_actor_reference, "actor", "approving_actor_reference")
        _validate_reference(
            self.authority_evidence_reference,
            "separation_approval_verification",
            "authority_evidence_reference",
        )
        _validate_digest(self.authority_evidence_digest, "authority_evidence_digest")
        _canonical_approved_at(self.approved_at)
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE_CODE:
            raise ValueError("purpose_code must remain employment_separation_approval")
        if (
            type(self.approval_reason_code) is not str
            or self.approval_reason_code != _APPROVAL_REASON_CODE
        ):
            raise ValueError(
                "approval_reason_code must remain human_approved_employment_separation"
            )
        _validate_evidence_version(self.evidence_version)
        if self.evidence_version != 1:
            raise ValueError("evidence_version must remain 1 for separation approval evidence")
        if self.human_confirmation is not True:
            raise ValueError("human confirmation is mandatory for employment separation approval")
        if type(self.approval_state) is not str or self.approval_state != _APPROVAL_STATE:
            raise ValueError(
                "approval_state must remain human_approved_for_authoritative_resolution"
            )
        if type(self.mutation_state) is not str or self.mutation_state != _MUTATION_STATE:
            raise ValueError("mutation_state must remain not_authorized_to_apply")
        if (
            type(self.external_execution_state) is not str
            or self.external_execution_state != _EXTERNAL_EXECUTION_STATE
        ):
            raise ValueError("external_execution_state must remain not_authorized_to_execute")

    def _payload(self) -> dict[str, object]:
        """Return value-minimized evidence without separation narrative or HR values."""
        return {
            "approval_reason_code": self.approval_reason_code,
            "approval_state": self.approval_state,
            "approved_at": _canonical_approved_at(self.approved_at),
            "approving_actor_reference": self.approving_actor_reference,
            "authority_evidence_digest": self.authority_evidence_digest,
            "authority_evidence_reference": self.authority_evidence_reference,
            "employment_record_reference": self.employment_record_reference,
            "evidence_version": self.evidence_version,
            "external_execution_state": self.external_execution_state,
            "human_confirmation": self.human_confirmation,
            "mutation_state": self.mutation_state,
            "person_record_reference": self.person_record_reference,
            "purpose_code": self.purpose_code,
            "review_digest": self.review_digest,
            "separation_review_reference": self.separation_review_reference,
            "tenant_record_id": self.tenant_record_id,
        }

    def _canonical_payload_json(self) -> str:
        """Serialize live evidence without consulting process-local issuance state."""
        return json.dumps(self._payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def _assert_integrity(self) -> tuple[dict[str, object], str]:
        """Return one checked snapshot while rejecting rewriting after issuance."""
        self._validate_fields()
        if self._issuance_marker is not _USED_ISSUANCE_MARKER or self._issuance_token is not None:
            raise ValueError("employment separation approval changed after issuance")
        packet_seal = self._creation_seal
        authoritative_seal = _authoritative_creation_seal(self)
        payload = self._payload()
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        live_seal = _seal(payload_json)
        if (
            type(packet_seal) is not str
            or type(authoritative_seal) is not str
            or not hmac.compare_digest(packet_seal, authoritative_seal)
            or not hmac.compare_digest(live_seal, authoritative_seal)
        ):
            raise ValueError("employment separation approval changed after issuance")
        return payload, payload_json

    def canonical_document(self) -> dict[str, object]:
        """Return the exact canonical document snapshot that passed integrity checks."""
        payload, _ = self._assert_integrity()
        return payload

    def canonical_json(self) -> str:
        """Return the exact canonical JSON snapshot that passed integrity checks."""
        _, payload_json = self._assert_integrity()
        return payload_json

    def sha256_digest(self) -> str:
        """Return SHA-256 over the exact checked canonical approval evidence."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        """Avoid leaking tenant, worker, review, or authority correlations into logs."""
        return "EmploymentSeparationApprovalReceipt(<redacted>)"


def approve_employment_separation(
    *,
    packet: EmploymentSeparationReviewPacket,
    authority: EmploymentSeparationApprovalAuthority,
    approving_actor_reference: str,
    approved_at: datetime,
) -> EmploymentSeparationApprovalReceipt:
    """Approve one exact review without granting Employment or downstream mutation authority."""
    if type(packet) is not EmploymentSeparationReviewPacket:
        raise TypeError("packet must be an EmploymentSeparationReviewPacket")
    frozen_approved_at = _freeze_approved_at(approved_at)
    if frozen_approved_at < packet.generated_at:
        raise ValueError("approved_at must not precede separation review generated_at")
    _validate_reference(approving_actor_reference, "actor", "approving_actor_reference")
    if approving_actor_reference != packet.reviewer_reference:
        raise ValueError("approving_actor_reference must be the reviewed accountable reviewer")

    packet_canonical_json = packet.canonical_json()
    review_digest = sha256(packet_canonical_json.encode("utf-8")).hexdigest()
    expected_scope = (
        packet.tenant_record_id,
        packet.separation_review_reference,
        review_digest,
        packet.person_record_reference,
        packet.employment_record_reference,
        approving_actor_reference,
    )

    verification = authority.verify_approval(
        packet=packet,
        approving_actor_reference=approving_actor_reference,
        approved_at=frozen_approved_at,
    )
    if packet.canonical_json() != packet_canonical_json:
        raise ValueError("separation review changed during authority verification")
    if type(verification) is not EmploymentSeparationApprovalVerification:
        raise TypeError("authority must return EmploymentSeparationApprovalVerification")

    verification_snapshot = (
        verification.tenant_record_id,
        verification.separation_review_reference,
        verification.review_digest,
        verification.person_record_reference,
        verification.employment_record_reference,
        verification.approving_actor_reference,
        verification.authority_evidence_reference,
        verification.authority_evidence_digest,
    )
    (
        verified_tenant,
        verified_review_reference,
        verified_review_digest,
        verified_person_reference,
        verified_employment_reference,
        verified_approving_actor,
        verified_authority_reference,
        verified_authority_digest,
    ) = verification_snapshot

    _validate_operational_uuid(verified_tenant, "tenant_record_id")
    _validate_reference(
        verified_review_reference,
        "employment_separation_review",
        "separation_review_reference",
    )
    _validate_digest(verified_review_digest, "review_digest")
    _validate_reference(verified_person_reference, "person_record", "person_record_reference")
    _validate_reference(
        verified_employment_reference,
        "employment_record",
        "employment_record_reference",
    )
    _validate_reference(verified_approving_actor, "actor", "approving_actor_reference")
    _validate_reference(
        verified_authority_reference,
        "separation_approval_verification",
        "authority_evidence_reference",
    )
    _validate_digest(verified_authority_digest, "authority_evidence_digest")

    verified_scope = verification_snapshot[:6]
    if verified_scope != expected_scope:
        raise ValueError("approval authority returned evidence for a different reviewed separation")

    receipt = EmploymentSeparationApprovalReceipt(
        tenant_record_id=expected_scope[0],
        separation_review_reference=expected_scope[1],
        review_digest=expected_scope[2],
        person_record_reference=expected_scope[3],
        employment_record_reference=expected_scope[4],
        approving_actor_reference=expected_scope[5],
        authority_evidence_reference=verified_authority_reference,
        authority_evidence_digest=verified_authority_digest,
        approved_at=frozen_approved_at,
        _issuance_token=_RECEIPT_ISSUANCE_TOKEN,
    )
    object.__setattr__(receipt, "_issuance_token", None)
    return receipt
