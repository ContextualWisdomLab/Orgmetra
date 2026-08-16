"""Behavioral tests for Orgmetra's bitemporal people-domain invariants."""

from datetime import date, datetime, timezone
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_domain import (
    AllocationExceededError,
    AssignmentRecord,
    BitemporalPeriod,
    CandidateWorkerLink,
    CandidateWorkerRegistry,
    CandidateWorkerRelinkError,
    EmploymentRecord,
    InvalidDomainValueError,
    PersonNameRecord,
    PersonRecord,
    PositionRecord,
    validate_assignment_portfolio,
)


PERSON_ID = UUID("00000000-0000-7000-8000-000000000001")
OTHER_PERSON_ID = UUID("00000000-0000-7000-8000-000000000002")
EMPLOYMENT_ID = UUID("00000000-0000-7000-8000-000000000003")
POSITION_ID = UUID("00000000-0000-7000-8000-000000000004")
OTHER_POSITION_ID = UUID("00000000-0000-7000-8000-000000000005")
ORG_ID = UUID("00000000-0000-7000-8000-000000000006")
JOB_ID = UUID("00000000-0000-7000-8000-000000000007")
CANDIDATE_ID = UUID("00000000-0000-7000-8000-000000000008")
LINK_ID = UUID("00000000-0000-7000-8000-000000000009")
PERSON_NAME_ID = UUID("00000000-0000-7000-8000-000000000011")


def period(
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = None,
    recorded_from: datetime = datetime(2026, 1, 2, tzinfo=timezone.utc),
    recorded_to: datetime | None = None,
) -> BitemporalPeriod:
    """Create a valid period for focused tests."""

    return BitemporalPeriod(
        effective_from=effective_from,
        effective_to=effective_to,
        recorded_from=recorded_from,
        recorded_to=recorded_to,
    )


class BitemporalPeriodTests(unittest.TestCase):
    """Verify effective-time and system-time semantics."""

    def test_rejects_non_increasing_effective_interval(self) -> None:
        with self.assertRaisesRegex(InvalidDomainValueError, "effective_to"):
            period(effective_to=date(2026, 1, 1))

    def test_rejects_non_increasing_recorded_interval(self) -> None:
        with self.assertRaisesRegex(InvalidDomainValueError, "recorded_to"):
            period(recorded_to=datetime(2026, 1, 2, tzinfo=timezone.utc))

    def test_rejects_naive_recorded_time(self) -> None:
        with self.assertRaisesRegex(InvalidDomainValueError, "timezone-aware"):
            period(recorded_from=datetime(2026, 1, 2))

    def test_half_open_effective_and_recorded_queries(self) -> None:
        value = period(
            effective_to=date(2026, 2, 1),
            recorded_to=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        self.assertTrue(value.is_effective_on(date(2026, 1, 1)))
        self.assertFalse(value.is_effective_on(date(2026, 2, 1)))
        self.assertTrue(value.was_known_at(datetime(2026, 2, 1, tzinfo=timezone.utc)))
        self.assertFalse(value.was_known_at(datetime(2026, 3, 1, tzinfo=timezone.utc)))

    def test_open_intervals_remain_visible(self) -> None:
        value = period()
        self.assertTrue(value.is_effective_on(date(2099, 1, 1)))
        self.assertTrue(value.was_known_at(datetime(2099, 1, 1, tzinfo=timezone.utc)))


class RecordValidationTests(unittest.TestCase):
    """Verify beginner-visible validation at aggregate construction."""

    def test_person_anchor_has_no_mutable_descriptive_attributes(self) -> None:
        person = PersonRecord(PERSON_ID)
        self.assertEqual(person.person_record_id, PERSON_ID)
        self.assertFalse(hasattr(person, "display_name"))
        self.assertFalse(hasattr(person, "period"))

    def test_person_name_requires_visible_name(self) -> None:
        with self.assertRaisesRegex(InvalidDomainValueError, "display_name"):
            PersonNameRecord(PERSON_NAME_ID, PERSON_ID, "   ", period())

    def test_employment_requires_status_code(self) -> None:
        with self.assertRaisesRegex(InvalidDomainValueError, "employment_status_code"):
            EmploymentRecord(EMPLOYMENT_ID, PERSON_ID, "", period())

    def test_position_requires_status_code(self) -> None:
        with self.assertRaisesRegex(InvalidDomainValueError, "position_status_code"):
            PositionRecord(POSITION_ID, ORG_ID, JOB_ID, "  ", period())

    def test_valid_versioned_records_normalize_human_readable_values(self) -> None:
        person_name = PersonNameRecord(
            PERSON_NAME_ID, PERSON_ID, "  Ada Lovelace  ", period()
        )
        employment = EmploymentRecord(
            EMPLOYMENT_ID, PERSON_ID, "  active  ", period()
        )
        position = PositionRecord(
            POSITION_ID, ORG_ID, JOB_ID, "  open  ", period()
        )

        self.assertEqual(person_name.display_name, "Ada Lovelace")
        self.assertEqual(employment.employment_status_code, "active")
        self.assertEqual(position.position_status_code, "open")


class AssignmentPortfolioTests(unittest.TestCase):
    """Verify multiple-membership allocation without atomistic assumptions."""

    def assignment(
        self,
        assignment_id: int,
        person_id: UUID,
        position_id: UUID,
        allocation: str,
        start: date,
        end: date | None,
    ) -> AssignmentRecord:
        """Create one assignment for allocation-boundary tests."""

        return AssignmentRecord(
            assignment_record_id=UUID(
                f"00000000-0000-7000-8000-{assignment_id:012d}"
            ),
            person_record_id=person_id,
            position_record_id=position_id,
            allocation_ratio=Decimal(allocation),
            period=period(effective_from=start, effective_to=end),
        )

    def test_rejects_non_positive_or_excessive_ratio(self) -> None:
        for ratio in ("0", "1.0001", "-0.1"):
            with self.subTest(ratio=ratio), self.assertRaisesRegex(
                InvalidDomainValueError, "allocation_ratio"
            ):
                self.assignment(
                    20, PERSON_ID, POSITION_ID, ratio, date(2026, 1, 1), None
                )

    def test_accepts_multiple_assignments_totalling_one(self) -> None:
        assignments = [
            self.assignment(
                21, PERSON_ID, POSITION_ID, "0.6", date(2026, 1, 1), None
            ),
            self.assignment(
                22, PERSON_ID, OTHER_POSITION_ID, "0.4", date(2026, 2, 1), None
            ),
        ]
        validate_assignment_portfolio(assignments)

    def test_rejects_overallocated_overlap(self) -> None:
        assignments = [
            self.assignment(
                23, PERSON_ID, POSITION_ID, "0.7", date(2026, 1, 1), None
            ),
            self.assignment(
                24, PERSON_ID, OTHER_POSITION_ID, "0.4", date(2026, 2, 1), None
            ),
        ]
        with self.assertRaisesRegex(AllocationExceededError, "1.1"):
            validate_assignment_portfolio(assignments)

    def test_adjacent_periods_do_not_overlap(self) -> None:
        assignments = [
            self.assignment(
                25,
                PERSON_ID,
                POSITION_ID,
                "1",
                date(2026, 1, 1),
                date(2026, 2, 1),
            ),
            self.assignment(
                26,
                PERSON_ID,
                OTHER_POSITION_ID,
                "1",
                date(2026, 2, 1),
                None,
            ),
        ]
        validate_assignment_portfolio(assignments)

    def test_people_are_evaluated_independently(self) -> None:
        assignments = [
            self.assignment(
                27, PERSON_ID, POSITION_ID, "1", date(2026, 1, 1), None
            ),
            self.assignment(
                28,
                OTHER_PERSON_ID,
                OTHER_POSITION_ID,
                "1",
                date(2026, 1, 1),
                None,
            ),
        ]
        validate_assignment_portfolio(assignments)


class CandidateWorkerRegistryTests(unittest.TestCase):
    """Verify append-only candidate-to-worker identity continuity."""

    def test_link_is_idempotent_for_same_candidate_and_person(self) -> None:
        registry = CandidateWorkerRegistry()
        link = CandidateWorkerLink(LINK_ID, CANDIDATE_ID, PERSON_ID)
        self.assertIs(registry.register(link), link)
        self.assertIs(registry.register(link), link)
        self.assertEqual(registry.get(CANDIDATE_ID), link)

    def test_candidate_cannot_be_relinked_to_different_person(self) -> None:
        registry = CandidateWorkerRegistry()
        registry.register(CandidateWorkerLink(LINK_ID, CANDIDATE_ID, PERSON_ID))
        with self.assertRaisesRegex(CandidateWorkerRelinkError, str(CANDIDATE_ID)):
            registry.register(
                CandidateWorkerLink(
                    UUID("00000000-0000-7000-8000-000000000010"),
                    CANDIDATE_ID,
                    OTHER_PERSON_ID,
                )
            )

    def test_unknown_candidate_returns_none(self) -> None:
        registry = CandidateWorkerRegistry()
        self.assertIsNone(registry.get(CANDIDATE_ID))


if __name__ == "__main__":
    unittest.main()
