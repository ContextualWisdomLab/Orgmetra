"""Corroborate append-only weight-eligibility correction authority.

The ordinary eligibility projection proves which population, reference duration,
case set, and point-weight artifact one receipt governs. This boundary proves
when that released receipt remained authoritative and which released successor
ended its half-open authority interval. It keeps row-level weights and person
attributes behind their scientific owners.
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

_RESOURCE_KIND = "weight_eligibility_supersession_authority"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "eligibility_receipt_reference",
        "eligibility_receipt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_eligibility_receipt_reference",
        "successor_eligibility_receipt_digest",
        "successor_evidence_version",
        "successor_released_at",
    }
)
_VIEW_FIELDS = frozenset(
    {
        "eligibility_receipt_reference",
        "eligibility_receipt_digest",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
    }
)


class WeightEligibilitySupersessionAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the eligibility receipt."""


class WeightEligibilitySupersessionAuthorityIntegrityError(RuntimeError):
    """Indicate that released eligibility correction evidence cannot authorize use."""


class WeightEligibilitySupersessionAuthorityRecord(tuple):
    """Immutable owner projection for one eligibility receipt authority interval."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        eligibility_receipt_reference: str,
        eligibility_receipt_digest: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
        superseded_at: datetime | None = None,
        successor_eligibility_receipt_reference: str | None = None,
        successor_eligibility_receipt_digest: str | None = None,
        successor_evidence_version: int | None = None,
        successor_released_at: datetime | None = None,
    ) -> WeightEligibilitySupersessionAuthorityRecord:
        """Validate one released predecessor and its optional atomic successor edge."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        receipt_ref = _require_reference(
            "eligibility_receipt_reference",
            eligibility_receipt_reference,
            "weight_eligibility_receipt",
        )
        receipt_digest = _require_digest(
            "eligibility_receipt_digest", eligibility_receipt_digest
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
        owner_release = _require_aware_datetime(
            "owner_contract_released_at", owner_contract_released_at
        )
        release_instant = _require_aware_datetime("released_at", released_at)
        if owner_release > release_instant:
            raise ValueError(
                "owner contract must be released no later than weight-eligibility receipt."
            )

        successor_values = (
            superseded_at,
            successor_eligibility_receipt_reference,
            successor_eligibility_receipt_digest,
            successor_evidence_version,
            successor_released_at,
        )
        if all(value is None for value in successor_values):
            cutover = None
            successor_ref = None
            successor_digest = None
            successor_version = None
            successor_release = None
        elif any(value is None for value in successor_values):
            raise ValueError(
                "eligibility supersession requires cutover and complete released successor coordinates."
            )
        else:
            cutover = _require_aware_datetime("superseded_at", superseded_at)
            successor_ref = _require_reference(
                "successor_eligibility_receipt_reference",
                successor_eligibility_receipt_reference,
                "weight_eligibility_receipt",
            )
            successor_digest = _require_digest(
                "successor_eligibility_receipt_digest",
                successor_eligibility_receipt_digest,
            )
            successor_version = _require_positive_integer(
                "successor_evidence_version", successor_evidence_version
            )
            successor_release = _require_aware_datetime(
                "successor_released_at", successor_released_at
            )
            if cutover <= release_instant:
                raise ValueError("superseded_at must be later than eligibility receipt release.")
            if successor_ref == receipt_ref:
                raise ValueError("successor eligibility receipt must have a new reference.")
            if successor_digest == receipt_digest:
                raise ValueError("successor eligibility receipt must identify new evidence.")
            if successor_version != 1:
                raise ValueError("successor_evidence_version must remain 1.")
            if successor_release <= release_instant:
                raise ValueError(
                    "successor eligibility receipt must be released after its predecessor."
                )
            if successor_release != cutover:
                raise ValueError(
                    "successor eligibility receipt must be released exactly at supersession."
                )

        current_fields: tuple[tuple[str, object], ...] = (
            ("eligibility_receipt_digest", receipt_digest),
            ("eligibility_receipt_reference", receipt_ref),
            ("evidence_version", version),
            ("owner_contract_digest", owner_digest),
            ("owner_contract_reference", owner_ref),
            ("owner_contract_released_at", owner_release),
            ("owner_contract_version", owner_version),
        )
        successor_fields: tuple[tuple[str, object], ...] | None
        if cutover is None:
            successor_fields = None
        else:
            successor_fields = (
                ("successor_eligibility_receipt_digest", successor_digest),
                ("successor_eligibility_receipt_reference", successor_ref),
                ("successor_evidence_version", successor_version),
                ("successor_released_at", successor_release),
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
        """Return immutable current-receipt authority coordinates."""
        return self[2]

    @property
    def released_at(self) -> datetime:
        """Return when this eligibility receipt became released authority."""
        return self[3]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive end of this receipt's authority interval."""
        return self[4]

    @property
    def successor_fields(self) -> tuple[tuple[str, object], ...] | None:
        """Return internal released successor coordinates, if any."""
        return self[5]


class WeightEligibilitySupersessionAuthorityView(tuple):
    """Minimized current-receipt authority issued only after authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> WeightEligibilitySupersessionAuthorityView:
        """Reject public construction; only the resolver may issue this view."""
        raise TypeError(
            "WeightEligibilitySupersessionAuthorityView is issued only by "
            "resolve_weight_eligibility_supersession_authority."
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh authorized tenant identity."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return current eligibility authority without successor disclosure."""
        return self[2]


@runtime_checkable
class WeightEligibilitySupersessionAuthorityReadPort(Protocol):
    """Owner read contract for one released eligibility correction state."""

    def read_weight_eligibility_supersession_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        eligibility_receipt_reference: str,
        eligibility_receipt_digest: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> WeightEligibilitySupersessionAuthorityRecord | None:
        """Return matching released eligibility supersession evidence or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    WeightEligibilitySupersessionAuthorityReadPort,
    "read_weight_eligibility_supersession_authority",
)


def resolve_weight_eligibility_supersession_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    eligibility_receipt_reference: str,
    eligibility_receipt_digest: str,
    evidence_version: int,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: WeightEligibilitySupersessionAuthorityReadPort,
) -> WeightEligibilitySupersessionAuthorityView:
    """Authorize then resolve the receipt's half-open append-only authority interval."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_weight_eligibility_supersession_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_weight_eligibility_supersession_authority."
        )

    tenant_id = _restore_operational_uuid(
        "tenant_record_id", _store_operational_uuid("tenant_record_id", tenant_record_id)
    )
    study_id = _restore_operational_uuid(
        "validity_study_id", _store_operational_uuid("validity_study_id", validity_study_id)
    )
    receipt_ref = _require_reference(
        "eligibility_receipt_reference",
        eligibility_receipt_reference,
        "weight_eligibility_receipt",
    )
    receipt_digest = _require_digest(
        "eligibility_receipt_digest", eligibility_receipt_digest
    )
    version = _require_positive_integer("evidence_version", evidence_version)
    if version != 1:
        raise ValueError("evidence_version must remain 1.")
    owner_ref = _require_reference(
        "owner_contract_reference", owner_contract_reference, "released_owner_contract"
    )
    owner_version = _require_positive_integer("owner_contract_version", owner_contract_version)
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
        eligibility_receipt_reference=receipt_ref,
        eligibility_receipt_digest=receipt_digest,
        evidence_version=version,
        owner_contract_reference=owner_ref,
        owner_contract_version=owner_version,
        owner_contract_digest=owner_digest,
    )
    if persisted is None:
        raise WeightEligibilitySupersessionAuthorityNotFound(str(study_id))
    if type(persisted) is not WeightEligibilitySupersessionAuthorityRecord:
        raise WeightEligibilitySupersessionAuthorityIntegrityError(
            "owner port returned non-canonical weight-eligibility supersession evidence"
        )

    successor_values = None if persisted.successor_fields is None else dict(persisted.successor_fields)
    record = WeightEligibilitySupersessionAuthorityRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        released_at=persisted.released_at,
        superseded_at=persisted.superseded_at,
        successor_eligibility_receipt_reference=(
            None
            if successor_values is None
            else successor_values["successor_eligibility_receipt_reference"]
        ),
        successor_eligibility_receipt_digest=(
            None
            if successor_values is None
            else successor_values["successor_eligibility_receipt_digest"]
        ),
        successor_evidence_version=(
            None
            if successor_values is None
            else successor_values["successor_evidence_version"]
        ),
        successor_released_at=(
            None if successor_values is None else successor_values["successor_released_at"]
        ),
        **dict(persisted.fields),
    )
    record_values = dict(record.fields)
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != _store_operational_uuid("requested tenant_record_id", tenant_id)
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != _store_operational_uuid("requested validity_study_id", study_id)
        or record_values["eligibility_receipt_reference"] != receipt_ref
        or record_values["eligibility_receipt_digest"] != receipt_digest
        or record_values["evidence_version"] != version
        or record_values["owner_contract_reference"] != owner_ref
        or record_values["owner_contract_version"] != owner_version
        or record_values["owner_contract_digest"] != owner_digest
    ):
        raise WeightEligibilitySupersessionAuthorityIntegrityError(
            "released eligibility supersession authority does not match requested coordinates"
        )
    if use_instant < record.released_at:
        raise WeightEligibilitySupersessionAuthorityIntegrityError(
            "weight-eligibility authority cannot be used before its release instant"
        )
    if record.superseded_at is not None and use_instant >= record.superseded_at:
        raise WeightEligibilitySupersessionAuthorityIntegrityError(
            "weight-eligibility authority cannot be used at or after supersession"
        )

    values = dict(record.fields)
    values["released_at"] = record.released_at
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_VIEW_FIELDS))
    return tuple.__new__(
        WeightEligibilitySupersessionAuthorityView,
        (
            _store_operational_uuid("tenant_record_id", record.tenant_record_id),
            _store_operational_uuid("validity_study_id", record.validity_study_id),
            fields,
        ),
    )


__all__ = [
    "WeightEligibilitySupersessionAuthorityIntegrityError",
    "WeightEligibilitySupersessionAuthorityNotFound",
    "WeightEligibilitySupersessionAuthorityReadPort",
    "WeightEligibilitySupersessionAuthorityRecord",
    "WeightEligibilitySupersessionAuthorityView",
    "resolve_weight_eligibility_supersession_authority",
]
