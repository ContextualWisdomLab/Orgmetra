"""Resolve exact typed component receipts behind one released final analysis weight.

The v1 final-weight receipt already commits component evidence digests, but a
digest alone is not an owner-record locator. This companion authority maps one
immutable final-weight receipt identity to the exact released base-weight and
specialized adjustment receipts needed for deterministic reproduction. It does
not copy row-level weights or foreign application-table values.
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

_RESOURCE_KIND = "final_weight_component_binding_authority"
_OPERATION = "read"
_EVIDENCE_REFERENCE_NAMESPACE_BY_KIND = {
    "nonresponse_adjustment_receipt": "nonresponse_adjustment_receipt",
    "calibration_adjustment_receipt": "calibration_adjustment_receipt",
    "trimming_bounding_adjustment_receipt": "trimming_bounding_adjustment_receipt",
}
_READ_FIELDS = frozenset(
    {
        "analysis_weight_receipt_reference",
        "analysis_weight_receipt_digest",
        "analysis_weight_evidence_version",
        "binding_reference",
        "binding_digest",
        "binding_version",
        "base_weight_evidence_receipt_reference",
        "base_weight_evidence_receipt_digest",
        "base_weight_evidence_version",
        "adjustment_bindings",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
)


class FinalWeightComponentBindingAuthorityNotFound(LookupError):
    """Indicate that no released component locator exists for the final-weight receipt."""


class FinalWeightComponentBindingAuthorityIntegrityError(RuntimeError):
    """Indicate that component-binding owner evidence is malformed or targets another receipt."""


class FinalWeightAdjustmentEvidenceBinding(tuple):
    """Exact released receipt identity for one governed specialized adjustment."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        sequence_number: int,
        evidence_kind: str,
        evidence_receipt_reference: str,
        evidence_version: int,
        evidence_receipt_digest: str,
    ) -> FinalWeightAdjustmentEvidenceBinding:
        """Validate a specialized receipt locator without copying adjustment values."""
        sequence = _require_positive_integer("sequence_number", sequence_number)
        kind = _require_code("evidence_kind", evidence_kind)
        namespace = _EVIDENCE_REFERENCE_NAMESPACE_BY_KIND.get(kind)
        if namespace is None:
            raise ValueError("evidence_kind must identify a governed specialized receipt.")
        receipt_reference = _require_reference(
            "evidence_receipt_reference", evidence_receipt_reference, namespace
        )
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1 for specialized adjustment receipts.")
        receipt_digest = _require_digest("evidence_receipt_digest", evidence_receipt_digest)
        return tuple.__new__(
            cls,
            (sequence, kind, receipt_reference, version, receipt_digest),
        )

    @property
    def sequence_number(self) -> int:
        """Return the adjustment sequence from the final-weight construction."""
        return self[0]

    @property
    def evidence_kind(self) -> str:
        """Return the governed specialized receipt family."""
        return self[1]

    @property
    def evidence_receipt_reference(self) -> str:
        """Return the exact immutable specialized receipt reference."""
        return self[2]

    @property
    def evidence_version(self) -> int:
        """Return the governed specialized receipt evidence version."""
        return self[3]

    @property
    def evidence_receipt_digest(self) -> str:
        """Return the immutable specialized receipt digest."""
        return self[4]


class FinalWeightComponentBindingAuthorityRecord(tuple):
    """Immutable owner locator from one final-weight receipt to typed component receipts."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        analysis_weight_receipt_reference: str,
        analysis_weight_receipt_digest: str,
        analysis_weight_evidence_version: int,
        binding_reference: str,
        binding_digest: str,
        binding_version: int,
        base_weight_evidence_receipt_reference: str,
        base_weight_evidence_receipt_digest: str,
        base_weight_evidence_version: int,
        adjustment_bindings: tuple[FinalWeightAdjustmentEvidenceBinding, ...],
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
        superseded_at: datetime | None = None,
    ) -> FinalWeightComponentBindingAuthorityRecord:
        """Validate immutable receipt locators and owner-resolved authority chronology."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        final_receipt_reference = _require_reference(
            "analysis_weight_receipt_reference",
            analysis_weight_receipt_reference,
            "analysis_weight_receipt",
        )
        final_receipt_digest = _require_digest(
            "analysis_weight_receipt_digest", analysis_weight_receipt_digest
        )
        final_version = _require_positive_integer(
            "analysis_weight_evidence_version", analysis_weight_evidence_version
        )
        if final_version != 1:
            raise ValueError("analysis_weight_evidence_version must remain 1.")
        locator_reference = _require_reference(
            "binding_reference",
            binding_reference,
            "final_weight_component_binding",
        )
        locator_digest = _require_digest("binding_digest", binding_digest)
        locator_version = _require_positive_integer("binding_version", binding_version)
        if locator_version != 1:
            raise ValueError("binding_version must remain 1.")
        base_receipt_reference = _require_reference(
            "base_weight_evidence_receipt_reference",
            base_weight_evidence_receipt_reference,
            "base_weight_evidence_receipt",
        )
        base_receipt_digest = _require_digest(
            "base_weight_evidence_receipt_digest",
            base_weight_evidence_receipt_digest,
        )
        base_version = _require_positive_integer(
            "base_weight_evidence_version", base_weight_evidence_version
        )
        if base_version != 1:
            raise ValueError("base_weight_evidence_version must remain 1.")
        if type(adjustment_bindings) is not tuple:
            raise ValueError("adjustment_bindings must be an immutable tuple.")
        detached_bindings: list[FinalWeightAdjustmentEvidenceBinding] = []
        for expected_sequence, binding in enumerate(adjustment_bindings, start=1):
            if type(binding) is not FinalWeightAdjustmentEvidenceBinding:
                raise ValueError(
                    "adjustment_bindings must contain exact FinalWeightAdjustmentEvidenceBinding values."
                )
            detached = FinalWeightAdjustmentEvidenceBinding(
                sequence_number=binding.sequence_number,
                evidence_kind=binding.evidence_kind,
                evidence_receipt_reference=binding.evidence_receipt_reference,
                evidence_version=binding.evidence_version,
                evidence_receipt_digest=binding.evidence_receipt_digest,
            )
            if detached != binding:
                raise ValueError("adjustment_bindings must contain canonical receipt locators.")
            if detached.sequence_number != expected_sequence:
                raise ValueError(
                    "adjustment binding sequence numbers must be contiguous starting at 1."
                )
            detached_bindings.append(detached)
        owner_reference = _require_reference(
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
            raise ValueError("owner contract must be released no later than component binding.")
        cutover = None
        if superseded_at is not None:
            cutover = _require_aware_datetime("superseded_at", superseded_at)
            if cutover <= release_instant:
                raise ValueError("superseded_at must be later than released_at.")
        fields: tuple[tuple[str, object], ...] = (
            ("adjustment_bindings", tuple(detached_bindings)),
            ("analysis_weight_evidence_version", final_version),
            ("analysis_weight_receipt_digest", final_receipt_digest),
            ("analysis_weight_receipt_reference", final_receipt_reference),
            ("base_weight_evidence_receipt_digest", base_receipt_digest),
            ("base_weight_evidence_receipt_reference", base_receipt_reference),
            ("base_weight_evidence_version", base_version),
            ("binding_digest", locator_digest),
            ("binding_reference", locator_reference),
            ("binding_version", locator_version),
            ("owner_contract_digest", owner_digest),
            ("owner_contract_reference", owner_reference),
            ("owner_contract_version", owner_version),
        )
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                fields,
                owner_release,
                release_instant,
                cutover,
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
        """Return immutable final-weight and component receipt coordinates."""
        return self[2]

    @property
    def owner_contract_released_at(self) -> datetime:
        """Return when the governing component-binding owner contract was released."""
        return self[3]

    @property
    def released_at(self) -> datetime:
        """Return when this component locator became released authority."""
        return self[4]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive end of this locator's authority interval."""
        return self[5]


class FinalWeightComponentBindingAuthorityView:
    """Sealed component locator issued only after purpose authorization."""

    __slots__ = ("_tenant_identity", "_study_identity", "_fields", "_issuance_marker")

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> FinalWeightComponentBindingAuthorityView:
        """Reject public construction; only the resolver may issue this view."""
        raise TypeError(
            "FinalWeightComponentBindingAuthorityView is issued only by "
            "resolve_final_weight_component_binding_authority."
        )

    def __setattr__(self, name: str, value: object) -> None:
        """Keep ordinary callers from mutating issued projection state."""
        raise AttributeError("FinalWeightComponentBindingAuthorityView is immutable.")

    def __delattr__(self, name: str) -> None:
        """Keep ordinary callers from deleting issued projection state."""
        raise AttributeError("FinalWeightComponentBindingAuthorityView is immutable.")

    def _require_issued(self) -> None:
        """Reject exact-runtime allocations not sealed by the resolver."""
        _require_final_weight_component_binding_view_issued(self)

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh authorized tenant identity."""
        self._require_issued()
        return _restore_operational_uuid(
            "tenant_record_id", object.__getattribute__(self, "_tenant_identity")
        )

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh authorized validity-study identity."""
        self._require_issued()
        return _restore_operational_uuid(
            "validity_study_id", object.__getattribute__(self, "_study_identity")
        )

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return immutable component receipt locators and owner chronology."""
        self._require_issued()
        return object.__getattribute__(self, "_fields")


@runtime_checkable
class FinalWeightComponentBindingAuthorityReadPort(Protocol):
    """Owner read contract keyed only by the immutable final-weight receipt identity."""

    def read_final_weight_component_binding_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        analysis_weight_receipt_reference: str,
        analysis_weight_receipt_digest: str,
        analysis_weight_evidence_version: int,
    ) -> FinalWeightComponentBindingAuthorityRecord | None:
        """Return the unique released component locator for a final-weight receipt."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    FinalWeightComponentBindingAuthorityReadPort,
    "read_final_weight_component_binding_authority",
)


def _resolve_final_weight_component_binding_authority_state(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    analysis_weight_receipt_reference: str,
    analysis_weight_receipt_digest: str,
    analysis_weight_evidence_version: int,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: FinalWeightComponentBindingAuthorityReadPort,
) -> tuple[int, int, tuple[tuple[str, object], ...]]:
    """Authorize and resolve deterministic typed-component locators for a final weight."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_final_weight_component_binding_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_final_weight_component_binding_authority."
        )
    tenant_id = _restore_operational_uuid(
        "tenant_record_id", _store_operational_uuid("tenant_record_id", tenant_record_id)
    )
    study_id = _restore_operational_uuid(
        "validity_study_id", _store_operational_uuid("validity_study_id", validity_study_id)
    )
    final_receipt_reference = _require_reference(
        "analysis_weight_receipt_reference",
        analysis_weight_receipt_reference,
        "analysis_weight_receipt",
    )
    final_receipt_digest = _require_digest(
        "analysis_weight_receipt_digest", analysis_weight_receipt_digest
    )
    final_version = _require_positive_integer(
        "analysis_weight_evidence_version", analysis_weight_evidence_version
    )
    if final_version != 1:
        raise ValueError("analysis_weight_evidence_version must remain 1.")
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
        analysis_weight_receipt_reference=final_receipt_reference,
        analysis_weight_receipt_digest=final_receipt_digest,
        analysis_weight_evidence_version=final_version,
    )
    if persisted is None:
        raise FinalWeightComponentBindingAuthorityNotFound(str(study_id))
    if type(persisted) is not FinalWeightComponentBindingAuthorityRecord:
        raise FinalWeightComponentBindingAuthorityIntegrityError(
            "owner port returned non-canonical final-weight component binding evidence"
        )
    try:
        record = FinalWeightComponentBindingAuthorityRecord(
            tenant_record_id=persisted.tenant_record_id,
            validity_study_id=persisted.validity_study_id,
            owner_contract_released_at=persisted.owner_contract_released_at,
            released_at=persisted.released_at,
            superseded_at=persisted.superseded_at,
            **dict(persisted.fields),
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise FinalWeightComponentBindingAuthorityIntegrityError(
            "owner port returned malformed final-weight component binding evidence"
        ) from exc
    if record != persisted:
        raise FinalWeightComponentBindingAuthorityIntegrityError(
            "owner port returned non-canonical final-weight component binding evidence"
        )
    values = dict(record.fields)
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != _store_operational_uuid("requested tenant_record_id", tenant_id)
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != _store_operational_uuid("requested validity_study_id", study_id)
        or values["analysis_weight_receipt_reference"] != final_receipt_reference
        or values["analysis_weight_receipt_digest"] != final_receipt_digest
        or values["analysis_weight_evidence_version"] != final_version
    ):
        raise FinalWeightComponentBindingAuthorityIntegrityError(
            "released final-weight component binding targets another final-weight receipt"
        )
    if use_instant < record.released_at:
        raise FinalWeightComponentBindingAuthorityIntegrityError(
            "final-weight component binding cannot be used before release"
        )
    if record.superseded_at is not None and use_instant >= record.superseded_at:
        raise FinalWeightComponentBindingAuthorityIntegrityError(
            "final-weight component binding cannot be used at or after supersession"
        )
    values["owner_contract_released_at"] = record.owner_contract_released_at
    values["released_at"] = record.released_at
    values["superseded_at"] = record.superseded_at
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_READ_FIELDS))
    return (
        _store_operational_uuid("tenant_record_id", record.tenant_record_id),
        _store_operational_uuid("validity_study_id", record.validity_study_id),
        fields,
    )


def _build_final_weight_component_binding_view_runtime():
    """Create closure-private sealing state and the authorized public resolver."""
    issuance_marker = object()

    def require_issued(view: FinalWeightComponentBindingAuthorityView) -> None:
        """Verify one component-binding view against the private capability."""
        try:
            marker = object.__getattribute__(view, "_issuance_marker")
        except AttributeError as exc:
            raise FinalWeightComponentBindingAuthorityIntegrityError(
                "final-weight component binding view was not issued by "
                "resolve_final_weight_component_binding_authority"
            ) from exc
        if marker is not issuance_marker:
            raise FinalWeightComponentBindingAuthorityIntegrityError(
                "final-weight component binding view was not issued by "
                "resolve_final_weight_component_binding_authority"
            )

    def resolve(
        *,
        principal: ValidationPrincipal,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        analysis_weight_receipt_reference: str,
        analysis_weight_receipt_digest: str,
        analysis_weight_evidence_version: int,
        used_at: datetime,
        purpose_code: str,
        policy: PurposeBoundAccessPolicy,
        read_port: FinalWeightComponentBindingAuthorityReadPort,
    ) -> FinalWeightComponentBindingAuthorityView:
        """Authorize then issue deterministic typed-component locators."""
        tenant_identity, study_identity, fields = (
            _resolve_final_weight_component_binding_authority_state(
                principal=principal,
                tenant_record_id=tenant_record_id,
                validity_study_id=validity_study_id,
                analysis_weight_receipt_reference=analysis_weight_receipt_reference,
                analysis_weight_receipt_digest=analysis_weight_receipt_digest,
                analysis_weight_evidence_version=analysis_weight_evidence_version,
                used_at=used_at,
                purpose_code=purpose_code,
                policy=policy,
                read_port=read_port,
            )
        )
        view = object.__new__(FinalWeightComponentBindingAuthorityView)
        object.__setattr__(view, "_tenant_identity", tenant_identity)
        object.__setattr__(view, "_study_identity", study_identity)
        object.__setattr__(view, "_fields", fields)
        object.__setattr__(view, "_issuance_marker", issuance_marker)
        return view

    return require_issued, resolve


(
    _require_final_weight_component_binding_view_issued,
    resolve_final_weight_component_binding_authority,
) = _build_final_weight_component_binding_view_runtime()
del _build_final_weight_component_binding_view_runtime
