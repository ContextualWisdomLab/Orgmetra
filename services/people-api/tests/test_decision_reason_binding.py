"""Regression coverage for high-impact decision-reason governance bindings."""

from __future__ import annotations

from collections.abc import Iterator
import re
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.mutation_http import _command_for_route
from orgmetra_people_api.mutations import EmploymentMutationCommand, mutation_command_digest
from authorization_test_support import issued_authorization

TENANT = UUID("0198a412-8a00-7000-8000-000000000001")
PERSON = UUID("0198a412-8a00-7000-8000-000000000002")
GENERATED_IDS = (
    UUID("0198a412-8a00-7000-8000-000000000010"),
    UUID("0198a412-8a00-7000-8000-000000000011"),
    UUID("0198a412-8a00-7000-8000-000000000012"),
    UUID("0198a412-8a00-7000-8000-000000000013"),
)
_GOVERNANCE_BINDING_PATTERN = re.compile(r"^governance_evidence_v1:[0-9a-f]{64}$")


def _id_factory(values: Iterator[UUID]):
    """Return the next deterministic operational UUID for command construction."""

    def next_id() -> UUID:
        return next(values)

    return next_id


def _payload(*, decision_reason: str, evidence_references: list[dict[str, str]] | None = None) -> dict[str, object]:
    """Return one high-impact employment command payload."""
    return {
        "person_record_id": str(PERSON),
        "employment_status_code": "active",
        "employment_concurrency_code": "exclusive",
        "effective_from": "2026-08-20",
        "decision_reason": decision_reason,
        "confirmation_reference": "human_confirmation:decision-20",
        "evidence_references": evidence_references
        if evidence_references is not None
        else [
            {"evidence_reference": "selection_decision:17", "evidence_version_code": "v3"},
            {"evidence_reference": "job_analysis:9", "evidence_version_code": "v5"},
        ],
    }


def _command(payload: dict[str, object]) -> EmploymentMutationCommand:
    """Build one deterministic employment command through the HTTP mapping boundary."""
    command = _command_for_route(
        "employment-records",
        TENANT,
        payload,
        _id_factory(iter(GENERATED_IDS)),
        "idempotency-key-reason-20",
    )
    if not isinstance(command, EmploymentMutationCommand):
        raise AssertionError("employment route did not return EmploymentMutationCommand")
    return command


def _authorization(command: EmploymentMutationCommand) -> AuthorizationDecision:
    """Return evaluator-issued authorization evidence for digest comparison."""
    return issued_authorization(
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-20",
        resource_reference=f"employment_record:{command.employment_record_id.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="employment_record",
        requested_fields=frozenset({"employment_record"}),
        required_scope_code="orgmetra.people.write",
    )


class DecisionReasonBindingTests(unittest.TestCase):
    """Require reason drift to change immutable retry and audit correlation evidence."""

    def test_decision_reason_changes_governance_binding_and_command_digest(self) -> None:
        """A changed high-impact reason must never replay as the same semantic command."""
        first_reason = "Create the exclusive employment after accountable hire confirmation."
        second_reason = "Create the exclusive employment after corrected accountable review."
        first = _command(_payload(decision_reason=first_reason))
        second = _command(_payload(decision_reason=second_reason))

        self.assertRegex(first.evidence_version_code, _GOVERNANCE_BINDING_PATTERN)
        self.assertRegex(second.evidence_version_code, _GOVERNANCE_BINDING_PATTERN)
        self.assertNotEqual(first.evidence_version_code, second.evidence_version_code)
        self.assertNotIn(first_reason, first.evidence_version_code)
        self.assertNotIn(second_reason, second.evidence_version_code)
        self.assertNotEqual(
            mutation_command_digest(command=first, authorization=_authorization(first)),
            mutation_command_digest(command=second, authorization=_authorization(second)),
        )

    def test_evidence_order_does_not_change_same_governance_binding(self) -> None:
        """Equivalent evidence sets remain order-insensitive after reason binding."""
        reason = "Create the employment after reviewed selection evidence."
        evidence = [
            {"evidence_reference": "selection_decision:17", "evidence_version_code": "v3"},
            {"evidence_reference": "job_analysis:9", "evidence_version_code": "v5"},
        ]
        forward = _command(_payload(decision_reason=reason, evidence_references=evidence))
        reverse = _command(_payload(decision_reason=reason, evidence_references=list(reversed(evidence))))
        self.assertEqual(forward.evidence_version_code, reverse.evidence_version_code)


if __name__ == "__main__":
    unittest.main()
