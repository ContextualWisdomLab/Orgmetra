"""Corroborate append-only point-weight/variance compatibility corrections.

The ordinary compatibility projection proves which released sampling, point-weight,
and variance-design coordinates were used together. This boundary proves the
half-open authority interval for that immutable compatibility identity and, when
corrected, the exact released successor identity that ends the interval.
Successor chronology is owner-resolved rather than caller-selected.
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

_RESOURCE_KIND = "weight_variance_supersession_authority"
_OPERATION = "read"
_READ_FIELDS = frozenset(
    {
        "authority_reference",
        "evidence_version",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "released_at",
        "superseded_at",
        "successor_authority_reference",
        "successor_evidence_version",
        "successor_released_at",
    }
)


class WeightVarianceSupersessionAuthorityNotFound(LookupError):
    """Indicate that no released owner evidence corroborates the compatibility authority."""


class WeightVarianceSupersessionAuthorityIntegrityError(RuntimeError):
    """Indicate that released compatibility correction evidence cannot authorize use."""


class WeightVarianceSupersessionAuthorityRecord(tuple):
    """Immutable owner projection for one compatibility-authority interval."""

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        authority_reference: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        released_at: datetime,
        superseded_at: datetime | None = None,
        successor_authority_reference: str | None = None,
        successor_evidence_version: int | None = None,
        successor_released_at: datetime | None = None,
    ) -> WeightVarianceSupersessionAuthorityRecord:
        """Validate one released predecessor and its optional atomic successor edge."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        authority_ref = _require_reference(
            "authority_reference", authority_reference, "variance_compatibility_authority"
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
                "owner contract must be released no later than compatibility authority release."
            )

        successor_values = (
            superseded_at,
            successor_authority_reference,
            successor_evidence_version,
            successor_released_at,
        )
        if all(value is None for value in successor_values):
            cutover = None
            successor_ref = None
            successor_version = None
            successor_release = None
        elif any(value is None for value in successor_values):
            raise ValueError(
                "weight/variance supersession requires cutover and complete released successor coordinates."
            )
        else:
            cutover = _require_aware_datetime("superseded_at", superseded_at)
            successor_ref = _require_reference(
                "successor_authority_reference",
                successor_authority_reference,
                "variance_compatibility_authority",
            )
            successor_version = _require_positive_integer(
                "successor_evidence_version", successor_evidence_version
            )
            successor_release = _require_aware_datetime(
                "successor_released_at", successor_released_at
            )
            if cutover <= release_instant:
                raise ValueError(
                    "superseded_at must be later than compatibility authority release."
                )
            if successor_ref == authority_ref:
                raise ValueError("successor compatibility authority must have a new reference.")
            if successor_version != 1:
                raise ValueError("successor_evidence_version must remain 1.")
            if successor_release <= release_instant:
                raise ValueError(
                    "successor compatibility authority must be released after its predecessor."
                )
            if successor_release != cutover:
                raise ValueError(
                    "successor compatibility authority must be released exactly at supersession."
                )

        current_fields: tuple[tuple[str, object], ...] = (
            ("authority_reference", authority_ref),
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
                ("successor_authority_reference", successor_ref),
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
        """Return immutable current-authority coordinates."""
        return self[2]

    @property
    def released_at(self) -> datetime:
        """Return when this compatibility authority became released."""
        return self[3]

    @property
    def superseded_at(self) -> datetime | None:
        """Return the exclusive end of this authority interval."""
        return self[4]

    @property
    def successor_fields(self) -> tuple[tuple[str, object], ...] | None:
        """Return internal released successor coordinates, if any."""
        return self[5]


class WeightVarianceSupersessionAuthorityView:
    """Sealed current compatibility authority issued only after authorization."""

    __slots__ = ("_tenant_identity", "_study_identity", "_fields", "_issuance_marker")

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> WeightVarianceSupersessionAuthorityView:
        """Reject public construction; only the resolver may issue this view."""
        raise TypeError(
            "WeightVarianceSupersessionAuthorityView is issued only by "
            "resolve_weight_variance_supersession_authority."
        )

    def __setattr__(self, name: str, value: object) -> None:
        """Keep ordinary callers from mutating issued projection state."""
        raise AttributeError("WeightVarianceSupersessionAuthorityView is immutable.")

    def __delattr__(self, name: str) -> None:
        """Keep ordinary callers from deleting issued projection state."""
        raise AttributeError("WeightVarianceSupersessionAuthorityView is immutable.")

    def _require_issued(self) -> None:
        """Reject exact-runtime allocations not sealed by the resolver."""
        _require_weight_variance_supersession_view_issued(self)

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
        """Return current authority without successor disclosure."""
        self._require_issued()
        return object.__getattribute__(self, "_fields")


@runtime_checkable
class WeightVarianceSupersessionAuthorityReadPort(Protocol):
    """Owner read contract for one released compatibility correction state."""

    def read_weight_variance_supersession_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        authority_reference: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
    ) -> WeightVarianceSupersessionAuthorityRecord | None:
        """Return matching released compatibility supersession evidence or ``None``."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    WeightVarianceSupersessionAuthorityReadPort,
    "read_weight_variance_supersession_authority",
)


def _resolve_weight_variance_supersession_authority_state(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    authority_reference: str,
    evidence_version: int,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: WeightVarianceSupersessionAuthorityReadPort,
) -> tuple[int, int, tuple[tuple[str, object], ...]]:
    """Authorize and resolve compatibility supersession into inert view state."""
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_weight_variance_supersession_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable read_weight_variance_supersession_authority."
        )

    tenant_id = _restore_operational_uuid(
        "tenant_record_id", _store_operational_uuid("tenant_record_id", tenant_record_id)
    )
    study_id = _restore_operational_uuid(
        "validity_study_id", _store_operational_uuid("validity_study_id", validity_study_id)
    )
    authority_ref = _require_reference(
        "authority_reference", authority_reference, "variance_compatibility_authority"
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
        authority_reference=authority_ref,
        evidence_version=version,
        owner_contract_reference=owner_ref,
        owner_contract_version=owner_version,
        owner_contract_digest=owner_digest,
    )
    if persisted is None:
        raise WeightVarianceSupersessionAuthorityNotFound(str(study_id))
    if type(persisted) is not WeightVarianceSupersessionAuthorityRecord:
        raise WeightVarianceSupersessionAuthorityIntegrityError(
            "owner port returned non-canonical weight/variance supersession evidence"
        )

    try:
        successor_values = (
            None if persisted.successor_fields is None else dict(persisted.successor_fields)
        )
        record = WeightVarianceSupersessionAuthorityRecord(
            tenant_record_id=persisted.tenant_record_id,
            validity_study_id=persisted.validity_study_id,
            released_at=persisted.released_at,
            superseded_at=persisted.superseded_at,
            successor_authority_reference=(
                None
                if successor_values is None
                else successor_values["successor_authority_reference"]
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
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise WeightVarianceSupersessionAuthorityIntegrityError(
            "owner port returned structurally invalid weight/variance supersession evidence"
        ) from exc
    if record != persisted:
        raise WeightVarianceSupersessionAuthorityIntegrityError(
            "owner port returned non-canonical weight/variance supersession structure"
        )

    record_values = dict(record.fields)
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != _store_operational_uuid("requested tenant_record_id", tenant_id)
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != _store_operational_uuid("requested validity_study_id", study_id)
        or record_values["authority_reference"] != authority_ref
        or record_values["evidence_version"] != version
        or record_values["owner_contract_reference"] != owner_ref
        or record_values["owner_contract_version"] != owner_version
        or record_values["owner_contract_digest"] != owner_digest
    ):
        raise WeightVarianceSupersessionAuthorityIntegrityError(
            "released weight/variance supersession authority does not match requested coordinates"
        )
    if use_instant < record.released_at:
        raise WeightVarianceSupersessionAuthorityIntegrityError(
            "compatibility authority must be released before scientific use"
        )
    if record.superseded_at is not None and use_instant >= record.superseded_at:
        raise WeightVarianceSupersessionAuthorityIntegrityError(
            "compatibility authority is superseded for this scientific-use instant"
        )

    fields = record.fields + (
        ("released_at", record.released_at),
        ("superseded_at", record.superseded_at),
    )
    return (
        _store_operational_uuid("tenant_record_id", record.tenant_record_id),
        _store_operational_uuid("validity_study_id", record.validity_study_id),
        fields,
    )


def _build_weight_variance_supersession_view_runtime():
    """Create closure-private sealing state and the authorized public resolver."""
    issuance_marker = object()

    def require_issued(view: WeightVarianceSupersessionAuthorityView) -> None:
        """Verify one supersession view against the closure-private capability."""
        try:
            marker = object.__getattribute__(view, "_issuance_marker")
        except AttributeError as exc:
            raise WeightVarianceSupersessionAuthorityIntegrityError(
                "weight/variance supersession view was not issued by "
                "resolve_weight_variance_supersession_authority"
            ) from exc
        if marker is not issuance_marker:
            raise WeightVarianceSupersessionAuthorityIntegrityError(
                "weight/variance supersession view was not issued by "
                "resolve_weight_variance_supersession_authority"
            )

    def resolve(
        *,
        principal: ValidationPrincipal,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        authority_reference: str,
        evidence_version: int,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        used_at: datetime,
        purpose_code: str,
        policy: PurposeBoundAccessPolicy,
        read_port: WeightVarianceSupersessionAuthorityReadPort,
    ) -> WeightVarianceSupersessionAuthorityView:
        """Authorize then resolve the compatibility authority's append-only interval."""
        tenant_identity, study_identity, fields = (
            _resolve_weight_variance_supersession_authority_state(
                principal=principal,
                tenant_record_id=tenant_record_id,
                validity_study_id=validity_study_id,
                authority_reference=authority_reference,
                evidence_version=evidence_version,
                owner_contract_reference=owner_contract_reference,
                owner_contract_version=owner_contract_version,
                owner_contract_digest=owner_contract_digest,
                used_at=used_at,
                purpose_code=purpose_code,
                policy=policy,
                read_port=read_port,
            )
        )
        view = object.__new__(WeightVarianceSupersessionAuthorityView)
        object.__setattr__(view, "_tenant_identity", tenant_identity)
        object.__setattr__(view, "_study_identity", study_identity)
        object.__setattr__(view, "_fields", fields)
        object.__setattr__(view, "_issuance_marker", issuance_marker)
        return view

    return require_issued, resolve


(
    _require_weight_variance_supersession_view_issued,
    resolve_weight_variance_supersession_authority,
) = _build_weight_variance_supersession_view_runtime()
del _build_weight_variance_supersession_view_runtime


__all__ = [
    "WeightVarianceSupersessionAuthorityIntegrityError",
    "WeightVarianceSupersessionAuthorityNotFound",
    "WeightVarianceSupersessionAuthorityReadPort",
    "WeightVarianceSupersessionAuthorityRecord",
    "WeightVarianceSupersessionAuthorityView",
    "resolve_weight_variance_supersession_authority",
]
