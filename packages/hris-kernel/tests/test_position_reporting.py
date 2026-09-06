"""Executable contract for tenant-scoped bitemporal position reporting."""

from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel.facts import PositionVersion
from orgmetra_hris_kernel.intervals import DateInterval, RecordedInterval
from orgmetra_hris_kernel.position_reporting import (
    PositionReportingHierarchyError,
    PositionReportingRelationship,
    build_position_reporting_snapshot,
)

TENANT_ALPHA = UUID("018f0d35-7b1a-7cc2-8d9c-111111111111")
TENANT_BETA = UUID("018f0d35-7b1a-7cc2-8d9c-222222222222")
POSITION_A = UUID("018f0d35-7b1a-7cc2-8d9c-aaaaaaaaaaa1")
POSITION_B = UUID("018f0d35-7b1a-7cc2-8d9c-aaaaaaaaaaa2")
POSITION_C = UUID("018f0d35-7b1a-7cc2-8d9c-aaaaaaaaaaa3")
POSITION_D = UUID("018f0d35-7b1a-7cc2-8d9c-aaaaaaaaaaa4")
RELATIONSHIP_A = UUID("018f0d35-7b1a-4cc2-8d9c-bbbbbbbbbbb1")
RELATIONSHIP_B = UUID("018f0d35-7b1a-4cc2-8d9c-bbbbbbbbbbb2")
RELATIONSHIP_C = UUID("018f0d35-7b1a-4cc2-8d9c-bbbbbbbbbbb3")
VERSION_A = UUID("018f0d35-7b1a-7cc2-8d9c-ccccccccccc1")
VERSION_B = UUID("018f0d35-7b1a-7cc2-8d9c-ccccccccccc2")
VERSION_C = UUID("018f0d35-7b1a-7cc2-8d9c-ccccccccccc3")
VERSION_D = UUID("018f0d35-7b1a-7cc2-8d9c-ccccccccccc4")
EFFECTIVE_ON = date(2026, 8, 23)
KNOWN_AT = datetime(2026, 8, 23, 3, 30, tzinfo=timezone.utc)


def position(
    position_record_id: UUID,
    position_record_version_id: UUID,
    *,
    tenant_record_id: UUID = TENANT_ALPHA,
    status: str = "active",
    effective: DateInterval | None = None,
    recorded: RecordedInterval | None = None,
) -> PositionVersion:
    """Build one visible position version for reporting-contract tests."""
    return PositionVersion(
        tenant_record_id=tenant_record_id,
        position_record_id=position_record_id,
        position_record_version_id=position_record_version_id,
        position_status_code=status,
        effective=effective or DateInterval(date(2026, 1, 1)),
        recorded=recorded
        or RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )


def relationship(
    relationship_id: UUID,
    subordinate: UUID,
    manager: UUID,
    *,
    tenant_record_id: UUID = TENANT_ALPHA,
    effective: DateInterval | None = None,
    recorded: RecordedInterval | None = None,
) -> PositionReportingRelationship:
    """Build one solid-line reporting relationship for tests."""
    return PositionReportingRelationship(
        tenant_record_id=tenant_record_id,
        position_reporting_relationship_id=relationship_id,
        subordinate_position_record_id=subordinate,
        manager_position_record_id=manager,
        relationship_type_code="solid_line",
        effective=effective or DateInterval(date(2026, 1, 1)),
        recorded=recorded
        or RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )


def visible_positions() -> list[PositionVersion]:
    """Return three staffable Alpha positions visible at the review coordinate."""
    return [
        position(POSITION_A, VERSION_A),
        position(POSITION_B, VERSION_B),
        position(POSITION_C, VERSION_C),
    ]


def test_builds_deterministic_position_reporting_snapshot() -> None:
    """Acyclic solid-line edges resolve to deterministic position-to-position evidence."""
    snapshot = build_position_reporting_snapshot(
        [
            relationship(RELATIONSHIP_B, POSITION_C, POSITION_B),
            relationship(RELATIONSHIP_A, POSITION_B, POSITION_A),
        ],
        visible_positions(),
        tenant_record_id=TENANT_ALPHA,
        effective_on=EFFECTIVE_ON,
        known_at=KNOWN_AT,
    )

    assert snapshot.tenant_record_id == TENANT_ALPHA
    assert snapshot.effective_on == EFFECTIVE_ON
    assert snapshot.known_at == KNOWN_AT
    assert snapshot.manager_by_subordinate == (
        (POSITION_B, POSITION_A),
        (POSITION_C, POSITION_B),
    )
    assert "aaaaaaaa" not in repr(snapshot)


def test_ignores_other_tenants_and_nonvisible_relationships() -> None:
    """Foreign and not-yet-effective edges cannot enter one tenant's reporting chart."""
    snapshot = build_position_reporting_snapshot(
        [
            relationship(
                RELATIONSHIP_A,
                POSITION_B,
                POSITION_A,
                tenant_record_id=TENANT_BETA,
            ),
            relationship(
                RELATIONSHIP_B,
                POSITION_C,
                POSITION_B,
                effective=DateInterval(date(2027, 1, 1)),
            ),
        ],
        visible_positions(),
        tenant_record_id=TENANT_ALPHA,
        effective_on=EFFECTIVE_ON,
        known_at=KNOWN_AT,
    )

    assert snapshot.manager_by_subordinate == ()


def test_rejects_two_visible_managers_for_one_subordinate() -> None:
    """One solid-line subordinate cannot resolve to two managers at one coordinate."""
    with pytest.raises(PositionReportingHierarchyError, match="more than one solid-line manager"):
        build_position_reporting_snapshot(
            [
                relationship(RELATIONSHIP_A, POSITION_C, POSITION_A),
                relationship(RELATIONSHIP_B, POSITION_C, POSITION_B),
            ],
            visible_positions(),
            tenant_record_id=TENANT_ALPHA,
            effective_on=EFFECTIVE_ON,
            known_at=KNOWN_AT,
        )


def test_rejects_visible_reporting_cycle() -> None:
    """A position reporting chain must fail closed when it cycles."""
    with pytest.raises(PositionReportingHierarchyError, match="form a cycle"):
        build_position_reporting_snapshot(
            [
                relationship(RELATIONSHIP_A, POSITION_A, POSITION_B),
                relationship(RELATIONSHIP_B, POSITION_B, POSITION_A),
            ],
            visible_positions(),
            tenant_record_id=TENANT_ALPHA,
            effective_on=EFFECTIVE_ON,
            known_at=KNOWN_AT,
        )


def test_rejects_self_reporting_at_construction() -> None:
    """A position cannot be its own direct solid-line manager."""
    with pytest.raises(PositionReportingHierarchyError, match="cannot report to itself"):
        relationship(RELATIONSHIP_A, POSITION_A, POSITION_A)


def test_rejects_missing_or_nonstaffable_endpoint_position() -> None:
    """Both ends of a visible reporting edge must resolve to staffable tenant seats."""
    with pytest.raises(PositionReportingHierarchyError, match="staffable position"):
        build_position_reporting_snapshot(
            [relationship(RELATIONSHIP_A, POSITION_B, POSITION_D)],
            visible_positions(),
            tenant_record_id=TENANT_ALPHA,
            effective_on=EFFECTIVE_ON,
            known_at=KNOWN_AT,
        )

    closed_positions = visible_positions() + [position(POSITION_D, VERSION_D, status="closed")]
    with pytest.raises(PositionReportingHierarchyError, match="staffable position"):
        build_position_reporting_snapshot(
            [relationship(RELATIONSHIP_A, POSITION_B, POSITION_D)],
            closed_positions,
            tenant_record_id=TENANT_ALPHA,
            effective_on=EFFECTIVE_ON,
            known_at=KNOWN_AT,
        )


def test_rejects_invalid_relationship_primitives() -> None:
    """Trust-bearing relationship primitives fail closed before graph traversal."""
    with pytest.raises(PositionReportingHierarchyError, match="relationship_type_code"):
        PositionReportingRelationship(
            tenant_record_id=TENANT_ALPHA,
            position_reporting_relationship_id=RELATIONSHIP_A,
            subordinate_position_record_id=POSITION_B,
            manager_position_record_id=POSITION_A,
            relationship_type_code="dotted_line",
            effective=DateInterval(date(2026, 1, 1)),
            recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        )

    with pytest.raises(PositionReportingHierarchyError, match="exact governed interval"):
        PositionReportingRelationship(
            tenant_record_id=TENANT_ALPHA,
            position_reporting_relationship_id=RELATIONSHIP_A,
            subordinate_position_record_id=POSITION_B,
            manager_position_record_id=POSITION_A,
            relationship_type_code="solid_line",
            effective=object(),  # type: ignore[arg-type]
            recorded=RecordedInterval(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        )


def test_rejects_untrusted_runtime_types_at_snapshot_boundary() -> None:
    """Caller-defined runtime subclasses cannot control identity or temporal comparisons."""

    class ForgedDate(date):
        """Caller-controlled date subtype rejected before interval comparison."""

    class ForgedRelationship(PositionReportingRelationship):
        """Validation-bypassing relationship subtype rejected at the snapshot boundary."""

    base = relationship(RELATIONSHIP_A, POSITION_B, POSITION_A)
    forged = object.__new__(ForgedRelationship)
    for field_name in (
        "tenant_record_id",
        "position_reporting_relationship_id",
        "subordinate_position_record_id",
        "manager_position_record_id",
        "relationship_type_code",
        "effective",
        "recorded",
    ):
        object.__setattr__(forged, field_name, getattr(base, field_name))

    with pytest.raises(PositionReportingHierarchyError, match="exact governed relationship"):
        build_position_reporting_snapshot(
            [forged],
            visible_positions(),
            tenant_record_id=TENANT_ALPHA,
            effective_on=EFFECTIVE_ON,
            known_at=KNOWN_AT,
        )

    with pytest.raises(PositionReportingHierarchyError, match="exact built-in date"):
        build_position_reporting_snapshot(
            [],
            visible_positions(),
            tenant_record_id=TENANT_ALPHA,
            effective_on=ForgedDate(2026, 8, 23),
            known_at=KNOWN_AT,
        )


def test_rejects_naive_or_subclassed_system_time() -> None:
    """System knowledge coordinates must be exact built-in timezone-aware datetimes."""

    class ForgedDateTime(datetime):
        """Caller-controlled datetime subtype rejected before recorded-time comparison."""

    with pytest.raises(PositionReportingHierarchyError, match="timezone-aware datetime"):
        build_position_reporting_snapshot(
            [],
            visible_positions(),
            tenant_record_id=TENANT_ALPHA,
            effective_on=EFFECTIVE_ON,
            known_at=datetime(2026, 8, 23, 3, 30),
        )

    with pytest.raises(PositionReportingHierarchyError, match="exact built-in datetime"):
        build_position_reporting_snapshot(
            [],
            visible_positions(),
            tenant_record_id=TENANT_ALPHA,
            effective_on=EFFECTIVE_ON,
            known_at=ForgedDateTime(2026, 8, 23, 3, 30, tzinfo=timezone.utc),
        )


def test_relationship_repr_is_redacted() -> None:
    """Routine logs do not expose position-correlation UUIDs."""
    value = relationship(RELATIONSHIP_A, POSITION_B, POSITION_A)
    assert repr(value) == "<PositionReportingRelationship governed position-reporting evidence>"
