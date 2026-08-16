"""Tenant- and identity-scoped bitemporal resolution tests."""

from dataclasses import replace
from datetime import date
from uuid import UUID

import pytest

from orgmetra_hris_kernel import (
    IdentityScopeError,
    SingleValuedFactError,
    resolve_bitemporal_facts,
    resolve_single_valued_fact,
)

from .conftest import JORDAN, JORDAN_EMPLOYMENT, RILEY, RILEY_EMPLOYMENT, TENANT, utc

FOREIGN_TENANT = UUID("20000000-0000-7000-8000-000000000101")


def test_resolution_hides_facts_recorded_after_the_knowledge_cutoff(
    jordan_active_employment,
) -> None:
    """A June correction must not appear in a May decision reconstruction."""
    visible = resolve_bitemporal_facts(
        [jordan_active_employment],
        tenant_record_id=TENANT,
        identity_of="employment_record_id",
        identity_value=JORDAN_EMPLOYMENT,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 3, 1, 14),
    )
    assert visible == []


def test_resolution_returns_only_the_requested_identity(
    jordan_active_employment,
) -> None:
    """Riley's employment must not leak into Jordan's history view."""
    riley = replace(
        jordan_active_employment,
        employment_record_id=RILEY_EMPLOYMENT,
        person_record_id=RILEY,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000202"),
    )
    visible = resolve_bitemporal_facts(
        [jordan_active_employment, riley],
        tenant_record_id=TENANT,
        identity_of="employment_record_id",
        identity_value=JORDAN_EMPLOYMENT,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 6, 1),
    )
    assert [fact.person_record_id for fact in visible] == [JORDAN]


def test_resolution_rejects_foreign_tenant_fact_with_colliding_identity(
    jordan_active_employment,
) -> None:
    """A colliding durable identifier in another tenant cannot leak into reconstruction."""
    foreign = replace(
        jordan_active_employment,
        tenant_record_id=FOREIGN_TENANT,
        employment_record_version_id=UUID("20000000-0000-7000-8000-000000000202"),
        employment_status_code="leave",
    )
    visible = resolve_bitemporal_facts(
        [foreign, jordan_active_employment],
        tenant_record_id=TENANT,
        identity_of="employment_record_id",
        identity_value=JORDAN_EMPLOYMENT,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 6, 1),
    )
    assert visible == [jordan_active_employment]


def test_resolution_rejects_unknown_identity_fields(jordan_active_employment) -> None:
    """Callers must name a real identity field before a historical query runs."""
    with pytest.raises(IdentityScopeError, match="identity field"):
        resolve_bitemporal_facts(
            [jordan_active_employment],
            tenant_record_id=TENANT,
            identity_of="display_name",
            identity_value=JORDAN,
            effective_on=date(2024, 5, 1),
            known_at=utc(2024, 6, 1),
        )


def test_single_valued_resolution_rejects_two_open_versions(
    jordan_active_employment,
) -> None:
    """HR must close the prior recorded version before inserting a replacement."""
    duplicate = replace(
        jordan_active_employment,
        employment_record_version_id=UUID("10000000-0000-7000-8000-000000000203"),
        employment_status_code="leave",
    )
    with pytest.raises(SingleValuedFactError, match="one version"):
        resolve_single_valued_fact(
            [jordan_active_employment, duplicate],
            tenant_record_id=TENANT,
            identity_of="employment_record_id",
            identity_value=JORDAN_EMPLOYMENT,
            effective_on=date(2024, 5, 1),
            known_at=utc(2024, 6, 1),
        )


def test_single_valued_resolution_returns_the_visible_version(
    jordan_active_employment,
) -> None:
    """One knowledge cutoff must yield at most one employment status."""
    found = resolve_single_valued_fact(
        [jordan_active_employment],
        tenant_record_id=TENANT,
        identity_of="employment_record_id",
        identity_value=JORDAN_EMPLOYMENT,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 6, 1),
    )
    assert found is not None
    assert found.employment_status_code == "active"
    assert found.tenant_record_id == TENANT
    missing = resolve_single_valued_fact(
        [jordan_active_employment],
        tenant_record_id=TENANT,
        identity_of="employment_record_id",
        identity_value=RILEY_EMPLOYMENT,
        effective_on=date(2024, 5, 1),
        known_at=utc(2024, 6, 1),
    )
    assert missing is None
