"""Executable contracts for converting an authorized vacancy into Assignment truth."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest
from uuid import UUID

import orgmetra_people_api
from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PositionMutationCommand,
    PositionMutationResult,
)
from orgmetra_people_api.vacancy_fill import (
    VacancyFillAuthority,
    VacancyFillIntegrityError,
    VacancyFillVerification,
    fill_position_vacancy,
)

TENANT = UUID("0198a412-8000-7000-8000-000000000001")
PERSON = UUID("0198a412-8000-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-8000-7000-8000-000000000030")
POSITION = UUID("0198a412-8000-7000-8000-000000000040")
ASSIGNMENT = UUID("0198a412-8000-7000-8000-000000000070")
AUDIT_EVENT = UUID("0198a412-8000-7000-8000-000000000080")
OUTBOX = UUID("0198a412-8000-7000-8000-000000000081")
EFFECTIVE_ON = date(2026, 8, 24)
CONFIRMATION = "human_confirmation:vacancy-review-17"
EVIDENCE_VERSION = "vacancy_fill_review:v1"
IDEMPOTENCY = "vacancy-fill-key-001"

PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:workforce-operator-17",
    granted_scope_codes=frozenset({"orgmetra.people.write"}),
)


def assignment_command(**overrides: object) -> AssignmentMutationCommand:
    """Build one deterministic Assignment command for a vacancy fill."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "employment_record_id": EMPLOYMENT,
        "person_record_id": PERSON,
        "position_record_id": POSITION,
        "assignment_record_id": ASSIGNMENT,
        "audit_event_record_id": AUDIT_EVENT,
        "outbox_delivery_record_id": OUTBOX,
        "allocation_ratio": Decimal("1.0000"),
        "effective_from": EFFECTIVE_ON,
        "confirmation_reference": CONFIRMATION,
        "evidence_version_code": EVIDENCE_VERSION,
        "idempotency_key": IDEMPOTENCY,
    }
    values.update(overrides)
    return AssignmentMutationCommand(**values)  # type: ignore[arg-type]


def assignment_policy(*, purpose_code: str = "workforce_admin") -> PurposeBoundAccessPolicy:
    """Return the exact assignment-create policy used by the authoritative People boundary."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-mutation-v1",
        resource_kind="assignment_record",
        purpose_code=purpose_code,
        operation_code="create_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"assignment_record"}),
    )


def verification(**overrides: object) -> VacancyFillVerification:
    """Build one authoritative vacancy verification result."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "employment_record_id": EMPLOYMENT,
        "person_record_id": PERSON,
        "position_record_id": POSITION,
        "effective_on": EFFECTIVE_ON,
        "position_status_code": "open",
        "available_allocation_ratio": Decimal("1.0000"),
        "confirmation_reference": CONFIRMATION,
        "evidence_version_code": EVIDENCE_VERSION,
        "review_state": "human_confirmed",
    }
    values.update(overrides)
    return VacancyFillVerification(**values)  # type: ignore[arg-type]


class RecordingVacancyAuthority:
    """Return one governed verification while recording protected resolver access."""

    def __init__(self, result: object | None = None) -> None:
        self.result = verification() if result is None else result
        self.calls: list[AssignmentMutationCommand] = []

    def verify_vacancy_fill(self, *, command: AssignmentMutationCommand) -> VacancyFillVerification:
        self.calls.append(command)
        return self.result  # type: ignore[return-value]


class RecordingMutationPort:
    """Capture the final authoritative Assignment write without touching PostgreSQL."""

    def __init__(self) -> None:
        self.assignment_calls: list[tuple[AssignmentMutationCommand, object]] = []

    def create_employment(
        self, *, command: EmploymentMutationCommand, authorization: object
    ) -> EmploymentMutationResult:
        del command, authorization
        raise AssertionError("vacancy fill must not create Employment")

    def create_position(self, *, command: PositionMutationCommand, authorization: object) -> PositionMutationResult:
        del command, authorization
        raise AssertionError("vacancy fill must not create Position")

    def create_assignment(self, *, command: AssignmentMutationCommand, authorization: object) -> AssignmentMutationResult:
        self.assignment_calls.append((command, authorization))
        return AssignmentMutationResult(assignment_record_id=command.assignment_record_id)


class VacancyFillTests(unittest.TestCase):
    """Prove vacancy evidence is re-resolved before authoritative Assignment mutation."""

    def test_orchestration_is_exported_from_people_api(self) -> None:
        """The public People API package must expose the vacancy-fill boundary."""
        self.assertIs(fill_position_vacancy, orgmetra_people_api.fill_position_vacancy)

    def test_fill_authorizes_then_resolves_then_persists_exact_assignment(self) -> None:
        authority = RecordingVacancyAuthority()
        port = RecordingMutationPort()
        command = assignment_command()

        result = fill_position_vacancy(
            principal=PRINCIPAL,
            command=command,
            purpose_code="workforce_admin",
            policy=assignment_policy(),
            vacancy_authority=authority,
            mutation_port=port,
        )

        self.assertIsInstance(authority, VacancyFillAuthority)
        self.assertEqual(authority.calls, [command])
        self.assertEqual(result.assignment_record_id, ASSIGNMENT)
        self.assertEqual(len(port.assignment_calls), 1)
        persisted_command, authorization = port.assignment_calls[0]
        self.assertIs(persisted_command, command)
        self.assertEqual(authorization.resource_reference, f"assignment_record:{ASSIGNMENT.hex}")
        self.assertEqual(authorization.purpose_code, "workforce_admin")

    def test_wrong_purpose_is_denied_before_protected_vacancy_resolution(self) -> None:
        authority = RecordingVacancyAuthority()
        port = RecordingMutationPort()

        with self.assertRaises(AuthorizationDeniedError):
            fill_position_vacancy(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="benefits_admin",
                policy=assignment_policy(),
                vacancy_authority=authority,
                mutation_port=port,
            )

        self.assertEqual(authority.calls, [])
        self.assertEqual(port.assignment_calls, [])

    def test_scope_or_capacity_drift_fails_before_assignment_mutation(self) -> None:
        cases = (
            verification(tenant_record_id=UUID("0198a412-8000-7000-8000-000000000002")),
            verification(employment_record_id=UUID("0198a412-8000-7000-8000-000000000032")),
            verification(person_record_id=UUID("0198a412-8000-7000-8000-000000000022")),
            verification(position_record_id=UUID("0198a412-8000-7000-8000-000000000042")),
            verification(effective_on=date(2026, 8, 25)),
            verification(available_allocation_ratio=Decimal("0.5000")),
            verification(confirmation_reference="human_confirmation:other-review"),
            verification(evidence_version_code="vacancy_fill_review:v2"),
        )
        for result in cases:
            with self.subTest(result=result):
                authority = RecordingVacancyAuthority(result)
                port = RecordingMutationPort()
                with self.assertRaises(VacancyFillIntegrityError):
                    fill_position_vacancy(
                        principal=PRINCIPAL,
                        command=assignment_command(),
                        purpose_code="workforce_admin",
                        policy=assignment_policy(),
                        vacancy_authority=authority,
                        mutation_port=port,
                    )
                self.assertEqual(port.assignment_calls, [])

    def test_verification_rejects_non_staffable_or_malformed_evidence(self) -> None:
        class ForgedText(str):
            pass

        class ForgedDecimal(Decimal):
            pass

        cases = (
            {"tenant_record_id": UUID(int=0)},
            {"effective_on": "2026-08-24"},
            {"position_status_code": "closed"},
            {"position_status_code": ForgedText("open")},
            {"available_allocation_ratio": 1},
            {"available_allocation_ratio": ForgedDecimal("1.0000")},
            {"available_allocation_ratio": Decimal("0")},
            {"available_allocation_ratio": Decimal("1.0001")},
            {"available_allocation_ratio": Decimal("0.12345")},
            {"confirmation_reference": "not-namespaced"},
            {"evidence_version_code": "has space"},
            {"review_state": "model_confirmed"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                verification(**overrides)

    def test_runtime_boundary_rejects_untrusted_command_authority_and_result_types(self) -> None:
        authority = RecordingVacancyAuthority()
        port = RecordingMutationPort()
        with self.assertRaisesRegex(TypeError, "AssignmentMutationCommand"):
            fill_position_vacancy(
                principal=PRINCIPAL,
                command=object(),  # type: ignore[arg-type]
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                vacancy_authority=authority,
                mutation_port=port,
            )
        with self.assertRaisesRegex(TypeError, "VacancyFillAuthority"):
            fill_position_vacancy(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                vacancy_authority=object(),  # type: ignore[arg-type]
                mutation_port=port,
            )
        invalid_authority = RecordingVacancyAuthority(object())
        with self.assertRaisesRegex(TypeError, "VacancyFillVerification"):
            fill_position_vacancy(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                vacancy_authority=invalid_authority,
                mutation_port=port,
            )

    def test_command_runtime_fields_and_verification_repr_are_fail_closed(self) -> None:
        command = assignment_command()
        object.__setattr__(command, "confirmation_reference", type("Forged", (str,), {})(CONFIRMATION))
        authority = RecordingVacancyAuthority()
        port = RecordingMutationPort()
        with self.assertRaisesRegex(TypeError, "trust-bearing fields"):
            fill_position_vacancy(
                principal=PRINCIPAL,
                command=command,
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                vacancy_authority=authority,
                mutation_port=port,
            )
        self.assertEqual(authority.calls, [])
        self.assertEqual(port.assignment_calls, [])
        self.assertEqual(repr(verification()), "VacancyFillVerification(<redacted>)")


if __name__ == "__main__":
    unittest.main()
