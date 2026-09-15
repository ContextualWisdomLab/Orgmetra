"""Regression contracts for stable Employment-separation persistence capabilities."""

from __future__ import annotations

from datetime import date, datetime, timezone
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.separation import (
    EmploymentSeparationCommand,
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
RECORDED_AT = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)

PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:capability-binding-test",
    granted_scope_codes=frozenset({"orgmetra.people.write"}),
)


def _command() -> EmploymentSeparationCommand:
    return EmploymentSeparationCommand(
        tenant_record_id=TENANT,
        person_record_id=PERSON,
        employment_record_id=EMPLOYMENT,
        expected_employment_record_version_id=EXPECTED_VERSION,
        separation_effective_on=date(2026, 10, 1),
        separation_reason_code="voluntary_resignation",
        evidence_reference="separation_packet:capability-binding-test",
        evidence_version_code="v1",
        confirmation_reference="human_confirmation:capability-binding-test",
        idempotency_key="separation-capability-binding-test",
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
    )


def _policy() -> PurposeBoundAccessPolicy:
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="employment-separation-v1",
        resource_kind="employment_record",
        purpose_code="workforce_admin",
        operation_code="separate_record",
        required_scope_code="orgmetra.people.write",
        permitted_fields=frozenset({"employment_record"}),
    )


class _DynamicLookupPort:
    """Expose any post-validation dynamic lookup of the persistence operation."""

    def __init__(self) -> None:
        self.operation_lookups = 0

    def __getattribute__(self, name: str) -> object:
        if name == "separate_employment":
            current = object.__getattribute__(self, "operation_lookups")
            object.__setattr__(self, "operation_lookups", current + 1)
        return object.__getattribute__(self, name)

    def separate_employment(
        self,
        *,
        command: EmploymentSeparationCommand,
        authorization: object,
    ) -> EmploymentSeparationResult:
        del authorization
        return EmploymentSeparationResult(
            employment_record_id=command.employment_record_id,
            separated_employment_record_version_id=TERMINAL_VERSION,
            recorded_at=RECORDED_AT,
            replayed=False,
        )


class _DescriptorPort:
    """Look structurally compatible while keeping behavior behind a descriptor."""

    def __init__(self) -> None:
        self.descriptor_calls = 0

    @property
    def separate_employment(self) -> object:
        self.descriptor_calls += 1
        raise RuntimeError("descriptor-backed persistence capability executed")


class _ProtocolPlaceholder(EmploymentSeparationPort):
    """Inherit only the Protocol stub; no concrete persistence operation exists."""


class EmploymentSeparationPortCapabilityBindingTests(unittest.TestCase):
    """Require one inert function capability from validation through persistence use."""

    def test_success_path_does_not_dynamically_resolve_operation_after_authorization(self) -> None:
        port = _DynamicLookupPort()

        result = separate_employment_record(
            principal=PRINCIPAL,
            command=_command(),
            purpose_code="workforce_admin",
            policy=_policy(),
            separation_port=port,  # type: ignore[arg-type]
        )

        self.assertEqual(result.employment_record_id, EMPLOYMENT)
        self.assertEqual(port.operation_lookups, 0)

    def test_descriptor_backed_operation_is_rejected_without_descriptor_execution(self) -> None:
        port = _DescriptorPort()

        with self.assertRaisesRegex(TypeError, "ordinary instance method"):
            separate_employment_record(
                principal=PRINCIPAL,
                command=_command(),
                purpose_code="workforce_admin",
                policy=_policy(),
                separation_port=port,  # type: ignore[arg-type]
            )

        self.assertEqual(port.descriptor_calls, 0)

    def test_protocol_placeholder_is_not_accepted_as_persistence_capability(self) -> None:
        with self.assertRaisesRegex(TypeError, "ordinary instance method"):
            separate_employment_record(
                principal=PRINCIPAL,
                command=_command(),
                purpose_code="workforce_admin",
                policy=_policy(),
                separation_port=_ProtocolPlaceholder(),
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
