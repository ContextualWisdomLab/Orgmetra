"""Assignment command allocation runtime-integrity regressions."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from orgmetra_people_api.mutations import AssignmentMutationCommand


class ForgedCommandAllocationRatio(Decimal):
    """Hide an invalid negative value from overloaded range comparisons."""

    def __le__(self, other: object) -> bool:
        """Pretend the negative value is above the command lower bound."""
        return False

    def __gt__(self, other: object) -> bool:
        """Pretend the negative value is below the command upper bound."""
        return False


def test_assignment_command_rejects_decimal_subclass_before_numeric_methods() -> None:
    """Executable Decimal subtype behavior must not enter a governed command."""
    with pytest.raises(ValueError, match="Decimal"):
        AssignmentMutationCommand(
            tenant_record_id=UUID("0198a412-8000-7000-8000-000000000001"),
            employment_record_id=UUID("0198a412-8000-7000-8000-000000000030"),
            person_record_id=UUID("0198a412-8000-7000-8000-000000000020"),
            position_record_id=UUID("0198a412-8000-7000-8000-000000000040"),
            assignment_record_id=UUID("0198a412-8000-7000-8000-000000000070"),
            audit_event_record_id=UUID("0198a412-8000-7000-8000-000000000080"),
            outbox_delivery_record_id=UUID("0198a412-8000-7000-8000-000000000081"),
            allocation_ratio=ForgedCommandAllocationRatio("-0.5000"),
            effective_from=date(2026, 8, 18),
            confirmation_reference="human_confirmation:review-88",
            evidence_version_code="decision_evidence_set:v1",
            idempotency_key="idempotency-key-17xx",
            assignment_category_code="primary",
        )
