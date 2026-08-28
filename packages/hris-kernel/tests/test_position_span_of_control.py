"""Regression coverage for PII-minimized Position span-of-control evidence."""

from datetime import date, datetime, timedelta, timezone
import hashlib
from uuid import UUID

import pytest

from orgmetra_hris_kernel.position_reporting import PositionReportingSnapshot
from orgmetra_hris_kernel.span_of_control import (
    PositionSpanOfControlError,
    PositionSpanOfControlSnapshot,
    build_position_span_of_control_snapshot,
)

TENANT = UUID("11111111-1111-4111-8111-111111111111")
MANAGER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1")
DIRECTOR = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2")
REPORT_A = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1")
REPORT_B = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2")
REPORT_C = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb3")
DAY = date(2026, 8, 28)
KNOWN = datetime(2026, 8, 28, 0, 0, tzinfo=timezone.utc)


def reporting_snapshot(
    edges: tuple[tuple[UUID, UUID], ...],
    *,
    tenant: UUID = TENANT,
    effective_on: date = DAY,
    known_at: datetime = KNOWN,
) -> PositionReportingSnapshot:
    """Build one direct parent snapshot fixture without adding Person evidence."""
    return PositionReportingSnapshot(
        tenant_record_id=tenant,
        effective_on=effective_on,
        known_at=known_at,
        manager_by_subordinate=edges,
    )


def test_span_snapshot_counts_direct_reporting_positions_only() -> None:
    """The structural metric counts direct-report Position seats, not workers."""
    snapshot = build_position_span_of_control_snapshot(
        reporting_snapshot(
            (
                (REPORT_A, MANAGER),
                (REPORT_B, MANAGER),
                (REPORT_C, MANAGER),
                (MANAGER, DIRECTOR),
            )
        )
    )

    assert snapshot.manager_position_count == 2
    assert snapshot.reporting_position_count == 4
    assert snapshot.span_by_manager == ((MANAGER, 3), (DIRECTOR, 1))
    assert snapshot.evidence_state == "structural_workforce_evidence"
    assert snapshot.decision_authority == "not_authorized_for_employment_decision"
    assert "person_record_id" not in snapshot.canonical_json()
    assert "assignment_record_id" not in snapshot.canonical_json()
    assert snapshot.content_digest() == hashlib.sha256(snapshot.canonical_json().encode("utf-8")).hexdigest()
    assert repr(snapshot) == "<PositionSpanOfControlSnapshot structural workforce evidence>"


def test_empty_reporting_graph_is_valid_zero_span_evidence() -> None:
    """An organization with no visible reporting edges yields a deterministic zero snapshot."""
    snapshot = build_position_span_of_control_snapshot(reporting_snapshot(()))
    assert snapshot.manager_position_count == 0
    assert snapshot.reporting_position_count == 0
    assert snapshot.span_by_manager == ()


def test_builder_rejects_non_governed_parent_runtime_type() -> None:
    """Caller-defined snapshot-like objects cannot control structural evidence."""
    class SnapshotLike:
        pass

    with pytest.raises(PositionSpanOfControlError, match="exact PositionReportingSnapshot"):
        build_position_span_of_control_snapshot(SnapshotLike())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("snapshot", "message"),
    [
        (reporting_snapshot((), tenant=UUID(int=0)), "tenant_record_id"),
        (reporting_snapshot((), effective_on=datetime(2026, 8, 28).date()), "effective_on"),
        (
            reporting_snapshot((), known_at=datetime(2026, 8, 28, tzinfo=timezone(timedelta(hours=9)))),
            "known_at",
        ),
    ],
)
def test_builder_rejects_noncanonical_parent_coordinates(
    snapshot: PositionReportingSnapshot,
    message: str,
) -> None:
    """Direct parent construction cannot bypass tenant/business/system coordinate integrity."""
    if message == "effective_on":
        class ForgedDate(date):
            pass

        object.__setattr__(snapshot, "effective_on", ForgedDate(2026, 8, 28))
    with pytest.raises(PositionSpanOfControlError, match=message):
        build_position_span_of_control_snapshot(snapshot)


def test_builder_rejects_mutated_edge_container() -> None:
    """Reporting edges must retain the immutable tuple representation emitted by the parent boundary."""
    snapshot = reporting_snapshot(((REPORT_A, MANAGER),))
    object.__setattr__(snapshot, "manager_by_subordinate", [(REPORT_A, MANAGER)])
    with pytest.raises(PositionSpanOfControlError, match="edge collection"):
        build_position_span_of_control_snapshot(snapshot)


def test_builder_rejects_noncanonical_edge_pair() -> None:
    """A caller cannot smuggle list-backed reporting pairs into workforce evidence."""
    snapshot = reporting_snapshot(((REPORT_A, MANAGER),))
    object.__setattr__(snapshot, "manager_by_subordinate", ([REPORT_A, MANAGER],))
    with pytest.raises(PositionSpanOfControlError, match="edge must be an exact two-item tuple"):
        build_position_span_of_control_snapshot(snapshot)


@pytest.mark.parametrize(
    ("edges", "message"),
    [
        (((REPORT_A, MANAGER), (REPORT_A, DIRECTOR)), "duplicate subordinate"),
        (((MANAGER, MANAGER),), "cannot report to itself"),
        (((MANAGER, DIRECTOR), (DIRECTOR, MANAGER)), "cycle"),
        (((UUID(int=0), MANAGER),), "subordinate_position_record_id"),
        (((REPORT_A, UUID(int=(1 << 128) - 1)),), "manager_position_record_id"),
    ],
)
def test_builder_fails_closed_on_forged_reporting_graph(
    edges: tuple[tuple[UUID, UUID], ...],
    message: str,
) -> None:
    """Direct construction of a contradictory parent graph cannot forge span evidence."""
    with pytest.raises(PositionSpanOfControlError, match=message):
        build_position_span_of_control_snapshot(reporting_snapshot(edges))


def test_direct_output_rejects_inconsistent_counts() -> None:
    """Direct output construction cannot claim counts that disagree with the manager spans."""
    with pytest.raises(PositionSpanOfControlError, match="do not reconcile"):
        PositionSpanOfControlSnapshot(
            tenant_record_id=TENANT,
            effective_on=DAY,
            known_at=KNOWN,
            manager_position_count=1,
            reporting_position_count=2,
            span_by_manager=((MANAGER, 1),),
        )


@pytest.mark.parametrize(
    "spans",
    [
        ((MANAGER, 0),),
        ((MANAGER, True),),
        ((DIRECTOR, 1), (MANAGER, 1)),
        ((MANAGER, 1), (MANAGER, 1)),
    ],
)
def test_direct_output_rejects_noncanonical_span_entries(
    spans: tuple[tuple[UUID, int], ...],
) -> None:
    """Manager spans remain positive exact integers in UUID order with one row per manager."""
    with pytest.raises(PositionSpanOfControlError, match="span_by_manager"):
        PositionSpanOfControlSnapshot(
            tenant_record_id=TENANT,
            effective_on=DAY,
            known_at=KNOWN,
            manager_position_count=len(spans),
            reporting_position_count=sum(int(value) for _, value in spans),
            span_by_manager=spans,
        )


@pytest.mark.parametrize(
    ("manager_count", "reporting_count"),
    [(-1, 0), (True, 0), (0, -1), (0, False)],
)
def test_direct_output_rejects_noncanonical_aggregate_counts(
    manager_count: object,
    reporting_count: object,
) -> None:
    """Aggregate count fields remain exact non-negative integers under direct construction."""
    with pytest.raises(PositionSpanOfControlError, match="exact non-negative integers"):
        PositionSpanOfControlSnapshot(
            tenant_record_id=TENANT,
            effective_on=DAY,
            known_at=KNOWN,
            manager_position_count=manager_count,  # type: ignore[arg-type]
            reporting_position_count=reporting_count,  # type: ignore[arg-type]
            span_by_manager=(),
        )


def test_direct_output_rejects_mutable_span_collection() -> None:
    """A mutable top-level span collection cannot become canonical audit evidence."""
    with pytest.raises(PositionSpanOfControlError, match="exact immutable tuple"):
        PositionSpanOfControlSnapshot(
            tenant_record_id=TENANT,
            effective_on=DAY,
            known_at=KNOWN,
            manager_position_count=0,
            reporting_position_count=0,
            span_by_manager=[],  # type: ignore[arg-type]
        )


def test_direct_output_rejects_mutable_span_entry() -> None:
    """A mutable manager/count entry cannot become canonical audit evidence."""
    with pytest.raises(PositionSpanOfControlError, match="entries must be exact two-item tuples"):
        PositionSpanOfControlSnapshot(
            tenant_record_id=TENANT,
            effective_on=DAY,
            known_at=KNOWN,
            manager_position_count=1,
            reporting_position_count=1,
            span_by_manager=([MANAGER, 1],),  # type: ignore[arg-type]
        )
