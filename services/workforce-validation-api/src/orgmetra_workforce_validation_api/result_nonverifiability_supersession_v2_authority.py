"""Versioned exact-artifact correction authority for non-reproducible validation evidence."""

from __future__ import annotations

from datetime import datetime
from inspect import getattr_static
from types import FunctionType
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_keyverse_adapter import (
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    require_purpose_bound_access,
)

from .registry import (
    ValidationPrincipal,
    _detach_policy,
    _require_aware_datetime,
    _require_code,
    _restore_operational_uuid,
    _store_operational_uuid,
)
from .result_nonverifiability import (
    ValidationResultNonVerifiabilityRecord,
    _FAILED_REFERENCE_KIND_BY_EVIDENCE_KIND,
    _require_failed_evidence_kind,
)
from .scientific_authority import _require_digest, _require_positive_integer, _require_reference

_RESOURCE_KIND = "validation_result_nonverifiability_supersession_authority"
_OPERATION = "read"
_VERSION = 2
_READ_FIELDS = frozenset(
    {
        "result_reference", "result_digest", "failed_evidence_kind", "failure_mode",
        "failed_evidence_reference", "failed_evidence_digest", "failed_evidence_released_at",
        "verification_attempt_reference", "verification_attempt_digest",
        "verification_attempt_released_at", "evidence_version", "owner_contract_reference",
        "owner_contract_version", "owner_contract_digest", "owner_contract_released_at",
        "released_at", "superseded_at", "successor_target_result_reference",
        "successor_target_result_digest", "successor_failed_evidence_kind",
        "successor_target_failed_evidence_reference", "successor_target_failed_evidence_digest",
        "successor_target_failed_evidence_released_at", "successor_verification_attempt_reference",
        "successor_verification_attempt_digest", "successor_verification_attempt_released_at",
    }
)
_VIEW_FIELDS = frozenset(
    {
        "result_reference", "result_digest", "failed_evidence_kind", "failure_mode",
        "failed_evidence_reference", "failed_evidence_digest", "failed_evidence_released_at",
        "verification_attempt_reference", "verification_attempt_digest",
        "verification_attempt_released_at", "evidence_version", "owner_contract_reference",
        "owner_contract_version", "owner_contract_digest", "owner_contract_released_at", "released_at",
    }
)


class ValidationResultNonVerifiabilitySupersessionV2AuthorityNotFound(LookupError):
    """Indicate that no released v2 correction authority matches the predecessor."""


class ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError(RuntimeError):
    """Indicate that released v2 correction evidence cannot authorize use."""


def _predecessor_fields(
    predecessor: ValidationResultNonVerifiabilityRecord, version: int
) -> tuple[tuple[str, object], ...]:
    """Return immutable predecessor provenance plus the governed correction version."""
    return (
        ("evidence_version", version),
        ("failed_evidence_digest", predecessor.failed_evidence_digest),
        ("failed_evidence_kind", predecessor.failed_evidence_kind),
        ("failed_evidence_reference", predecessor.failed_evidence_reference),
        ("failed_evidence_released_at", predecessor.failed_evidence_released_at),
        ("failure_mode", predecessor.failure_mode),
        ("owner_contract_digest", predecessor.owner_contract_digest),
        ("owner_contract_reference", predecessor.owner_contract_reference),
        ("owner_contract_released_at", predecessor.owner_contract_released_at),
        ("owner_contract_version", predecessor.owner_contract_version),
        ("result_digest", predecessor.result_digest),
        ("result_reference", predecessor.result_reference),
        ("verification_attempt_digest", predecessor.verification_attempt_digest),
        ("verification_attempt_reference", predecessor.verification_attempt_reference),
        ("verification_attempt_released_at", predecessor.verification_attempt_released_at),
    )


class ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord(tuple):
    """Bind a non-reproducible predecessor to an exact-artifact successor attempt."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        predecessor: ValidationResultNonVerifiabilityRecord,
        evidence_version: int,
        superseded_at: datetime | None = None,
        successor_target_result_reference: str | None = None,
        successor_target_result_digest: str | None = None,
        successor_failed_evidence_kind: str | None = None,
        successor_target_failed_evidence_reference: str | None = None,
        successor_target_failed_evidence_digest: str | None = None,
        successor_target_failed_evidence_released_at: datetime | None = None,
        successor_verification_attempt_reference: str | None = None,
        successor_verification_attempt_digest: str | None = None,
        successor_verification_attempt_released_at: datetime | None = None,
    ) -> ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord:
        """Validate exact predecessor provenance and an optional atomic successor cutover."""
        if type(predecessor) is not ValidationResultNonVerifiabilityRecord:
            raise TypeError("predecessor must be an exact ValidationResultNonVerifiabilityRecord.")
        if predecessor.failure_mode != "non_reproducible":
            raise ValueError("v2 supersession is reserved for non_reproducible predecessors.")
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != _VERSION:
            raise ValueError("evidence_version must be 2 for exact-artifact supersession.")
        failed_reference = predecessor.failed_evidence_reference
        failed_digest = predecessor.failed_evidence_digest
        failed_release = predecessor.failed_evidence_released_at
        if failed_reference is None or failed_digest is None or failed_release is None:
            raise ValueError("non_reproducible predecessor must retain exact failed-artifact evidence.")

        successor_values = (
            superseded_at, successor_target_result_reference, successor_target_result_digest,
            successor_failed_evidence_kind, successor_target_failed_evidence_reference,
            successor_target_failed_evidence_digest, successor_target_failed_evidence_released_at,
            successor_verification_attempt_reference, successor_verification_attempt_digest,
            successor_verification_attempt_released_at,
        )
        if all(value is None for value in successor_values):
            cutover = None
            successor_fields = None
        elif any(value is None for value in successor_values):
            raise ValueError(
                "v2 supersession requires cutover, exact predecessor target, exact failed artifact, "
                "and complete successor verification-attempt evidence."
            )
        else:
            cutover = _require_aware_datetime("superseded_at", superseded_at)
            if cutover <= predecessor.released_at:
                raise ValueError("superseded_at must be later than predecessor release.")
            target_result_reference = _require_reference(
                "successor_target_result_reference", successor_target_result_reference,
                "validation_analysis_result",
            )
            target_result_digest = _require_digest(
                "successor_target_result_digest", successor_target_result_digest
            )
            target_kind = _require_failed_evidence_kind(successor_failed_evidence_kind)
            target_failed_reference = _require_reference(
                "successor_target_failed_evidence_reference", successor_target_failed_evidence_reference,
                _FAILED_REFERENCE_KIND_BY_EVIDENCE_KIND[predecessor.failed_evidence_kind],
            )
            target_failed_digest = _require_digest(
                "successor_target_failed_evidence_digest", successor_target_failed_evidence_digest
            )
            target_failed_release = _require_aware_datetime(
                "successor_target_failed_evidence_released_at",
                successor_target_failed_evidence_released_at,
            )
            successor_reference = _require_reference(
                "successor_verification_attempt_reference", successor_verification_attempt_reference,
                "validation_evidence_verification_attempt",
            )
            successor_digest = _require_digest(
                "successor_verification_attempt_digest", successor_verification_attempt_digest
            )
            successor_release = _require_aware_datetime(
                "successor_verification_attempt_released_at",
                successor_verification_attempt_released_at,
            )
            if (
                target_result_reference != predecessor.result_reference
                or target_result_digest != predecessor.result_digest
            ):
                raise ValueError("successor attempt must target the exact predecessor result.")
            if target_kind != predecessor.failed_evidence_kind:
                raise ValueError("successor attempt must re-evaluate the same failed-evidence family.")
            if (
                target_failed_reference != failed_reference
                or target_failed_digest != failed_digest
                or target_failed_release != failed_release
            ):
                raise ValueError("successor attempt must target the exact failed artifact and release chronology.")
            if successor_reference == predecessor.verification_attempt_reference:
                raise ValueError("successor verification attempt must use a new reference.")
            if successor_digest in {
                predecessor.result_digest, failed_digest, predecessor.verification_attempt_digest,
                predecessor.owner_contract_digest,
            }:
                raise ValueError("successor verification attempt must identify new evidence.")
            if successor_release != cutover:
                raise ValueError("successor verification attempt must be released exactly at supersession.")
            successor_fields = (
                ("successor_failed_evidence_kind", target_kind),
                ("successor_target_failed_evidence_digest", target_failed_digest),
                ("successor_target_failed_evidence_reference", target_failed_reference),
                ("successor_target_failed_evidence_released_at", target_failed_release),
                ("successor_target_result_digest", target_result_digest),
                ("successor_target_result_reference", target_result_reference),
                ("successor_verification_attempt_digest", successor_digest),
                ("successor_verification_attempt_reference", successor_reference),
                ("successor_verification_attempt_released_at", successor_release),
            )
        return tuple.__new__(cls, (predecessor, version, cutover, successor_fields))

    @property
    def predecessor(self) -> ValidationResultNonVerifiabilityRecord:
        """Return the exact immutable predecessor owner record."""
        return self[0]

    @property
    def evidence_version(self) -> int:
        """Return the governed exact-artifact correction contract version."""
        return self[1]

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return immutable predecessor provenance plus v2 evidence version."""
        return _predecessor_fields(self.predecessor, self.evidence_version)

    @property
    def released_at(self) -> datetime:
        """Return when the predecessor negative outcome became released evidence."""
        return self.predecessor.released_at

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive end of predecessor authority when a successor exists."""
        return self[2]

    @property
    def successor_fields(self) -> tuple[tuple[str, object], ...] | None:
        """Return owner-internal exact-artifact successor coordinates."""
        return self[3]


class ValidationResultNonVerifiabilitySupersessionV2AuthorityView(tuple):
    """Expose minimized predecessor provenance without reusable successor authority."""

    __slots__ = ()

    def __new__(
        cls, *, tenant_record_id: UUID, validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> ValidationResultNonVerifiabilitySupersessionV2AuthorityView:
        """Reject public construction so only the resolver can issue an authorized view."""
        raise TypeError(
            "ValidationResultNonVerifiabilitySupersessionV2AuthorityView is issued only by "
            "resolve_validation_result_nonverifiability_supersession_v2_authority."
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh authorized tenant identity."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh authorized validity-study identity."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return predecessor provenance without cutover or successor coordinates."""
        return self[2]


@runtime_checkable
class ValidationResultNonVerifiabilitySupersessionV2AuthorityReadPort(Protocol):
    """Read exact-artifact supersession evidence through the workforce-validation ACL."""

    def read_validation_result_nonverifiability_supersession_v2_authority(
        self, *, tenant_record_id: UUID, validity_study_id: UUID, result_reference: str,
        result_digest: str, failed_evidence_kind: str, verification_attempt_reference: str,
        verification_attempt_digest: str, evidence_version: int, owner_contract_reference: str,
        owner_contract_version: int, owner_contract_digest: str,
    ) -> ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord | None:
        """Return one released v2 correction record or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    ValidationResultNonVerifiabilitySupersessionV2AuthorityReadPort,
    "read_validation_result_nonverifiability_supersession_v2_authority",
)


def resolve_validation_result_nonverifiability_supersession_v2_authority(
    *, principal: ValidationPrincipal, tenant_record_id: UUID, validity_study_id: UUID,
    result_reference: str, result_digest: str, failed_evidence_kind: str,
    verification_attempt_reference: str, verification_attempt_digest: str, evidence_version: int,
    owner_contract_reference: str, owner_contract_version: int, owner_contract_digest: str,
    used_at: datetime, purpose_code: str, policy: PurposeBoundAccessPolicy,
    read_port: ValidationResultNonVerifiabilitySupersessionV2AuthorityReadPort,
) -> ValidationResultNonVerifiabilitySupersessionV2AuthorityView:
    """Authorize then resolve one exact-artifact non-reproducible correction interval."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_validation_result_nonverifiability_supersession_v2_authority", None
    )
    if type(read_capability) is not FunctionType or read_capability is _PROTOCOL_READ_CAPABILITY:
        raise TypeError(
            "read_port must expose a statically callable "
            "read_validation_result_nonverifiability_supersession_v2_authority."
        )

    tenant_id = _restore_operational_uuid(
        "tenant_record_id", _store_operational_uuid("tenant_record_id", tenant_record_id)
    )
    study_id = _restore_operational_uuid(
        "validity_study_id", _store_operational_uuid("validity_study_id", validity_study_id)
    )
    result_ref = _require_reference("result_reference", result_reference, "validation_analysis_result")
    result_evidence_digest = _require_digest("result_digest", result_digest)
    evidence_kind = _require_failed_evidence_kind(failed_evidence_kind)
    attempt_ref = _require_reference(
        "verification_attempt_reference", verification_attempt_reference,
        "validation_evidence_verification_attempt",
    )
    attempt_digest = _require_digest("verification_attempt_digest", verification_attempt_digest)
    version = _require_positive_integer("evidence_version", evidence_version)
    if version != _VERSION:
        raise ValueError("evidence_version must be 2 for exact-artifact supersession.")
    owner_ref = _require_reference(
        "owner_contract_reference", owner_contract_reference, "released_owner_contract"
    )
    owner_version = _require_positive_integer("owner_contract_version", owner_contract_version)
    owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
    use_instant = _require_aware_datetime("used_at", used_at)
    purpose = _require_code("purpose_code", purpose_code)
    detached_principal = ValidationPrincipal(
        tenant_record_id=principal.tenant_record_id, actor_reference=principal.actor_reference,
        granted_scope_codes=principal.granted_scope_codes,
    )
    require_purpose_bound_access(
        request=PurposeBoundAccessRequest(
            tenant_record_id=tenant_id, actor_tenant_record_id=detached_principal.tenant_record_id,
            resource_tenant_record_id=tenant_id, actor_reference=detached_principal.actor_reference,
            resource_reference=f"{_RESOURCE_KIND}:{study_id}", purpose_code=purpose,
            operation_code=_OPERATION, resource_kind=_RESOURCE_KIND, requested_fields=_READ_FIELDS,
            granted_scope_codes=detached_principal.granted_scope_codes,
        ),
        policy=_detach_policy(policy),
    )
    persisted = read_capability(
        read_port, tenant_record_id=tenant_id, validity_study_id=study_id,
        result_reference=result_ref, result_digest=result_evidence_digest,
        failed_evidence_kind=evidence_kind, verification_attempt_reference=attempt_ref,
        verification_attempt_digest=attempt_digest, evidence_version=version,
        owner_contract_reference=owner_ref, owner_contract_version=owner_version,
        owner_contract_digest=owner_digest,
    )
    if persisted is None:
        raise ValidationResultNonVerifiabilitySupersessionV2AuthorityNotFound(str(study_id))
    if type(persisted) is not ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord:
        raise ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError(
            "owner port returned non-canonical v2 non-verifiability supersession evidence"
        )
    predecessor = persisted.predecessor
    values = dict(persisted.fields)
    requested_values = {
        "evidence_version": version,
        "failed_evidence_kind": evidence_kind,
        "owner_contract_digest": owner_digest,
        "owner_contract_reference": owner_ref,
        "owner_contract_version": owner_version,
        "result_digest": result_evidence_digest,
        "result_reference": result_ref,
        "verification_attempt_digest": attempt_digest,
        "verification_attempt_reference": attempt_ref,
    }
    if (
        _store_operational_uuid("record tenant_record_id", predecessor.tenant_record_id)
        != _store_operational_uuid("requested tenant_record_id", tenant_id)
        or _store_operational_uuid("record validity_study_id", predecessor.validity_study_id)
        != _store_operational_uuid("requested validity_study_id", study_id)
        or any(values[name] != value for name, value in requested_values.items())
    ):
        raise ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError(
            "owner evidence does not match requested v2 non-verifiability correction coordinates"
        )
    if use_instant < persisted.released_at:
        raise ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError(
            "v2 non-verifiability authority cannot be used before predecessor release"
        )
    if persisted.superseded_at is not None and use_instant >= persisted.superseded_at:
        raise ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError(
            "v2 non-verifiability authority ended at its owner-resolved supersession instant"
        )
    projection_values = {**values, "released_at": persisted.released_at}
    fields = tuple((name, projection_values[name]) for name in sorted(_VIEW_FIELDS))
    return tuple.__new__(
        ValidationResultNonVerifiabilitySupersessionV2AuthorityView,
        (_store_operational_uuid("tenant_record_id", tenant_id),
         _store_operational_uuid("validity_study_id", study_id), fields),
    )


__all__ = [
    "ValidationResultNonVerifiabilitySupersessionV2AuthorityIntegrityError",
    "ValidationResultNonVerifiabilitySupersessionV2AuthorityNotFound",
    "ValidationResultNonVerifiabilitySupersessionV2AuthorityReadPort",
    "ValidationResultNonVerifiabilitySupersessionV2AuthorityRecord",
    "ValidationResultNonVerifiabilitySupersessionV2AuthorityView",
    "resolve_validation_result_nonverifiability_supersession_v2_authority",
]
