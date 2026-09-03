"""Build immutable Assignment category corrections and supersession provenance."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from uuid import UUID

from orgmetra_hris_kernel.correction import close_recorded_interval
from orgmetra_hris_kernel.errors import CorrectionError
from orgmetra_hris_kernel.facts import AssignmentFact
from orgmetra_hris_kernel.intervals import RecordedInterval

_EXPLICIT_ASSIGNMENT_CATEGORY_CODES = frozenset({"primary", "concurrent_secondary"})
_MAX_UUID_INT = (1 << 128) - 1


def _require_operational_uuid(value: object, field_name: str) -> UUID:
    """Require exact runtime UUID identity and reject protocol sentinel values."""
    if type(value) is not UUID:
        raise CorrectionError(
            f"{field_name} must be an exact UUID.",
            next_action="Use the authoritative operational UUID assigned to this correction record.",
        )
    if value.int in (0, _MAX_UUID_INT):
        raise CorrectionError(
            f"{field_name} must be an operational UUID, not a reserved sentinel.",
            next_action="Allocate a non-reserved operational UUID and retry the correction.",
        )
    return value


def _require_recorded_at(value: object) -> datetime:
    """Detach one exact system timestamp from caller-controlled timezone behavior."""
    if type(value) is not datetime or value.tzinfo is None:
        raise CorrectionError(
            "recorded_at must be an exact timezone-aware datetime.",
            next_action="Use the database-owned correction timestamp with an explicit UTC offset.",
        )
    try:
        offset = value.utcoffset()
    except Exception as exc:
        raise CorrectionError(
            "recorded_at must expose a stable UTC offset.",
            next_action="Use the database-owned correction timestamp with an explicit UTC offset.",
        ) from exc
    if type(offset) is not timedelta:
        raise CorrectionError(
            "recorded_at must expose a stable UTC offset.",
            next_action="Use the database-owned correction timestamp with an explicit UTC offset.",
        )
    return value.replace(tzinfo=timezone(offset))


@dataclass(frozen=True, slots=True)
class AssignmentSupersessionFact:
    """Link one superseded Assignment fact to its immutable replacement."""

    tenant_record_id: UUID
    assignment_supersession_record_id: UUID
    predecessor_assignment_record_id: UUID
    replacement_assignment_record_id: UUID
    recorded_at: datetime

    def __post_init__(self) -> None:
        """Reject malformed provenance identities and detach its recorded timestamp."""
        for field_name in (
            "tenant_record_id",
            "assignment_supersession_record_id",
            "predecessor_assignment_record_id",
            "replacement_assignment_record_id",
        ):
            _require_operational_uuid(getattr(self, field_name), field_name)
        object.__setattr__(self, "recorded_at", _require_recorded_at(self.recorded_at))
        if self.predecessor_assignment_record_id == self.replacement_assignment_record_id:
            raise CorrectionError(
                "Supersession provenance requires distinct Assignment identities.",
                next_action="Allocate a new replacement Assignment record ID and retry the correction.",
            )


def correct_assignment_category(
    predecessor: AssignmentFact,
    *,
    replacement_assignment_record_id: UUID,
    assignment_supersession_record_id: UUID,
    corrected_category_code: str,
    recorded_at: datetime,
) -> tuple[AssignmentFact, AssignmentFact, AssignmentSupersessionFact]:
    """Close one explicit Assignment fact and create a linked category replacement.

    The replacement preserves tenant, Employment, Person, Position, allocation,
    and effective-time truth. It receives a new Assignment identity and a new
    open recorded interval beginning exactly when the predecessor closes. This
    operation corrects a committed explicit category; classifying historical
    ``legacy_unspecified`` rows remains outside this contract.

    Callers must re-run the Assignment portfolio and Position-capacity invariants
    against locked authoritative state before persisting the three returned facts
    in one transaction.

    Args:
        predecessor: Recorded-open, explicitly classified Assignment being corrected.
        replacement_assignment_record_id: New operational identity for the replacement.
        assignment_supersession_record_id: Identity of the normalized provenance edge.
        corrected_category_code: Exact explicit category chosen by the reviewer.
        recorded_at: System-recorded time shared by closure, replacement, and edge.

    Returns:
        The closed predecessor, open replacement, and normalized supersession fact.

    Raises:
        CorrectionError: The predecessor is not explicitly classified, the
            correction is malformed or a no-op, the identity is reused, or the
            predecessor history cannot be closed.
    """
    if (
        type(predecessor.assignment_category_code) is not str
        or predecessor.assignment_category_code not in _EXPLICIT_ASSIGNMENT_CATEGORY_CODES
    ):
        raise CorrectionError(
            "Predecessor Assignment must have an explicit governed category.",
            next_action=(
                "Use the separately governed historical-classification workflow for "
                "legacy or malformed Assignment facts."
            ),
        )
    if (
        type(corrected_category_code) is not str
        or corrected_category_code not in _EXPLICIT_ASSIGNMENT_CATEGORY_CODES
    ):
        raise CorrectionError(
            "The corrected category must be primary or concurrent_secondary.",
            next_action="Choose the reviewed explicit Assignment category, then save again.",
        )
    if corrected_category_code == predecessor.assignment_category_code:
        raise CorrectionError(
            "Assignment category correction must select a different category.",
            next_action="Keep the existing Assignment when its category is already correct.",
        )

    predecessor_assignment_record_id = _require_operational_uuid(
        predecessor.assignment_record_id,
        "predecessor_assignment_record_id",
    )
    replacement_assignment_record_id = _require_operational_uuid(
        replacement_assignment_record_id,
        "replacement_assignment_record_id",
    )
    assignment_supersession_record_id = _require_operational_uuid(
        assignment_supersession_record_id,
        "assignment_supersession_record_id",
    )
    recorded_at = _require_recorded_at(recorded_at)
    if replacement_assignment_record_id == predecessor_assignment_record_id:
        raise CorrectionError(
            "A category correction requires a new replacement Assignment identity.",
            next_action="Allocate a new Assignment record ID and retry the correction.",
        )

    closed = close_recorded_interval(predecessor, recorded_to=recorded_at)
    replacement = replace(
        predecessor,
        assignment_record_id=replacement_assignment_record_id,
        assignment_category_code=corrected_category_code,
        recorded=RecordedInterval(start=recorded_at),
    )
    supersession = AssignmentSupersessionFact(
        tenant_record_id=predecessor.tenant_record_id,
        assignment_supersession_record_id=assignment_supersession_record_id,
        predecessor_assignment_record_id=predecessor_assignment_record_id,
        replacement_assignment_record_id=replacement_assignment_record_id,
        recorded_at=recorded_at,
    )
    return closed, replacement, supersession
