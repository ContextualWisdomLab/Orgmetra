"""Executable contracts for governed candidate-to-worker hire acceptance."""

from __future__ import annotations

from datetime import date
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.hire import (
    HireAcceptanceCommand,
    HireAcceptancePort,
    HireAcceptanceResult,
    accept_confirmed_hire,
)

TENANT = UUID("0198a412-7000-7000-8000-000000000001")
CANDIDATE = UUID("0198a412-7000-7000-8000-000000000010")
DECISION = UUID("0198a412-7000-7000-8000-000000000011")
PERSON = UUID("0198a412-7000-7000-8000-000000000020")
PERSON_NAME = UUID("0198a412-7000-7000-8000-000000000021")
EMPLOYMENT = UUID("0198a412-7000-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-7000-7000-8000-000000000031")
CONVERSION = UUID("0198a412-7000-7000-8000-000000000040")
AUDIT_EVENT = UUID("0198a412-7000-7000-8000-000000000050")
OUTBOX_DELIVERY = UUID("0198a412-7000-7000-8000-000000000051")
EFFECTIVE_FROM = date(2026, 8, 18)


def command(**overrides: object) -> HireAcceptanceCommand:
    """Build one deterministic accepted-hire command for tests."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "candidate_profile_id": CANDIDATE,
        "selection_decision_id": DECISION,
        "person_record_id": PERSON,
        "person_name_record_id": PERSON_NAME,
        "employment_record_id": EMPLOYMENT,
        "employment_record_version_id": EMPLOYMENT_VERSION,
        "candidate_worker_conversion_record_id": CONVERSION,
        "audit_event_record_id": AUDIT_EVENT,
        "outbox_delivery_record_id": OUTBOX_DELIVERY,
        "effective_from": EFFECTIVE_FROM,
        "display_name": "Ada Lovelace",
        "employment_status_code": "active",
    }
    values.update(overrides)
    return HireAcceptanceCommand(**values)  # type: ignore[arg-type]


def policy(*, purpose_code: str = "candidate_hire") -> PurposeBoundAccessPolicy:
    """Return the exact write policy required to materialize a confirmed hire."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-hire-v1",
        resource_kind="selection_decision",
        purpose_code=purpose_code,
        operation_code="materialize_worker",
        required_scope_code="orgmetra.people.materialize_worker",
        permitted_fields=frozenset({"candidate_worker_conversion"}),
    )


PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:operator-17",
    granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
)


class RecordingHirePort:
    """Capture the authorized command without persisting HR data."""

    def __init__(self) -> None:
        self.calls: list[tuple[HireAcceptanceCommand, object]] = []

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        self.calls.append((command, authorization))
        return HireAcceptanceResult(
            person_record_id=command.person_record_id,
            employment_record_id=command.employment_record_id,
            candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
        )


class HireAcceptanceTests(unittest.TestCase):
    """Prove exact-target authorization happens before any authoritative write."""

    def test_authorizes_exact_selection_decision_before_materializing_worker(self) -> None:
        port = RecordingHirePort()
        request = command()

        result = accept_confirmed_hire(
            principal=PRINCIPAL,
            command=request,
            purpose_code="candidate_hire",
            policy=policy(),
            mutation_port=port,
        )

        self.assertIsInstance(port, HireAcceptancePort)
        self.assertEqual(result.person_record_id, PERSON)
        self.assertEqual(len(port.calls), 1)
        written_command, authorization = port.calls[0]
        self.assertEqual(written_command, request)
        self.assertEqual(authorization.resource_reference, f"selection_decision:{DECISION.hex}")
        self.assertEqual(authorization.actor_reference, PRINCIPAL.actor_reference)
        self.assertEqual(authorization.operation_code, "materialize_worker")
        self.assertEqual(authorization.authorized_fields, frozenset({"candidate_worker_conversion"}))

    def test_policy_denial_prevents_mutation(self) -> None:
        port = RecordingHirePort()

        with self.assertRaises(AuthorizationDeniedError):
            accept_confirmed_hire(
                principal=PRINCIPAL,
                command=command(),
                purpose_code="candidate_hire",
                policy=policy(purpose_code="benefits_admin"),
                mutation_port=port,
            )

        self.assertEqual(port.calls, [])

    def test_command_rejects_reserved_or_malformed_identifiers(self) -> None:
        invalid_values = (
            {"tenant_record_id": UUID(int=0)},
            {"candidate_profile_id": UUID(int=(1 << 128) - 1)},
            {"selection_decision_id": "not-a-uuid"},
        )
        for overrides in invalid_values:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                command(**overrides)

    def test_command_rejects_bad_business_values(self) -> None:
        invalid_values = (
            {"effective_from": "2026-08-18"},
            {"display_name": "   "},
            {"employment_status_code": "Active Worker"},
        )
        for overrides in invalid_values:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                command(**overrides)

    def test_service_rejects_mismatched_tenant_before_port_call(self) -> None:
        port = RecordingHirePort()
        other_tenant_principal = AuthenticatedPrincipal(
            tenant_record_id=UUID("0198a412-7000-7000-8000-000000000099"),
            actor_reference="keyverse_subject:operator-99",
            granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
        )

        with self.assertRaises(AuthorizationDeniedError):
            accept_confirmed_hire(
                principal=other_tenant_principal,
                command=command(),
                purpose_code="candidate_hire",
                policy=policy(),
                mutation_port=port,
            )

        self.assertEqual(port.calls, [])

    def test_mutation_port_must_implement_protocol(self) -> None:
        with self.assertRaisesRegex(TypeError, "mutation_port must implement HireAcceptancePort"):
            accept_confirmed_hire(
                principal=PRINCIPAL,
                command=command(),
                purpose_code="candidate_hire",
                policy=policy(),
                mutation_port=object(),  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
