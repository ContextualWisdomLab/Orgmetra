"""Corroborate exact final-weight component receipts against final-weight semantics.

This cross-owner consistency service is used after purpose-authorized final-weight
and component-binding reads. It turns exact receipt locators into a deterministic
resolution contract and verifies both owner scope and scientific transform
semantics without copying row-level weights or foreign source values.
"""

from __future__ import annotations

from datetime import datetime
from inspect import getattr_static
from types import FunctionType
from typing import Protocol, runtime_checkable
from uuid import UUID

from .final_weight_authority import (
    FinalAnalysisWeightAuthorityRecord,
    FinalWeightAdjustmentCoordinate,
)
from .final_weight_component_binding_authority import (
    FinalWeightComponentBindingAuthorityRecord,
    _EVIDENCE_REFERENCE_NAMESPACE_BY_KIND,
)
from .registry import (
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


class FinalWeightComponentEvidenceNotFound(LookupError):
    """Indicate that an exact bound component receipt cannot be deterministically resolved."""


class FinalWeightComponentEvidenceIntegrityError(RuntimeError):
    """Indicate that resolved component evidence disagrees with final-weight authority."""


class BaseWeightComponentEvidence(tuple):
    """Scope-bound base-weight receipt projection needed to reproduce a final weight."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        receipt_reference: str,
        receipt_digest: str,
        evidence_version: int,
        method_code: str,
        method_version: int,
        output_weight_artifact_digest: str,
        released_at: datetime,
        superseded_at: datetime | None = None,
    ) -> BaseWeightComponentEvidence:
        """Validate immutable owner scope, receipt identity, semantics and chronology."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        reference = _require_reference(
            "receipt_reference", receipt_reference, "base_weight_evidence_receipt"
        )
        digest = _require_digest("receipt_digest", receipt_digest)
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1 for base-weight evidence.")
        method = _require_code("method_code", method_code)
        method_ver = _require_positive_integer("method_version", method_version)
        output_digest = _require_digest(
            "output_weight_artifact_digest", output_weight_artifact_digest
        )
        release = _require_aware_datetime("released_at", released_at)
        cutover = None
        if superseded_at is not None:
            cutover = _require_aware_datetime("superseded_at", superseded_at)
            if cutover <= release:
                raise ValueError("superseded_at must be later than released_at.")
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                reference,
                digest,
                version,
                method,
                method_ver,
                output_digest,
                release,
                cutover,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity from native owner evidence."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity from native owner evidence."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def receipt_reference(self) -> str:
        """Return the exact base-weight evidence receipt reference."""
        return self[2]

    @property
    def receipt_digest(self) -> str:
        """Return the immutable base-weight evidence receipt digest."""
        return self[3]

    @property
    def evidence_version(self) -> int:
        """Return the governed base-weight evidence version."""
        return self[4]

    @property
    def method_code(self) -> str:
        """Return the base-weight method code used by the final-weight chain."""
        return self[5]

    @property
    def method_version(self) -> int:
        """Return the base-weight method version."""
        return self[6]

    @property
    def output_weight_artifact_digest(self) -> str:
        """Return the resulting base-weight artifact digest."""
        return self[7]

    @property
    def released_at(self) -> datetime:
        """Return when this component became released authority."""
        return self[8]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive end of this component's authority interval."""
        return self[9]


class AdjustmentComponentEvidence(tuple):
    """Scope-bound specialized-adjustment projection normalized to final-weight semantics."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        evidence_kind: str,
        receipt_reference: str,
        receipt_digest: str,
        evidence_version: int,
        method_reference: str,
        method_version: int,
        input_weight_artifact_digest: str,
        output_weight_artifact_digest: str,
        configuration_digest: str,
        released_at: datetime,
        superseded_at: datetime | None = None,
    ) -> AdjustmentComponentEvidence:
        """Validate owner scope, exact receipt identity and transform semantics."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        kind = _require_code("evidence_kind", evidence_kind)
        namespace = _EVIDENCE_REFERENCE_NAMESPACE_BY_KIND.get(kind)
        if namespace is None:
            raise ValueError("evidence_kind must identify a governed specialized receipt.")
        reference = _require_reference("receipt_reference", receipt_reference, namespace)
        digest = _require_digest("receipt_digest", receipt_digest)
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1 for specialized evidence.")
        method = _require_reference("method_reference", method_reference, "weight_method")
        method_ver = _require_positive_integer("method_version", method_version)
        input_digest = _require_digest(
            "input_weight_artifact_digest", input_weight_artifact_digest
        )
        output_digest = _require_digest(
            "output_weight_artifact_digest", output_weight_artifact_digest
        )
        if input_digest == output_digest:
            raise ValueError(
                "output_weight_artifact_digest must identify the transformed weight artifact."
            )
        configuration = _require_digest("configuration_digest", configuration_digest)
        release = _require_aware_datetime("released_at", released_at)
        cutover = None
        if superseded_at is not None:
            cutover = _require_aware_datetime("superseded_at", superseded_at)
            if cutover <= release:
                raise ValueError("superseded_at must be later than released_at.")
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                kind,
                reference,
                digest,
                version,
                method,
                method_ver,
                input_digest,
                output_digest,
                configuration,
                release,
                cutover,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity from native owner evidence."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity from native owner evidence."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def evidence_kind(self) -> str:
        """Return the governed specialized receipt family."""
        return self[2]

    @property
    def receipt_reference(self) -> str:
        """Return the exact specialized receipt reference."""
        return self[3]

    @property
    def receipt_digest(self) -> str:
        """Return the immutable specialized receipt digest."""
        return self[4]

    @property
    def evidence_version(self) -> int:
        """Return the governed specialized evidence version."""
        return self[5]

    @property
    def method_reference(self) -> str:
        """Return the released weight-method semantic used by the final chain."""
        return self[6]

    @property
    def method_version(self) -> int:
        """Return the released weight-method version."""
        return self[7]

    @property
    def input_weight_artifact_digest(self) -> str:
        """Return the transform input artifact digest."""
        return self[8]

    @property
    def output_weight_artifact_digest(self) -> str:
        """Return the transform output artifact digest."""
        return self[9]

    @property
    def configuration_digest(self) -> str:
        """Return the immutable transform configuration digest."""
        return self[10]

    @property
    def released_at(self) -> datetime:
        """Return when this specialized component became released authority."""
        return self[11]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive end of this component's authority interval."""
        return self[12]


class FinalWeightComponentEvidenceResolution(tuple):
    """Canonical exact component evidence corroborated against one final-weight receipt."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        base_weight: BaseWeightComponentEvidence,
        adjustments: tuple[AdjustmentComponentEvidence, ...],
    ) -> FinalWeightComponentEvidenceResolution:
        """Detach already-corroborated component projections."""
        if type(base_weight) is not BaseWeightComponentEvidence:
            raise TypeError("base_weight must be an exact BaseWeightComponentEvidence.")
        canonical_base = BaseWeightComponentEvidence(
            tenant_record_id=base_weight.tenant_record_id,
            validity_study_id=base_weight.validity_study_id,
            receipt_reference=base_weight.receipt_reference,
            receipt_digest=base_weight.receipt_digest,
            evidence_version=base_weight.evidence_version,
            method_code=base_weight.method_code,
            method_version=base_weight.method_version,
            output_weight_artifact_digest=base_weight.output_weight_artifact_digest,
            released_at=base_weight.released_at,
            superseded_at=base_weight.superseded_at,
        )
        if canonical_base != base_weight:
            raise ValueError("base_weight must be canonical component evidence.")
        if type(adjustments) is not tuple:
            raise TypeError("adjustments must be an immutable tuple.")
        canonical_adjustments: list[AdjustmentComponentEvidence] = []
        for adjustment in adjustments:
            canonical_adjustments.append(_canonical_adjustment_evidence(adjustment))
        return tuple.__new__(cls, (canonical_base, tuple(canonical_adjustments)))

    @property
    def base_weight(self) -> BaseWeightComponentEvidence:
        """Return the exact corroborated base-weight component."""
        return self[0]

    @property
    def adjustments(self) -> tuple[AdjustmentComponentEvidence, ...]:
        """Return specialized components in final-weight sequence order."""
        return self[1]


@runtime_checkable
class FinalWeightComponentEvidenceReadPort(Protocol):
    """Deterministic scope-bound receipt-identity resolver for component evidence."""

    def read_base_weight_component_evidence(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        receipt_reference: str,
        receipt_digest: str,
        evidence_version: int,
    ) -> BaseWeightComponentEvidence | None:
        """Resolve one canonical scope-bound base-weight projection by receipt identity."""
        ...

    def read_adjustment_component_evidence(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        evidence_kind: str,
        receipt_reference: str,
        receipt_digest: str,
        evidence_version: int,
    ) -> AdjustmentComponentEvidence | None:
        """Resolve one canonical scope-bound specialized projection by receipt identity."""
        ...


_BASE_READ_CAPABILITY = getattr_static(
    FinalWeightComponentEvidenceReadPort, "read_base_weight_component_evidence"
)
_ADJUSTMENT_READ_CAPABILITY = getattr_static(
    FinalWeightComponentEvidenceReadPort, "read_adjustment_component_evidence"
)


def _canonical_adjustment_evidence(value: object) -> AdjustmentComponentEvidence:
    """Reconstruct specialized projection so exact runtime type cannot hide structure."""
    if type(value) is not AdjustmentComponentEvidence:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component port returned non-canonical specialized evidence"
        )
    try:
        canonical = AdjustmentComponentEvidence(
            tenant_record_id=value.tenant_record_id,
            validity_study_id=value.validity_study_id,
            evidence_kind=value.evidence_kind,
            receipt_reference=value.receipt_reference,
            receipt_digest=value.receipt_digest,
            evidence_version=value.evidence_version,
            method_reference=value.method_reference,
            method_version=value.method_version,
            input_weight_artifact_digest=value.input_weight_artifact_digest,
            output_weight_artifact_digest=value.output_weight_artifact_digest,
            configuration_digest=value.configuration_digest,
            released_at=value.released_at,
            superseded_at=value.superseded_at,
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component port returned malformed specialized evidence"
        ) from exc
    if canonical != value:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component port returned non-canonical specialized evidence"
        )
    return canonical


def _canonical_base_evidence(value: object) -> BaseWeightComponentEvidence:
    """Reconstruct base projection so exact runtime type cannot hide structure."""
    if type(value) is not BaseWeightComponentEvidence:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component port returned non-canonical base-weight evidence"
        )
    try:
        canonical = BaseWeightComponentEvidence(
            tenant_record_id=value.tenant_record_id,
            validity_study_id=value.validity_study_id,
            receipt_reference=value.receipt_reference,
            receipt_digest=value.receipt_digest,
            evidence_version=value.evidence_version,
            method_code=value.method_code,
            method_version=value.method_version,
            output_weight_artifact_digest=value.output_weight_artifact_digest,
            released_at=value.released_at,
            superseded_at=value.superseded_at,
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component port returned malformed base-weight evidence"
        ) from exc
    if canonical != value:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component port returned non-canonical base-weight evidence"
        )
    return canonical


def _canonical_final_weight(value: object) -> FinalAnalysisWeightAuthorityRecord:
    """Reconstruct final-weight authority before any cross-owner comparison."""
    if type(value) is not FinalAnalysisWeightAuthorityRecord:
        raise FinalWeightComponentEvidenceIntegrityError(
            "final_weight must be exact canonical final-weight authority evidence"
        )
    try:
        canonical = FinalAnalysisWeightAuthorityRecord(
            tenant_record_id=value.tenant_record_id,
            validity_study_id=value.validity_study_id,
            owner_contract_released_at=value.owner_contract_released_at,
            released_at=value.released_at,
            superseded_at=value.superseded_at,
            **dict(value.fields),
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise FinalWeightComponentEvidenceIntegrityError(
            "final_weight is malformed canonical authority evidence"
        ) from exc
    if canonical != value:
        raise FinalWeightComponentEvidenceIntegrityError(
            "final_weight contains non-canonical hidden or malformed structure"
        )
    return canonical


def _canonical_binding(value: object) -> FinalWeightComponentBindingAuthorityRecord:
    """Reconstruct component binding before any locator is trusted."""
    if type(value) is not FinalWeightComponentBindingAuthorityRecord:
        raise FinalWeightComponentEvidenceIntegrityError(
            "binding must be exact canonical final-weight component binding evidence"
        )
    try:
        canonical = FinalWeightComponentBindingAuthorityRecord(
            tenant_record_id=value.tenant_record_id,
            validity_study_id=value.validity_study_id,
            owner_contract_released_at=value.owner_contract_released_at,
            released_at=value.released_at,
            superseded_at=value.superseded_at,
            **dict(value.fields),
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise FinalWeightComponentEvidenceIntegrityError(
            "binding is malformed canonical authority evidence"
        ) from exc
    if canonical != value:
        raise FinalWeightComponentEvidenceIntegrityError(
            "binding contains non-canonical hidden or malformed structure"
        )
    return canonical


def _require_component_scope(
    *,
    component_tenant_record_id: UUID,
    component_validity_study_id: UUID,
    tenant_record_id: UUID,
    validity_study_id: UUID,
) -> None:
    """Require normalized component evidence to prove the same owner scope as the final weight."""
    if (
        _store_operational_uuid("component tenant_record_id", component_tenant_record_id)
        != _store_operational_uuid("final tenant_record_id", tenant_record_id)
        or _store_operational_uuid(
            "component validity_study_id", component_validity_study_id
        )
        != _store_operational_uuid("final validity_study_id", validity_study_id)
    ):
        raise FinalWeightComponentEvidenceIntegrityError(
            "component evidence belongs to another tenant or validity study"
        )


def _require_component_valid_at_construction(
    *, released_at: datetime, superseded_at: datetime | None, constructed_at: datetime
) -> None:
    """Require component evidence to be released and current when the final weight was built."""
    if released_at > constructed_at:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component evidence was not released by final-weight construction"
        )
    if superseded_at is not None and constructed_at >= superseded_at:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component evidence was superseded before final-weight construction"
        )


def _require_component_current_at_use(
    *, superseded_at: datetime | None, used_at: datetime
) -> None:
    """Require component authority to remain current at the governed scientific-use instant."""
    if superseded_at is not None and used_at >= superseded_at:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component evidence is not current at the governed use instant"
        )


def corroborate_final_weight_component_evidence(
    *,
    final_weight: FinalAnalysisWeightAuthorityRecord,
    binding: FinalWeightComponentBindingAuthorityRecord,
    used_at: datetime,
    read_port: FinalWeightComponentEvidenceReadPort,
) -> FinalWeightComponentEvidenceResolution:
    """Resolve exact component receipts and prove scope and semantics match the final weight."""
    base_capability = getattr_static(type(read_port), "read_base_weight_component_evidence", None)
    adjustment_capability = getattr_static(
        type(read_port), "read_adjustment_component_evidence", None
    )
    if type(base_capability) is not FunctionType or base_capability is _BASE_READ_CAPABILITY:
        raise TypeError("read_port must expose read_base_weight_component_evidence.")
    if (
        type(adjustment_capability) is not FunctionType
        or adjustment_capability is _ADJUSTMENT_READ_CAPABILITY
    ):
        raise TypeError("read_port must expose read_adjustment_component_evidence.")

    final_record = _canonical_final_weight(final_weight)
    binding_record = _canonical_binding(binding)
    use_instant = _require_aware_datetime("used_at", used_at)
    final_values = dict(final_record.fields)
    binding_values = dict(binding_record.fields)

    if (
        _store_operational_uuid("final tenant_record_id", final_record.tenant_record_id)
        != _store_operational_uuid("binding tenant_record_id", binding_record.tenant_record_id)
        or _store_operational_uuid("final validity_study_id", final_record.validity_study_id)
        != _store_operational_uuid("binding validity_study_id", binding_record.validity_study_id)
        or final_values["analysis_weight_receipt_reference"]
        != binding_values["analysis_weight_receipt_reference"]
        or final_values["analysis_weight_receipt_digest"]
        != binding_values["analysis_weight_receipt_digest"]
        or final_values["evidence_version"]
        != binding_values["analysis_weight_evidence_version"]
    ):
        raise FinalWeightComponentEvidenceIntegrityError(
            "component binding targets a different final-weight receipt"
        )
    if binding_record.released_at < final_record.released_at:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component binding cannot be released before final-weight authority"
        )
    if use_instant < final_record.released_at or use_instant < binding_record.released_at:
        raise FinalWeightComponentEvidenceIntegrityError(
            "final-weight evidence and component binding must be released before use"
        )
    if final_record.superseded_at is not None and use_instant >= final_record.superseded_at:
        raise FinalWeightComponentEvidenceIntegrityError(
            "final-weight evidence is not current at the governed use instant"
        )
    if binding_record.superseded_at is not None and use_instant >= binding_record.superseded_at:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component binding is not current at the governed use instant"
        )

    tenant_id = _restore_operational_uuid(
        "tenant_record_id", _store_operational_uuid("tenant_record_id", final_record.tenant_record_id)
    )
    study_id = _restore_operational_uuid(
        "validity_study_id", _store_operational_uuid("validity_study_id", final_record.validity_study_id)
    )
    base_value = base_capability(
        read_port,
        tenant_record_id=tenant_id,
        validity_study_id=study_id,
        receipt_reference=binding_values["base_weight_evidence_receipt_reference"],
        receipt_digest=binding_values["base_weight_evidence_receipt_digest"],
        evidence_version=binding_values["base_weight_evidence_version"],
    )
    if base_value is None:
        raise FinalWeightComponentEvidenceNotFound(
            str(binding_values["base_weight_evidence_receipt_reference"])
        )
    base = _canonical_base_evidence(base_value)
    _require_component_scope(
        component_tenant_record_id=base.tenant_record_id,
        component_validity_study_id=base.validity_study_id,
        tenant_record_id=tenant_id,
        validity_study_id=study_id,
    )
    if (
        base.receipt_reference != binding_values["base_weight_evidence_receipt_reference"]
        or base.receipt_digest != binding_values["base_weight_evidence_receipt_digest"]
        or base.evidence_version != binding_values["base_weight_evidence_version"]
        or base.receipt_digest != final_values["base_weight_evidence_digest"]
        or base.method_code != final_values["base_weight_method_code"]
        or base.method_version != final_values["base_weight_method_version"]
        or base.output_weight_artifact_digest != final_values["base_weight_artifact_digest"]
    ):
        raise FinalWeightComponentEvidenceIntegrityError(
            "base-weight component semantics disagree with the final-weight receipt"
        )
    constructed_at = final_values["constructed_at"]
    _require_component_valid_at_construction(
        released_at=base.released_at,
        superseded_at=base.superseded_at,
        constructed_at=constructed_at,
    )
    _require_component_current_at_use(
        superseded_at=base.superseded_at,
        used_at=use_instant,
    )

    adjustments = final_values["adjustments"]
    if type(adjustments) is not tuple:
        raise FinalWeightComponentEvidenceIntegrityError(
            "final-weight adjustments are not canonical immutable coordinates"
        )
    adjustment_bindings = binding_values["adjustment_bindings"]
    if type(adjustment_bindings) is not tuple:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component adjustment bindings are not canonical immutable coordinates"
        )
    binding_by_sequence = {item.sequence_number: item for item in adjustment_bindings}
    specialized_sequences = {
        item.sequence_number
        for item in adjustments
        if item.evidence_kind in _EVIDENCE_REFERENCE_NAMESPACE_BY_KIND
    }
    if set(binding_by_sequence) != specialized_sequences:
        raise FinalWeightComponentEvidenceIntegrityError(
            "component binding must cover every and only specialized final-weight adjustment"
        )

    resolved_adjustments: list[AdjustmentComponentEvidence] = []
    for adjustment in adjustments:
        if type(adjustment) is not FinalWeightAdjustmentCoordinate:
            raise FinalWeightComponentEvidenceIntegrityError(
                "final-weight adjustment coordinates must remain canonical"
            )
        if adjustment.sequence_number not in specialized_sequences:
            continue
        locator = binding_by_sequence[adjustment.sequence_number]
        if (
            locator.evidence_kind != adjustment.evidence_kind
            or locator.evidence_receipt_digest != adjustment.evidence_receipt_digest
        ):
            raise FinalWeightComponentEvidenceIntegrityError(
                "component binding digest or evidence kind disagrees with final-weight adjustment"
            )
        component_value = adjustment_capability(
            read_port,
            tenant_record_id=tenant_id,
            validity_study_id=study_id,
            evidence_kind=locator.evidence_kind,
            receipt_reference=locator.evidence_receipt_reference,
            receipt_digest=locator.evidence_receipt_digest,
            evidence_version=locator.evidence_version,
        )
        if component_value is None:
            raise FinalWeightComponentEvidenceNotFound(locator.evidence_receipt_reference)
        component = _canonical_adjustment_evidence(component_value)
        _require_component_scope(
            component_tenant_record_id=component.tenant_record_id,
            component_validity_study_id=component.validity_study_id,
            tenant_record_id=tenant_id,
            validity_study_id=study_id,
        )
        if (
            component.evidence_kind != locator.evidence_kind
            or component.receipt_reference != locator.evidence_receipt_reference
            or component.receipt_digest != locator.evidence_receipt_digest
            or component.evidence_version != locator.evidence_version
        ):
            raise FinalWeightComponentEvidenceIntegrityError(
                "resolved component identity disagrees with the exact binding locator"
            )
        if (
            component.method_reference != adjustment.method_reference
            or component.method_version != adjustment.method_version
            or component.input_weight_artifact_digest != adjustment.input_weight_artifact_digest
            or component.output_weight_artifact_digest != adjustment.output_weight_artifact_digest
            or component.configuration_digest != adjustment.configuration_digest
        ):
            raise FinalWeightComponentEvidenceIntegrityError(
                "resolved adjustment semantics disagree with the final-weight adjustment"
            )
        _require_component_valid_at_construction(
            released_at=component.released_at,
            superseded_at=component.superseded_at,
            constructed_at=constructed_at,
        )
        _require_component_current_at_use(
            superseded_at=component.superseded_at,
            used_at=use_instant,
        )
        resolved_adjustments.append(component)

    return FinalWeightComponentEvidenceResolution(
        base_weight=base,
        adjustments=tuple(resolved_adjustments),
    )