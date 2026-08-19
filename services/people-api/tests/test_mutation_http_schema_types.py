"""Regression contracts for exact OpenAPI scalar types and bounds on People mutations."""

from __future__ import annotations

import unittest
from collections.abc import Callable
from uuid import UUID

from orgmetra_people_api.mutation_http import _command_for_route

TENANT = UUID("0198a412-8100-7000-8000-000000000001")
PERSON = UUID("0198a412-8100-7000-8000-000000000020")
_GENERATED_IDS = tuple(
    UUID(value)
    for value in (
        "0198a412-8100-7000-8000-000000000030",
        "0198a412-8100-7000-8000-000000000031",
        "0198a412-8100-7000-8000-000000000080",
        "0198a412-8100-7000-8000-000000000081",
    )
)


def id_factory() -> Callable[[], UUID]:
    """Return a fresh deterministic UUID supplier for one command-mapping case."""
    values = iter(_GENERATED_IDS)
    return lambda: next(values)


def employment_payload(**overrides: object) -> dict[str, object]:
    """Return one canonical employment request payload with optional field overrides."""
    payload: dict[str, object] = {
        "person_record_id": str(PERSON),
        "employment_status_code": "active",
        "employment_concurrency_code": "exclusive",
        "effective_from": "2026-08-18",
        "decision_reason": "Confirmed hire requires an exclusive employment record.",
        "confirmation_reference": "human_confirmation:review-88",
        "evidence_references": [
            {"evidence_reference": "decision:17", "evidence_version_code": "v1"}
        ],
    }
    payload.update(overrides)
    return payload


class PeopleMutationSchemaTypeTests(unittest.TestCase):
    """Reject JSON values that violate the exact published mutation schema."""

    def test_integer_basic_iso_date_is_not_coerced_to_openapi_string_date(self) -> None:
        """An integer YYYYMMDD must not cross the HTTP command boundary as a date string."""
        with self.assertRaisesRegex(ValueError, "effective_from"):
            _command_for_route(
                "employment-records",
                TENANT,
                employment_payload(effective_from=20260818),
                id_factory(),
                "idempotency-key-17xx",
            )

    def test_decision_reason_above_openapi_maximum_is_rejected(self) -> None:
        """Decision rationale must stay within the published 4000-character bound."""
        with self.assertRaisesRegex(ValueError, "decision_reason"):
            _command_for_route(
                "employment-records",
                TENANT,
                employment_payload(decision_reason="r" * 4001),
                id_factory(),
                "idempotency-key-17xx",
            )

    def test_confirmation_reference_above_openapi_maximum_is_rejected(self) -> None:
        """Human-confirmation references must stay within the published 300-character bound."""
        overlong_reference = "human_confirmation:" + ("a" * (301 - len("human_confirmation:")))
        self.assertEqual(len(overlong_reference), 301)
        with self.assertRaisesRegex(ValueError, "confirmation_reference"):
            _command_for_route(
                "employment-records",
                TENANT,
                employment_payload(confirmation_reference=overlong_reference),
                id_factory(),
                "idempotency-key-17xx",
            )


if __name__ == "__main__":
    unittest.main()
