"""Realistic HRIS cases a buyer uses to correct history and staff people.

These tests describe the kernel a purchaser can sell: retroactive assignment
corrections, identity-scoped historical queries, covering employment, shared
positions, and organization cycles. Run them before changing production code.
"""

from datetime import date, datetime, timedelta, timezone
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
    EmploymentVersionRecord,
    InvalidDomainValueError,
    OrganizationCycleError,
    OrganizationUnitVersionRecord,
    PersonNameRecord,
    PositionAssignmentConflictError,
    TemporalAmbiguityError,
    resolve_bitemporal_fact,
    resolve_bitemporal_facts_by_identity,
    validate_assignment_employment_coverage,
    validate_assignment_portfolio,
    validate_assignment_portfolio_history,
    validate_organization_hierarchy,
)


PERSON_ID = UUID("00000000-0000-7000-8000-000000000001")
OTHER_PERSON_ID = UUID("00000000-0000-7000-8000-000000000002")
EMPLOYMENT_ID = UUID("00000000-0000-7000-8000-000000000003")
OTHER_EMPLOYMENT_ID = UUID("00000000-0000-7000-8000-000000000015")
POSITION_ID = UUID("00000000-0000-7000-8000-000000000004")
OTHER_POSITION_ID = UUID("00000000-0000-7000-8000-000000000005")
ORG_A = UUID("00000000-0000-7000-8000-000000000016")
ORG_B = UUID("00000000-0000-7000-8000-000000000017")
CANDIDATE_ID = UUID("00000000-0000-7000-8000-000000000008")
LINK_ID = UUID("00000000-0000-7000-8000-000000000009")
SEOUL = timezone(timedelta(hours=9))


def _period(
    *,
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = None,
    recorded_from: datetime,
    recorded_to: datetime | None = None,
) -> BitemporalPeriod:
    """Build one half-open bitemporal period for buyer-visible cases."""

    return BitemporalPeriod(
        effective_from=effective_from,
        effective_to=effective_to,
        recorded_from=recorded_from,
        recorded_to=recorded_to,
    )


def _assignment(
    assignment_id: int,
    *,
    person_id: UUID = PERSON_ID,
    employment_id: UUID = EMPLOYMENT_ID,
    position_id: UUID = POSITION_ID,
    allocation: str = "1",
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = None,
    recorded_from: datetime,
    recorded_to: datetime | None = None,
) -> AssignmentRecord:
    """Build one assignment row, including recorded-time bounds."""

    return AssignmentRecord(
        assignment_record_id=UUID(f"00000000-0000-7000-8000-{assignment_id:012d}"),
        person_record_id=person_id,
        employment_record_id=employment_id,
        position_record_id=position_id,
        allocation_ratio=Decimal(allocation),
        period=_period(
            effective_from=effective_from,
            effective_to=effective_to,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
        ),
    )


def _name(
    record_id: int,
    display_name: str,
    *,
    person_id: UUID = PERSON_ID,
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = None,
    recorded_from: datetime,
    recorded_to: datetime | None = None,
) -> PersonNameRecord:
    """Build one versioned name, including effective-dated legal changes."""

    return PersonNameRecord(
        person_name_record_id=UUID(f"00000000-0000-7000-8000-{record_id:012d}"),
        person_record_id=person_id,
        display_name=display_name,
        period=_period(
            effective_from=effective_from,
            effective_to=effective_to,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
        ),
    )


class AssignmentRecordedTimeTests(unittest.TestCase):
    """A legal retroactive FTE correction must remain reconstructable."""

    def test_correction_triple_is_valid_after_superseding_the_original_row(self) -> None:
        original = _assignment(
            41,
            allocation="1.0",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
            recorded_to=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        corrected = _assignment(
            42,
            allocation="0.5",
            position_id=POSITION_ID,
            recorded_from=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        concurrent = _assignment(
            43,
            allocation="0.5",
            position_id=OTHER_POSITION_ID,
            recorded_from=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )

        validate_assignment_portfolio(
            (original, corrected, concurrent),
            known_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        validate_assignment_portfolio_history((original, corrected, concurrent))

    def test_open_original_and_correction_still_exceed_allocation(self) -> None:
        original = _assignment(
            44,
            allocation="1.0",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        correction = _assignment(
            45,
            allocation="0.5",
            position_id=OTHER_POSITION_ID,
            recorded_from=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )

        with self.assertRaises(AllocationExceededError):
            validate_assignment_portfolio(
                (original, correction),
                known_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            )

    def test_rejects_naive_portfolio_knowledge_time(self) -> None:
        with self.assertRaisesRegex(InvalidDomainValueError, "timezone-aware"):
            validate_assignment_portfolio((), known_at=datetime(2026, 3, 1))

    def test_rejects_ratio_that_cannot_persist_as_numeric_five_four(self) -> None:
        with self.assertRaisesRegex(InvalidDomainValueError, "four decimal"):
            _assignment(
                46,
                allocation="0.00001",
                recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )


class AssignmentEmploymentAndPositionTests(unittest.TestCase):
    """Assignments belong to one employment and one seat with capacity one."""

    def test_assignment_requires_covering_employment_for_the_same_person(self) -> None:
        assignment = _assignment(
            51,
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        employment = EmploymentRecord(EMPLOYMENT_ID, PERSON_ID)
        version = EmploymentVersionRecord(
            UUID("00000000-0000-7000-8000-000000000018"),
            EMPLOYMENT_ID,
            "active",
            _period(recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc)),
        )

        validate_assignment_employment_coverage(
            assignment,
            (employment,),
            (version,),
            known_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )

    def test_rejects_assignment_without_covering_employment(self) -> None:
        assignment = _assignment(
            52,
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        employment = EmploymentRecord(OTHER_EMPLOYMENT_ID, PERSON_ID)
        version = EmploymentVersionRecord(
            UUID("00000000-0000-7000-8000-000000000019"),
            OTHER_EMPLOYMENT_ID,
            "active",
            _period(recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc)),
        )

        with self.assertRaisesRegex(InvalidDomainValueError, "covering employment"):
            validate_assignment_employment_coverage(
                assignment,
                (employment,),
                (version,),
                known_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            )

    def test_concurrent_employments_keep_assignments_on_the_named_relationship(self) -> None:
        first = _assignment(
            53,
            employment_id=EMPLOYMENT_ID,
            position_id=POSITION_ID,
            allocation="0.5",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        second = _assignment(
            54,
            employment_id=OTHER_EMPLOYMENT_ID,
            position_id=OTHER_POSITION_ID,
            allocation="0.5",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        validate_assignment_portfolio(
            (first, second),
            known_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(first.employment_record_id, EMPLOYMENT_ID)
        self.assertEqual(second.employment_record_id, OTHER_EMPLOYMENT_ID)

    def test_job_share_on_one_position_is_accepted_at_capacity_one(self) -> None:
        first = _assignment(
            55,
            person_id=PERSON_ID,
            allocation="0.5",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        second = _assignment(
            56,
            person_id=OTHER_PERSON_ID,
            employment_id=OTHER_EMPLOYMENT_ID,
            allocation="0.5",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        validate_assignment_portfolio(
            (first, second),
            known_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )

    def test_rejects_two_full_assignments_to_the_same_position(self) -> None:
        first = _assignment(
            57,
            person_id=PERSON_ID,
            allocation="1",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        second = _assignment(
            58,
            person_id=OTHER_PERSON_ID,
            employment_id=OTHER_EMPLOYMENT_ID,
            allocation="1",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        with self.assertRaises(PositionAssignmentConflictError):
            validate_assignment_portfolio(
                (first, second),
                known_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            )


class IdentityScopedResolutionTests(unittest.TestCase):
    """Historical queries must not treat two people as one ambiguous fact."""

    def test_mixed_identities_resolve_each_visible_name(self) -> None:
        ada = _name(
            61,
            "Ada Lovelace",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        alan = _name(
            62,
            "Alan Turing",
            person_id=OTHER_PERSON_ID,
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )

        resolved = resolve_bitemporal_facts_by_identity(
            (ada, alan),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            identity_of=lambda fact: fact.person_record_id,
        )

        self.assertEqual(resolved[PERSON_ID], ada)
        self.assertEqual(resolved[OTHER_PERSON_ID], alan)

    def test_single_fact_helper_rejects_mixed_identities(self) -> None:
        ada = _name(
            63,
            "Ada Lovelace",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        alan = _name(
            64,
            "Alan Turing",
            person_id=OTHER_PERSON_ID,
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        with self.assertRaisesRegex(InvalidDomainValueError, "one identity"):
            resolve_bitemporal_fact(
                (ada, alan),
                effective_on=date(2026, 1, 15),
                known_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                identity_of=lambda fact: fact.person_record_id,
            )

    def test_ambiguity_names_the_next_action_for_one_identity(self) -> None:
        first = _name(
            65,
            "Ada Byron",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        second = _name(
            66,
            "Ada Lovelace",
            recorded_from=datetime(2026, 1, 3, tzinfo=timezone.utc),
        )
        with self.assertRaisesRegex(TemporalAmbiguityError, "close the superseded"):
            resolve_bitemporal_fact(
                (first, second),
                effective_on=date(2026, 1, 15),
                known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
                identity_of=lambda fact: fact.person_record_id,
            )

    def test_legal_name_change_is_effective_dated_not_only_corrected(self) -> None:
        maiden = _name(
            67,
            "Ada Byron",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 6, 1),
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        married = _name(
            68,
            "Ada Lovelace",
            effective_from=date(2026, 6, 1),
            recorded_from=datetime(2026, 5, 15, tzinfo=timezone.utc),
        )
        before_change = resolve_bitemporal_fact(
            (maiden, married),
            effective_on=date(2026, 5, 31),
            known_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
            identity_of=lambda fact: fact.person_record_id,
        )
        after_change = resolve_bitemporal_fact(
            (maiden, married),
            effective_on=date(2026, 6, 1),
            known_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
            identity_of=lambda fact: fact.person_record_id,
        )
        self.assertEqual(before_change, maiden)
        self.assertEqual(after_change, married)

    def test_recorded_to_boundary_hides_the_closed_row(self) -> None:
        closed = _name(
            69,
            "Ada Byron",
            recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
            recorded_to=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        resolved = resolve_bitemporal_fact(
            (closed,),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            identity_of=lambda fact: fact.person_record_id,
        )
        self.assertIsNone(resolved)

    def test_seoul_knowledge_time_matches_equivalent_utc_instant(self) -> None:
        value = _name(
            70,
            "Ada Lovelace",
            recorded_from=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
        )
        resolved = resolve_bitemporal_fact(
            (value,),
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 2, 9, 0, tzinfo=SEOUL),
            identity_of=lambda fact: fact.person_record_id,
        )
        self.assertEqual(resolved, value)


class OrganizationCycleTests(unittest.TestCase):
    """Immediate self-parent is not enough; A→B→A must fail closed."""

    def test_rejects_visible_organization_cycle(self) -> None:
        unit_a = OrganizationUnitVersionRecord(
            UUID("00000000-0000-7000-8000-000000000071"),
            ORG_A,
            "Platform",
            "department",
            _period(recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc)),
            parent_organization_unit_id=ORG_B,
        )
        unit_b = OrganizationUnitVersionRecord(
            UUID("00000000-0000-7000-8000-000000000072"),
            ORG_B,
            "Product",
            "department",
            _period(recorded_from=datetime(2026, 1, 2, tzinfo=timezone.utc)),
            parent_organization_unit_id=ORG_A,
        )
        with self.assertRaises(OrganizationCycleError):
            validate_organization_hierarchy(
                (unit_a, unit_b),
                effective_on=date(2026, 1, 15),
                known_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            )


class CandidateRelinkLeakageTests(unittest.TestCase):
    """Adapter-crossing errors must not embed HR identifiers."""

    def test_relink_error_omits_candidate_and_person_identifiers(self) -> None:
        registry = CandidateWorkerRegistry()
        registry.register(CandidateWorkerLink(LINK_ID, CANDIDATE_ID, PERSON_ID))
        with self.assertRaises(CandidateWorkerRelinkError) as captured:
            registry.register(
                CandidateWorkerLink(
                    UUID("00000000-0000-7000-8000-000000000010"),
                    CANDIDATE_ID,
                    OTHER_PERSON_ID,
                )
            )
        message = str(captured.exception)
        self.assertEqual(message, "candidate is already linked to a different person")
        self.assertNotIn(str(CANDIDATE_ID), message)
        self.assertNotIn(str(PERSON_ID), message)
        self.assertNotIn(str(OTHER_PERSON_ID), message)


if __name__ == "__main__":
    unittest.main()
