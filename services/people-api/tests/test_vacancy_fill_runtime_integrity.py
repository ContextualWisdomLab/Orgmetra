"""Adversarial runtime regressions for governed vacancy fill orchestration."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.mutations import AssignmentMutationCommand
from orgmetra_people_api.vacancy_fill import (
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

PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:workforce-operator-17",
    granted_scope_codes=frozenset({"orgmetra.people.write"}),
)
POLICY = PurposeBoundAccessPolicy(
    tenant_record_id=TENANT,
    policy_version_code="people-mutation-v1",
    resource_kind="assignment_record",
    purpose_code="workforce_admin",
    operation_code="create_record",
    required_scope_code="orgmetra.people.write",
    permitted_fields=frozenset({"assignment_record"}),
)


def command() -> AssignmentMutationCommand:
    """Build one valid vacancy-fill Assignment command."""
    return AssignmentMutationCommand(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        position_record_id=POSITION,
        assignment_record_id=ASSIGNMENT,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX,
        allocation_ratio=Decimal("1.0000"),
        effective_from=EFFECTIVE_ON,
        confirmation_reference=CONFIRMATION,
        evidence_version_code=EVIDENCE_VERSION,
        idempotency_key="vacancy-fill-key-001",
    )


def valid_verification() -> VacancyFillVerification:
    """Build one fresh human-confirmed vacancy verification."""
    return VacancyFillVerification(
        tenant_record_id=TENANT,
        employment_record_id=EMPLOYMENT,
        person_record_id=PERSON,
        position_record_id=POSITION,
        effective_on=EFFECTIVE_ON,
        position_status_code="open",
        available_allocation_ratio=Decimal("1.0000"),
        confirmation_reference=CONFIRMATION,
        evidence_version_code=EVIDENCE_VERSION,
    )


class RecordingAuthority:
    """Record whether protected staffing resolution was reached."""

    def __init__(self) -> None:
        self.calls = 0

    def verify_vacancy_fill(self, *, command: AssignmentMutationCommand) -> VacancyFillVerification:
        del command
        self.calls += 1
        return valid_verification()


class VacancyFillRuntimeIntegrityTests(unittest.TestCase):
    """Close runtime-forgery and unavailable-persistence paths before protected resolution."""

    def test_invalid_mutation_port_fails_before_protected_vacancy_resolution(self) -> None:
        authority = RecordingAuthority()
        with self.assertRaisesRegex(TypeError, "PeopleMutationPort"):
            fill_position_vacancy(
                principal=PRINCIPAL,
                command=command(),
                purpose_code="workforce_admin",
                policy=POLICY,
                vacancy_authority=authority,
                mutation_port=object(),  # type: ignore[arg-type]
            )
        self.assertEqual(authority.calls, 0)

    def test_forged_purpose_and_command_primitives_fail_before_resolver(self) -> None:
        class ForgedText(str):
            pass

        authority = RecordingAuthority()
        with self.assertRaisesRegex(TypeError, "purpose_code"):
            fill_position_vacancy(
                principal=PRINCIPAL,
                command=command(),
                purpose_code=ForgedText("workforce_admin"),
                policy=POLICY,
                vacancy_authority=authority,
                mutation_port=object(),  # type: ignore[arg-type]
            )
        for field_name, value in (
            ("tenant_record_id", "not-a-uuid"),
            ("effective_from", type("ForgedDate", (date,), {})(2026, 8, 24)),
            ("allocation_ratio", type("ForgedDecimal", (Decimal,), {})("1.0000")),
            ("allocation_ratio", Decimal("0")),
            ("allocation_ratio", Decimal("1.0001")),
            ("allocation_ratio", Decimal("0.12345")),
            ("confirmation_reference", "not-namespaced"),
            ("evidence_version_code", ""),
            ("idempotency_key", "too-short"),
        ):
            with self.subTest(field_name=field_name):
                forged = command()
                object.__setattr__(forged, field_name, value)
                with self.assertRaises((TypeError, ValueError)):
                    fill_position_vacancy(
                        principal=PRINCIPAL,
                        command=forged,
                        purpose_code="workforce_admin",
                        policy=POLICY,
                        vacancy_authority=authority,
                        mutation_port=object(),  # type: ignore[arg-type]
                    )
        self.assertEqual(authority.calls, 0)

    def test_nonfinite_command_allocation_fails_before_protected_resolver(self) -> None:
        """Reject exact Decimal NaN before protected staffing truth can be inspected."""

        class NeverMutationPort:
            """Satisfy the mutation-port protocol without permitting a write."""

            def create_employment(self, *, command: object, authorization: object) -> object:
                del command, authorization
                raise AssertionError("nonfinite vacancy fill must not create Employment")

            def create_position(self, *, command: object, authorization: object) -> object:
                del command, authorization
                raise AssertionError("nonfinite vacancy fill must not create Position")

            def create_assignment(self, *, command: object, authorization: object) -> object:
                del command, authorization
                raise AssertionError("nonfinite vacancy fill must not create Assignment")

        authority = RecordingAuthority()
        forged = command()
        object.__setattr__(forged, "allocation_ratio", Decimal("NaN"))
        with self.assertRaisesRegex(ValueError, "finite"):
            fill_position_vacancy(
                principal=PRINCIPAL,
                command=forged,
                purpose_code="workforce_admin",
                policy=POLICY,
                vacancy_authority=authority,
                mutation_port=NeverMutationPort(),  # type: ignore[arg-type]
            )
        self.assertEqual(authority.calls, 0)

    def test_verification_rejects_nonfinite_and_forged_text_evidence(self) -> None:
        class ForgedText(str):
            pass

        for overrides in (
            {"tenant_record_id": "not-a-uuid"},
            {"available_allocation_ratio": Decimal("NaN")},
            {"confirmation_reference": ForgedText(CONFIRMATION)},
            {"evidence_version_code": ForgedText(EVIDENCE_VERSION)},
            {"review_state": ForgedText("human_confirmed")},
        ):
            values = {
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
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                VacancyFillVerification(**values)  # type: ignore[arg-type]

    def test_post_construction_forged_allocation_fails_closed_before_mutation(self) -> None:
        """A mutated verification value object must fail closed, never compare as passable."""

        class ForgedDecimal(Decimal):
            pass

        class StaticAuthority:
            """Return one pre-built verification regardless of the requested command."""

            def __init__(self, verification: VacancyFillVerification) -> None:
                self.verification = verification
                self.calls = 0

            def verify_vacancy_fill(self, *, command: AssignmentMutationCommand) -> VacancyFillVerification:
                del command
                self.calls += 1
                return self.verification

        class NeverAssignmentPort:
            """Record whether any authoritative persistence write was reached."""

            def __init__(self) -> None:
                self.assignment_calls: list[object] = []

            def create_employment(self, *, command: object, authorization: object) -> object:
                del command, authorization
                raise AssertionError("vacancy fill must not create Employment")

            def create_position(self, *, command: object, authorization: object) -> object:
                del command, authorization
                raise AssertionError("vacancy fill must not create Position")

            def create_assignment(self, *, command: object, authorization: object) -> object:
                self.assignment_calls.append((command, authorization))
                raise AssertionError("forged vacancy evidence reached the Assignment write")

        # A NaN allocation would otherwise compare ``False`` against every threshold
        # and silently pass the capacity check, so both forged shapes fail closed.
        for forged_ratio in (Decimal("NaN"), ForgedDecimal("1.0000"), Decimal("Infinity")):
            with self.subTest(ratio=str(forged_ratio)):
                verification = valid_verification()
                object.__setattr__(verification, "available_allocation_ratio", forged_ratio)
                authority = StaticAuthority(verification)
                port = NeverAssignmentPort()
                with self.assertRaisesRegex(
                    VacancyFillIntegrityError,
                    "finite exact Decimal",
                ):
                    fill_position_vacancy(
                        principal=PRINCIPAL,
                        command=command(),
                        purpose_code="workforce_admin",
                        policy=POLICY,
                        vacancy_authority=authority,  # type: ignore[arg-type]
                        mutation_port=port,  # type: ignore[arg-type]
                    )
                self.assertEqual(authority.calls, 1)
                self.assertEqual(port.assignment_calls, [])

    def test_post_construction_non_staffable_or_nonhuman_evidence_fails_closed(self) -> None:
        class NeverMutationPort:
            """Satisfy the mutation-port protocol without permitting a write."""

            def create_employment(self, *, command: object, authorization: object) -> object:
                del command, authorization
                raise AssertionError("invalid vacancy evidence must not create Employment")

            def create_position(self, *, command: object, authorization: object) -> object:
                del command, authorization
                raise AssertionError("invalid vacancy evidence must not create Position")

            def create_assignment(self, *, command: object, authorization: object) -> object:
                del command, authorization
                raise AssertionError("invalid vacancy evidence must not create Assignment")

        for field_name, value in (
            ("position_status_code", "closed"),
            ("review_state", "model_confirmed"),
        ):
            with self.subTest(field_name=field_name):
                verification = valid_verification()
                object.__setattr__(verification, field_name, value)
                authority = type(
                    "StaticAuthority",
                    (),
                    {
                        "verify_vacancy_fill": lambda self, *, command: verification,
                    },
                )()
                with self.assertRaisesRegex(
                    VacancyFillIntegrityError,
                    "failed runtime validation",
                ):
                    fill_position_vacancy(
                        principal=PRINCIPAL,
                        command=command(),
                        purpose_code="workforce_admin",
                        policy=POLICY,
                        vacancy_authority=authority,  # type: ignore[arg-type]
                        mutation_port=NeverMutationPort(),
                    )


if __name__ == "__main__":
    unittest.main()
