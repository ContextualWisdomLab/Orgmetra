"""Corroborate released base/design-weight evidence without copying row-level weights.

This boundary keeps stage-wise inclusion-probability evidence with its sampling
owner. Workforce validation receives only released references, versions, digests,
set identity, method identity, and the resulting base-weight artifact needed to
reproduce the scientific weight lineage.
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

_RESOURCE_KIND = "base_weight_authority"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "base_weight_evidence_receipt_reference",
        "base_weight_evidence_receipt_digest",
        "evidence_version",
        "source_universe_receipt_reference",
        "source_universe_receipt_version",
        "source_universe_receipt_digest",
        "source_universe_released_at",
        "sampling_design_receipt_reference",
        "sampling_design_receipt_version",
        "sampling_design_receipt_digest",
        "sampling_design_released_at",
        "sampled_occurrence_set_digest",
        "selection_probability_set_digest",
        "selection_stage_count",
        "base_weight_method_code",
        "base_weight_method_version",
        "base_weight_artifact_digest",
        "constructed_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
    }
)


class BaseWeightAuthorityNotFound(LookError := LookupError):
    """Indicate that no released owner evidence corroborates the base weight."""


class BaseWeightAuthorityIntegrityError(RuntimeError):
    """Indicate that released owner evidence cannot corroborate the requested base weight."""


class BaseWeightAuthorityRecord(tuple):
    """Immutable owner projection for one released base/design-weight construction."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        base_weight_evidence_receipt_reference: str,
        base_weight_evidence_receipt_digest: str,
        evidence_version: int,
        source_universe_receipt_reference: str,
        source_universe_receipt_version: int,
        source_universe_receipt_digest: str,
        source_universe_released_at: datetime,
        sampling_design_receipt_reference: str,
        sampling_design_receipt_version: int,
        sampling_design_receipt_digest: str,
        sampling_design_released_at: datetime,
        sampled_occurrence_set_digest: str,
        selection_probability_set_digest: str,
        selection_stage_count: int,
        base_weight_method_code: str,
        base_weight_method_version: int,
        base_weight_artifact_digest: str,
        constructed_at: datetime,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
    ) -> BaseWeightAuthorityRecord:
        """Validate the minimum released provenance needed to reproduce a base weight."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        receipt_ref = _require_reference(
            "base_weight_evidence_receipt_reference",
            base_weight_evidence_receipt_reference,
            "base_weight_evidence_receipt",
        )
        receipt_digest = _require_digest(
            "base_weight_evidence_receipt_digest", base_weight_evidence_receipt_digest
        )
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1.")
        source_ref = _require_reference(
            "source_universe_receipt_reference",
            source_universe_receipt_reference,
            "source_universe_receipt",
        )
        source_version = _require_positive_integer(
            "source_universe_receipt_version", source_universe_receipt_version
        )
        source_digest = _require_digest(
            "source_universe_receipt_digest", source_universe_receipt_digest
        )
        source_released = _require_aware_datetime(
            "source_universe_released_at", source_universe_released_at
        )
        sampling_ref = _require_reference(
            "sampling_design_receipt_reference",
            sampling_design_receipt_reference,
            "sampling_design_receipt",
        )
        sampling_version = _require_positive_integer(
            "sampling_design_receipt_version", sampling_design_receipt_version
        )
        sampling_digest = _require_digest(
            "sampling_design_receipt_digest", sampling_design_receipt_digest
        )
        sampling_released = _require_aware_datetime(
            "sampling_design_released_at", sampling_design_released_at
        )
        sampled_digest = _require_digest(
            "sampled_occurrence_set_digest", sampled_occurrence_set_digest
        )
        probability_digest = _require_digest(
            "selection_probability_set_digest", selection_probability_set_digest
        )
        stage_count = _require_positive_integer("selection_stage_count", selection_stage_count)
        method_code = _require_code("base_weight_method_code", base_weight_method_code)
        method_version = _require_positive_integer(
            "base_weight_method_version", base_weight_method_version
        )
        artifact_digest = _require_digest(
            "base_weight_artifact_digest", base_weight_artifact_digest
        )
        constructed = _require_aware_datetime("constructed_at", constructed_at)
        if source_released > constructed:
            raise ValueError("source_universe_released_at cannot be later than constructed_at.")
        if sampling_released > constructed:
            raise ValueError("sampling_design_released_at cannot be later than constructed_at.")
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
        if release_instant < constructed:
            raise ValueError("released_at cannot precede constructed_at.")
        if contract_released_at > release_instant:
            raise ValueError(
                "owner contract must be released no later than base-weight evidence receipt."
            )

        fields: tuple[tuple[str, object], ...] = (
            ("base_weight_artifact_digest", artifact_digest),
            ("base_weight_evidence_receipt_digest", receipt_digest),
            ("base_weight_evidence_receipt_reference", receipt_ref),
            ("base_weight_method_code", method_code),
            ("base_weight_method_version", method_version),
            ("constructed_at", constructed),
            ("evidence_version", version),
            ("owner_contract_digest", owner_digest),
            ("owner_contract_reference", owner_ref),
            ("owner_contract_released_at", contract_released_at),
            ("owner_contract_version", owner_version),
            ("sampled_occurrence_set_digest", sampled_digest),
            ("sampling_design_receipt_digest", sampling_digest),
            ("sampling_design_receipt_reference", sampling_ref),
            ("sampling_design_receipt_version", sampling_version),
            ("sampling_design_released_at", sampling_released),
            ("selection_probability_set_digest", probability_digest),
            ("selection_stage_count", stage_count),
            ("source_universe_receipt_digest", source_digest),
            ("source_universe_receipt_reference", source_ref),
            ("source_universe_receipt_version", source_version),
            ("source_universe_released_at", source_released),
        )
        return tuple.__new__(cls, (tenant_identity, study_identity, fields, release_instant))

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
        """Return immutable, value-minimized base-weight provenance."""
        return self[2]

    @property
    def released_at(self) -> datetime:
        """Return when the base-weight evidence became released authority."""
        return self[3]


class BaseWeightAuthorityView(tuple):
    """Field-minimized base-weight evidence issued only after authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> BaseWeightAuthorityView:
        """Reject public construction; only the resolver may issue this view."""
        raise TypeError(
            "BaseWeightAuthorityView is issued only by resolve_base_weight_authority."
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
        """Return released base-weight provenance without row-level probabilities."""
        return self[2]


@runtime_checkable
class BaseWeightAuthorityReadPort(Protocol):
    """Owner read contract for one released base/design-weight receipt."""

    def read_base_weight_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        base_weight_evidence_receipt_reference: str,
        base_weight_evidence_receipt_digest: str,
        evidence_version: int,
        source_universe_receipt_reference: str,
        source_universe_receipt_version: int,
        source_universe_receipt_digest: str,
        sampling_design_receipt_reference: str,
        sampling_design_receipt_version: int,
        sampling_design_receipt_digest: str,
        selection_probability_set_digest: str,
        owner_contract_reference: str,
        owner_contract_version: int,
    ) -> BaseWeightAuthorityRecord | None:
        """Return matching released base-weight evidence or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    BaseWeightAuthorityReadPort, "read_base_weight_authority"
)


def resolve_base_weight_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    base_weight_evidence_receipt_reference: str,
    base_weight_evidence_receipt_digest: str,
    evidence_version: int,
    source_universe_receipt_reference: str,
    source_universe_receipt_version: int,
    source_universe_receipt_digest: str,
    source_universe_released_at: datetime,
    sampling_design_receipt_reference: str,
    sampling_design_receipt_version: int,
    sampling_design_receipt_digest: str,
    sampling_design_released_at: datetime,
    sampled_occurrence_set_digest: str,
    selection_probability_set_digest: str,
    selection_stage_count: int,
    base_weight_method_code: str,
    base_weight_method_version: int,
    base_weight_artifact_digest: str,
    constructed_at: datetime,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: BaseWeightAuthorityReadPort,
) -> BaseWeightAuthorityView:
    """Authorize then corroborate released stage-wise base-weight evidence."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(type(read_port), "read_base_weight_authority", None)
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError("read_port must expose a statically callable read_base_weight_authority.")

    requested = BaseWeightAuthorityRecord(
        tenant_record_id=tenant_record_id,
        validity_study_id=validity_study_id,
        base_weight_evidence_receipt_reference=base_weight_evidence_receipt_reference,
        base_weight_evidence_receipt_digest=base_weight_evidence_receipt_digest,
        evidence_version=evidence_version,
        source_universe_receipt_reference=source_universe_receipt_reference,
        source_universe_receipt_version=source_universe_receipt_version,
        source_universe_receipt_digest=source_universe_receipt_digest,
        source_universe_released_at=source_universe_released_at,
        sampling_design_receipt_reference=sampling_design_receipt_reference,
        sampling_design_receipt_version=sampling_design_receipt_version,
        sampling_design_receipt_digest=sampling_design_receipt_digest,
        sampling_design_released_at=sampling_design_released_at,
        sampled_occurrence_set_digest=sampled_occurrence_set_digest,
        selection_probability_set_digest=selection_probability_set_digest,
        selection_stage_count=selection_stage_count,
        base_weight_method_code=base_weight_method_code,
        base_weight_method_version=base_weight_method_version,
        base_weight_artifact_digest=base_weight_artifact_digest,
        constructed_at=constructed_at,
        owner_contract_reference=owner_contract_reference,
        owner_contract_version=owner_contract_version,
        owner_contract_digest=owner_contract_digest,
        owner_contract_released_at=constructed_at,
        released_at=constructed_at,
    )
    tenant_id = requested.tenant_record_id
    study_id = requested.validity_study_id
    requested_values = dict(requested.fields)
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
        tenant_record_id=requested.tenant_record_id,
        validity_study_id=requested.validity_study_id,
        base_weight_evidence_receipt_reference=requested_values[
            "base_weight_evidence_receipt_reference"
        ],
        base_weight_evidence_receipt_digest=requested_values[
            "base_weight_evidence_receipt_digest"
        ],
        evidence_version=requested_values["evidence_version"],
        source_universe_receipt_reference=requested_values[
            "source_universe_receipt_reference"
        ],
        source_universe_receipt_version=requested_values[
            "source_universe_receipt_version"
        ],
        source_universe_receipt_digest=requested_values[
            "source_universe_receipt_digest"
        ],
        sampling_design_receipt_reference=requested_values[
            "sampling_design_receipt_reference"
        ],
        sampling_design_receipt_version=requested_values[
            "sampling_design_receipt_version"
        ],
        sampling_design_receipt_digest=requested_values[
            "sampling_design_receipt_digest"
        ],
        selection_probability_set_digest=requested_values[
            "selection_probability_set_digest"
        ],
        owner_contract_reference=requested_values["owner_contract_reference"],
        owner_contract_version=requested_values["owner_contract_version"],
    )
    if persisted is None:
        raise BaseWeightAuthorityNotFound(str(study_id))
    if type(persisted) is not BaseWeightAuthorityRecord:
        raise BaseWeightAuthorityIntegrityError(
            "owner port returned non-canonical base-weight authority evidence"
        )

    record = BaseWeightAuthorityRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        released_at=persisted.released_at,
        **dict(persisted.fields),
    )
    record_values = dict(record.fields)
    requested_match = tuple(
        (field_name, field_value)
        for field_name, field_value in requested.fields
        if field_name != "owner_contract_released_at"
    )
    record_match = tuple(
        (field_name, record_values[field_name])
        for field_name, _ in requested_match
    )
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != _store_operational_uuid("requested tenant_record_id", requested.tenant_record_id)
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != _store_operational_uuid("requested validity_study_id", requested.validity_study_id)
        or record_match != requested_match
    ):
        raise BaseWeightAuthorityIntegrityError(
            "released base-weight authority does not match requested coordinates"
        )
    if use_instant < record.released_at:
        raise BaseWeightAuthorityIntegrityError(
            "base-weight authority cannot be used before its release instant"
        )

    values = dict(record.fields)
    values["released_at"] = record.released_at
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_READ_FIELDS))
    return tuple.__new__(
        BaseWeightAuthorityView,
        (
            _store_operational_uuid("tenant_record_id", record.tenant_record_id),
            _store_operational_uuid("validity_study_id", record.validity_study_id),
            fields,
        ),
    )


__all__ = [
    "BaseWeightAuthorityIntegrityError",
    "BaseWeightAuthorityNotFound",
    "BaseWeightAuthorityReadPort",
    "BaseWeightAuthorityRecord",
    "BaseWeightAuthorityView",
    "resolve_base_weight_authority",
]