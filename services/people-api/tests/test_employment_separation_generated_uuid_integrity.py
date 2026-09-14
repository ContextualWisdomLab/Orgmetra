"""Server-generated UUID payload integrity for Employment separation HTTP."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_people_api.separation_http import _generated_operational_uuid


class _ExecutableUuidPayload:
    """Tripwire for nested UUID payload comparison before exact scalar validation."""

    calls = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls += 1
        raise AssertionError(f"UUID payload comparison executed for {other!r}")


class EmploymentSeparationGeneratedUuidIntegrityTests(unittest.TestCase):
    """Require inert scalar authority for generated audit and outbox identities."""

    def test_generated_uuid_rejects_malformed_retained_payload_before_comparison(self) -> None:
        """An exact UUID with a behavior-bearing retained payload must fail closed."""
        malformed = UUID("0198a412-9000-7000-8000-000000000080")
        object.__setattr__(malformed, "int", _ExecutableUuidPayload())
        _ExecutableUuidPayload.calls = 0

        with self.assertRaisesRegex(RuntimeError, "operational UUID"):
            _generated_operational_uuid("audit_event_record_id", lambda: malformed)

        self.assertEqual(_ExecutableUuidPayload.calls, 0)


if __name__ == "__main__":
    unittest.main()
