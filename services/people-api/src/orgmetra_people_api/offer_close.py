"""Connect candidate acceptance evidence to authoritative confirmed-hire materialization.

Candidate response evidence is a necessary candidate-originated fact, never hire
authority. This boundary validates the supplied response envelope, verifies that the
authenticated caller is purpose-bound to materialize the exact selection decision before
protected candidate/offer resolution, asks an injected authoritative host to resolve the
response, verifies the returned scope, and delegates to the existing confirmed-hire path.
No candidate PII or compensation value is copied into this orchestration boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_candidate_offer_response import CandidateOfferResponsePacket
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import authorize_resource_fields
from orgmetra_people_api.hire import (
    HireAcceptanceCommand,
    HireAcceptancePort,
    HireAcceptanceResult,
    accept_confirmed_hire,
)

_MAX_UUID_INT = (1 << 128) - 1
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_HIRE_MUTATION_FIELDS = frozenset({"candidate_worker_conversion"})


class OfferToHireIntegrityError(RuntimeError):
    """Indicate that offer-response evidence cannot safely authorize hire orchestration."""


def _validate_operational_uuid(value: object, field_name: str) -> None:
    """Require an exact non-sentinel UUID from authoritative Orgmetra resolution."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an exact operational UUID")


def _validate_digest(value: object, field_name: str) -> None:
    """Require exact built-in lowercase SHA-256 hexadecimal evidence."""
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _validate_candidate_actor(value: object) -> None:
    """Require the bounded external candidate subject reviewed by the response contract."""
    if (
        type(value) is not str
        or len(value) > 288
        or _REFERENCE_PATTERN.fullmatch(value) is None
        or not value.startswith("candidate:")
    ):
        raise ValueError("candidate_actor_reference must be a bounded candidate: opaque reference")


def _validate_authority_reference(value: object) -> None:
    """Require one Orgmetra-owned opaque UUIDv4 authority evidence reference."""
    message = "authority_evidence_reference must be an opaque offer_hire_verification: UUIDv4 reference"
    if (
        type(value) is not str
        or len(value) > 160
        or _REFERENCE_PATTERN.fullmatch(value) is None
        or not value.startswith("offer_hire_verification:")
    ):
        raise ValueError(message)
    suffix = value.split(":", 1)[1]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError(message) from error
    if str(parsed) != suffix or parsed.version != 4 or parsed.int in (0, _MAX_UUID_INT):
        raise ValueError(message)


@dataclass(frozen=True, slots=True, repr=False)
class CandidateOfferHireVerification:
    """PII-minimized evidence that an authoritative host resolved one accepted offer to hire scope."""

    tenant_record_id: UUID
    candidate_profile_id: UUID
    selection_decision_id: UUID
    offer_response_digest: str
    offer_approval_digest: str
    offer_terms_digest: str
    candidate_actor_reference: str
    authority_evidence_reference: str
    authority_evidence_digest: str

    def __repr__(self) -> str:
        """Avoid emitting candidate, selection, offer, or authority correlation in routine logs."""
        return "CandidateOfferHireVerification(<redacted>)"

    def __post_init__(self) -> None:
        """Reject malformed authoritative evidence before the hire path can consume it."""
        self.validate_live()

    def validate_live(self) -> None:
        """Revalidate fields so post-construction rewriting cannot cross the trust boundary."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_operational_uuid(self.candidate_profile_id, "candidate_profile_id")
        _validate_operational_uuid(self.selection_decision_id, "selection_decision_id")
        _validate_digest(self.offer_response_digest, "offer_response_digest")
        _validate_digest(self.offer_approval_digest, "offer_approval_digest")
        _validate_digest(self.offer_terms_digest, "offer_terms_digest")
        _validate_candidate_actor(self.candidate_actor_reference)
        _validate_authority_reference(self.authority_evidence_reference)
        _validate_digest(self.authority_evidence_digest, "authority_evidence_digest")


@runtime_checkable
class CandidateOfferHireAuthority(Protocol):
    """Resolve one candidate response to exact authoritative candidate and selection scope."""

    def verify_offer_acceptance(
        self,
        *,
        tenant_record_id: str,
        candidate_profile_reference: str,
        selection_decision_id: UUID,
        offer_response_reference: str,
        offer_response_digest: str,
        candidate_actor_reference: str,
        identity_resolution_reference: str,
        identity_resolution_digest: str,
        offer_approval_reference: str,
        offer_approval_digest: str,
        offer_terms_reference: str,
        offer_terms_digest: str,
        responded_at: str,
    ) -> CandidateOfferHireVerification:
        """Return exact-scope evidence only after authoritative identity/offer resolution succeeds."""


def _snapshot_response(response: CandidateOfferResponsePacket) -> tuple[str, dict[str, object]]:
    """Freeze one verified candidate-response representation before authoritative host work."""
    if type(response) is not CandidateOfferResponsePacket:
        raise TypeError("response must be the exact CandidateOfferResponsePacket runtime type")
    try:
        canonical_json = response.canonical_json()
    except (KeyError, ValueError) as error:
        raise OfferToHireIntegrityError("candidate offer response evidence is not intact") from error
    payload = json.loads(canonical_json)
    return sha256(canonical_json.encode("utf-8")).hexdigest(), payload


def _snapshot_verification(value: CandidateOfferHireVerification) -> CandidateOfferHireVerification:
    """Copy and revalidate exact authority evidence before comparing it with requested scope."""
    if type(value) is not CandidateOfferHireVerification:
        raise TypeError("authority must return the exact CandidateOfferHireVerification runtime type")
    return CandidateOfferHireVerification(
        tenant_record_id=value.tenant_record_id,
        candidate_profile_id=value.candidate_profile_id,
        selection_decision_id=value.selection_decision_id,
        offer_response_digest=value.offer_response_digest,
        offer_approval_digest=value.offer_approval_digest,
        offer_terms_digest=value.offer_terms_digest,
        candidate_actor_reference=value.candidate_actor_reference,
        authority_evidence_reference=value.authority_evidence_reference,
        authority_evidence_digest=value.authority_evidence_digest,
    )


def close_accepted_offer_to_hire(
    *,
    response: CandidateOfferResponsePacket,
    principal: AuthenticatedPrincipal,
    command: HireAcceptanceCommand,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    authority: CandidateOfferHireAuthority,
    mutation_port: HireAcceptancePort,
) -> HireAcceptanceResult:
    """Require response integrity, authorization, and exact mapping before hire mutation.

    The candidate response cannot authorize employment creation by itself. The supplied packet
    is first validated as immutable candidate-originated evidence and checked against the hire
    command tenant. Before candidate identity or offer provenance is resolved, the authenticated
    principal must be purpose-bound to materialize the exact immutable selection decision. The
    injected authority then re-resolves candidate and offer scope. Only after those checks does
    this function invoke the existing confirmed-hire service, which independently reauthorizes
    the same selection decision immediately before persistence.
    """
    if type(command) is not HireAcceptanceCommand:
        raise TypeError("command must be the exact HireAcceptanceCommand runtime type")
    if not isinstance(authority, CandidateOfferHireAuthority):
        raise TypeError("authority must implement CandidateOfferHireAuthority")

    response_digest, payload = _snapshot_response(response)
    if payload.get("response_code") != "offer_accepted":
        raise OfferToHireIntegrityError("candidate offer response must be accepted before hire orchestration")
    if payload.get("tenant_record_id") != str(command.tenant_record_id):
        raise OfferToHireIntegrityError("candidate response tenant does not match the hire command")

    authorize_resource_fields(
        principal=principal,
        tenant_record_id=command.tenant_record_id,
        resource_tenant_record_id=command.tenant_record_id,
        resource_reference=f"selection_decision:{command.selection_decision_id.hex}",
        purpose_code=purpose_code,
        operation_code="materialize_worker",
        resource_kind="selection_decision",
        requested_fields=_HIRE_MUTATION_FIELDS,
        policy=policy,
    )

    verification = authority.verify_offer_acceptance(
        tenant_record_id=str(payload["tenant_record_id"]),
        candidate_profile_reference=str(payload["candidate_profile_reference"]),
        selection_decision_id=command.selection_decision_id,
        offer_response_reference=str(payload["offer_response_reference"]),
        offer_response_digest=response_digest,
        candidate_actor_reference=str(payload["candidate_actor_reference"]),
        identity_resolution_reference=str(payload["identity_resolution_reference"]),
        identity_resolution_digest=str(payload["identity_resolution_digest"]),
        offer_approval_reference=str(payload["offer_approval_reference"]),
        offer_approval_digest=str(payload["offer_approval_digest"]),
        offer_terms_reference=str(payload["offer_terms_reference"]),
        offer_terms_digest=str(payload["offer_terms_digest"]),
        responded_at=str(payload["responded_at"]),
    )
    verified = _snapshot_verification(verification)

    if verified.tenant_record_id != command.tenant_record_id:
        raise OfferToHireIntegrityError("authority tenant does not match the hire command")
    if verified.candidate_profile_id != command.candidate_profile_id:
        raise OfferToHireIntegrityError("authority candidate profile does not match the hire command")
    if verified.selection_decision_id != command.selection_decision_id:
        raise OfferToHireIntegrityError("authority selection decision does not match the hire command")
    expected_evidence = (
        response_digest,
        payload["offer_approval_digest"],
        payload["offer_terms_digest"],
        payload["candidate_actor_reference"],
    )
    verified_evidence = (
        verified.offer_response_digest,
        verified.offer_approval_digest,
        verified.offer_terms_digest,
        verified.candidate_actor_reference,
    )
    if verified_evidence != expected_evidence:
        raise OfferToHireIntegrityError("authority evidence does not match the accepted offer response")

    try:
        response.canonical_json()
    except (KeyError, ValueError) as error:
        raise OfferToHireIntegrityError(
            "candidate offer response changed during authoritative verification"
        ) from error

    return accept_confirmed_hire(
        principal=principal,
        command=command,
        purpose_code=purpose_code,
        policy=policy,
        mutation_port=mutation_port,
    )
