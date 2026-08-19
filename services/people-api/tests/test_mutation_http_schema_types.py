"""Regression contracts for exact OpenAPI scalar types on People mutations."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_people_api.mutation_http import _command_for_route

TENANT = UUID("0198a412-8100-7000-8000-000000000001")
PERSON = UUID("0198a412-8100-7000-8000-000000000020")
IDS = iter(
    UUID(value)
    for value in (
        "0198a412-8100-7000-8000-000000000030",
        "0198a412-8100-7000-8000-000000000031",
        "0198a412-8100-7000-8000-000000000080",
        "0198a412-8100-7000-8000-000000000081",
    )
)


class PeopleMutationSchemaTypeTests(unittest.TestCase):
    """Reject JSON scalar types that only become valid after string coercion."""

    def test_integer_basic_iso_date_is_not_coerced_to_openapi_string_date(self) -> None:
        """An integer YYYYMMDD must not cross the HTTP command boundary as a date string."""
        payload: dict[str, object] = {
            "person_record_id": str(PERSON),
            "employment_status_code": "active",
            "employment_concurrency_code": "exclusive",
            "effective_from": 20260818,
            "decision_reason": "Confirmed hire requires an exclusive employment record.",
            "confirmation_reference": "human_confirmation:review-88",
            "evidence_references": [
                {"evidence_reference": "decision:17", "evidence_version_code": "v1"}
            ],
        }

        with self.assertRaisesRegex(ValueError, "effective_from"):
            _command_for_route(
                "employment-records",
                TENANT,
                payload,
                lambda: next(IDS),
                "idempotency-key-17xx",
            )


if __name__ == "__main__":
    unittest.main()
