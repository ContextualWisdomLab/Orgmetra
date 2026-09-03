"""Regressions for exact evidence-reference validation and semantic binding."""

from __future__ import annotations

from datetime import date
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.mutation_http import _command_for_route
from orgmetra_people_api.mutations import mutation_command_digest
from authorization_test_support import issued_authorization

TENANT = UUID("0198a412-8200-7000-8000-000000000001")
PERSON = UUID("0198a412-8200-7000-8000-000000000020")
EMPLOYMENT = UUID("0198a412-8200-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-8200-7000-8000-000000000031")
AUDIT_EVENT = UUID("0198a412-8200-7000-8000-000000000080")
OUTBOX = UUID("0198a412-8200-7000-8000-000000000081")


class SequentialIdFactory:
    """Return deterministic identifiers for one HTTP command construction."""

    def __init__(self) -> None:
        self._values = iter((EMPLOYMENT, EMPLOYMENT_VERSION, AUDIT_EVENT, OUTBOX))

    def __call__(self) -> UUID:
        """Return the next deterministic operational UUID."""
        return next(self._values)


def employment_payload(evidence_references: list[object]) -> dict[str, object]:
    """Return one otherwise-valid high-impact employment request body."""
    return {
        "person_record_id": str(PERSON),
        "employment_status_code": "active",
        "employment_concurrency_code": "exclusive",
        "effective_from": date(2026, 8, 19).isoformat(),
        "decision_reason": "Human-confirmed workforce administration action.",
        "confirmation_reference": "human_confirmation:review-99",
        "evidence_references": evidence_references,
    }


def command_for(evidence_references: list[object]):
    """Build one employment command from the public evidence-reference shape."""
    return _command_for_route(
        "employment-records",
        TENANT,
        employment_payload(evidence_references),
        SequentialIdFactory(),
        "idempotency-evidence-99",
    )


def authorization() -> AuthorizationDecision:
    """Return evaluator-issued allow evidence used solely for command digests."""
    return issued_authorization(
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-99",
        resource_reference=f"employment_record:{EMPLOYMENT.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="employment_record",
        requested_fields=frozenset({"employment_record"}),
        required_scope_code="orgmetra.people.write",
    )


class EvidenceReferenceBindingRegressionTests(unittest.TestCase):
    """Prove every evidence item is validated and bound into retry semantics."""

    def test_openapi_evidence_reference_shape_fails_closed(self) -> None:
        cases = (
            [{"evidence_version_code": "v1"}],
            [{"evidence_reference": "decision:17", "evidence_version_code": "v1", "candidate_name": "do-not-copy"}],
            [{"evidence_reference": 17, "evidence_version_code": "v1"}],
            [{"evidence_reference": "", "evidence_version_code": "v1"}],
            [{"evidence_reference": "decision:17", "evidence_version_code": 1}],
            [{"evidence_reference": "decision:17", "evidence_version_code": ""}],
            [{"evidence_reference": "x" * 501, "evidence_version_code": "v1"}],
            [{"evidence_reference": "decision:17", "evidence_version_code": "v" * 201}],
            [{"evidence_reference": f"decision:{index}", "evidence_version_code": "v1"} for index in range(101)],
            [
                {"evidence_reference": "decision:17", "evidence_version_code": "v1"},
                {"evidence_reference": "decision:17", "evidence_version_code": "v1"},
            ],
        )
        for evidence_references in cases:
            with self.subTest(evidence_references=evidence_references), self.assertRaises(ValueError):
                command_for(evidence_references)

    def test_entire_evidence_set_is_bound_to_semantic_idempotency_digest(self) -> None:
        first = [
            {"evidence_reference": "decision:17", "evidence_version_code": "v1"},
            {"evidence_reference": "job_analysis:42", "evidence_version_code": "v3"},
        ]
        changed_second_version = [
            {"evidence_reference": "decision:17", "evidence_version_code": "v1"},
            {"evidence_reference": "job_analysis:42", "evidence_version_code": "v4"},
        ]
        changed_second_reference = [
            {"evidence_reference": "decision:17", "evidence_version_code": "v1"},
            {"evidence_reference": "job_analysis:43", "evidence_version_code": "v3"},
        ]
        decision = authorization()
        first_digest = mutation_command_digest(command=command_for(first), authorization=decision)
        self.assertNotEqual(
            first_digest,
            mutation_command_digest(command=command_for(changed_second_version), authorization=decision),
        )
        self.assertNotEqual(
            first_digest,
            mutation_command_digest(command=command_for(changed_second_reference), authorization=decision),
        )
        self.assertEqual(
            first_digest,
            mutation_command_digest(command=command_for(list(reversed(first))), authorization=decision),
        )


if __name__ == "__main__":
    unittest.main()
