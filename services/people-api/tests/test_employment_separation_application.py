"""Executable application contracts for governed Employment separation."""

from __future__ import annotations

from datetime import date, datetime, timezone
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.separation import (
    EmploymentSeparationCommand,
    EmploymentSeparationIntegrityError,
    EmploymentSeparationPort,
    EmploymentSeparationResult,
    separate_employment_record,
)

TENANT = UUID("0198a412-8000-7000-8000-000000000001")
PERSON = UUID("0198a412-8000-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-8000-7000-8000-000000000030")
EXPECTED_VERSION = UUID("0198a412-8000-7000-8000-000000000031")
TERMINAL_VERSION = UUID("0198a412-8000-7000-8000-000000000032")
AUDIT_EVENT = UUID("0198a412-8000-7000-8000-000000000080")
OUTBOX = UUID("0198a412-8000-7000-8000-000000000081")
RECORDED_AT = datetime(2026, 9, 12, 14, 45, tzinfo=timezone.utc)

PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:people-operator-17",
    granted_scope_codes=frozenset({"orgmetra.people.write"}),
)


def command(**overrides: object) -> EmploymentSeparationCommand:
    """Build one deterministic separation command."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "person_record_id": PERSON,
        "employment_record_id": EMPLOYMENT,
        "expected_employment_record_version_id": EXPECTED_VERSION,
        "separation_effective_on": date(2026, 10, 1),
        "separation_reason_code": "voluntary_resignation",
        "evidence_reference": "separation_packet:case-17",
        "evidence_version_code": "v1",
        "confirmation_reference": "human_confirmation:case-17",
        "idempotency_key": "employment-separation-case-17",
        "audit_event_record_id": AUDIT_EVENT,
        "outbox_delivery_record_id": OUTBOX,
    }
    values.update(overrides)
    return EmploymentSeparationCommand(**values)  # type: ignore[arg-type]


def policy(*, purpose_code: str = "workforce_admin") -> PurposeBoundAccessPolicy:
    """Return the exact policy required by the separation application boundary."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="employment-separation-v1",
        resource_kind="employment_record",
        purpose_code=purpose_code,
        operation_code="separate_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"employment_record"}),
    )


class RecordingSeparationPort:
    """Capture the authorized command without touching persistence."""

    def __init__(self) -> None:
        self.calls: list[tuple[EmploymentSeparationCommand, object]] = []

    def separate_employment(self, *, command: EmploymentSeparationCommand, authorization: object) -> EmploymentSeparationResult:
        self.calls.append((command, authorization))
        return EmploymentSeparationResult(
            employment_record_id=command.employment_record_id,
            separated_employment_record_version_id=TERMINAL_VERSION,
            recorded_at=RECORDED_AT,
            replayed=False,
        )


class WrongIdentityPort(RecordingSeparationPort):
    """Return a foreign Employment identity to prove result binding fails closed."""

    def separate_employment(self, *, command: EmploymentSeparationCommand, authorization: object) -> EmploymentSeparationResult:
        del command, authorization
        return EmploymentSeparationResult(
            employment_record_id=UUID("0198a412-8000-7000-8000-000000000099"),
            separated_employment_record_version_id=TERMINAL_VERSION,
            recorded_at=RECORDED_AT,
            replayed=False,
        )


class InvalidResultPort(RecordingSeparationPort):
    """Satisfy the protocol while returning an untrusted implementation result."""

    def separate_employment(self, *, command: EmploymentSeparationCommand, authorization: object) -> object:
        del command, authorization
        return object()


class EmploymentSeparationApplicationTests(unittest.TestCase):
    """Prove authorization and typed result binding before exposing separation truth."""

    def test_authorizes_exact_employment_before_persistence(self) -> None:
        port = RecordingSeparationPort()
        submitted_command = command()
        result = separate_employment_record(
            principal=PRINCIPAL,
            command=submitted_command,
            purpose_code="workforce_admin",
            policy=policy(),
            separation_port=port,
        )

        self.assertIsInstance(port, EmploymentSeparationPort)
        self.assertEqual(result.employment_record_id, EMPLOYMENT)
        self.assertEqual(result.separated_employment_record_version_id, TERMINAL_VERSION)
        self.assertEqual(result.recorded_at, RECORDED_AT)
        self.assertFalse(result.replayed)
        recorded_command, authorization = port.calls[0]
        self.assertIsNot(recorded_command, submitted_command)
        self.assertEqual(authorization.resource_reference, f"employment_record:{EMPLOYMENT.hex}")
        self.assertEqual(authorization.operation_code, "separate_record")
        self.assertEqual(authorization.purpose_code, "workforce_admin")

    def test_policy_denial_prevents_separation(self) -> None:
        port = RecordingSeparationPort()
        with self.assertRaises(AuthorizationDeniedError):
            separate_employment_record(
                principal=PRINCIPAL,
                command=command(),
                purpose_code="workforce_admin",
                policy=policy(purpose_code="benefits_admin"),
                separation_port=port,
            )
        self.assertEqual(port.calls, [])

    def test_requires_workforce_admin_purpose(self) -> None:
        port = RecordingSeparationPort()
        with self.assertRaisesRegex(ValueError, "workforce_admin"):
            separate_employment_record(
                principal=PRINCIPAL,
                command=command(),
                purpose_code="benefits_admin",
                policy=policy(purpose_code="benefits_admin"),
                separation_port=port,
            )
        self.assertEqual(port.calls, [])

    def test_command_rejects_malformed_high_impact_evidence(self) -> None:
        cases = (
            lambda: command(tenant_record_id=UUID(int=0)),
            lambda: command(separation_effective_on="2026-10-01"),
            lambda: command(separation_reason_code="Voluntary resignation"),
            lambda: command(evidence_reference="not-namespaced"),
            lambda: command(evidence_version_code="has space"),
            lambda: command(confirmation_reference="not-namespaced"),
            lambda: command(idempotency_key="short"),
            lambda: command(idempotency_key="x" * 201),
        )
        for builder in cases:
            with self.subTest(builder=builder), self.assertRaises(ValueError):
                builder()

    def test_result_rejects_malformed_database_evidence(self) -> None:
        cases = (
            lambda: EmploymentSeparationResult(
                employment_record_id=UUID(int=0),
                separated_employment_record_version_id=TERMINAL_VERSION,
                recorded_at=RECORDED_AT,
                replayed=False,
            ),
            lambda: EmploymentSeparationResult(
                employment_record_id=EMPLOYMENT,
                separated_employment_record_version_id=UUID(int=0),
                recorded_at=RECORDED_AT,
                replayed=False,
            ),
            lambda: EmploymentSeparationResult(
                employment_record_id=EMPLOYMENT,
                separated_employment_record_version_id=TERMINAL_VERSION,
                recorded_at=datetime(2026, 9, 12, 14, 45),
                replayed=False,
            ),
            lambda: EmploymentSeparationResult(
                employment_record_id=EMPLOYMENT,
                separated_employment_record_version_id=TERMINAL_VERSION,
                recorded_at=RECORDED_AT,
                replayed=1,  # type: ignore[arg-type]
            ),
        )
        for builder in cases:
            with self.subTest(builder=builder), self.assertRaises(ValueError):
                builder()

    def test_foreign_result_identity_fails_closed(self) -> None:
        with self.assertRaises(EmploymentSeparationIntegrityError):
            separate_employment_record(
                principal=PRINCIPAL,
                command=command(),
                purpose_code="workforce_admin",
                policy=policy(),
                separation_port=WrongIdentityPort(),
            )

    def test_requires_typed_command_port_and_result(self) -> None:
        with self.assertRaisesRegex(TypeError, "EmploymentSeparationCommand"):
            separate_employment_record(
                principal=PRINCIPAL,
                command=object(),  # type: ignore[arg-type]
                purpose_code="workforce_admin",
                policy=policy(),
                separation_port=RecordingSeparationPort(),
            )
        with self.assertRaisesRegex(TypeError, "EmploymentSeparationPort"):
            separate_employment_record(
                principal=PRINCIPAL,
                command=command(),
                purpose_code="workforce_admin",
                policy=policy(),
                separation_port=object(),  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(TypeError, "EmploymentSeparationResult"):
            separate_employment_record(
                principal=PRINCIPAL,
                command=command(),
                purpose_code="workforce_admin",
                policy=policy(),
                separation_port=InvalidResultPort(),  # type: ignore[arg-type]
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
