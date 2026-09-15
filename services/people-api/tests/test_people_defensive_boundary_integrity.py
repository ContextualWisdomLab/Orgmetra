"""Adversarial coverage for defensive People boundary invariants."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch
from uuid import UUID

from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.authorization import _principal_authority
from orgmetra_people_api.mutation_http import (
    _detach_authenticated_principal,
    _parse_command_headers,
)
from orgmetra_people_api.mutations import (
    AssignmentMutationResult,
    EmploymentMutationResult,
    PositionMutationResult,
    _snapshot_assignment_result,
    _snapshot_employment_result,
    _snapshot_position_result,
)
from orgmetra_people_api.separation import EmploymentSeparationResult

TENANT = UUID("0198a412-9300-7000-8000-000000000001")
EMPLOYMENT = UUID("0198a412-9300-7000-8000-000000000010")
VERSION = UUID("0198a412-9300-7000-8000-000000000011")
POSITION = UUID("0198a412-9300-7000-8000-000000000012")
ASSIGNMENT = UUID("0198a412-9300-7000-8000-000000000013")
RECORDED_AT = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def _principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:operator-17",
        granted_scope_codes=frozenset({"orgmetra.people.write"}),
    )


class PeopleDefensiveBoundaryIntegrityTests(unittest.TestCase):
    """Exercise fail-closed branches that protect low-level forged evidence."""

    def test_principal_constructor_rejects_behavior_bearing_uuid_payload(self) -> None:
        tenant = UUID(str(TENANT))
        object.__setattr__(tenant, "int", object())

        with self.assertRaisesRegex(ValueError, "inert UUID payload"):
            AuthenticatedPrincipal(
                tenant_record_id=tenant,
                actor_reference="keyverse:operator-17",
                granted_scope_codes=frozenset({"orgmetra.people.write"}),
            )

    def test_shared_authorization_rejects_low_level_tenant_type_corruption(self) -> None:
        principal = _principal()
        object.__setattr__(principal, "tenant_record_id", str(TENANT))

        with self.assertRaisesRegex(TypeError, "exact UUID"):
            _principal_authority(principal)

    def test_shared_authorization_rejects_low_level_empty_scope_corruption(self) -> None:
        principal = _principal()
        object.__setattr__(principal, "granted_scope_codes", frozenset())

        with self.assertRaisesRegex(TypeError, "non-empty frozenset"):
            _principal_authority(principal)

    def test_http_principal_detachment_rejects_low_level_tenant_type_corruption(self) -> None:
        principal = _principal()
        object.__setattr__(principal, "tenant_record_id", str(TENANT))

        with self.assertRaisesRegex(TypeError, "exact UUID"):
            _detach_authenticated_principal(principal)

    def test_http_principal_detachment_rejects_low_level_empty_scope_corruption(self) -> None:
        principal = _principal()
        object.__setattr__(principal, "granted_scope_codes", frozenset())

        with self.assertRaisesRegex(TypeError, "non-empty frozenset"):
            _detach_authenticated_principal(principal)

    def test_command_header_parser_rejects_non_mapping_scope_before_lookup(self) -> None:
        with self.assertRaisesRegex(Exception, "scope is invalid"):
            _parse_command_headers([])  # type: ignore[arg-type]

    def test_mutation_receipt_rejects_forged_storage_and_preserves_value_protocols(self) -> None:
        forged = tuple.__new__(EmploymentMutationResult, ())
        with self.assertRaisesRegex(ValueError, "storage is invalid"):
            _ = forged.employment_record_id

        result = EmploymentMutationResult(employment_record_id=EMPLOYMENT)
        same_result = EmploymentMutationResult(employment_record_id=EMPLOYMENT)
        sibling_result = PositionMutationResult(position_record_id=EMPLOYMENT)
        plain_tuple = (EMPLOYMENT.int, None)

        self.assertEqual(result, same_result)
        self.assertEqual(hash(result), hash(same_result))
        self.assertNotEqual(result, sibling_result)
        self.assertNotEqual(sibling_result, result)
        self.assertNotEqual(result, plain_tuple)
        self.assertNotEqual(plain_tuple, result)
        self.assertIsInstance(hash(result), int)
        self.assertIn("EmploymentMutationResult", repr(result))
        self.assertIn("employment_record_id", repr(result))

    def test_snapshot_revalidates_runtime_replay_digest_capability(self) -> None:
        cases = (
            (
                EmploymentMutationResult(employment_record_id=EMPLOYMENT),
                EmploymentMutationResult,
                _snapshot_employment_result,
            ),
            (
                PositionMutationResult(position_record_id=POSITION),
                PositionMutationResult,
                _snapshot_position_result,
            ),
            (
                AssignmentMutationResult(assignment_record_id=ASSIGNMENT),
                AssignmentMutationResult,
                _snapshot_assignment_result,
            ),
        )
        for result, result_type, snapshot in cases:
            with self.subTest(result_type=result_type.__name__):
                with patch.object(result_type, "replay_command_digest", new=property(lambda self: 7)):
                    with self.assertRaisesRegex(ValueError, "replay_command_digest"):
                        snapshot(result)

    def test_separation_receipt_rejects_forged_storage_and_preserves_value_protocols(self) -> None:
        forged_version = tuple.__new__(
            EmploymentSeparationResult,
            (EMPLOYMENT.int, 0, RECORDED_AT, False),
        )
        with self.assertRaisesRegex(ValueError, "separated_employment_record_version_id"):
            _ = forged_version.separated_employment_record_version_id

        forged_replay = tuple.__new__(
            EmploymentSeparationResult,
            (EMPLOYMENT.int, VERSION.int, RECORDED_AT, "false"),
        )
        with self.assertRaisesRegex(ValueError, "replayed must be a bool"):
            _ = forged_replay.replayed

        result = EmploymentSeparationResult(
            employment_record_id=EMPLOYMENT,
            separated_employment_record_version_id=VERSION,
            recorded_at=RECORDED_AT,
            replayed=False,
        )
        same_result = EmploymentSeparationResult(
            employment_record_id=EMPLOYMENT,
            separated_employment_record_version_id=VERSION,
            recorded_at=RECORDED_AT,
            replayed=False,
        )
        plain_tuple = tuple(result)

        self.assertEqual(result, same_result)
        self.assertEqual(hash(result), hash(same_result))
        self.assertNotEqual(result, plain_tuple)
        self.assertNotEqual(plain_tuple, result)
        self.assertIsInstance(hash(result), int)
        self.assertIn("EmploymentSeparationResult", repr(result))
        self.assertIn("separated_employment_record_version_id", repr(result))


if __name__ == "__main__":
    unittest.main()
