"""Corroborate append-only validation-result correction authority.

One validation-result record proves what immutable scientific evidence was
released. This application boundary proves when that released result remained
authoritative and which complete released successor ended its half-open
authority interval. Successor coordinates stay internal to the owner boundary.
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
from .scientific_authority import (
    _require_digest,
    _require_positive_integer,
    _require_reference,
)

_RESOURCE_KIND = "validation_result_supersession_authority"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "evidence_version",
        "correction_sequence",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_result_reference",
        "successor_correction_sequence",
        "successor_result_digest",
        "successor_released_at",
    }
)
_VIEW_FIELDS = frozenset(
    {
        "result_reference",
        "result_digest",
        "evidence_version",
        "correction_sequence",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
    }
)


class ValidationResultSupersessionAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the result version."""


class ValidationResultSupersessionAuthorityIntegrityError(RuntimeError):
    """Indicate that released correction evidence cannot authorize result use."""


class ValidationResultSupersessionAuthorityRecord(tuple):
    """Immutable owner projection for one released result authority interval."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        evidence_version: int,
        correction_sequence: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
        superseded_at: datetime | None = None,
        successor_result_reference: str | None = None,
        successor_correction_sequence: int | None = None,
        successor_result_digest: str | None = None,
        successor_released_at: datetime | None = None,
    ) -> ValidationResultSupersessionAuthorityRecord:
        """Validate released predecessor/successor chronology without result values."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        result_ref = _require_reference(
            "result_reference", result_reference, "validation_analysis_result"
        )
        result_evidence_digest = _require_digest("result_digest", result_digest)
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1.")
        correction = _require_positive_integer("correction_sequence", correction_sequence)
        owner_ref = _require_reference(
            "owner_contract_reference", owner_contract_reference, "released_owner_contract"
        )
        owner_version = _require_positive_integer(
            "owner_contract_version", owner_contract_version
        )
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        contract_released_at = _require_aware_datetime(
            "owner_contract_released_at", owner_contract_released_at
        )
        release_instant = _require_aware_datetime("released_at", released_at)
        if contract_released_at > release_instant:
            raise ValueError(
                "owner contract must be released no later than validation result."
            )

        supersession_values = (
            superseded_at,
            successor_result_reference,
            successor_correction_sequence,
            successor_result_digest,
            successor_released_at,
        )
        if all(value is None for value in supersession_values):
            cutover = None
            successor_ref = None
            successor_correction = None
            successor_digest = None
            successor_release = None
        elif any(value is None for value in supersession_values):
            raise ValueError(
                "result supersession requires time and complete released successor coordinates."
            )
        else:
            cutover = _require_aware_datetime("superseded_at", superseded_at)
            successor_ref = _require_reference(
                "successor_result_reference",
                successor_result_reference,
                "validation_analysis_result",
            )
            successor_correction = _require_positive_integer(
                "successor_correction_sequence", successor_correction_sequence
            )
            successor_digest = _require_digest(
                "successor_result_digest", successor_result_digest
            )
            successor_release = _require_aware_datetime(
                "successor_released_at", successor_released_at
            )
            if cutover < release_instant:
                raise ValueError("superseded_at cannot precede validation-result release.")
            if successor_ref == result_ref:
                raise ValueError("successor validation result must use a new reference.")
            if successor_correction != correction + 1:
                raise ValueError(
                    "successor correction_sequence must advance exactly by one."
                )
            if successor_digest == result_evidence_digest:
                raise ValueError("successor validation result must identify new evidence.")
            if successor_release <= release_instant:
                raise ValueError(
                    "successor validation result must be released after its predecessor."
                )
            if successor_release != cutover:
                raise ValueError(
                    "successor validation result must be released exactly at supersession."
                )

        current_fields: tuple[tuple[str, object], ...] = (
            ("correction_sequence", correction),
            ("evidence_version", version),
            ("owner_contract_digest", owner_digest),
            ("owner_contract_reference", owner_ref),
            ("owner_contract_released_at", contract_released_at),
            ("owner_contract_version", owner_version),
            ("result_digest", result_evidence_digest),
            ("result_reference", result_ref),
        )
        successor_fields: tuple[tuple[str, object], ...] | None
        if cutover is None:
            successor_fields = None
        else:
            successor_fields = (
                ("successor_correction_sequence", successor_correction),
                ("successor_released_at", successor_release),
                ("successor_result_digest", successor_digest),
                ("successor_result_reference", successor_ref),
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
        """Return immutable current-result authority coordinates."""
        return self[2]

    @property
    def released_at(self) -> datetime:
        """Return when this validation result became released authority."""
        return self[3]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive end of this result's authority interval."""
        return self[4]

    @property
    def successor_fields(self) -> tuple[tuple[str, object], ...] | None:
        """Return internal released successor coordinates, if any."""
        return self[5]


class ValidationResultSupersessionAuthorityView(tuple):
    """Minimized current-result authority issued only after purpose authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> ValidationResultSupersessionAuthorityView:
        """Reject public construction; only the resolver may issue this view."""
        raise TypeError(
            "ValidationResultSupersessionAuthorityView is issued only by "
            "resolve_validation_result_supersession_authority."
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
        """Return released current-result provenance without successor disclosure."""
        return self[2]


@runtime_checkable
class ValidationResultSupersessionAuthorityReadPort(Protocol):
    """Owner read contract for one released validation-result correction state."""

    def read_validation_result_supersession_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        result_reference: str,
        result_digest: str,
        evidence_version: int,
        correction_sequence: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> ValidationResultSupersessionAuthorityRecord | None:
        """Return matching released supersession evidence or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    ValidationResultSupersessionAuthorityReadPort,
    "read_validation_result_supersession_authority",
)


def resolve_validation_result_supersession_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    result_reference: str,
    result_digest: str,
    evidence_version: int,
    correction_sequence: int,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: ValidationResultSupersessionAuthorityReadPort,
) -> ValidationResultSupersessionAuthorityView:
    """Authorize then resolve the result's half-open append-only authority interval."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_validation_result_supersession_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_validation_result_supersession_authority."
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
    version = _require_positive_integer("evidence_version", evidence_version)
    if version != 1:
        raise ValueError("evidence_version must remain 1.")
    correction = _require_positive_integer("correction_sequence", correction_sequence)
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
        evidence_version=version,
        correction_sequence=correction,
        owner_contract_reference=owner_ref,
        owner_contract_version=owner_version,
        owner_contract_digest=owner_digest,
    )
    if persisted is None:
        raise ValidationResultSupersessionAuthorityNotFound(str(study_id))
    if type(persisted) is not ValidationResultSupersessionAuthorityRecord:
        raise ValidationResultSupersessionAuthorityIntegrityError(
            "owner port returned non-canonical validation-result supersession evidence"
        )

    try:
        persisted_fields = dict(persisted.fields)
        persisted_successor = (
            None if persisted.successor_fields is None else dict(persisted.successor_fields)
        )
        record = ValidationResultSupersessionAuthorityRecord(
            tenant_record_id=persisted.tenant_record_id,
            validity_study_id=persisted.validity_study_id,
            result_reference=persisted_fields["result_reference"],
            result_digest=persisted_fields["result_digest"],
            evidence_version=persisted_fields["evidence_version"],
            correction_sequence=persisted_fields["correction_sequence"],
            owner_contract_reference=persisted_fields["owner_contract_reference"],
            owner_contract_version=persisted_fields["owner_contract_version"],
            owner_contract_digest=persisted_fields["owner_contract_digest"],
            owner_contract_released_at=persisted_fields["owner_contract_released_at"],
            released_at=persisted.released_at,
            superseded_at=persisted.superseded_at,
            successor_result_reference=(
                None
                if persisted_successor is None
                else persisted_successor["successor_result_reference"]
            ),
            successor_correction_sequence=(
                None
                if persisted_successor is None
                else persisted_successor["successor_correction_sequence"]
            ),
            successor_result_digest=(
                None
                if persisted_successor is None
                else persisted_successor["successor_result_digest"]
            ),
            successor_released_at=(
                None
                if persisted_successor is None
                else persisted_successor["successor_released_at"]
            ),
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise ValidationResultSupersessionAuthorityIntegrityError(
            "owner port returned malformed validation-result supersession evidence"
        ) from exc
    if record != persisted:
        raise ValidationResultSupersessionAuthorityIntegrityError(
            "owner port returned non-canonical validation-result supersession structure"
        )

    record_values = dict(record.fields)
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != _store_operational_uuid("requested tenant_record_id", tenant_id)
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != _store_operational_uuid("requested validity_study_id", study_id)
        or record_values["result_reference"] != result_ref
        or record_values["result_digest"] != result_evidence_digest
        or record_values["evidence_version"] != version
        or record_values["correction_sequence"] != correction
        or record_values["owner_contract_reference"] != owner_ref
        or record_values["owner_contract_version"] != owner_version
        or record_values["owner_contract_digest"] != owner_digest
    ):
        raise ValidationResultSupersessionAuthorityIntegrityError(
            "owner evidence does not match requested validation-result correction coordinates"
        )
    if use_instant < record.released_at:
        raise ValidationResultSupersessionAuthorityIntegrityError(
            "validation-result authority cannot be used before its release instant"
        )
    if record.superseded_at is not None and use_instant >= record.superseded_at:
        raise ValidationResultSupersessionAuthorityIntegrityError(
            "validation-result authority ended at its owner-resolved supersession instant"
        )

    values = {
        **record_values,
        "released_at": record.released_at,
    }
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_VIEW_FIELDS))
    return tuple.__new__(
        ValidationResultSupersessionAuthorityView,
        (
            _store_operational_uuid("tenant_record_id", tenant_id),
            _store_operational_uuid("validity_study_id", study_id),
            fields,
        ),
    )


__all__ = [
    "ValidationResultSupersessionAuthorityIntegrityError",
    "ValidationResultSupersessionAuthorityNotFound",
    "ValidationResultSupersessionAuthorityReadPort",
    "ValidationResultSupersessionAuthorityRecord",
    "ValidationResultSupersessionAuthorityView",
    "resolve_validation_result_supersession_authority",
]
