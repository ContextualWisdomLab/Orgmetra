"""Executable contracts for governed People employment, position, and assignment writes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.mutations import (
    AssignmentMutationCommand,
    AssignmentMutationResult,
    EmploymentMutationCommand,
    EmploymentMutationResult,
    PeopleMutationPort,
    PositionMutationCommand,
    PositionMutationResult,
    command_route,
    create_assignment_record,
    create_employment_record,
    create_position_record,
    mutation_command_digest,
    parse_allocation_ratio,
    validate_idempotency_key,
)
from authorization_test_support import issued_authorization

TENANT = UUID("0198a412-8000-7000-8000-000000000001")
PERSON = UUID("0198a412-8000-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-8000-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-8000-7000-8000-000000000031")
POSITION = UUID("0198a412-8000-7000-8000-000000000040")
POSITION_VERSION = UUID("0198a412-8000-7000-8000-000000000041")
ORGANIZATION = UUID("0198a412-8000-7000-8000-000000000050")
JOB = UUID("0198a412-8000-7000-8000-000000000060")
ASSIGNMENT = UUID("0198a412-8000-7000-8000-000000000070")
AUDIT_EVENT = UUID("0198a412-8000-7000-8000-000000000080")
OUTBOX = UUID("0198a412-8000-7000-8000-000000000081")
EFFECTIVE_FROM = date(2026, 8, 18)
CONFIRMATION = "human_confirmation:review-88"
EVIDENCE = "decision_evidence_set:v1"
IDEMPOTENCY = "idempotency-key-17xx"


def employment_command(**overrides: object) -> EmploymentMutationCommand:
    """Build one deterministic employment command."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "person_record_id": PERSON,
        "employment_record_id": EMPLOYMENT,
        "employment_record_version_id": EMPLOYMENT_VERSION,
        "audit_event_record_id": AUDIT_EVENT,
        "outbox_delivery_record_id": OUTBOX,
        "employment_status_code": "active",
        "employment_concurrency_code": "exclusive",
        "effective_from": EFFECTIVE_FROM,
        "confirmation_reference": CONFIRMATION,
        "evidence_version_code": EVIDENCE,
        "idempotency_key": IDEMPOTENCY,
    }
    values.update(overrides)
    return EmploymentMutationCommand(**values)  # type: ignore[arg-type]


def position_command(**overrides: object) -> PositionMutationCommand:
    """Build one deterministic position command."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "organization_unit_id": ORGANIZATION,
        "job_profile_id": JOB,
        "position_record_id": POSITION,
        "position_record_version_id": POSITION_VERSION,
        "audit_event_record_id": AUDIT_EVENT,
        "outbox_delivery_record_id": OUTBOX,
        "position_status_code": "open",
        "effective_from": EFFECTIVE_FROM,
        "confirmation_reference": CONFIRMATION,
        "evidence_version_code": EVIDENCE,
        "idempotency_key": IDEMPOTENCY,
    }
    values.update(overrides)
    return PositionMutationCommand(**values)  # type: ignore[arg-type]


def assignment_command(**overrides: object) -> AssignmentMutationCommand:
    """Build one deterministic assignment command."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "employment_record_id": EMPLOYMENT,
        "person_record_id": PERSON,
        "position_record_id": POSITION,
        "assignment_record_id": ASSIGNMENT,
        "audit_event_record_id": AUDIT_EVENT,
        "outbox_delivery_record_id": OUTBOX,
        "allocation_ratio": Decimal("1.0000"),
        "effective_from": EFFECTIVE_FROM,
        "confirmation_reference": CONFIRMATION,
        "evidence_version_code": EVIDENCE,
        "idempotency_key": IDEMPOTENCY,
    }
    values.update(overrides)
    return AssignmentMutationCommand(**values)  # type: ignore[arg-type]


def employment_policy(*, purpose_code: str = "workforce_admin") -> PurposeBoundAccessPolicy:
    """Return the exact employment-create policy."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-mutation-v1",
        resource_kind="employment_record",
        purpose_code=purpose_code,
        operation_code="create_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"employment_record"}),
    )


def position_policy() -> PurposeBoundAccessPolicy:
    """Return the exact position-create policy."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-mutation-v1",
        resource_kind="position_record",
        purpose_code="job_architecture_admin",
        operation_code="create_record",
        required_scope_code="orgmetra.job_architecture.write",
        permitted_fields=frozenset({"position_record"}),
    )


def assignment_policy() -> PurposeBoundAccessPolicy:
    """Return the exact assignment-create policy."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-mutation-v1",
        resource_kind="assignment_record",
        purpose_code="workforce_admin",
        operation_code="create_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"assignment_record"}),
    )


PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:operator-17",
    granted_scope_codes=frozenset({"orgmetra.people.write", "orgmetra.job_architecture.write"}),
)


class RecordingMutationPort:
    """Capture authorized commands without persisting HR data."""

    def __init__(self) -> None:
        self.employment_calls: list[object] = []
        self.position_calls: list[object] = []
        self.assignment_calls: list[object] = []

    def create_employment(self, *, command: EmploymentMutationCommand, authorization: object) -> EmploymentMutationResult:
        self.employment_calls.append((command, authorization))
        return EmploymentMutationResult(employment_record_id=command.employment_record_id)

    def create_position(self, *, command: PositionMutationCommand, authorization: object) -> PositionMutationResult:
        self.position_calls.append((command, authorization))
        return PositionMutationResult(position_record_id=command.position_record_id)

    def create_assignment(self, *, command: AssignmentMutationCommand, authorization: object) -> AssignmentMutationResult:
        self.assignment_calls.append((command, authorization))
        return AssignmentMutationResult(assignment_record_id=command.assignment_record_id)


class InvalidResultPort(RecordingMutationPort):
    """Satisfy the protocol while returning a malformed implementation result."""

    def create_employment(self, *, command: EmploymentMutationCommand, authorization: object) -> object:
        del command, authorization
        return object()

    def create_position(self, *, command: PositionMutationCommand, authorization: object) -> object:
        del command, authorization
        return object()

    def create_assignment(self, *, command: AssignmentMutationCommand, authorization: object) -> object:
        del command, authorization
        return object()


class PeopleMutationTests(unittest.TestCase):
    """Prove exact-target authorization happens before any authoritative write."""

    def test_authorizes_each_record_kind_before_persistence(self) -> None:
        port = RecordingMutationPort()
        employment = create_employment_record(
            principal=PRINCIPAL,
            command=employment_command(),
            purpose_code="workforce_admin",
            policy=employment_policy(),
            mutation_port=port,
        )
        position = create_position_record(
            principal=PRINCIPAL,
            command=position_command(),
            purpose_code="job_architecture_admin",
            policy=position_policy(),
            mutation_port=port,
        )
        assignment = create_assignment_record(
            principal=PRINCIPAL,
            command=assignment_command(),
            purpose_code="workforce_admin",
            policy=assignment_policy(),
            mutation_port=port,
        )
        self.assertIsInstance(port, PeopleMutationPort)
        self.assertEqual(employment.employment_record_id, EMPLOYMENT)
        self.assertEqual(position.position_record_id, POSITION)
        self.assertEqual(assignment.assignment_record_id, ASSIGNMENT)
        self.assertEqual(port.employment_calls[0][1].resource_reference, f"employment_record:{EMPLOYMENT.hex}")
        self.assertEqual(port.position_calls[0][1].resource_reference, f"position_record:{POSITION.hex}")
        self.assertEqual(port.assignment_calls[0][1].resource_reference, f"assignment_record:{ASSIGNMENT.hex}")

    def test_policy_denial_prevents_mutation(self) -> None:
        port = RecordingMutationPort()
        with self.assertRaises(AuthorizationDeniedError):
            create_employment_record(
                principal=PRINCIPAL,
                command=employment_command(),
                purpose_code="workforce_admin",
                policy=employment_policy(purpose_code="benefits_admin"),
                mutation_port=port,
            )
        self.assertEqual(port.employment_calls, [])

    def test_commands_reject_reserved_or_malformed_values(self) -> None:
        cases = (
            lambda: employment_command(tenant_record_id=UUID(int=0)),
            lambda: employment_command(effective_from="2026-08-18"),
            lambda: employment_command(employment_status_code="hired"),
            lambda: employment_command(employment_concurrency_code="primary"),
            lambda: employment_command(confirmation_reference="not-namespaced"),
            lambda: employment_command(evidence_version_code="has space"),
            lambda: employment_command(idempotency_key="short"),
            lambda: employment_command(idempotency_key="x" * 201),
            lambda: employment_command(idempotency_key="idempotency-key-17\n"),
            lambda: employment_command(idempotency_key=17),
            lambda: position_command(position_record_id=UUID(int=(1 << 128) - 1)),
            lambda: position_command(effective_from="2026-08-18"),
            lambda: position_command(position_status_code="staffable"),
            lambda: assignment_command(allocation_ratio="1.0000"),
            lambda: assignment_command(allocation_ratio=Decimal("0")),
            lambda: assignment_command(allocation_ratio=Decimal("1.0001")),
            lambda: assignment_command(effective_from="2026-08-18"),
            lambda: EmploymentMutationResult(employment_record_id=UUID(int=0)),
            lambda: PositionMutationResult(position_record_id=UUID(int=0)),
            lambda: AssignmentMutationResult(assignment_record_id=UUID(int=0)),
        )
        for builder in cases:
            with self.subTest(builder=builder), self.assertRaises(ValueError):
                builder()

    def test_parse_allocation_ratio_accepts_only_openapi_tokens(self) -> None:
        self.assertEqual(parse_allocation_ratio("1.0000"), Decimal("1.0000"))
        self.assertEqual(parse_allocation_ratio("0.2500"), Decimal("0.2500"))
        for raw in (1, "1", "1.0", "0.1", "2.0000"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_allocation_ratio(raw)

    def test_service_requires_typed_commands_ports_and_results(self) -> None:
        with self.assertRaisesRegex(TypeError, "EmploymentMutationCommand"):
            create_employment_record(
                principal=PRINCIPAL,
                command=object(),  # type: ignore[arg-type]
                purpose_code="workforce_admin",
                policy=employment_policy(),
                mutation_port=RecordingMutationPort(),
            )
        with self.assertRaisesRegex(TypeError, "PositionMutationCommand"):
            create_position_record(
                principal=PRINCIPAL,
                command=object(),  # type: ignore[arg-type]
                purpose_code="job_architecture_admin",
                policy=position_policy(),
                mutation_port=RecordingMutationPort(),
            )
        with self.assertRaisesRegex(TypeError, "AssignmentMutationCommand"):
            create_assignment_record(
                principal=PRINCIPAL,
                command=object(),  # type: ignore[arg-type]
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                mutation_port=RecordingMutationPort(),
            )
        with self.assertRaisesRegex(TypeError, "PeopleMutationPort"):
            create_employment_record(
                principal=PRINCIPAL,
                command=employment_command(),
                purpose_code="workforce_admin",
                policy=employment_policy(),
                mutation_port=object(),  # type: ignore[arg-type]
            )
        invalid = InvalidResultPort()
        with self.assertRaisesRegex(TypeError, "EmploymentMutationResult"):
            create_employment_record(
                principal=PRINCIPAL,
                command=employment_command(),
                purpose_code="workforce_admin",
                policy=employment_policy(),
                mutation_port=invalid,  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(TypeError, "PositionMutationResult"):
            create_position_record(
                principal=PRINCIPAL,
                command=position_command(),
                purpose_code="job_architecture_admin",
                policy=position_policy(),
                mutation_port=invalid,  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(TypeError, "AssignmentMutationResult"):
            create_assignment_record(
                principal=PRINCIPAL,
                command=assignment_command(),
                purpose_code="workforce_admin",
                policy=assignment_policy(),
                mutation_port=invalid,  # type: ignore[arg-type]
            )

    def test_command_digest_excludes_generated_ids_and_changes_with_semantics(self) -> None:
        authorization = issued_authorization(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            resource_reference=f"employment_record:{EMPLOYMENT.hex}",
            policy_version_code="people-mutation-v1",
            purpose_code="workforce_admin",
            operation_code="create_record",
            resource_kind="employment_record",
            requested_fields=frozenset({"employment_record"}),
            required_scope_code="orgmetra.people.write",
        )
        first = mutation_command_digest(command=employment_command(), authorization=authorization)
        retried = mutation_command_digest(
            command=employment_command(
                employment_record_id=UUID("0198a412-8000-7000-8000-000000000032"),
                audit_event_record_id=UUID("0198a412-8000-7000-8000-000000000082"),
            ),
            authorization=authorization,
        )
        changed = mutation_command_digest(
            command=employment_command(employment_status_code="leave"),
            authorization=authorization,
        )
        self.assertEqual(first, retried)
        self.assertNotEqual(first, changed)
        self.assertEqual(command_route(employment_command()), "employment-records")
        self.assertEqual(command_route(position_command()), "position-records")
        self.assertEqual(command_route(assignment_command()), "assignment-records")
        self.assertEqual(validate_idempotency_key(IDEMPOTENCY), IDEMPOTENCY)
        position_digest = mutation_command_digest(
            command=position_command(),
            authorization=authorization,
        )
        assignment_digest = mutation_command_digest(
            command=assignment_command(),
            authorization=authorization,
        )
        self.assertNotEqual(first, position_digest)
        self.assertNotEqual(first, assignment_digest)
        with self.assertRaisesRegex(TypeError, "People mutation command"):
            command_route(object())  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "AuthorizationDecision"):
            mutation_command_digest(command=employment_command(), authorization=object())  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "People mutation command"):
            mutation_command_digest(command=object(), authorization=authorization)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
