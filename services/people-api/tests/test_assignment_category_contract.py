"""Regression contract for explicit, non-heuristic assignment classification."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_hris_kernel import (
    AssignmentFact,
    AssignmentPortfolioError,
    DateInterval,
    RecordedInterval,
    validate_assignment_portfolio,
)
from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.mutations import AssignmentMutationCommand, mutation_command_digest

TENANT = UUID("0199a412-9200-7000-8000-000000000001")
PERSON = UUID("0199a412-9200-7000-8000-000000000002")
EMPLOYMENT = UUID("0199a412-9200-7000-8000-000000000003")
PRIMARY_POSITION = UUID("0199a412-9200-7000-8000-000000000004")
SECONDARY_POSITION = UUID("0199a412-9200-7000-8000-000000000005")
ASSIGNMENT_A = UUID("0199a412-9200-7000-8000-000000000006")
ASSIGNMENT_B = UUID("0199a412-9200-7000-8000-000000000007")
AUDIT = UUID("0199a412-9200-7000-8000-000000000008")
OUTBOX = UUID("0199a412-9200-7000-8000-000000000009")
KNOWN_AT = datetime(2026, 9, 2, 5, 0, tzinfo=timezone.utc)


class ForgedAssignmentCategory(str):
    """Spoof governed membership while retaining different serialized text."""

    def __hash__(self) -> int:
        return hash("primary")

    def __eq__(self, other: object) -> bool:
        return other == "primary"


def assignment_fact(*, assignment_id: UUID, position_id: UUID, category: str) -> AssignmentFact:
    """Build one visible assignment with an explicit classification code."""
    return AssignmentFact(
        tenant_record_id=TENANT,
        assignment_record_id=assignment_id,
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        position_record_id=position_id,
        allocation_ratio=Decimal("0.5000"),
        effective=DateInterval(date(2026, 9, 1)),
        recorded=RecordedInterval(KNOWN_AT),
        assignment_category_code=category,
    )


def assignment_command(*, category: str) -> AssignmentMutationCommand:
    """Build one governed assignment command with an explicit classification code."""
    return AssignmentMutationCommand(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        position_record_id=PRIMARY_POSITION,
        assignment_record_id=ASSIGNMENT_A,
        audit_event_record_id=AUDIT,
        outbox_delivery_record_id=OUTBOX,
        allocation_ratio=Decimal("1.0000"),
        effective_from=date(2026, 9, 1),
        confirmation_reference="human_confirmation:assignment-162",
        evidence_version_code="assignment-evidence-v1",
        idempotency_key="assignment-category-contract-162",
        assignment_category_code=category,
    )


def authorization() -> AuthorizationDecision:
    """Return exact allow evidence used only to prove idempotency semantics."""
    fields = frozenset({"assignment_record"})
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-162",
        resource_reference=f"assignment_record:{ASSIGNMENT_A.hex}",
        policy_version_code="assignment-policy-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="assignment_record",
        requested_fields=fields,
        authorized_fields=fields,
        reason_code="allowed",
        next_action="Continue with only the authorized fields.",
    )


class AssignmentCategoryContractTests(unittest.TestCase):
    """Keep assignment semantics explicit instead of inferring them from allocation or order."""

    def test_portfolio_allows_one_primary_plus_explicit_secondary(self) -> None:
        assignments = [
            assignment_fact(assignment_id=ASSIGNMENT_A, position_id=PRIMARY_POSITION, category="primary"),
            assignment_fact(
                assignment_id=ASSIGNMENT_B,
                position_id=SECONDARY_POSITION,
                category="concurrent_secondary",
            ),
        ]

        visible = validate_assignment_portfolio(
            assignments,
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 9, 2),
            known_at=KNOWN_AT,
        )

        self.assertEqual([fact.assignment_category_code for fact in visible], ["primary", "concurrent_secondary"])

    def test_portfolio_rejects_two_visible_primary_assignments(self) -> None:
        assignments = [
            assignment_fact(assignment_id=ASSIGNMENT_A, position_id=PRIMARY_POSITION, category="primary"),
            assignment_fact(assignment_id=ASSIGNMENT_B, position_id=SECONDARY_POSITION, category="primary"),
        ]

        with self.assertRaisesRegex(AssignmentPortfolioError, "primary"):
            validate_assignment_portfolio(
                assignments,
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                employment_record_id=EMPLOYMENT,
                effective_on=date(2026, 9, 2),
                known_at=KNOWN_AT,
            )

    def test_legacy_unspecified_is_preserved_without_heuristic_classification(self) -> None:
        historical = assignment_fact(
            assignment_id=ASSIGNMENT_A,
            position_id=PRIMARY_POSITION,
            category="legacy_unspecified",
        )

        visible = validate_assignment_portfolio(
            [historical],
            tenant_record_id=TENANT,
            person_record_id=PERSON,
            employment_record_id=EMPLOYMENT,
            effective_on=date(2026, 9, 2),
            known_at=KNOWN_AT,
        )

        self.assertEqual(visible[0].assignment_category_code, "legacy_unspecified")

    def test_portfolio_rejects_category_string_subclass_spoofing(self) -> None:
        forged = ForgedAssignmentCategory("not_a_governed_category")
        self.assertEqual(forged, "primary")

        with self.assertRaisesRegex(AssignmentPortfolioError, "assignment_category_code"):
            validate_assignment_portfolio(
                [
                    assignment_fact(
                        assignment_id=ASSIGNMENT_A,
                        position_id=PRIMARY_POSITION,
                        category=forged,
                    )
                ],
                tenant_record_id=TENANT,
                person_record_id=PERSON,
                employment_record_id=EMPLOYMENT,
                effective_on=date(2026, 9, 2),
                known_at=KNOWN_AT,
            )

    def test_new_write_requires_primary_or_concurrent_secondary(self) -> None:
        self.assertEqual(assignment_command(category="primary").assignment_category_code, "primary")
        self.assertEqual(
            assignment_command(category="concurrent_secondary").assignment_category_code,
            "concurrent_secondary",
        )
        for invalid in ("legacy_unspecified", "secondary", "", "primary_assignment", None):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "assignment_category_code"):
                assignment_command(category=invalid)  # type: ignore[arg-type]

    def test_new_write_rejects_category_string_subclass_spoofing(self) -> None:
        forged = ForgedAssignmentCategory("legacy_unspecified")
        self.assertEqual(forged, "primary")

        with self.assertRaisesRegex(ValueError, "assignment_category_code"):
            assignment_command(category=forged)

    def test_idempotency_digest_includes_assignment_category(self) -> None:
        primary = mutation_command_digest(command=assignment_command(category="primary"), authorization=authorization())
        secondary = mutation_command_digest(
            command=assignment_command(category="concurrent_secondary"),
            authorization=authorization(),
        )

        self.assertNotEqual(primary, secondary)


if __name__ == "__main__":
    unittest.main()
