"""Corroborate append-only supersession of released non-verifiability outcomes.

A released ``not_verifiable`` outcome remains authoritative only until a new
immutable verification attempt re-evaluates the same result and failed-evidence
obligation. This boundary binds that successor attempt to the predecessor
cutover without exposing successor coordinates as reusable downstream authority.
"""

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
    _require_failed_evidence_kind,
    _require_failure_mode,
)
from .scientific_authority import (
    _require_digest,
    _require_positive_integer,
    _require_reference,
)

_RESOURCE_KIND = "validation_result_nonverifiability_supersession_authority"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "failed_evidence_kind",
        "failure_mode",
        "verification_attempt_reference",
        "verification_attempt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_target_result_reference",
        "successor_target_result_digest",
        "successor_failed_evidence_kind",
        "successor_verification_attempt_reference",
        "successor_verification_attempt_digest",
        "successor_verification_attempt_released_at",
    }
)
_VIEW_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "failed_evidence_kind",
        "failure_mode",
        "verification_attempt_reference",
        "verification_attempt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
    }
)


class ValidationResultNonVerifiabilitySupersessionAuthorityNotFound(LookupError):
    """Indicate that no released successor authority matches the negative outcome."""


class ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError(RuntimeError):
    """Indicate that negative-outcome successor evidence cannot authorize use."""


class ValidationResultNonVerifiabilitySupersessionAuthorityRecord(tuple):
    """Immutable owner projection for one negative-outcome authority interval."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        failed_evidence_kind: str,
        failure_mode: str,
        verification_attempt_reference: str,
        verification_attempt_digest: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
        superseded_at: datetime | None = None,
        successor_target_result_reference: str | None = None,
        successor_target_result_digest: str | None = None,
        successor_failed_evidence_kind: str | None = None,
        successor_verification_attempt_reference: str | None = None,
        successor_verification_attempt_digest: str | None = None,
        successor_verification_attempt_released_at: datetime | None = None,
    ) -> ValidationResultNonVerifiabilitySupersessionAuthorityRecord:
        """Validate predecessor chronology and one complete same-obligation successor attempt."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        result_ref = _require_reference(
            "result_reference", result_reference, "validation_analysis_result"
        )
        result_evidence_digest = _require_digest("result_digest", result_digest)
        evidence_kind = _require_failed_evidence_kind(failed_evidence_kind)
        mode = _require_failure_mode(failure_mode)
        if mode == "non_reproducible":
            raise ValueError(
                "non_reproducible supersession requires exact failed-evidence identity; "
                "the v1 supersession contract fails closed instead of dropping it."
            )
        attempt_ref = _require_reference(
            "verification_attempt_reference",
            verification_attempt_reference,
            "validation_evidence_verification_attempt",
        )
        attempt_digest = _require_digest(
            "verification_attempt_digest", verification_attempt_digest
        )
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1.")
        owner_ref = _require_reference(
            "owner_contract_reference", owner_contract_reference, "released_owner_contract"
        )
        owner_version = _require_positive_integer(
            "owner_contract_version", owner_contract_version
        )
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        owner_released = _require_aware_datetime(
            "owner_contract_released_at", owner_contract_released_at
        )
        release_instant = _require_aware_datetime("released_at", released_at)
        if owner_released > release_instant:
            raise ValueError(
                "owner contract must be released no later than non-verifiability outcome."
            )
        if len({result_evidence_digest, attempt_digest, owner_digest}) != 3:
            raise ValueError(
                "result, verification-attempt, and owner-contract digests must be distinct."
            )

        successor_values = (
            superseded_at,
            successor_target_result_reference,
            successor_target_result_digest,
            successor_failed_evidence_kind,
            successor_verification_attempt_reference,
            successor_verification_attempt_digest,
            successor_verification_attempt_released_at,
        )
        if all(value is None for value in successor_values):
            cutover = None
            successor_target_ref = None
            successor_target_digest = None
            successor_evidence_kind = None
            successor_ref = None
            successor_digest = None
            successor_release = None
        elif any(value is None for value in successor_values):
            raise ValueError(
                "non-verifiability supersession requires cutover, same-result and "
                "failed-evidence-obligation binding, and complete successor attempt."
            )
        else:
            cutover = _require_aware_datetime("superseded_at", superseded_at)
            successor_target_ref = _require_reference(
                "successor_target_result_reference",
                successor_target_result_reference,
                "validation_analysis_result",
            )
            successor_target_digest = _require_digest(
                "successor_target_result_digest",
                successor_target_result_digest,
            )
            successor_evidence_kind = _require_failed_evidence_kind(
                successor_failed_evidence_kind
            )
            successor_ref = _require_reference(
                "successor_verification_attempt_reference",
                successor_verification_attempt_reference,
                "validation_evidence_verification_attempt",
            )
            successor_digest = _require_digest(
                "successor_verification_attempt_digest",
                successor_verification_attempt_digest,
            )
            successor_release = _require_aware_datetime(
                "successor_verification_attempt_released_at",
                successor_verification_attempt_released_at,
            )
            if cutover <= release_instant:
                raise ValueError(
                    "superseded_at must be later than non-verifiability release."
                )
            if (
                successor_target_ref != result_ref
                or successor_target_digest != result_evidence_digest
            ):
                raise ValueError(
                    "successor verification attempt must target the exact predecessor result."
                )
            if successor_evidence_kind != evidence_kind:
                raise ValueError(
                    "successor verification attempt must re-evaluate the same failed-evidence obligation."
                )
            if successor_ref == attempt_ref:
                raise ValueError("successor verification attempt must use a new reference.")
            if successor_digest in {result_evidence_digest, attempt_digest, owner_digest}:
                raise ValueError("successor verification attempt must identify new evidence.")
            if successor_release != cutover:
                raise ValueError(
                    "successor verification attempt must be released exactly at supersession."
                )

        current_fields: tuple[tuple[str, object], ...] = (
            ("evidence_version", version),
            ("failed_evidence_kind", evidence_kind),
            ("failure_mode", mode),
            ("owner_contract_digest", owner_digest),
            ("owner_contract_reference", owner_ref),
            ("owner_contract_released_at", owner_released),
            ("owner_contract_version", owner_version),
            ("result_digest", result_evidence_digest),
            ("result_reference", result_ref),
            ("verification_attempt_digest", attempt_digest),
            ("verification_attempt_reference", attempt_ref),
        )
        successor_fields: tuple[tuple[str, object], ...] | None
        if cutover is None:
            successor_fields = None
        else:
            successor_fields = (
                ("successor_failed_evidence_kind", successor_evidence_kind),
                ("successor_target_result_digest", successor_target_digest),
                ("successor_target_result_reference", successor_target_ref),
                ("successor_verification_attempt_digest", successor_digest),
                ("successor_verification_attempt_reference", successor_ref),
                ("successor_verification_attempt_released_at", successor_release),
            )
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                current_fields,
                release_instant,
                cutover,
                successor_fields,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return immutable predecessor authority coordinates."""
        return self[2]

    @property
    def released_at(self) -> datetime:
        """Return when this non-verifiability outcome became released evidence."""
        return self[3]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive end of this negative outcome's authority interval."""
        return self[4]

    @property
    def successor_fields(self) -> tuple[tuple[str, object], ...] | None:
        """Return owner-internal successor obligation, attempt, and target-result coordinates."""
        return self[5]


class ValidationResultNonVerifiabilitySupersessionAuthorityView(tuple):
    """Minimized predecessor authority issued only after purpose authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> ValidationResultNonVerifiabilitySupersessionAuthorityView:
        """Reject public construction; only the resolver may issue this view."""
        raise TypeError(
            "ValidationResultNonVerifiabilitySupersessionAuthorityView is issued only by "
            "resolve_validation_result_nonverifiability_supersession_authority."
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
        """Return predecessor provenance without cutover or successor disclosure."""
        return self[2]


@runtime_checkable
class ValidationResultNonVerifiabilitySupersessionAuthorityReadPort(Protocol):
    """Owner read contract for released non-verifiability supersession evidence."""

    def read_validation_result_nonverifiability_supersession_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        failed_evidence_kind: str,
        failure_mode: str,
        verification_attempt_reference: str,
        verification_attempt_digest: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> ValidationResultNonVerifiabilitySupersessionAuthorityRecord | None:
        """Return matching released successor authority or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    ValidationResultNonVerifiabilitySupersessionAuthorityReadPort,
    "read_validation_result_nonverifiability_supersession_authority",
)


def resolve_validation_result_nonverifiability_supersession_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    result_reference: str,
    result_digest: str,
    failed_evidence_kind: str,
    failure_mode: str,
    verification_attempt_reference: str,
    verification_attempt_digest: str,
    evidence_version: int,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: ValidationResultNonVerifiabilitySupersessionAuthorityReadPort,
) -> ValidationResultNonVerifiabilitySupersessionAuthorityView:
    """Authorize then resolve one negative outcome's append-only authority interval."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port),
        "read_validation_result_nonverifiability_supersession_authority",
        None,
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_validation_result_nonverifiability_supersession_authority."
        )

    tenant_id = _restore_operational_uuid(
        "tenant_record_id", _store_operational_uuid("tenant_record_id", tenant_record_id)
    )
    study_id = _restore_operational_uuid(
        "validity_study_id", _store_operational_uuid("validity_study_id", validity_study_id)
    )
    result_ref = _require_reference(
        "result_reference", result_reference, "validation_analysis_result"
    )
    result_evidence_digest = _require_digest("result_digest", result_digest)
    evidence_kind = _require_failed_evidence_kind(failed_evidence_kind)
    mode = _require_failure_mode(failure_mode)
    attempt_ref = _require_reference(
        "verification_attempt_reference",
        verification_attempt_reference,
        "validation_evidence_verification_attempt",
    )
    attempt_digest = _require_digest(
        "verification_attempt_digest", verification_attempt_digest
    )
    version = _require_positive_integer("evidence_version", evidence_version)
    if version != 1:
        raise ValueError("evidence_version must remain 1.")
    owner_ref = _require_reference(
        "owner_contract_reference", owner_contract_reference, "released_owner_contract"
    )
    owner_version = _require_positive_integer(
        "owner_contract_version", owner_contract_version
    )
    owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
    use_instant = _require_aware_datetime("used_at", used_at)
    purpose = _require_code("purpose_code", purpose_code)
    detached_principal = ValidationPrincipal(
        tenant_record_id=principal.tenant_record_id,
        actor_reference=principal.actor_reference,
        granted_scope_codes=principal.granted_scope_codes,
    )
    detached_policy = _detach_policy(policy)

    require_purpose_bound_access(
        request=PurposeBoundAccessRequest(
            tenant_record_id=tenant_id,
            actor_tenant_record_id=detached_principal.tenant_record_id,
            resource_tenant_record_id=tenant_id,
            actor_reference=detached_principal.actor_reference,
            resource_reference=f"{_RESOURCE_KIND}:{study_id}",
            purpose_code=purpose,
            operation_code=_OPERATION,
            resource_kind=_RESOURCE_KIND,
            requested_fields=_READ_FIELDS,
            granted_scope_codes=detached_principal.granted_scope_codes,
        ),
        policy=detached_policy,
    )

    persisted = read_capability(
        read_port,
        tenant_record_id=tenant_id,
        validity_study_id=study_id,
        result_reference=result_ref,
        result_digest=result_evidence_digest,
        failed_evidence_kind=evidence_kind,
        failure_mode=mode,
        verification_attempt_reference=attempt_ref,
        verification_attempt_digest=attempt_digest,
        evidence_version=version,
        owner_contract_reference=owner_ref,
        owner_contract_version=owner_version,
        owner_contract_digest=owner_digest,
    )
    if persisted is None:
        raise ValidationResultNonVerifiabilitySupersessionAuthorityNotFound(str(study_id))
    if type(persisted) is not ValidationResultNonVerifiabilitySupersessionAuthorityRecord:
        raise ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError(
            "owner port returned non-canonical non-verifiability supersession evidence"
        )

    try:
        persisted_fields = dict(persisted.fields)
        persisted_successor = (
            None if persisted.successor_fields is None else dict(persisted.successor_fields)
        )
        record = ValidationResultNonVerifiabilitySupersessionAuthorityRecord(
            tenant_record_id=persisted.tenant_record_id,
            validity_study_id=persisted.validity_study_id,
            result_reference=persisted_fields["result_reference"],
            result_digest=persisted_fields["result_digest"],
            failed_evidence_kind=persisted_fields["failed_evidence_kind"],
            failure_mode=persisted_fields["failure_mode"],
            verification_attempt_reference=persisted_fields["verification_attempt_reference"],
            verification_attempt_digest=persisted_fields["verification_attempt_digest"],
            evidence_version=persisted_fields["evidence_version"],
            owner_contract_reference=persisted_fields["owner_contract_reference"],
            owner_contract_version=persisted_fields["owner_contract_version"],
            owner_contract_digest=persisted_fields["owner_contract_digest"],
            owner_contract_released_at=persisted_fields["owner_contract_released_at"],
            released_at=persisted.released_at,
            superseded_at=persisted.superseded_at,
            successor_target_result_reference=(
                None
                if persisted_successor is None
                else persisted_successor["successor_target_result_reference"]
            ),
            successor_target_result_digest=(
                None
                if persisted_successor is None
                else persisted_successor["successor_target_result_digest"]
            ),
            successor_failed_evidence_kind=(
                None
                if persisted_successor is None
                else persisted_successor["successor_failed_evidence_kind"]
            ),
            successor_verification_attempt_reference=(
                None
                if persisted_successor is None
                else persisted_successor["successor_verification_attempt_reference"]
            ),
            successor_verification_attempt_digest=(
                None
                if persisted_successor is None
                else persisted_successor["successor_verification_attempt_digest"]
            ),
            successor_verification_attempt_released_at=(
                None
                if persisted_successor is None
                else persisted_successor["successor_verification_attempt_released_at"]
            ),
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError(
            "owner port returned structurally invalid non-verifiability supersession evidence"
        ) from exc
    if record != persisted:
        raise ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError(
            "owner port returned non-canonical non-verifiability supersession structure"
        )

    record_values = dict(record.fields)
    requested_values = {
        "evidence_version": version,
        "failed_evidence_kind": evidence_kind,
        "failure_mode": mode,
        "owner_contract_digest": owner_digest,
        "owner_contract_reference": owner_ref,
        "owner_contract_version": owner_version,
        "result_digest": result_evidence_digest,
        "result_reference": result_ref,
        "verification_attempt_digest": attempt_digest,
        "verification_attempt_reference": attempt_ref,
    }
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != _store_operational_uuid("requested tenant_record_id", tenant_id)
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != _store_operational_uuid("requested validity_study_id", study_id)
        or any(record_values[name] != value for name, value in requested_values.items())
    ):
        raise ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError(
            "owner evidence does not match requested non-verifiability correction coordinates"
        )
    if use_instant < record.released_at:
        raise ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError(
            "non-verifiability authority cannot be used before its release instant"
        )
    if record.superseded_at is not None and use_instant >= record.superseded_at:
        raise ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError(
            "non-verifiability authority ended at its owner-resolved supersession instant"
        )

    values = {**record_values, "released_at": record.released_at}
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_VIEW_FIELDS))
    return tuple.__new__(
        ValidationResultNonVerifiabilitySupersessionAuthorityView,
        (
            _store_operational_uuid("tenant_record_id", tenant_id),
            _store_operational_uuid("validity_study_id", study_id),
            fields,
        ),
    )


__all__ = [
    "ValidationResultNonVerifiabilitySupersessionAuthorityIntegrityError",
    "ValidationResultNonVerifiabilitySupersessionAuthorityNotFound",
    "ValidationResultNonVerifiabilitySupersessionAuthorityReadPort",
    "ValidationResultNonVerifiabilitySupersessionAuthorityRecord",
    "ValidationResultNonVerifiabilitySupersessionAuthorityView",
    "resolve_validation_result_nonverifiability_supersession_authority",
]
