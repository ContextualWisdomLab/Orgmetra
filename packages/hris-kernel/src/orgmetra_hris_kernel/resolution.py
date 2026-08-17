"""Tenant- and identity-scoped reconstruction at one effective day and knowledge cutoff."""

from __future__ import annotations

from datetime import date, datetime
from typing import TypeVar
from uuid import UUID

from orgmetra_hris_kernel.errors import IdentityScopeError, SingleValuedFactError
from orgmetra_hris_kernel.facts import IDENTITY_FIELDS

FactT = TypeVar("FactT")


def resolve_bitemporal_facts(
    facts: list[FactT],
    *,
    tenant_record_id: UUID,
    identity_of: str,
    identity_value: UUID,
    effective_on: date,
    known_at: datetime,
) -> list[FactT]:
    """Return one tenant's facts for an identity that were true and already known.

    Args:
        facts: Candidate versions or assignments, including other tenants.
        tenant_record_id: Tenant namespace that owns the reconstruction.
        identity_of: The identity field to scope, such as `employment_record_id`.
        identity_value: The durable identifier being reconstructed.
        effective_on: The real-world day under review.
        known_at: The system knowledge cutoff.

    Returns:
        The matching tenant-scoped facts. Review this list, then approve, correct, or export.
    """
    if identity_of not in IDENTITY_FIELDS:
        raise IdentityScopeError(
            f"Unsupported identity field: {identity_of}",
            next_action=(
                "Query by employment, person, organization, position, assignment, or tenant identity."
            ),
        )
    visible: list[FactT] = []
    for fact in facts:
        if getattr(fact, "tenant_record_id") != tenant_record_id:
            continue
        if getattr(fact, identity_of) != identity_value:
            continue
        effective = getattr(fact, "effective")
        recorded = getattr(fact, "recorded")
        if not effective.contains(effective_on):
            continue
        if not recorded.contains(known_at):
            continue
        visible.append(fact)
    return visible


def resolve_single_valued_fact(
    facts: list[FactT],
    *,
    tenant_record_id: UUID,
    identity_of: str,
    identity_value: UUID,
    effective_on: date,
    known_at: datetime,
) -> FactT | None:
    """Return the one visible version of a single-valued tenant-scoped fact family.

    Returns:
        The visible version, or `None` when nothing was known yet.

    Raises:
        SingleValuedFactError: Two versions are visible. Close the prior recorded
            interval before inserting the replacement.
    """
    visible = resolve_bitemporal_facts(
        facts,
        tenant_record_id=tenant_record_id,
        identity_of=identity_of,
        identity_value=identity_value,
        effective_on=effective_on,
        known_at=known_at,
    )
    if len(visible) > 1:
        raise SingleValuedFactError(
            "One tenant-scoped identity resolved to more than one version.",
            next_action="Close the prior recorded interval, then insert exactly one replacement.",
        )
    if not visible:
        return None
    return visible[0]
