"""Buyer-visible tests for effective-time and knowledge-time historical resolution."""

from datetime import date, datetime, timezone
import unittest
from uuid import UUID

from orgmetra_domain import (
    BitemporalPeriod,
    InvalidDomainValueError,
    PersonNameRecord,
    TemporalAmbiguityError,
    resolve_bitemporal_fact,
)


PERSON_ID = UUID("00000000-0000-7000-8000-000000000001")
OTHER_PERSON_ID = UUID("00000000-0000-7000-8000-000000000002")
OLD_NAME_ID = UUID("00000000-0000-7000-8000-000000000101")
CORRECTED_NAME_ID = UUID("00000000-0000-7000-8000-000000000102")
AMBIGUOUS_NAME_ID = UUID("00000000-0000-7000-8000-000000000103")


def name_record(
    record_id: UUID,
    display_name: str,
    recorded_from: datetime,
    recorded_to: datetime | None = None,
    *,
    person_id: UUID = PERSON_ID,
) -> PersonNameRecord:
    """Build one versioned name fact for historical-query tests."""

    return PersonNameRecord(
        person_name_record_id=record_id,
        person_record_id=person_id,
        display_name=display_name,
        period=BitemporalPeriod(
            effective_from=date(2026, 1, 1),
            effective_to=None,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
        ),
    )


class BitemporalResolutionTests(unittest.TestCase):
    """Resolve exactly what Orgmetra knew at a business/knowledge coordinate."""

    def test_retroactive_correction_preserves_then_replaces_historical_visibility(self) -> None:
        original = name_record(
            OLD_NAME_ID,
            "Ada Byron",
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        corrected = name_record(
            CORRECTED_NAME_ID,
            "Ada Lovelace",
            datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        history = (original, corrected)

        known_in_january = resolve_bitemporal_fact(
            history,
            identity_of=lambda fact: fact.person_record_id,
            identity=PERSON_ID,
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )
        known_in_february = resolve_bitemporal_fact(
            history,
            identity_of=lambda fact: fact.person_record_id,
            identity=PERSON_ID,
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 2, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(known_in_january, original)
        self.assertEqual(known_in_february, corrected)

    def test_returns_none_when_no_fact_is_visible_at_coordinate(self) -> None:
        value = name_record(
            OLD_NAME_ID,
            "Ada Lovelace",
            datetime(2026, 1, 2, tzinfo=timezone.utc),
        )

        resolved = resolve_bitemporal_fact(
            (value,),
            identity_of=lambda fact: fact.person_record_id,
            identity=PERSON_ID,
            effective_on=date(2025, 12, 31),
            known_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        )

        self.assertIsNone(resolved)

    def test_rejects_naive_knowledge_time(self) -> None:
        with self.assertRaisesRegex(InvalidDomainValueError, "timezone-aware"):
            resolve_bitemporal_fact(
                (),
                identity_of=lambda fact: fact.person_record_id,
                identity=PERSON_ID,
                effective_on=date(2026, 1, 1),
                known_at=datetime(2026, 1, 2),
            )

    def test_ignores_visible_facts_for_other_identities(self) -> None:
        requested = name_record(
            OLD_NAME_ID,
            "Ada Lovelace",
            datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        other = name_record(
            AMBIGUOUS_NAME_ID,
            "Grace Hopper",
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            person_id=OTHER_PERSON_ID,
        )

        resolved = resolve_bitemporal_fact(
            (requested, other),
            identity_of=lambda fact: fact.person_record_id,
            identity=PERSON_ID,
            effective_on=date(2026, 1, 15),
            known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
        )

        self.assertEqual(resolved, requested)

    def test_fails_closed_when_two_facts_are_simultaneously_visible(self) -> None:
        first = name_record(
            OLD_NAME_ID,
            "Ada Byron",
            datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        second = name_record(
            AMBIGUOUS_NAME_ID,
            "Ada Lovelace",
            datetime(2026, 1, 3, tzinfo=timezone.utc),
        )

        with self.assertRaisesRegex(TemporalAmbiguityError, "multiple facts"):
            resolve_bitemporal_fact(
                (first, second),
                identity_of=lambda fact: fact.person_record_id,
                identity=PERSON_ID,
                effective_on=date(2026, 1, 15),
                known_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            )


if __name__ == "__main__":
    unittest.main()
