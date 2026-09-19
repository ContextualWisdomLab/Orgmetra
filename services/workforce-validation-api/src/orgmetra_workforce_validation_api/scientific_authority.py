"""Resolve purpose-bound scientific auxiliary-use authority through its owner port.

This application boundary corroborates opaque calibration auxiliary coordinates
without copying protected auxiliary values or querying another bounded context's
application tables. It deliberately stops before durable PostgreSQL adoption:
the repository port must later be backed by released/versioned owner evidence.
The returned projection is data, not a reusable authorization credential.
"""

from __future__ import annotations

from datetime import datetime
from inspect import getattr_static
import re
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

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$")
_RESOURCE_KIND = "calibration_auxiliary_authority"
_OPERATION = "read"
_CALIBRATION_AUXILIARY_VIEW_ISSUANCE_MARKER = object()
_READ_FIELDS = frozenset(
    {
        "authority_reference",
        "auxiliary_projection_reference",
        "auxiliary_projection_version",
        "auxiliary_projection_digest",
        "scientific_purpose_reference",
        "scientific_purpose_digest",
        "owner_contract_reference",
        "owner_contract_version",
        "owner_contract_digest",
        "owner_contract_released_at",
        "authorization_receipt_reference",
        "authorization_receipt_digest",
        "authorization_receipt_released_at",
        "scientific_use_receipt_reference",
        "scientific_use_receipt_digest",
        "scientific_use_at",
        "authorized_from",
        "authorized_to",
    }
)


class CalibrationAuxiliaryAuthorityNotFound(LookupError):
    """Indicate that no owner evidence corroborates the requested authority tuple."""


class CalibrationAuxiliaryAuthorityIntegrityError(RuntimeError):
    """Indicate that owner evidence does not match the authorized scientific use."""


def _require_reference(field_name: str, value: object, namespace: str) -> str:
    """Require one exact opaque namespaced reference without protected source values."""
    if (
        type(value) is not str
        or _REFERENCE_PATTERN.fullmatch(value) is None
        or value.partition(":")[0] != namespace
    ):
        raise ValueError(f"{field_name} must be an exact {namespace}: opaque reference.")
    return value


def _require_digest(field_name: str, value: object) -> str:
    """Require lowercase SHA-256 evidence rather than caller-readable source content."""
    if type(value) is not str or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex.")
    return value


def _require_positive_integer(field_name: str, value: object) -> int:
    """Require a strict positive integer contract version without accepting booleans."""
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


class CalibrationAuxiliaryAuthorityRecord(tuple):
    """Immutable owner projection corroborating one auxiliary-use authorization.

    Only opaque references, digests, versions, target identities, the exact
    scientific-use instant, and its authorization interval cross this boundary.
    Raw calibration attributes, benchmark values, protected characteristics, and
    row-level weights remain behind their authoritative owners.
    """

    __slots__ = ()

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        authority_reference: str,
        auxiliary_projection_reference: str,
        auxiliary_projection_version: int,
        auxiliary_projection_digest: str,
        scientific_purpose_reference: str,
        scientific_purpose_digest: str,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        owner_contract_released_at: datetime,
        authorization_receipt_reference: str,
        authorization_receipt_digest: str,
        authorization_receipt_released_at: datetime,
        scientific_use_receipt_reference: str,
        scientific_use_receipt_digest: str,
        scientific_use_at: datetime,
        authorized_from: datetime,
        authorized_to: datetime | None,
    ) -> CalibrationAuxiliaryAuthorityRecord:
        """Validate and detach every authority-bearing scalar before tuple storage."""
        tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
        study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
        authority_ref = _require_reference(
            "authority_reference", authority_reference, "scientific_auxiliary_authority"
        )
        projection_ref = _require_reference(
            "auxiliary_projection_reference",
            auxiliary_projection_reference,
            "calibration_auxiliary_projection",
        )
        projection_version = _require_positive_integer(
            "auxiliary_projection_version", auxiliary_projection_version
        )
        projection_digest = _require_digest(
            "auxiliary_projection_digest", auxiliary_projection_digest
        )
        purpose_ref = _require_reference(
            "scientific_purpose_reference",
            scientific_purpose_reference,
            "scientific_data_use_purpose",
        )
        purpose_digest = _require_digest("scientific_purpose_digest", scientific_purpose_digest)
        owner_ref = _require_reference(
            "owner_contract_reference", owner_contract_reference, "released_owner_contract"
        )
        owner_version = _require_positive_integer(
            "owner_contract_version", owner_contract_version
        )
        owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
        owner_contract_release = _require_aware_datetime(
            "owner_contract_released_at", owner_contract_released_at
        )
        authorization_ref = _require_reference(
            "authorization_receipt_reference",
            authorization_receipt_reference,
            "scientific_data_authorization",
        )
        authorization_digest = _require_digest(
            "authorization_receipt_digest", authorization_receipt_digest
        )
        authorization_release = _require_aware_datetime(
            "authorization_receipt_released_at", authorization_receipt_released_at
        )
        scientific_use_ref = _require_reference(
            "scientific_use_receipt_reference",
            scientific_use_receipt_reference,
            "scientific_use_receipt",
        )
        scientific_use_digest = _require_digest(
            "scientific_use_receipt_digest", scientific_use_receipt_digest
        )
        use_instant = _require_aware_datetime("scientific_use_at", scientific_use_at)
        authorization_start = _require_aware_datetime("authorized_from", authorized_from)
        authorization_end = (
            None
            if authorized_to is None
            else _require_aware_datetime("authorized_to", authorized_to)
        )
        if owner_contract_release > authorization_start:
            raise ValueError(
                "owner contract must be released no later than authorized_from."
            )
        if authorization_release < owner_contract_release:
            raise ValueError(
                "authorization receipt cannot predate owner contract release."
            )
        if authorization_release > authorization_start:
            raise ValueError(
                "authorization receipt must be released no later than authorized_from."
            )
        if authorization_end is not None and authorization_end <= authorization_start:
            raise ValueError("authorized_to must be later than authorized_from.")
        if use_instant < authorization_start or (
            authorization_end is not None and use_instant >= authorization_end
        ):
            raise ValueError(
                "scientific_use_at must fall inside the authorization interval."
            )
        return tuple.__new__(
            cls,
            (
                tenant_identity,
                study_identity,
                authority_ref,
                projection_ref,
                projection_version,
                projection_digest,
                purpose_ref,
                purpose_digest,
                owner_ref,
                owner_version,
                owner_digest,
                owner_contract_release,
                authorization_ref,
                authorization_digest,
                authorization_release,
                scientific_use_ref,
                scientific_use_digest,
                use_instant,
                authorization_start,
                authorization_end,
            ),
        )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh tenant identity for this owner evidence."""
        return _restore_operational_uuid("tenant_record_id", self[0])

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity bound to the scientific use."""
        return _restore_operational_uuid("validity_study_id", self[1])

    @property
    def authority_reference(self) -> str:
        """Return the opaque owner authority reference."""
        return self[2]

    @property
    def auxiliary_projection_reference(self) -> str:
        """Return the opaque purpose-limited auxiliary projection reference."""
        return self[3]

    @property
    def auxiliary_projection_version(self) -> int:
        """Return the positive version of the purpose-limited auxiliary projection."""
        return self[4]

    @property
    def auxiliary_projection_digest(self) -> str:
        """Return the projection evidence digest without exposing source attributes."""
        return self[5]

    @property
    def scientific_purpose_reference(self) -> str:
        """Return the governed scientific-use purpose reference."""
        return self[6]

    @property
    def scientific_purpose_digest(self) -> str:
        """Return the exact scientific-use purpose evidence digest."""
        return self[7]

    @property
    def owner_contract_reference(self) -> str:
        """Return the released owner-contract reference."""
        return self[8]

    @property
    def owner_contract_version(self) -> int:
        """Return the positive released owner-contract version."""
        return self[9]

    @property
    def owner_contract_digest(self) -> str:
        """Return the immutable bytes digest for the released owner contract."""
        return self[10]

    @property
    def owner_contract_released_at(self) -> datetime:
        """Return the owner-resolved contract release instant."""
        return self[11]

    @property
    def authorization_receipt_reference(self) -> str:
        """Return the authoritative scientific-use authorization receipt reference."""
        return self[12]

    @property
    def authorization_receipt_digest(self) -> str:
        """Return the authorization receipt digest used for exact correlation."""
        return self[13]

    @property
    def authorization_receipt_released_at(self) -> datetime:
        """Return the owner-resolved release instant of the authorization receipt."""
        return self[14]

    @property
    def scientific_use_receipt_reference(self) -> str:
        """Return the immutable scientific-use receipt reference."""
        return self[15]

    @property
    def scientific_use_receipt_digest(self) -> str:
        """Return the immutable scientific-use receipt digest."""
        return self[16]

    @property
    def scientific_use_at(self) -> datetime:
        """Return the owner-resolved UTC instant for the exact scientific use."""
        return self[17]

    @property
    def authorized_from(self) -> datetime:
        """Return the UTC instant when this scientific use became authorized."""
        return self[18]

    @property
    def authorized_to(self) -> datetime | None:
        """Return the exclusive UTC authorization end when one exists."""
        return self[19]


class CalibrationAuxiliaryAuthorityView:
    """Sealed field-minimized data view issued only after owner resolution."""

    __slots__ = ("_tenant_identity", "_study_identity", "_fields", "_issuance_marker")

    def __new__(
        cls,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        fields: tuple[tuple[str, object], ...],
    ) -> CalibrationAuxiliaryAuthorityView:
        """Reject public construction; the resolver is the only supported issuer."""
        raise TypeError(
            "CalibrationAuxiliaryAuthorityView is issued only by "
            "resolve_calibration_auxiliary_authority."
        )

    def __setattr__(self, name: str, value: object) -> None:
        """Keep ordinary callers from mutating issued projection state."""
        raise AttributeError("CalibrationAuxiliaryAuthorityView is immutable.")

    def __delattr__(self, name: str) -> None:
        """Keep ordinary callers from deleting issued projection state."""
        raise AttributeError("CalibrationAuxiliaryAuthorityView is immutable.")

    def _require_issued(self) -> None:
        """Reject raw allocations not sealed by the authorized resolver path."""
        try:
            marker = object.__getattribute__(self, "_issuance_marker")
        except AttributeError as exc:
            raise CalibrationAuxiliaryAuthorityIntegrityError(
                "calibration auxiliary authority view was not issued by the resolver"
            ) from exc
        if marker is not _CALIBRATION_AUXILIARY_VIEW_ISSUANCE_MARKER:
            raise CalibrationAuxiliaryAuthorityIntegrityError(
                "calibration auxiliary authority view was not issued by the resolver"
            )

    @property
    def tenant_record_id(self) -> UUID:
        """Return a fresh authorized tenant identity."""
        self._require_issued()
        return _restore_operational_uuid(
            "tenant_record_id", object.__getattribute__(self, "_tenant_identity")
        )

    @property
    def validity_study_id(self) -> UUID:
        """Return a fresh validity-study identity."""
        self._require_issued()
        return _restore_operational_uuid(
            "validity_study_id", object.__getattribute__(self, "_study_identity")
        )

    @property
    def fields(self) -> tuple[tuple[str, object], ...]:
        """Return immutable corroborating authority fields without protected values."""
        self._require_issued()
        return object.__getattribute__(self, "_fields")


@runtime_checkable
class CalibrationAuxiliaryAuthorityReadPort(Protocol):
    """Owner read contract for released calibration auxiliary-use authority evidence."""

    def read_calibration_auxiliary_authority(
        self,
        *,
        tenant_record_id: UUID,
        validity_study_id: UUID,
        authority_reference: str,
        auxiliary_projection_reference: str,
        auxiliary_projection_version: int,
        auxiliary_projection_digest: str,
        scientific_purpose_reference: str,
        scientific_purpose_digest: str,
        owner_contract_reference: str,
        owner_contract_version: int,
        owner_contract_digest: str,
        authorization_receipt_reference: str,
        authorization_receipt_digest: str,
        scientific_use_receipt_reference: str,
        scientific_use_receipt_digest: str,
    ) -> CalibrationAuxiliaryAuthorityRecord | None:
        """Return matching released authority evidence or ``None`` through an owner ACL."""
        ...


_PROTOCOL_READ_CAPABILITY = getattr_static(
    CalibrationAuxiliaryAuthorityReadPort, "read_calibration_auxiliary_authority"
)


def resolve_calibration_auxiliary_authority(
    *,
    principal: ValidationPrincipal,
    tenant_record_id: UUID,
    validity_study_id: UUID,
    authority_reference: str,
    auxiliary_projection_reference: str,
    auxiliary_projection_version: int,
    auxiliary_projection_digest: str,
    scientific_purpose_reference: str,
    scientific_purpose_digest: str,
    owner_contract_reference: str,
    owner_contract_version: int,
    owner_contract_digest: str,
    authorization_receipt_reference: str,
    authorization_receipt_digest: str,
    scientific_use_receipt_reference: str,
    scientific_use_receipt_digest: str,
    used_at: datetime,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: CalibrationAuxiliaryAuthorityReadPort,
) -> CalibrationAuxiliaryAuthorityView:
    """Authorize and corroborate one exact calibration auxiliary-use authority tuple.

    The exact owner capability is captured inertly before authorization and the
    same function is invoked afterward. The request carries no protected source
    values. Owner evidence must reproduce every caller-supplied leaf coordinate,
    including the projection reference/version/digest, receipt references and the
    released owner-contract digest. Owner evidence must also prove that both the
    governing contract and authorization receipt existed before the authorization
    interval became effective; neither release instant is a caller coordinate.
    The scientific-use receipt is independently bound to the same use instant
    before any corroborating fields are returned.
    """
    if type(principal) is not ValidationPrincipal:
        raise TypeError("principal must be an exact ValidationPrincipal.")
    if type(policy) is not PurposeBoundAccessPolicy:
        raise TypeError("policy must be an exact PurposeBoundAccessPolicy.")
    read_capability = getattr_static(
        type(read_port), "read_calibration_auxiliary_authority", None
    )
    if (
        type(read_capability) is not FunctionType
        or read_capability is _PROTOCOL_READ_CAPABILITY
    ):
        raise TypeError(
            "read_port must expose a statically callable "
            "read_calibration_auxiliary_authority."
        )

    detached_principal = ValidationPrincipal(
        tenant_record_id=principal.tenant_record_id,
        actor_reference=principal.actor_reference,
        granted_scope_codes=principal.granted_scope_codes,
    )
    tenant_identity = _store_operational_uuid("tenant_record_id", tenant_record_id)
    study_identity = _store_operational_uuid("validity_study_id", validity_study_id)
    tenant_id = _restore_operational_uuid("tenant_record_id", tenant_identity)
    study_id = _restore_operational_uuid("validity_study_id", study_identity)
    authority_ref = _require_reference(
        "authority_reference", authority_reference, "scientific_auxiliary_authority"
    )
    projection_ref = _require_reference(
        "auxiliary_projection_reference",
        auxiliary_projection_reference,
        "calibration_auxiliary_projection",
    )
    projection_version = _require_positive_integer(
        "auxiliary_projection_version", auxiliary_projection_version
    )
    projection_digest = _require_digest(
        "auxiliary_projection_digest", auxiliary_projection_digest
    )
    purpose_ref = _require_reference(
        "scientific_purpose_reference",
        scientific_purpose_reference,
        "scientific_data_use_purpose",
    )
    purpose_digest = _require_digest("scientific_purpose_digest", scientific_purpose_digest)
    owner_ref = _require_reference(
        "owner_contract_reference", owner_contract_reference, "released_owner_contract"
    )
    owner_version = _require_positive_integer("owner_contract_version", owner_contract_version)
    owner_digest = _require_digest("owner_contract_digest", owner_contract_digest)
    authorization_ref = _require_reference(
        "authorization_receipt_reference",
        authorization_receipt_reference,
        "scientific_data_authorization",
    )
    authorization_digest = _require_digest(
        "authorization_receipt_digest", authorization_receipt_digest
    )
    scientific_use_ref = _require_reference(
        "scientific_use_receipt_reference",
        scientific_use_receipt_reference,
        "scientific_use_receipt",
    )
    scientific_use_digest = _require_digest(
        "scientific_use_receipt_digest", scientific_use_receipt_digest
    )
    use_instant = _require_aware_datetime("used_at", used_at)
    purpose = _require_code("purpose_code", purpose_code)
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
        tenant_record_id=_restore_operational_uuid("tenant_record_id", tenant_identity),
        validity_study_id=_restore_operational_uuid("validity_study_id", study_identity),
        authority_reference=authority_ref,
        auxiliary_projection_reference=projection_ref,
        auxiliary_projection_version=projection_version,
        auxiliary_projection_digest=projection_digest,
        scientific_purpose_reference=purpose_ref,
        scientific_purpose_digest=purpose_digest,
        owner_contract_reference=owner_ref,
        owner_contract_version=owner_version,
        owner_contract_digest=owner_digest,
        authorization_receipt_reference=authorization_ref,
        authorization_receipt_digest=authorization_digest,
        scientific_use_receipt_reference=scientific_use_ref,
        scientific_use_receipt_digest=scientific_use_digest,
    )
    if persisted is None:
        raise CalibrationAuxiliaryAuthorityNotFound(str(study_id))
    if type(persisted) is not CalibrationAuxiliaryAuthorityRecord:
        raise CalibrationAuxiliaryAuthorityIntegrityError(
            "owner port returned non-canonical calibration auxiliary authority evidence"
        )

    try:
        record = CalibrationAuxiliaryAuthorityRecord(
            tenant_record_id=persisted.tenant_record_id,
            validity_study_id=persisted.validity_study_id,
            authority_reference=persisted.authority_reference,
            auxiliary_projection_reference=persisted.auxiliary_projection_reference,
            auxiliary_projection_version=persisted.auxiliary_projection_version,
            auxiliary_projection_digest=persisted.auxiliary_projection_digest,
            scientific_purpose_reference=persisted.scientific_purpose_reference,
            scientific_purpose_digest=persisted.scientific_purpose_digest,
            owner_contract_reference=persisted.owner_contract_reference,
            owner_contract_version=persisted.owner_contract_version,
            owner_contract_digest=persisted.owner_contract_digest,
            owner_contract_released_at=persisted.owner_contract_released_at,
            authorization_receipt_reference=persisted.authorization_receipt_reference,
            authorization_receipt_digest=persisted.authorization_receipt_digest,
            authorization_receipt_released_at=persisted.authorization_receipt_released_at,
            scientific_use_receipt_reference=persisted.scientific_use_receipt_reference,
            scientific_use_receipt_digest=persisted.scientific_use_receipt_digest,
            scientific_use_at=persisted.scientific_use_at,
            authorized_from=persisted.authorized_from,
            authorized_to=persisted.authorized_to,
        )
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise CalibrationAuxiliaryAuthorityIntegrityError(
            "owner port returned malformed calibration auxiliary authority evidence"
        ) from exc
    if record != persisted:
        raise CalibrationAuxiliaryAuthorityIntegrityError(
            "owner port returned non-canonical calibration auxiliary authority evidence"
        )
    if (
        _store_operational_uuid("record tenant_record_id", record.tenant_record_id)
        != tenant_identity
        or _store_operational_uuid("record validity_study_id", record.validity_study_id)
        != study_identity
        or record.authority_reference != authority_ref
        or record.auxiliary_projection_reference != projection_ref
        or record.auxiliary_projection_version != projection_version
        or record.auxiliary_projection_digest != projection_digest
        or record.scientific_purpose_reference != purpose_ref
        or record.scientific_purpose_digest != purpose_digest
        or record.owner_contract_reference != owner_ref
        or record.owner_contract_version != owner_version
        or record.owner_contract_digest != owner_digest
        or record.authorization_receipt_reference != authorization_ref
        or record.authorization_receipt_digest != authorization_digest
        or record.scientific_use_receipt_reference != scientific_use_ref
        or record.scientific_use_receipt_digest != scientific_use_digest
        or record.scientific_use_at != use_instant
    ):
        raise CalibrationAuxiliaryAuthorityIntegrityError(
            "owner evidence does not match the requested calibration auxiliary authority"
        )

    values = {
        "authority_reference": record.authority_reference,
        "auxiliary_projection_reference": record.auxiliary_projection_reference,
        "auxiliary_projection_version": record.auxiliary_projection_version,
        "auxiliary_projection_digest": record.auxiliary_projection_digest,
        "scientific_purpose_reference": record.scientific_purpose_reference,
        "scientific_purpose_digest": record.scientific_purpose_digest,
        "owner_contract_reference": record.owner_contract_reference,
        "owner_contract_version": record.owner_contract_version,
        "owner_contract_digest": record.owner_contract_digest,
        "owner_contract_released_at": record.owner_contract_released_at,
        "authorization_receipt_reference": record.authorization_receipt_reference,
        "authorization_receipt_digest": record.authorization_receipt_digest,
        "authorization_receipt_released_at": record.authorization_receipt_released_at,
        "scientific_use_receipt_reference": record.scientific_use_receipt_reference,
        "scientific_use_receipt_digest": record.scientific_use_receipt_digest,
        "scientific_use_at": record.scientific_use_at,
        "authorized_from": record.authorized_from,
        "authorized_to": record.authorized_to,
    }
    fields = tuple((field_name, values[field_name]) for field_name in sorted(_READ_FIELDS))
    view = object.__new__(CalibrationAuxiliaryAuthorityView)
    object.__setattr__(view, "_tenant_identity", tenant_identity)
    object.__setattr__(view, "_study_identity", study_identity)
    object.__setattr__(view, "_fields", fields)
    object.__setattr__(
        view, "_issuance_marker", _CALIBRATION_AUXILIARY_VIEW_ISSUANCE_MARKER
    )
    return view
