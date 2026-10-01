"""Corroborate released trimming or bounding weight-adjustment evidence.

This application boundary binds an exact governed trimming rule to the affected
case set and weight-artifact transition without copying case identities or
row-level weights.
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

_RESOURCE_KIND = "trimming_bounding_authority"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "adjustment_receipt_reference",
        "adjustment_receipt_digest",
        "evidence_version",
        "rule_reference",
        "rule_version",
        "rule_configuration_digest",
        "affected_case_occurrence_set_digest",
        "affected_case_count",
        "input_weight_artifact_digest",
        "output_weight_artifact_digest",
        "constructed_at",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
    }
)


class TrimmingBoundingAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the adjustment receipt."""


class TrimmingBoundingAuthorityIntegrityError(RuntimeError):
    """Indicate that owner evidence cannot corroborate the requested adjustment."""


class TrimmingBoundingAuthorityRecord(tuple):
    """Immutable owner projection for one released trimming/bounding adjustment."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        adjustment_receipt_reference: str,
        adjustment_receipt_digest: str,
        evidence_version: int,
        rule_reference: str,
        rule_version: int,
        rule_configuration_digest: str,
        affected_case_occurrence_set_digest: str,
        affected_case_count: int,
        input_weight_artifact_digest: str,
        output_weight_artifact_digest: str,
        constructed_at: datetime,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
        superseded_at: datetime | None = None,
    ) -> TrimmingBoundingAuthorityRecord:
        """Validate and detach the minimum immutable trimming authority."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        receipt_ref = _require_reference(
            "adjustment_receipt_reference",
            adjustment_receipt_reference,
            "trimming_bounding_adjustment_receipt",
        )
        receipt_digest = _require_digest(
            "adjustment_receipt_digest", adjustment_receipt_digest
        )
        version = _require_positive_integer("evidence_version", evidence_version)
        if version != 1:
            raise ValueError("evidence_version must remain 1.")
        rule_ref = _require_reference(
            "rule_reference", rule_reference, "weight_trimming_rule"
        )
        rule_ver = _require_positive_integer("rule_version", rule_version)
        configuration = _require_digest(
            "rule_configuration_digest", rule_configuration_digest
        )
        affected_digest = _require_digest(
            "affected_case_occurrence_set_digest",
            affected_case_occurrence_set_digest,
        )
        affected_count = _require_positive_integer(
            "affected_case_count", affected_case_count
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
        supersession_instant = (
            None
            if superseded_at is None
            else _require_aware_datetime("superseded_at", superseded_at)
        )
        if release_instant < constructed:
            raise ValueError("released_at cannot precede constructed_at.")
        if owner_released > release_instant:
            raise ValueError(
                "owner_contract_released_at cannot be later than released_at."
            )
        if supersession_instant is not None and supersession_instant <= release_instant:
            raise ValueError("superseded_at must be later than released_at.")
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                receipt_ref,
                receipt_digest,
                version,
                rule_ref,
                rule_ver,
                configuration,
                affected_digest,
                affected_count,
                input_digest,
                output_digest,
                constructed,
                owner_ref,
                owner_version,
                owner_digest,
                owner_released,
                release_instant,
                supersession_instant,
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
    def adjustment_receipt_reference(self) -> str:
        """Return the typed trimming/bounding receipt reference."""
        return self[2]

    @property
    def adjustment_receipt_digest(self) -> str:
        """Return the exact trimming/bounding receipt digest."""
        return self[3]

    @property
    def evidence_version(self) -> int:
        """Return the evidence version."""
        return self[4]

    @property
    def rule_reference(self) -> str:
        """Return the governed trimming-rule reference."""
        return self[5]

    @property
    def rule_version(self) -> int:
        """Return the governed trimming-rule version."""
        return self[6]

    @property
    def rule_configuration_digest(self) -> str:
        """Return the immutable trimming-rule configuration digest."""
        return self[7]

    @property
    def affected_case_occurrence_set_digest(self) -> str:
        """Return the exact affected-case occurrence-set digest."""
        return self[8]

    @property
    def affected_case_count(self) -> int:
        """Return the positive number of affected case occurrences."""
        return self[9]

    @property
    def input_weight_artifact_digest(self) -> str:
        """Return the input weight artifact digest."""
        return self[10]

    @property
    def output_weight_artifact_digest(self) -> str:
        """Return the adjusted output weight artifact digest."""
        return self[11]

    @property
    def constructed_at(self) -> datetime:
        """Return when the typed adjustment receipt was constructed."""
        return self[12]

    @property
    def owner_contract_reference(self) -> str:
        """Return the released owner-contract reference."""
        return self[13]

    @property
    def owner_contract_version(self) -> int:
        """Return the released owner-contract version."""
        return self[14]

    @property
    def owner_contract_digest(self) -> str:
        """Return the released owner-contract digest."""
        return self[15]

    @property
    def owner_contract_released_at(self) -> datetime:
        """Return when the governing owner contract became released authority."""
        return self[16]

    @property
    def released_at(self) -> datetime:
        """Return when this adjustment became released authority."""
        return self[17]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive owner-resolved cutover for this receipt."""
        return self[18]


class TrimmingBoundingAuthorityView:
    """Field-minimized adjustment evidence issued only after authorization."""

    __slots__ = ("_tenant_identity", "_study_identity", "_fields", "_issuance_marker")

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> TrimmingBoundingAuthorityView:
        """Reject direct construction; only the resolver may issue this view."""
        raise TypeError(
            "TrimmingBoundingAuthorityView is issued only by "
            "resolve_trimming_bounding_authority."
        )

    def __setattr__(self, name: str, value: object) -> None:
        """Reject mutation after resolver-controlled issuance."""
        raise AttributeError("TrimmingBoundingAuthorityView is immutable.")

    def __delattr__(self, name: str) -> None:
        """Reject deletion after resolver-controlled issuance."""
        raise AttributeError("TrimmingBoundingAuthorityView is immutable.")

    def _require_issued(self) -> None:
        """Require the exact in-process marker written by the resolver."""
        _require_trimming_bounding_view_issued(self)

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
        """Return immutable adjustment provenance without case identities."""
        self._require_issued()
        return object.__getattribute__(self, "_fields")


@runtime_checkable
class TrimmingBoundingAuthorityReadPort(Protocol):
    """Owner read contract for released trimming/bounding adjustment evidence."""

    def read_trimming_bounding_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        adjustment_receipt_reference: str,
        adjustment_receipt_digest: str,
        evidence_version: int,
        rule_reference: str,
        rule_version: int,
        rule_configuration_digest: str,
        affected_case_occurrence_set_digest: str,
        affected_case_count: int,
        input_weight_artifact_digest: str,
        output_weight_artifact_digest: str,
        constructed_at: datetime,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> TrimmingBoundingAuthorityRecord | None:
        """Return matching released adjustment evidence or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    TrimmingBoundingAuthorityReadPort, "read_trimming_bounding_authority"
)


def _coordinate_tuple(record: TrimmingBoundingAuthorityRecord) -> tuple[object, ...]:
    """Return caller-known coordinates, excluding owner-resolved release instants."""
    return record[:16]


def _resolve_trimming_bounding_authority_state(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    adjustment_receipt_reference: str,
    adjustment_receipt_digest: str,
    evidence_version: int,
    rule_reference: str,
    rule_version: int,
    rule_configuration_digest: str,
    affected_case_occurrence_set_digest: str,
    affected_case_count: int,
    input_weight_artifact_digest: str,
    output_weight_artifact_digest: str,
    constructed_at: datetime,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: TrimmingBoundingAuthorityReadPort,
) -> tuple[int, int, tuple[tuple[str, object], ...]]:
    """Authorize and corroborate exact released trimming/bounding evidence."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(type(read_port), "read_trimming_bounding_authority", None)
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable read_trimming_bounding_authority."
        )

    requested = TrimmingBoundingAuthorityRecord(
        tenant_record_id=tenant_record_id,
        validity_study_id=validity_study_id,
        adjustment_receipt_reference=adjustment_receipt_reference,
        adjustment_receipt_digest=adjustment_receipt_digest,
        evidence_version=evidence_version,
        rule_reference=rule_reference,
        rule_version=rule_version,
        rule_configuration_digest=rule_configuration_digest,
        affected_case_occurrence_set_digest=affected_case_occurrence_set_digest,
        affected_case_count=affected_case_count,
        input_weight_artifact_digest=input_weight_artifact_digest,
        output_weight_artifact_digest=output_weight_artifact_digest,
        constructed_at=constructed_at,
        owner_contract_reference=owner_contract_reference,
        owner_contract_version=owner_contract_version,
        owner_contract_digest=owner_contract_digest,
        owner_contract_released_at=constructed_at,
        released_at=constructed_at,
        superseded_at=None,
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
        adjustment_receipt_reference=requested.adjustment_receipt_reference,
        adjustment_receipt_digest=requested.adjustment_receipt_digest,
        evidence_version=requested.evidence_version,
        rule_reference=requested.rule_reference,
        rule_version=requested.rule_version,
        rule_configuration_digest=requested.rule_configuration_digest,
        affected_case_occurrence_set_digest=requested.affected_case_occurrence_set_digest,
        affected_case_count=requested.affected_case_count,
        input_weight_artifact_digest=requested.input_weight_artifact_digest,
        output_weight_artifact_digest=requested.output_weight_artifact_digest,
        constructed_at=requested.constructed_at,
        owner_contract_reference=requested.owner_contract_reference,
        owner_contract_version=requested.owner_contract_version,
        owner_contract_digest=requested.owner_contract_digest,
    )
    if persisted is None:
        raise TrimmingBoundingAuthorityNotFound(str(study_id))
    if type(persisted) is not TrimmingBoundingAuthorityRecord:
        raise TrimmingBoundingAuthorityIntegrityError(
            "owner port returned non-canonical trimming/bounding authority evidence"
        )

    try:
        record = TrimmingBoundingAuthorityRecord(
            tenant_record_id=persisted.tenant_record_id,
            validity_study_id=persisted.validity_study_id,
            adjustment_receipt_reference=persisted.adjustment_receipt_reference,
            adjustment_receipt_digest=persisted.adjustment_receipt_digest,
            evidence_version=persisted.evidence_version,
            rule_reference=persisted.rule_reference,
            rule_version=persisted.rule_version,
            rule_configuration_digest=persisted.rule_configuration_digest,
            affected_case_occurrence_set_digest=persisted.affected_case_occurrence_set_digest,
            affected_case_count=persisted.affected_case_count,
            input_weight_artifact_digest=persisted.input_weight_artifact_digest,
            output_weight_artifact_digest=persisted.output_weight_artifact_digest,
            constructed_at=persisted.constructed_at,
            owner_contract_reference=persisted.owner_contract_reference,
            owner_contract_version=persisted.owner_contract_version,
            owner_contract_digest=persisted.owner_contract_digest,
            owner_contract_released_at=persisted.owner_contract_released_at,
            released_at=persisted.released_at,
            superseded_at=persisted.superseded_at,
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise TrimmingBoundingAuthorityIntegrityError(
            "owner port returned malformed trimming/bounding authority evidence"
        ) from exc
    if record != persisted:
        raise TrimmingBoundingAuthorityIntegrityError(
            "owner port returned non-canonical trimming/bounding authority evidence"
        )
    if _coordinate_tuple(record) != _coordinate_tuple(requested):
        raise TrimmingBoundingAuthorityIntegrityError(
            "released trimming/bounding authority does not match requested coordinates"
        )
    if record.released_at > use_instant:
        raise TrimmingBoundingAuthorityIntegrityError(
            "trimming/bounding evidence must be released before scientific use"
        )
    if record.superseded_at is not None and use_instant >= record.superseded_at:
        raise TrimmingBoundingAuthorityIntegrityError(
            "trimming/bounding evidence is superseded for this scientific-use instant"
        )

    fields: tuple[tuple[str, object], ...] = (
        ("adjustment_receipt_digest", record.adjustment_receipt_digest),
        ("adjustment_receipt_reference", record.adjustment_receipt_reference),
        ("affected_case_count", record.affected_case_count),
        ("affected_case_occurrence_set_digest", record.affected_case_occurrence_set_digest),
        ("constructed_at", record.constructed_at),
        ("evidence_version", record.evidence_version),
        ("input_weight_artifact_digest", record.input_weight_artifact_digest),
        ("output_weight_artifact_digest", record.output_weight_artifact_digest),
        ("owner_contract_digest", record.owner_contract_digest),
        ("owner_contract_reference", record.owner_contract_reference),
        ("owner_contract_released_at", record.owner_contract_released_at),
        ("owner_contract_version", record.owner_contract_version),
        ("released_at", record.released_at),
        ("rule_configuration_digest", record.rule_configuration_digest),
        ("rule_reference", record.rule_reference),
        ("rule_version", record.rule_version),
        ("superseded_at", record.superseded_at),
    )
    return (
        _store_operational_uuid("tenant_record_id", tenant_id),
        _store_operational_uuid("validity_study_id", study_id),
        fields,
    )


def _build_trimming_bounding_view_runtime():
    """Create closure-private sealing state and the authorized public resolver."""
    issuance_marker = object()

    def require_issued(view: TrimmingBoundingAuthorityView) -> None:
        """Verify one trimming/bounding view against the private capability."""
        try:
            marker = object.__getattribute__(view, "_issuance_marker")
        except AttributeError as exc:
            raise TrimmingBoundingAuthorityIntegrityError(
                "trimming/bounding authority view was not issued by the resolver"
            ) from exc
        if marker is not issuance_marker:
            raise TrimmingBoundingAuthorityIntegrityError(
                "trimming/bounding authority view has an invalid issuance marker"
            )

    def resolve(
        *,
        principal: ValidationPrincipal,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        adjustment_receipt_reference: str,
        adjustment_receipt_digest: str,
        evidence_version: int,
        rule_reference: str,
        rule_version: int,
        rule_configuration_digest: str,
        affected_case_occurrence_set_digest: str,
        affected_case_count: int,
        input_weight_artifact_digest: str,
        output_weight_artifact_digest: str,
        constructed_at: datetime,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        used_at: datetime,
        purpose_code: str,
        policy: PurposeBoundAccessPolicy,
        read_port: TrimmingBoundingAuthorityReadPort,
    ) -> TrimmingBoundingAuthorityView:
        """Authorize then issue exact released trimming/bounding evidence."""
        tenant_identity, study_identity, fields = (
            _resolve_trimming_bounding_authority_state(
                principal=principal,
                tenant_record_id=tenant_record_id,
                validity_study_id=validity_study_id,
                adjustment_receipt_reference=adjustment_receipt_reference,
                adjustment_receipt_digest=adjustment_receipt_digest,
                evidence_version=evidence_version,
                rule_reference=rule_reference,
                rule_version=rule_version,
                rule_configuration_digest=rule_configuration_digest,
                affected_case_occurrence_set_digest=affected_case_occurrence_set_digest,
                affected_case_count=affected_case_count,
                input_weight_artifact_digest=input_weight_artifact_digest,
                output_weight_artifact_digest=output_weight_artifact_digest,
                constructed_at=constructed_at,
                owner_contract_reference=owner_contract_reference,
                owner_contract_version=owner_contract_version,
                owner_contract_digest=owner_contract_digest,
                used_at=used_at,
                purpose_code=purpose_code,
                policy=policy,
                read_port=read_port,
            )
        )
        view = object.__new__(TrimmingBoundingAuthorityView)
        object.__setattr__(view, "_tenant_identity", tenant_identity)
        object.__setattr__(view, "_study_identity", study_identity)
        object.__setattr__(view, "_fields", fields)
        object.__setattr__(view, "_issuance_marker", issuance_marker)
        return view

    return require_issued, resolve


(
    _require_trimming_bounding_view_issued,
    resolve_trimming_bounding_authority,
) = _build_trimming_bounding_view_runtime()
del _build_trimming_bounding_view_runtime
