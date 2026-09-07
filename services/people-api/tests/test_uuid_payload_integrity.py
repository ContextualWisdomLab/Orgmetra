"""Reject forged exact UUID payloads before sentinel comparison in People boundaries."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_people_api.mutations import _validate_operational_uuid
from orgmetra_people_api.postgres_hire import _is_operational_uuid as _is_hire_operational_uuid
from orgmetra_people_api.postgres_mutations import (
    _is_operational_uuid as _is_mutation_operational_uuid,
)

_OPERATIONAL_UUID = UUID("0198a412-9000-7000-8000-0000000000aa")


class _ExecutableUUIDPayload:
    """Tripwire that exposes sentinel comparison before integer-payload validation."""

    def __init__(self) -> None:
        self.calls = 0

    def __eq__(self, other: object) -> bool:
        self.calls += 1
        raise TypeError("UUID payload equality executed before exact integer validation")

    def __ne__(self, other: object) -> bool:
        self.calls += 1
        raise TypeError("UUID payload inequality executed before exact integer validation")


def _forged_uuid(payload: object) -> UUID:
    """Return an exact UUID whose internal integer slot was rewritten after construction."""
    value = UUID(str(_OPERATIONAL_UUID))
    object.__setattr__(value, "int", payload)
    return value


class PeopleUuidPayloadIntegrityTests(unittest.TestCase):
    """Keep application and durable People UUID gates inert on corrupted exact UUIDs."""

    def test_application_uuid_gate_rejects_executable_internal_payload(self) -> None:
        payload = _ExecutableUUIDPayload()

        with self.assertRaisesRegex(ValueError, "tenant_record_id must be an operational UUID"):
            _validate_operational_uuid("tenant_record_id", _forged_uuid(payload))

        self.assertEqual(payload.calls, 0)

    def test_postgres_uuid_gates_reject_executable_internal_payload(self) -> None:
        for validator in (_is_hire_operational_uuid, _is_mutation_operational_uuid):
            with self.subTest(validator=validator.__module__):
                payload = _ExecutableUUIDPayload()

                self.assertFalse(validator(_forged_uuid(payload)))
                self.assertEqual(payload.calls, 0)

    def test_exact_operational_uuid_remains_accepted(self) -> None:
        _validate_operational_uuid("tenant_record_id", _OPERATIONAL_UUID)
        self.assertTrue(_is_hire_operational_uuid(_OPERATIONAL_UUID))
        self.assertTrue(_is_mutation_operational_uuid(_OPERATIONAL_UUID))


if __name__ == "__main__":
    unittest.main()
