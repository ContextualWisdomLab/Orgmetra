"""Adversarial runtime-integrity regressions for Naruon calendar intents."""

from __future__ import annotations

import pytest

from orgmetra_naruon_adapter import (
    CalendarIntentContext,
    ContractViolation,
    build_calendar_intent,
)

TENANT_ID = "11111111-1111-4111-8111-111111111111"
PERSON_ID = "22222222-2222-4222-8222-222222222222"


class ForgedActionKind(str):
    """Pretend an unreviewed action key equals the reviewed performance action."""

    def __hash__(self) -> int:
        """Collide with the reviewed action key in the action-summary mapping."""
        return hash("performance_review")

    def __eq__(self, other: object) -> bool:
        """Claim equality with the reviewed action while retaining other text."""
        return other == "performance_review"


class ForgedResourceReference(str):
    """Return a safe-looking split while retaining an unreviewed raw reference."""

    def count(self, sub: str, *args: int) -> int:
        """Pretend the raw value has exactly one namespace separator."""
        if sub == ":":
            return 1
        return super().count(sub, *args)

    def split(self, sep: str | None = None, maxsplit: int = -1) -> list[str]:
        """Present a reviewed resource pair regardless of the stored raw text."""
        if sep == ":" and maxsplit == 1:
            return ["person_record", PERSON_ID]
        return super().split(sep, maxsplit)


class DerivedCalendarIntentContext(CalendarIntentContext):
    """Represent a validation-bypassing subclass of the governed context."""


def valid_context(**changes: object) -> CalendarIntentContext:
    """Build one valid governed context with optional adversarial overrides."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT_ID,
        "resource_reference": f"person_record:{PERSON_ID}",
        "actor_reference": "keyverse_subject:hr-manager-7",
        "purpose_code": "workforce_scheduling",
        "reason_code": "manager_confirmed_reminder",
        "evidence_version": "policy-v3",
        "action_kind": "performance_review",
        "human_confirmed": True,
        "target_source_id": "caldav-source-7",
    }
    values.update(changes)
    return CalendarIntentContext(**values)  # type: ignore[arg-type]


def test_rejects_action_kind_string_subclass_that_forges_reviewed_allowlist() -> None:
    """Reject an unknown underlying action even when equality/hash are forged."""
    forged = ForgedActionKind("shadow_rejection")

    with pytest.raises(ContractViolation, match="action kind"):
        build_calendar_intent(valid_context(action_kind=forged))


def test_rejects_resource_reference_string_subclass_before_audit_correlation() -> None:
    """Reject a subclass that can validate one resource but retain another value."""
    forged = ForgedResourceReference("external_secret:customer@example.invalid")

    with pytest.raises(ContractViolation, match="resource_reference"):
        build_calendar_intent(valid_context(resource_reference=forged))


def test_rejects_calendar_context_subclasses_at_the_governance_boundary() -> None:
    """Reject subclass instances that can bypass frozen dataclass construction rules."""
    base = valid_context()
    derived = DerivedCalendarIntentContext(
        tenant_record_id=base.tenant_record_id,
        resource_reference=base.resource_reference,
        actor_reference=base.actor_reference,
        purpose_code=base.purpose_code,
        reason_code=base.reason_code,
        evidence_version=base.evidence_version,
        action_kind=base.action_kind,
        human_confirmed=base.human_confirmed,
        target_source_id=base.target_source_id,
    )

    with pytest.raises(ContractViolation, match="governed context type"):
        build_calendar_intent(derived)
