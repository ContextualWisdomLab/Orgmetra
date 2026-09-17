"""Corroborate released typed nonresponse-adjustment evidence through an owner port.

This application boundary binds the exact disposition-aware adjustment receipt
that produced a point-weight artifact. It preserves treatment and chronology
evidence without copying response values, source attributes, or row-level
weights. Durable PostgreSQL/release resolution remains a persistence-owner task
after this service reaches protected truth.
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

_RESOURCE_KIND = "nonresponse_adjustment_authority"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "nonresponse_receipt_reference",
        "nonresponse_receipt_digest",
        "evidence_version",
        "response_disposition_receipt_reference",
        "response_disposition_receipt_version",
        "response_disposition_receipt_digest",
        "response_disposition_receipt_released_at",
        "adjustment_population_digest",
        "method_reference",
        "method_version",
        "configuration_digest",
        "ineligible_treatment_code",
        "unknown_treatment_code",
        "unavailable_treatment_code",
        "input_weight_artifact_digest",
        "output_weight_artifact_digest",
        "constructed_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
    }
)


class NonresponseAdjustmentAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the nonresponse receipt."""


class NonresponseAdjustmentAuthorityIntegrityError(RuntimeError):
    """Indicate that owner evidence cannot corroborate the requested nonresponse receipt."""


class NonresponseAdjustmentAuthorityRecord(tuple):
    """Immutable owner projection for one released typed nonresponse receipt."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        nonresponse_receipt_reference: str,
        nonresponse_receipt_digest: str,
        evidence_version: int,
        response_disposition_receipt_reference: str,
        response_disposition_receipt_version: int,
        response_disposition_receipt_digest: str,
        response_disposition_receipt_released_at: datetime,
        adjustment_population_digest: str,
        method_reference: str,
        method_version: int,
        configuration_digest: str,
        ineligible_treatment_code: str,
        unknown_treatment_code: str,
        unavailable_treatment_code: str,
        input_weight_artifact_digest: str,
        output_weight_artifact_digest: str,
        constructed_at: datetime,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
    ) -> NonresponseAdjustmentAuthorityRecord:
        """Validate and detach the minimum disposition-aware scientific authority."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        receipt_ref = _require_reference(
            "nonresponse_receipt_reference",
            nonresponse_receipt_reference,
            "nonresponse_adjustment_receipt",
        )
        receipt_digest = _require_digest(
            "nonresponse_receipt_digest", nonresponse_receipt_digest
        )
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1.")
        disposition_ref = _require_reference(
            "response_disposition_receipt_reference",
            response_disposition_receipt_reference,
            "response_disposition_receipt",
        )
        disposition_version = _require_positive_integer(
            "response_disposition_receipt_version",
            response_disposition_receipt_version,
        )
        disposition_digest = _require_digest(
            "response_disposition_receipt_digest",
            response_disposition_receipt_digest,
        )
        disposition_released = _require_aware_datetime(
            "response_disposition_receipt_released_at",
            response_disposition_receipt_released_at,
        )
        population_digest = _require_digest(
            "adjustment_population_digest", adjustment_population_digest
        )
        method_ref = _require_reference(
            "method_reference", method_reference, "weight_method"
        )
        method_ver = _require_positive_integer("method_version", method_version)
        configuration = _require_digest("configuration_digest", configuration_digest)
        ineligible = _require_code("ineligible_treatment_code", ineligible_treatment_code)
        unknown = _require_code("unknown_treatment_code", unknown_treatment_code)
        unavailable = _require_code(
            "unavailable_treatment_code", unavailable_treatment_code
        )
        input_digest = _require_digest(
            "input_weight_artifact_digest", input_weight_artifact_digest
        )
        output_digest = _require_digest(
            "output_weight_artifact_digest", output_weight_artifact_digest
        )
        if input_digest == output_digest:
            raise ValueError(
                "output_weight_artifact_digest must identify the adjusted weight artifact."
            )
        constructed = _require_aware_datetime("constructed_at", constructed_at)
        if disposition_released > constructed:
            raise ValueError(
                "response_disposition_receipt_released_at cannot be later than constructed_at."
            )
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
        if release_instant < constructed:
            raise ValueError("released_at cannot precede constructed_at.")
        if owner_released > release_instant:
            raise ValueError(
                "owner_contract_released_at cannot be later than released_at."
            )

        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                receipt_ref,
                receipt_digest,
                version,
                disposition_ref,
                disposition_version,
                disposition_digest,
                disposition_released,
                population_digest,
                method_ref,
                method_ver,
                configuration,
                ineligible,
                unknown,
                unavailable,
                input_digest,
                output_digest,
                constructed,
                owner_ref,
                owner_version,
                owner_digest,
                owner_released,
                release_instant,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity for this released evidence."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity for this released evidence."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def nonresponse_receipt_reference(self) -> str:
        """Return the typed nonresponse-adjustment receipt reference."""
        return self[2]

    @property
    def nonresponse_receipt_digest(self) -> str:
        """Return the exact nonresponse-adjustment receipt digest."""
        return self[3]

    @property
    def evidence_version(self) -> int:
        """Return the receipt evidence version."""
        return self[4]

    @property
    def response_disposition_receipt_reference(self) -> str:
        """Return the exact response/disposition input receipt reference."""
        return self[5]

    @property
    def response_disposition_receipt_version(self) -> int:
        """Return the exact response/disposition input receipt version."""
        return self[6]

    @property
    def response_disposition_receipt_digest(self) -> str:
        """Return the exact response/disposition input receipt digest."""
        return self[7]

    @property
    def response_disposition_receipt_released_at(self) -> datetime:
        """Return when the disposition input became released evidence."""
        return self[8]

    @property
    def adjustment_population_digest(self) -> str:
        """Return the adjustment population digest."""
        return self[9]

    @property
    def method_reference(self) -> str:
        """Return the controlled nonresponse method reference."""
        return self[10]

    @property
    def method_version(self) -> int:
        """Return the controlled nonresponse method version."""
        return self[11]

    @property
    def configuration_digest(self) -> str:
        """Return the immutable method configuration digest."""
        return self[12]

    @property
    def ineligible_treatment_code(self) -> str:
        """Return the explicit treatment for ineligible cases."""
        return self[13]

    @property
    def unknown_treatment_code(self) -> str:
        """Return the explicit treatment for unknown dispositions."""
        return self[14]

    @property
    def unavailable_treatment_code(self) -> str:
        """Return the explicit treatment for unavailable dispositions."""
        return self[15]

    @property
    def input_weight_artifact_digest(self) -> str:
        """Return the input weight artifact digest."""
        return self[16]

    @property
    def output_weight_artifact_digest(self) -> str:
        """Return the nonresponse-adjusted output weight artifact digest."""
        return self[17]

    @property
    def constructed_at(self) -> datetime:
        """Return when the typed nonresponse receipt was constructed."""
        return self[18]

    @property
    def owner_contract_reference(self) -> str:
        """Return the released owner-contract reference."""
        return self[19]

    @property
    def owner_contract_version(self) -> int:
        """Return the released owner-contract version."""
        return self[20]

    @property
    def owner_contract_digest(self) -> str:
        """Return the released owner-contract digest."""
        return self[21]

    @property
    def owner_contract_released_at(self) -> datetime:
        """Return when the governing owner contract became released authority."""
        return self[22]

    @property
    def released_at(self) -> datetime:
        """Return when this typed nonresponse evidence became released authority."""
        return self[23]


class NonresponseAdjustmentAuthorityView(tuple):
    """Field-minimized nonresponse evidence issued only after authorization."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> NonresponseAdjustmentAuthorityView:
        """Reject direct construction; only the resolver may issue this view."""
        raise TypeError(
            "NonresponseAdjustmentAuthorityView is issued only by "
            "resolve_nonresponse_adjustment_authority."
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
        """Return immutable nonresponse provenance without response values."""
        return self[2]


@runtime_checkable
class NonresponseAdjustmentAuthorityReadPort(Protocol):
    """Owner read contract for released typed nonresponse-adjustment evidence."""

    def read_nonresponse_adjustment_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        nonresponse_receipt_reference: str,
        nonresponse_receipt_digest: str,
        evidence_version: int,
        response_disposition_receipt_reference: str,
        response_disposition_receipt_version: int,
        response_disposition_receipt_digest: str,
        adjustment_population_digest: str,
        method_reference: str,
        method_version: int,
        configuration_digest: str,
        ineligible_treatment_code: str,
        unknown_treatment_code: str,
        unavailable_treatment_code: str,
        input_weight_artifact_digest: str,
        output_weight_artifact_digest: str,
        constructed_at: datetime,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> NonresponseAdjustmentAuthorityRecord | None:
        """Return matching released typed nonresponse evidence or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    NonresponseAdjustmentAuthorityReadPort, "read_nonresponse_adjustment_authority"
)


def _coordinate_tuple(record: NonresponseAdjustmentAuthorityRecord) -> tuple[object, ...]:
    """Return caller-known coordinates, excluding owner-resolved release instants."""
    return record[:8] + record[9:22]


def resolve_nonresponse_adjustment_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    nonresponse_receipt_reference: str,
    nonresponse_receipt_digest: str,
    evidence_version: int,
    response_disposition_receipt_reference: str,
    response_disposition_receipt_version: int,
    response_disposition_receipt_digest: str,
    adjustment_population_digest: str,
    method_reference: str,
    method_version: int,
    configuration_digest: str,
    ineligible_treatment_code: str,
    unknown_treatment_code: str,
    unavailable_treatment_code: str,
    input_weight_artifact_digest: str,
    output_weight_artifact_digest: str,
    constructed_at: datetime,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: NonresponseAdjustmentAuthorityReadPort,
) -> NonresponseAdjustmentAuthorityView:
    """Authorize then corroborate the exact released nonresponse receipt."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_nonresponse_adjustment_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_nonresponse_adjustment_authority."
        )

    constructed = _require_aware_datetime("constructed_at", constructed_at)
    requested = NonresponseAdjustmentAuthorityRecord(
        tenant_record_id=tenant_record_id,
        validity_study_id=validity_study_id,
        nonresponse_receipt_reference=nonresponse_receipt_reference,
        nonresponse_receipt_digest=nonresponse_receipt_digest,
        evidence_version=evidence_version,
        response_disposition_receipt_reference=response_disposition_receipt_reference,
        response_disposition_receipt_version=response_disposition_receipt_version,
        response_disposition_receipt_digest=response_disposition_receipt_digest,
        response_disposition_receipt_released_at=constructed,
        adjustment_population_digest=adjustment_population_digest,
        method_reference=method_reference,
        method_version=method_version,
        configuration_digest=configuration_digest,
        ineligible_treatment_code=ineligible_treatment_code,
        unknown_treatment_code=unknown_treatment_code,
        unavailable_treatment_code=unavailable_treatment_code,
        input_weight_artifact_digest=input_weight_artifact_digest,
        output_weight_artifact_digest=output_weight_artifact_digest,
        constructed_at=constructed,
        owner_contract_reference=owner_contract_reference,
        owner_contract_version=owner_contract_version,
        owner_contract_digest=owner_contract_digest,
        owner_contract_released_at=constructed,
        released_at=constructed,
    )
    tenant_id = requested.tenant_record_id
    study_id = requested.validity_study_id
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
        nonresponse_receipt_reference=requested.nonresponse_receipt_reference,
        nonresponse_receipt_digest=requested.nonresponse_receipt_digest,
        evidence_version=requested.evidence_version,
        response_disposition_receipt_reference=requested.response_disposition_receipt_reference,
        response_disposition_receipt_version=requested.response_disposition_receipt_version,
        response_disposition_receipt_digest=requested.response_disposition_receipt_digest,
        adjustment_population_digest=requested.adjustment_population_digest,
        method_reference=requested.method_reference,
        method_version=requested.method_version,
        configuration_digest=requested.configuration_digest,
        ineligible_treatment_code=requested.ineligible_treatment_code,
        unknown_treatment_code=requested.unknown_treatment_code,
        unavailable_treatment_code=requested.unavailable_treatment_code,
        input_weight_artifact_digest=requested.input_weight_artifact_digest,
        output_weight_artifact_digest=requested.output_weight_artifact_digest,
        constructed_at=requested.constructed_at,
        owner_contract_reference=requested.owner_contract_reference,
        owner_contract_version=requested.owner_contract_version,
        owner_contract_digest=requested.owner_contract_digest,
    )
    if persisted is None:
        raise NonresponseAdjustmentAuthorityNotFound(str(study_id))
    if type(persisted) is not NonresponseAdjustmentAuthorityRecord:
        raise NonresponseAdjustmentAuthorityIntegrityError(
            "owner port returned non-canonical nonresponse-adjustment authority evidence"
        )

    record = NonresponseAdjustmentAuthorityRecord(
        tenant_record_id=persisted.tenant_record_id,
        validity_study_id=persisted.validity_study_id,
        nonresponse_receipt_reference=persisted.nonresponse_receipt_reference,
        nonresponse_receipt_digest=persisted.nonresponse_receipt_digest,
        evidence_version=persisted.evidence_version,
        response_disposition_receipt_reference=persisted.response_disposition_receipt_reference,
        response_disposition_receipt_version=persisted.response_disposition_receipt_version,
        response_disposition_receipt_digest=persisted.response_disposition_receipt_digest,
        response_disposition_receipt_released_at=persisted.response_disposition_receipt_released_at,
        adjustment_population_digest=persisted.adjustment_population_digest,
        method_reference=persisted.method_reference,
        method_version=persisted.method_version,
        configuration_digest=persisted.configuration_digest,
        ineligible_treatment_code=persisted.ineligible_treatment_code,
        unknown_treatment_code=persisted.unknown_treatment_code,
        unavailable_treatment_code=persisted.unavailable_treatment_code,
        input_weight_artifact_digest=persisted.input_weight_artifact_digest,
        output_weight_artifact_digest=persisted.output_weight_artifact_digest,
        constructed_at=persisted.constructed_at,
        owner_contract_reference=persisted.owner_contract_reference,
        owner_contract_version=persisted.owner_contract_version,
        owner_contract_digest=persisted.owner_contract_digest,
        owner_contract_released_at=persisted.owner_contract_released_at,
        released_at=persisted.released_at,
    )
    if _coordinate_tuple(record) != _coordinate_tuple(requested):
        raise NonresponseAdjustmentAuthorityIntegrityError(
            "released nonresponse-adjustment authority does not match requested coordinates"
        )
    if record.released_at > use_instant:
        raise NonresponseAdjustmentAuthorityIntegrityError(
            "nonresponse-adjustment evidence must be released before scientific use"
        )

    fields: tuple[tuple[str, object], ...] = (
        ("adjustment_population_digest", record.adjustment_population_digest),
        ("configuration_digest", record.configuration_digest),
        ("constructed_at", record.constructed_at),
        ("evidence_version", record.evidence_version),
        ("ineligible_treatment_code", record.ineligible_treatment_code),
        ("input_weight_artifact_digest", record.input_weight_artifact_digest),
        ("method_reference", record.method_reference),
        ("method_version", record.method_version),
        ("nonresponse_receipt_digest", record.nonresponse_receipt_digest),
        ("nonresponse_receipt_reference", record.nonresponse_receipt_reference),
        ("output_weight_artifact_digest", record.output_weight_artifact_digest),
        ("owner_contract_digest", record.owner_contract_digest),
        ("owner_contract_reference", record.owner_contract_reference),
        ("owner_contract_released_at", record.owner_contract_released_at),
        ("owner_contract_version", record.owner_contract_version),
        ("released_at", record.released_at),
        ("response_disposition_receipt_digest", record.response_disposition_receipt_digest),
        ("response_disposition_receipt_reference", record.response_disposition_receipt_reference),
        ("response_disposition_receipt_released_at", record.response_disposition_receipt_released_at),
        ("response_disposition_receipt_version", record.response_disposition_receipt_version),
        ("unavailable_treatment_code", record.unavailable_treatment_code),
        ("unknown_treatment_code", record.unknown_treatment_code),
    )
    return tuple.__new__(
        NonresponseAdjustmentAuthorityView,
        (
            _store_operational_uuid("tenant_record_id", tenant_id),
            _store_operational_uuid("validity_study_id", study_id),
            fields,
        ),
    )
