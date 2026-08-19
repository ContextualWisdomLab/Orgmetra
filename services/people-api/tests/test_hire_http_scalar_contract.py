"""Regression contracts for exact JSON scalar typing on confirmed-hire materialization."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_people_api.hire_http import _InvalidHttpRequest, _command_from_payload

TENANT = UUID("0198a412-7200-7000-8000-000000000001")
IDEMPOTENCY_KEY = "hire-idempotency-key-17"


def _valid_payload() -> dict[str, object]:
    """Return one valid confirmed-hire command using the published JSON scalar forms."""
    return {
        "candidate_profile_id": "0198a412-7200-7000-8000-000000000010",
        "selection_decision_id": "0198a412-7200-7000-8000-000000000011",
        "person_record_id": "0198a412-7200-7000-8000-000000000020",
        "person_name_record_id": "0198a412-7200-7000-8000-000000000021",
        "employment_record_id": "0198a412-7200-7000-8000-000000000030",
        "employment_record_version_id": "0198a412-7200-7000-8000-000000000031",
        "candidate_worker_conversion_record_id": "0198a412-7200-7000-8000-000000000040",
        "audit_event_record_id": "0198a412-7200-7000-8000-000000000050",
        "outbox_delivery_record_id": "0198a412-7200-7000-8000-000000000051",
        "effective_from": "2026-08-18",
        "display_name": "Ada Lovelace",
        "employment_status_code": "active",
    }


class HireHttpScalarContractTests(unittest.TestCase):
    """Prove request parsing rejects coercible non-string UUID and date JSON scalars."""

    def test_non_string_uuid_scalar_is_rejected(self) -> None:
        """Reject a JSON number even when string coercion would form a parseable UUID."""
        payload = _valid_payload()
        payload["candidate_profile_id"] = 12345678123456781234567812345678

        with self.assertRaises(_InvalidHttpRequest):
            _command_from_payload(TENANT, payload, IDEMPOTENCY_KEY)

    def test_non_string_effective_date_scalar_is_rejected(self) -> None:
        """Reject a JSON number even when Python accepts its basic-date string form."""
        payload = _valid_payload()
        payload["effective_from"] = 20260818

        with self.assertRaises(_InvalidHttpRequest):
            _command_from_payload(TENANT, payload, IDEMPOTENCY_KEY)


if __name__ == "__main__":
    unittest.main()
