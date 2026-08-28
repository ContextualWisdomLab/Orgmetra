"""Regression for authorization ordering in accepted-offer hire orchestration."""

from __future__ import annotations

from datetime import date, datetime, timezone
import unittest
from uuid import UUID

from orgmetra_candidate_offer_response import build_candidate_offer_response
from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.hire import HireAcceptanceCommand, HireAcceptanceResult
from orgmetra_people_api.offer_close import CandidateOfferHireVerification, close_accepted_offer_to_hire

TENANT = UUID("0198a412-7000-7000-8000-000000000001")
CANDIDATE = UUID("0198a412-7000-7000-8000-000000000010")
DECISION = UUID("0198a412-7000-7000-8000-000000000011")
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64


class RecordingAuthority:
    """Record whether protected candidate/offer resolution was attempted."""

    def __init__(self) -> None:
        """Start with no protected-resolution calls."""
        self.calls = 0

    def verify_offer_acceptance(self, **scope: object) -> CandidateOfferHireVerification:
        """Return valid evidence only if incorrectly reached before denial."""
        self.calls += 1
        return CandidateOfferHireVerification(
            tenant_record_id=TENANT,
            candidate_profile_id=CANDIDATE,
            selection_decision_id=DECISION,
            offer_response_digest=str(scope["offer_response_digest"]),
            offer_approval_digest=DIGEST_A,
            offer_terms_digest=DIGEST_B,
            candidate_actor_reference="candidate:subject-17",
            authority_evidence_reference="offer_hire_verification:6ba7b815-9dad-41d1-80b4-00c04fd430c8",
            authority_evidence_digest=DIGEST_D,
        )


class RecordingPort:
    """Fail if hire persistence is reached after an authorization denial."""

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        """Raise because denied requests must never reach persistence."""
        del command, authorization
        raise AssertionError("denied offer-to-hire request reached persistence")


class OfferToHireAuthorizationOrderTests(unittest.TestCase):
    """Require purpose-bound authorization before protected offer/candidate resolution."""

    def test_policy_denial_prevents_authority_resolution(self) -> None:
        """Wrong-purpose callers must not invoke the candidate/offer authority resolver."""
        authority = RecordingAuthority()
        response = build_candidate_offer_response(
            tenant_record_id=str(TENANT),
            offer_response_reference="candidate_offer_response:6ba7b811-9dad-41d1-80b4-00c04fd430c8",
            candidate_profile_reference="candidate_profile:6ba7b810-9dad-41d1-80b4-00c04fd430c8",
            offer_approval_reference="offer_approval:6ba7b812-9dad-41d1-80b4-00c04fd430c8",
            offer_approval_digest=DIGEST_A,
            offer_terms_reference="offer_terms:6ba7b813-9dad-41d1-80b4-00c04fd430c8",
            offer_terms_digest=DIGEST_B,
            candidate_actor_reference="candidate:subject-17",
            identity_resolution_reference="identity_resolution:6ba7b814-9dad-41d1-80b4-00c04fd430c8",
            identity_resolution_digest=DIGEST_C,
            response_code="offer_accepted",
            responded_at=datetime(2026, 8, 24, 7, 0, tzinfo=timezone.utc),
            recorded_at=datetime(2026, 8, 24, 7, 1, tzinfo=timezone.utc),
        )
        command = HireAcceptanceCommand(
            tenant_record_id=TENANT,
            candidate_profile_id=CANDIDATE,
            selection_decision_id=DECISION,
            person_record_id=UUID("0198a412-7000-7000-8000-000000000020"),
            person_name_record_id=UUID("0198a412-7000-7000-8000-000000000021"),
            employment_record_id=UUID("0198a412-7000-7000-8000-000000000030"),
            employment_record_version_id=UUID("0198a412-7000-7000-8000-000000000031"),
            candidate_worker_conversion_record_id=UUID("0198a412-7000-7000-8000-000000000040"),
            audit_event_record_id=UUID("0198a412-7000-7000-8000-000000000050"),
            outbox_delivery_record_id=UUID("0198a412-7000-7000-8000-000000000051"),
            effective_from=date(2026, 8, 25),
            display_name="Ada Lovelace",
            idempotency_key="offer-close-auth-order-17",
        )
        principal = AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse_subject:operator-17",
            granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
        )
        denied_policy = PurposeBoundAccessPolicy(
            tenant_record_id=TENANT,
            policy_version_code="people-hire-v1",
            resource_kind="selection_decision",
            purpose_code="benefits_admin",
            operation_code="materialize_worker",
            required_scope_code="orgmetra.people.materialize_worker",
            permitted_fields=frozenset({"candidate_worker_conversion"}),
        )

        with self.assertRaises(AuthorizationDeniedError):
            close_accepted_offer_to_hire(
                response=response,
                principal=principal,
                command=command,
                purpose_code="candidate_hire",
                policy=denied_policy,
                authority=authority,
                mutation_port=RecordingPort(),
            )

        self.assertEqual(authority.calls, 0)


if __name__ == "__main__":
    unittest.main()
