"""Regressions for semantic revalidation at durable People authorization boundaries."""

from __future__ import annotations

import unittest

from orgmetra_people_api.hire import HireDecisionIntegrityError
from orgmetra_people_api.mutations import PeopleMutationIntegrityError, mutation_command_digest
from orgmetra_people_api.postgres_hire import _validate_authorization as validate_hire_authorization
from orgmetra_people_api.postgres_mutations import _require_authorization as require_people_authorization
from test_people_mutations import EMPLOYMENT, TENANT, employment_command
from test_postgres_hire_acceptance import allowed_authorization, command as hire_command
from test_postgres_people_mutations import employment_authorization


def _contradict_allowed_decision(decision: object) -> object:
    """Simulate post-construction corruption that leaves the runtime class unchanged."""
    object.__setattr__(decision, "reason_code", "access_denied")
    return decision


class AuthorizationDecisionDurableRevalidationTests(unittest.TestCase):
    """Require durable consumers to reject contradictory exact decision objects."""

    def test_semantic_digest_revalidates_decision_before_reading_evidence(self) -> None:
        """Idempotency evidence must not hash a contradictory allow decision."""
        decision = _contradict_allowed_decision(employment_authorization())

        with self.assertRaises(ValueError):
            mutation_command_digest(
                command=employment_command(),
                authorization=decision,  # type: ignore[arg-type]
            )

    def test_generic_postgres_boundary_revalidates_before_accepting_allow(self) -> None:
        """Generic persistence must reject a contradictory exact decision before SQL."""
        decision = _contradict_allowed_decision(employment_authorization())

        with self.assertRaises(PeopleMutationIntegrityError):
            require_people_authorization(
                authorization=decision,
                tenant_record_id=TENANT,
                resource_reference=f"employment_record:{EMPLOYMENT.hex}",
                resource_kind="employment_record",
                requested_fields=frozenset({"employment_record"}),
            )

    def test_hire_postgres_boundary_revalidates_before_accepting_allow(self) -> None:
        """Hire persistence must reject a contradictory exact decision before SQL."""
        decision = _contradict_allowed_decision(allowed_authorization())

        with self.assertRaises(HireDecisionIntegrityError):
            validate_hire_authorization(hire_command(), decision)


if __name__ == "__main__":
    unittest.main()
