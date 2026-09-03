"""Tenant-scoped bitemporal organization hierarchy integrity and evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from uuid import UUID

from orgmetra_hris_kernel.errors import (
    IntervalError,
    OrganizationHierarchyError,
    SingleValuedFactError,
)
from orgmetra_hris_kernel.facts import OrganizationUnitVersion
from orgmetra_hris_kernel.resolution import resolve_single_valued_fact

_MAX_UUID_INT = (1 << 128) - 1


def _validate_operational_uuid(field_name: str, value: object) -> UUID:
    """Require one exact, non-sentinel UUID for hierarchy evidence."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{field_name} must be an operational UUID.")
    return value


def _validate_hierarchy_temporal_coordinate(effective_on: date, known_at: object) -> datetime:
    """Validate and detach exact business and recorded-time values before hierarchy use."""
    if type(effective_on) is not date:
        raise IntervalError(
            "Organization hierarchy snapshot effective date must be a calendar date.",
            next_action="Provide an exact business date, then rebuild the hierarchy snapshot.",
        )
    if type(known_at) is not datetime or known_at.tzinfo is None:
        raise IntervalError(
            "Organization hierarchy snapshot knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the hierarchy snapshot.",
        )
    try:
        offset = known_at.utcoffset()
    except Exception as exc:  # noqa: BLE001 - normalize provider behavior at trust boundary.
        raise IntervalError(
            "Organization hierarchy snapshot knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the hierarchy snapshot.",
        ) from exc
    if type(offset) is not timedelta:
        raise IntervalError(
            "Organization hierarchy snapshot knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the hierarchy snapshot.",
        )
    try:
        return (known_at.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except OverflowError as exc:
        raise IntervalError(
            "Organization hierarchy snapshot knowledge cutoff must be timezone-aware.",
            next_action="Convert the knowledge cutoff to UTC, then rebuild the hierarchy snapshot.",
        ) from exc


def _visible_parent_links(
    organization_versions: list[OrganizationUnitVersion],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> tuple[tuple[UUID, UUID | None], ...]:
    """Resolve one visible parent link per tenant organization unit in stable order."""
    _validate_operational_uuid("tenant_record_id", tenant_record_id)
    known_at = _validate_hierarchy_temporal_coordinate(effective_on, known_at)
    scoped = [
        version
        for version in organization_versions
        if version.tenant_record_id == tenant_record_id
    ]
    unit_ids = sorted(
        {version.organization_unit_id for version in scoped},
        key=str,
    )
    parent_links: list[tuple[UUID, UUID | None]] = []
    for unit_id in unit_ids:
        visible = resolve_single_valued_fact(
            scoped,
            tenant_record_id=tenant_record_id,
            identity_of="organization_unit_id",
            identity_value=unit_id,
            effective_on=effective_on,
            known_at=known_at,
        )
        if visible is not None:
            parent_id = visible.parent_organization_unit_id
            parent_links.append((unit_id, parent_id))
    return tuple(parent_links)


def _require_acyclic_parent_links(parent_links: tuple[tuple[UUID, UUID | None], ...]) -> None:
    """Reject a cycle while allowing a parent anchor that is not visible at this coordinate."""
    parents = dict(parent_links)
    for start in parents:
        seen: set[UUID] = set()
        current: UUID | None = start
        while current is not None:
            if current in seen:
                raise OrganizationHierarchyError(
                    "Visible organization parent links form a cycle in this tenant.",
                    next_action=(
                        "Close or correct the superseded parent link, then validate the organization chart again."
                    ),
                )
            seen.add(current)
            current = parents.get(current)


@dataclass(frozen=True, slots=True)
class OrganizationHierarchySnapshot:
    """Deterministic opaque organization structure at one bitemporal coordinate.

    ``parent_links`` carries only durable opaque organization-unit UUIDs and their
    visible parent anchors. A parent anchor may be absent from the visible unit set
    when that parent was not yet known or was outside the requested business-time
    coordinate; the opaque anchor is retained rather than silently rewritten into
    a root. Direct construction snapshots caller-owned link containers before
    validation so later caller mutation cannot rewrite canonical evidence. It also
    requires canonical ordering, unique unit identities, exact built-in temporal
    coordinate types, and an acyclic visible graph.
    """

    tenant_record_id: UUID
    effective_on: date
    known_at: datetime
    parent_links: tuple[tuple[UUID, UUID | None], ...]

    def __post_init__(self) -> None:
        """Detach caller-owned containers and reject ambiguous hierarchy evidence."""
        known_at = _validate_hierarchy_temporal_coordinate(self.effective_on, self.known_at)
        object.__setattr__(self, "known_at", known_at)
        object.__setattr__(
            self,
            "parent_links",
            tuple(tuple(parent_link) for parent_link in self.parent_links),
        )
        _validate_operational_uuid("tenant_record_id", self.tenant_record_id)
        for parent_link in self.parent_links:
            if len(parent_link) != 2:
                raise ValueError("parent_links must contain organization-unit and parent identities.")
            unit_id, parent_id = parent_link
            _validate_operational_uuid("organization_unit_id", unit_id)
            if parent_id is not None:
                _validate_operational_uuid("parent_organization_unit_id", parent_id)
        unit_ids = tuple(unit_id for unit_id, _parent_id in self.parent_links)
        if len(unit_ids) != len(set(unit_ids)):
            raise SingleValuedFactError(
                "Organization hierarchy snapshot contains a duplicate organization unit.",
                next_action="Resolve each organization unit to one visible parent link, then rebuild the snapshot.",
            )
        if unit_ids != tuple(sorted(unit_ids, key=str)):
            raise SingleValuedFactError(
                "Organization hierarchy snapshot must use canonical organization-unit order.",
                next_action="Sort parent links by organization-unit UUID, then rebuild the snapshot.",
            )
        _require_acyclic_parent_links(self.parent_links)

    @property
    def unit_count(self) -> int:
        """Return the number of visible organization units in this snapshot."""
        return len(self.parent_links)

    @property
    def root_unit_count(self) -> int:
        """Return the number of visible units that explicitly have no parent."""
        return sum(parent_id is None for _unit_id, parent_id in self.parent_links)

    @property
    def reporting_edge_count(self) -> int:
        """Return the number of visible units carrying a parent anchor."""
        return sum(parent_id is not None for _unit_id, parent_id in self.parent_links)

    def canonical_json(self) -> str:
        """Return deterministic hierarchy evidence for audit and reporting correlation."""
        if (
            type(self.effective_on) is not date
            or type(self.known_at) is not datetime
            or self.known_at.tzinfo is not timezone.utc
        ):
            raise IntervalError(
                "Organization hierarchy snapshot temporal evidence is not detached UTC data.",
                next_action="Rebuild the hierarchy snapshot from exact temporal coordinates.",
            )
        payload = {
            "effective_on": self.effective_on.isoformat(),
            "known_at": self.known_at.isoformat().replace("+00:00", "Z"),
            "parent_links": [
                {
                    "organization_unit_id": str(unit_id),
                    "parent_organization_unit_id": None if parent_id is None else str(parent_id),
                }
                for unit_id, parent_id in self.parent_links
            ],
            "reporting_edge_count": self.reporting_edge_count,
            "root_unit_count": self.root_unit_count,
            "schema_version": "orgmetra.organization_hierarchy_snapshot.v1",
            "tenant_record_id": str(self.tenant_record_id),
            "unit_count": self.unit_count,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def content_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 hierarchy evidence bytes."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def validate_organization_hierarchy(
    organization_versions: list[OrganizationUnitVersion],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> None:
    """Reject invalid visible parent links inside one tenant at one bitemporal coordinate.

    Each durable unit is first resolved through the normal single-valued
    bitemporal rule, so two simultaneously visible versions fail closed before
    graph traversal. Parent anchors without a visible version terminate the
    currently known chain rather than importing facts from another tenant or a
    future knowledge state. Because parent identities are tenant-qualified and
    the parent field is an opaque UUID without its own tenant qualifier, a UUID
    collision across tenants is retained as an unproven parent anchor rather
    than misclassified as foreign.

    Args:
        organization_versions: Candidate parent-link versions, including other tenants.
        tenant_record_id: Tenant namespace whose organization chart is reviewed.
        effective_on: Exact built-in business date represented by the chart.
        known_at: Exact built-in timezone-aware system knowledge cutoff used to reconstruct it.

    Raises:
        IntervalError: The temporal coordinate is not an exact supported date/datetime pair.
        SingleValuedFactError: One unit has two visible versions at the coordinate.
        OrganizationHierarchyError: Visible parent links contain a cycle.
    """
    parent_links = _visible_parent_links(
        organization_versions,
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
    )
    _require_acyclic_parent_links(parent_links)


def build_organization_hierarchy_snapshot(
    organization_versions: list[OrganizationUnitVersion],
    *,
    tenant_record_id: UUID,
    effective_on: date,
    known_at: datetime,
) -> OrganizationHierarchySnapshot:
    """Build deterministic tenant organization structure at one effective/recorded coordinate.

    The builder reuses the authoritative single-valued bitemporal resolution and
    cycle rules. It preserves an opaque parent anchor when the source does not
    provide enough tenant-qualified evidence to resolve that parent. It does not infer names,
    headcount, managerial authority, legal reporting lines, or employment
    decisions. Downstream consumers receive only the tenant identity, opaque
    unit/parent identities, the exact business date, and the exact system-knowledge
    cutoff needed to reproduce the structure.

    Args:
        organization_versions: Candidate organization parent-link versions, including other tenants.
        tenant_record_id: Tenant namespace whose organization structure is reconstructed.
        effective_on: Exact built-in business date represented by the structure.
        known_at: Exact built-in timezone-aware system-knowledge cutoff used for reconstruction.

    Returns:
        Canonically ordered hierarchy evidence suitable for authorized reporting and audit correlation.

    Raises:
        IntervalError: The temporal coordinate is not an exact supported date/datetime pair.
        SingleValuedFactError: One unit has contradictory visible versions.
        OrganizationHierarchyError: Visible parent links contain a cycle.
    """
    known_at = _validate_hierarchy_temporal_coordinate(effective_on, known_at)
    return OrganizationHierarchySnapshot(
        tenant_record_id=tenant_record_id,
        effective_on=effective_on,
        known_at=known_at,
        parent_links=_visible_parent_links(
            organization_versions,
            tenant_record_id=tenant_record_id,
            effective_on=effective_on,
            known_at=known_at,
        ),
    )
