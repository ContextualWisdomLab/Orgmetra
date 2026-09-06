"""PII-minimized structural span-of-control evidence for Position reporting.

This module counts direct-report Position seats from one governed bitemporal
``PositionReportingSnapshot``. It never counts workers, infers a supervisor from
Person or Assignment, recommends an ideal span, or grants employment-decision
authority. The output is descriptive organization-design evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import hashlib
import json
from uuid import UUID

from orgmetra_hris_kernel.errors import KernelError
from orgmetra_hris_kernel.position_reporting import PositionReportingSnapshot

_EVIDENCE_STATE = "structural_workforce_evidence"
_DECISION_AUTHORITY = "not_authorized_for_employment_decision"
_SCHEMA_VERSION = "orgmetra.position_span_of_control.v1"


class PositionSpanOfControlError(KernelError):
    """Span-of-control evidence is malformed or contradicts its reporting graph."""


def _raise(message: str, next_action: str) -> None:
    """Raise one consistent fail-closed structural-evidence error."""
    raise PositionSpanOfControlError(message, next_action=next_action)


def _require_uuid(value: UUID, field_name: str) -> None:
    """Require one exact non-sentinel opaque UUID."""
    if type(value) is not UUID or value.int in (0, (1 << 128) - 1):
        _raise(
            f"{field_name} must be an exact non-sentinel UUID.",
            "Re-resolve the governed Position reporting evidence, then rebuild the span snapshot.",
        )


def _require_business_date(value: date) -> None:
    """Require an exact built-in business date."""
    if type(value) is not date:
        _raise(
            "effective_on must be an exact built-in date.",
            "Use the authoritative HR business date, then rebuild the span snapshot.",
        )


def _require_utc_knowledge_time(value: datetime) -> None:
    """Require the detached built-in UTC instant emitted by the reporting boundary."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        _raise(
            "known_at must be the exact built-in UTC system-knowledge instant from Position reporting.",
            "Rebuild the Position reporting snapshot at the authoritative system-knowledge cutoff.",
        )


def _validated_graph(
    snapshot: PositionReportingSnapshot,
) -> tuple[tuple[UUID, UUID], ...]:
    """Revalidate direct-construction-resistant subordinate-to-manager edges."""
    edges = snapshot.manager_by_subordinate
    if type(edges) is not tuple:
        _raise(
            "Position reporting edge collection must be an exact immutable tuple.",
            "Rebuild the Position reporting snapshot through the governed parent boundary.",
        )

    manager_by_subordinate: dict[UUID, UUID] = {}
    for edge in edges:
        if type(edge) is not tuple or len(edge) != 2:
            _raise(
                "Each Position reporting edge must be an exact two-item tuple.",
                "Rebuild the Position reporting snapshot through the governed parent boundary.",
            )
        subordinate, manager = edge
        _require_uuid(subordinate, "subordinate_position_record_id")
        _require_uuid(manager, "manager_position_record_id")
        if subordinate == manager:
            _raise(
                "A Position cannot report to itself in span-of-control evidence.",
                "Correct the reporting relationship, then rebuild the span snapshot.",
            )
        if subordinate in manager_by_subordinate:
            _raise(
                "Position span-of-control evidence contains a duplicate subordinate.",
                "Resolve the single visible solid-line manager, then rebuild the span snapshot.",
            )
        manager_by_subordinate[subordinate] = manager

    for start in manager_by_subordinate:
        seen: set[UUID] = set()
        current: UUID | None = start
        while current is not None:
            if current in seen:
                _raise(
                    "Position span-of-control evidence contains a reporting cycle.",
                    "Correct one reporting relationship in the cycle, then rebuild the span snapshot.",
                )
            seen.add(current)
            current = manager_by_subordinate.get(current)

    return tuple(manager_by_subordinate.items())


@dataclass(frozen=True, slots=True, repr=False)
class PositionSpanOfControlSnapshot:
    """Deterministic direct-report Position counts at one business/system coordinate."""

    tenant_record_id: UUID
    effective_on: date
    known_at: datetime
    manager_position_count: int
    reporting_position_count: int
    span_by_manager: tuple[tuple[UUID, int], ...]
    evidence_state: str = field(init=False, default=_EVIDENCE_STATE)
    decision_authority: str = field(init=False, default=_DECISION_AUTHORITY)

    def __post_init__(self) -> None:
        """Reject contradictory or caller-forged structural output evidence."""
        _require_uuid(self.tenant_record_id, "tenant_record_id")
        _require_business_date(self.effective_on)
        _require_utc_knowledge_time(self.known_at)
        if (
            type(self.manager_position_count) is not int
            or self.manager_position_count < 0
            or type(self.reporting_position_count) is not int
            or self.reporting_position_count < 0
        ):
            _raise(
                "Position span-of-control counts must be exact non-negative integers.",
                "Rebuild the snapshot from governed Position reporting evidence.",
            )
        if type(self.span_by_manager) is not tuple:
            _raise(
                "span_by_manager must be an exact immutable tuple.",
                "Rebuild the snapshot from governed Position reporting evidence.",
            )

        previous_manager_int = -1
        direct_report_total = 0
        for entry in self.span_by_manager:
            if type(entry) is not tuple or len(entry) != 2:
                _raise(
                    "span_by_manager entries must be exact two-item tuples.",
                    "Rebuild the snapshot from governed Position reporting evidence.",
                )
            manager, direct_report_count = entry
            _require_uuid(manager, "manager_position_record_id")
            if type(direct_report_count) is not int or direct_report_count <= 0:
                _raise(
                    "span_by_manager counts must be positive exact integers.",
                    "Rebuild the snapshot from governed Position reporting evidence.",
                )
            if manager.int <= previous_manager_int:
                _raise(
                    "span_by_manager must contain one manager per row in ascending UUID order.",
                    "Rebuild the snapshot from governed Position reporting evidence.",
                )
            previous_manager_int = manager.int
            direct_report_total += direct_report_count

        if (
            self.manager_position_count != len(self.span_by_manager)
            or self.reporting_position_count != direct_report_total
        ):
            _raise(
                "Position span-of-control counts do not reconcile with span_by_manager.",
                "Rebuild the snapshot from one consistent Position reporting graph.",
            )

    def __repr__(self) -> str:
        """Keep opaque Position identifiers out of routine logs."""
        return "<PositionSpanOfControlSnapshot structural workforce evidence>"

    def canonical_json(self) -> str:
        """Return deterministic value-minimized evidence for audit correlation."""
        payload = {
            "decision_authority": self.decision_authority,
            "effective_on": self.effective_on.isoformat(),
            "evidence_state": self.evidence_state,
            "known_at": self.known_at.isoformat().replace("+00:00", "Z"),
            "manager_position_count": self.manager_position_count,
            "reporting_position_count": self.reporting_position_count,
            "schema_version": _SCHEMA_VERSION,
            "span_by_manager": [
                {
                    "direct_report_position_count": direct_report_count,
                    "manager_position_record_id": str(manager),
                }
                for manager, direct_report_count in self.span_by_manager
            ],
            "tenant_record_id": str(self.tenant_record_id),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def content_digest(self) -> str:
        """Return SHA-256 over the exact canonical UTF-8 evidence bytes."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_position_span_of_control_snapshot(
    reporting_snapshot: PositionReportingSnapshot,
) -> PositionSpanOfControlSnapshot:
    """Count direct-report Position seats from one governed reporting snapshot.

    The metric is deliberately structural. It counts subordinate Position seats
    per manager Position and does not interpret the result as an optimal span,
    a worker-performance signal, or a staffing recommendation.
    """
    if type(reporting_snapshot) is not PositionReportingSnapshot:
        _raise(
            "Position span-of-control requires the exact PositionReportingSnapshot runtime type.",
            "Build the Position reporting snapshot through the governed HRIS kernel boundary first.",
        )
    _require_uuid(reporting_snapshot.tenant_record_id, "tenant_record_id")
    _require_business_date(reporting_snapshot.effective_on)
    _require_utc_knowledge_time(reporting_snapshot.known_at)
    edges = _validated_graph(reporting_snapshot)

    direct_reports_by_manager: dict[UUID, int] = {}
    for _subordinate, manager in edges:
        direct_reports_by_manager[manager] = direct_reports_by_manager.get(manager, 0) + 1

    spans = tuple(sorted(direct_reports_by_manager.items(), key=lambda item: item[0].int))
    return PositionSpanOfControlSnapshot(
        tenant_record_id=reporting_snapshot.tenant_record_id,
        effective_on=reporting_snapshot.effective_on,
        known_at=reporting_snapshot.known_at,
        manager_position_count=len(spans),
        reporting_position_count=len(edges),
        span_by_manager=spans,
    )
