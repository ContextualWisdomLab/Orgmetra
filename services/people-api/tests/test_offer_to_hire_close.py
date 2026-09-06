"""Executable contracts for closing accepted offers through authoritative hire materialization."""

from __future__ import annotations

from datetime import date, datetime, timezone
import unittest
from uuid import UUID

from orgmetra_candidate_offer_response import build_candidate_offer_response
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.hire import HireAcceptanceCommand, HireAcceptanceResult
from orgmetra_people_api.offer_close import (
    CandidateOfferHireAuthority,
    CandidateOfferHireVerification,
    OfferToHireIntegrityError,
    close_accepted_offer_to_hire,
)

TENANT = UUID("0198a412-7000-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a412-7000-7000-8000-000000000099")
CANDIDATE = UUID("0198a412-7000-7000-8000-000000000010")
OTHER_CANDIDATE = UUID("0198a412-7000-7000-8000-000000000098")
DECISION = UUID("0198a412-7000-7000-8000-000000000011")
PERSON = UUID("0198a412-7000-7000-8000-000000000020")
PERSON_NAME = UUID("0198a412-7000-7000-8000-000000000021")
EMPLOYMENT = UUID("0198a412-7000-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-7000-7000-8000-000000000031")
CONVERSION = UUID("0198a412-7000-7000-8000-000000000040")
AUDIT_EVENT = UUID("0198a412-7000-7000-8000-000000000050")
OUTBOX_DELIVERY = UUID("0198a412-7000-7000-8000-000000000051")
CANDIDATE_PROFILE_REFERENCE = "candidate_profile:6ba7b810-9dad-41d1-80b4-00c04fd430c8"
RESPONSE_REFERENCE = "candidate_offer_response:6ba7b811-9dad-41d1-80b4-00c04fd430c8"
OFFER_APPROVAL_REFERENCE = "offer_approval:6ba7b812-9dad-41d1-80b4-00c04fd430c8"
OFFER_TERMS_REFERENCE = "offer_terms:6ba7b813-9dad-41d1-80b4-00c04fd430c8"
IDENTITY_RESOLUTION_REFERENCE = "identity_resolution:6ba7b814-9dad-41d1-80b4-00c04fd430c8"
AUTHORITY_EVIDENCE_REFERENCE = "offer_hire_verification:6ba7b815-9dad-41d1-80b4-00c04fd430c8"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
RESPONDED_AT = datetime(2026, 8, 24, 7, 0, tzinfo=timezone.utc)
RECORDED_AT = datetime(2026, 8, 24, 7, 1, tzinfo=timezone.utc)


def response(*, response_code: str = "offer_accepted", tenant_record_id: str | None = None):
    """Build one value-minimized candidate offer response."""
    return build_candidate_offer_response(
        tenant_record_id=tenant_record_id or str(TENANT),
        offer_response_reference=RESPONSE_REFERENCE,
        candidate_profile_reference=CANDIDATE_PROFILE_REFERENCE,
        offer_approval_reference=OFFER_APPROVAL_REFERENCE,
        offer_approval_digest=DIGEST_A,
        offer_terms_reference=OFFER_TERMS_REFERENCE,
        offer_terms_digest=DIGEST_B,
        candidate_actor_reference="candidate:subject-17",
        identity_resolution_reference=IDENTITY_RESOLUTION_REFERENCE,
        identity_resolution_digest=DIGEST_C,
        response_code=response_code,
        responded_at=RESPONDED_AT,
        recorded_at=RECORDED_AT,
    )


def command(**overrides: object) -> HireAcceptanceCommand:
    """Build one deterministic confirmed-hire command."""
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
        "effective_from": date(2026, 8, 25),
        "display_name": "Ada Lovelace",
        "idempotency_key": "offer-close-idempotency-17",
        "employment_status_code": "active",
    }
    values.update(overrides)
    return HireAcceptanceCommand(**values)  # type: ignore[arg-type]


PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference="keyverse_subject:operator-17",
    granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
)
POLICY = PurposeBoundAccessPolicy(
    tenant_record_id=TENANT,
    policy_version_code="people-hire-v1",
    resource_kind="selection_decision",
    purpose_code="candidate_hire",
    operation_code="materialize_worker",
    required_scope_code="orgmetra.people.materialize_worker",
    permitted_fields=frozenset({"candidate_worker_conversion"}),
)


class RecordingHirePort:
    """Capture authoritative hire calls without persisting HR data."""

    def __init__(self) -> None:
        """Start with no persistence calls."""
        self.calls: list[HireAcceptanceCommand] = []

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        """Record one already-authorized hire command."""
        del authorization
        self.calls.append(command)
        return HireAcceptanceResult(
            person_record_id=command.person_record_id,
            employment_record_id=command.employment_record_id,
            candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
        )


class RecordingAuthority:
    """Resolve candidate-response evidence to exact authoritative hire scope."""

    def __init__(self) -> None:
        """Start with no authority calls and no forged output overrides."""
        self.calls: list[dict[str, object]] = []
        self.mutate_response = None
        self.override: dict[str, object] = {}

    def verify_offer_acceptance(self, **scope: object) -> CandidateOfferHireVerification:
        """Return exact-scope authority evidence for the reviewed response."""
        self.calls.append(scope)
        if self.mutate_response is not None:
            self.mutate_response()
        values: dict[str, object] = {
            "tenant_record_id": TENANT,
            "candidate_profile_id": CANDIDATE,
            "selection_decision_id": DECISION,
            "offer_response_digest": scope["offer_response_digest"],
            "offer_approval_digest": DIGEST_A,
            "offer_terms_digest": DIGEST_B,
            "candidate_actor_reference": "candidate:subject-17",
            "authority_evidence_reference": AUTHORITY_EVIDENCE_REFERENCE,
            "authority_evidence_digest": DIGEST_D,
        }
        values.update(self.override)
        return CandidateOfferHireVerification(**values)  # type: ignore[arg-type]


def valid_verification(**overrides: object) -> CandidateOfferHireVerification:
    """Build one exact authoritative verification for constructor-integrity tests."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "candidate_profile_id": CANDIDATE,
        "selection_decision_id": DECISION,
        "offer_response_digest": DIGEST_C,
        "offer_approval_digest": DIGEST_A,
        "offer_terms_digest": DIGEST_B,
        "candidate_actor_reference": "candidate:subject-17",
        "authority_evidence_reference": AUTHORITY_EVIDENCE_REFERENCE,
        "authority_evidence_digest": DIGEST_D,
    }
    values.update(overrides)
    return CandidateOfferHireVerification(**values)  # type: ignore[arg-type]


class OfferToHireCloseTests(unittest.TestCase):
    """Prove candidate response is necessary evidence but never hire authority itself."""

    def test_declined_offer_never_reaches_authority_or_hire_port(self) -> None:
        """A candidate decline must stop before authoritative hire work."""
        authority = RecordingAuthority()
        port = RecordingHirePort()

        with self.assertRaisesRegex(OfferToHireIntegrityError, "accepted"):
            close_accepted_offer_to_hire(
                response=response(response_code="offer_declined"),
                principal=PRINCIPAL,
                command=command(),
                purpose_code="candidate_hire",
                policy=POLICY,
                authority=authority,
                mutation_port=port,
            )

        self.assertEqual(authority.calls, [])
        self.assertEqual(port.calls, [])

    def test_accepted_offer_requires_authoritative_mapping_before_hire(self) -> None:
        """A valid response reaches the existing confirmed-hire path only after exact-scope verification."""
        authority = RecordingAuthority()
        port = RecordingHirePort()
        packet = response()

        result = close_accepted_offer_to_hire(
            response=packet,
            principal=PRINCIPAL,
            command=command(),
            purpose_code="candidate_hire",
            policy=POLICY,
            authority=authority,
            mutation_port=port,
        )

        self.assertIsInstance(authority, CandidateOfferHireAuthority)
        self.assertEqual(result.employment_record_id, EMPLOYMENT)
        self.assertEqual(port.calls, [command()])
        self.assertEqual(len(authority.calls), 1)
        scope = authority.calls[0]
        self.assertEqual(scope["tenant_record_id"], str(TENANT))
        self.assertEqual(scope["candidate_profile_reference"], CANDIDATE_PROFILE_REFERENCE)
        self.assertEqual(scope["selection_decision_id"], DECISION)
        self.assertEqual(scope["offer_response_digest"], packet.sha256_digest())
        self.assertEqual(scope["offer_approval_digest"], DIGEST_A)
        self.assertEqual(scope["offer_terms_digest"], DIGEST_B)
        self.assertEqual(repr(valid_verification()), "CandidateOfferHireVerification(<redacted>)")

    def test_authority_scope_mismatch_blocks_hire(self) -> None:
        """A response-to-selection mapping cannot be widened after authority verification."""
        for field_name, value, message in (
            ("tenant_record_id", OTHER_TENANT, "tenant"),
            ("candidate_profile_id", OTHER_CANDIDATE, "candidate profile"),
            ("selection_decision_id", UUID("0198a412-7000-7000-8000-000000000097"), "selection decision"),
        ):
            authority = RecordingAuthority()
            authority.override[field_name] = value
            port = RecordingHirePort()
            with self.subTest(field_name=field_name), self.assertRaisesRegex(OfferToHireIntegrityError, message):
                close_accepted_offer_to_hire(
                    response=response(),
                    principal=PRINCIPAL,
                    command=command(),
                    purpose_code="candidate_hire",
                    policy=POLICY,
                    authority=authority,
                    mutation_port=port,
                )
            self.assertEqual(port.calls, [])

    def test_authority_must_bind_exact_response_and_offer_evidence(self) -> None:
        """Authoritative mapping must echo exact immutable response, offer, and candidate provenance."""
        for field_name, value in (
            ("offer_response_digest", "e" * 64),
            ("offer_approval_digest", "e" * 64),
            ("offer_terms_digest", "e" * 64),
            ("candidate_actor_reference", "candidate:other-subject"),
        ):
            authority = RecordingAuthority()
            authority.override[field_name] = value
            port = RecordingHirePort()
            with self.subTest(field_name=field_name), self.assertRaises(OfferToHireIntegrityError):
                close_accepted_offer_to_hire(
                    response=response(),
                    principal=PRINCIPAL,
                    command=command(),
                    purpose_code="candidate_hire",
                    policy=POLICY,
                    authority=authority,
                    mutation_port=port,
                )
            self.assertEqual(port.calls, [])

    def test_authority_time_response_mutation_blocks_hire(self) -> None:
        """Mutating response evidence during authority work must not authorize a hire."""
        packet = response()
        authority = RecordingAuthority()
        authority.mutate_response = lambda: object.__setattr__(packet, "offer_terms_digest", "f" * 64)
        port = RecordingHirePort()

        with self.assertRaisesRegex(OfferToHireIntegrityError, "changed during authoritative verification"):
            close_accepted_offer_to_hire(
                response=packet,
                principal=PRINCIPAL,
                command=command(),
                purpose_code="candidate_hire",
                policy=POLICY,
                authority=authority,
                mutation_port=port,
            )

        self.assertEqual(port.calls, [])

    def test_preexisting_response_tamper_fails_before_authority(self) -> None:
        """A response rewritten before orchestration must fail before authority work."""
        packet = response()
        object.__setattr__(packet, "offer_terms_digest", "f" * 64)
        authority = RecordingAuthority()

        with self.assertRaisesRegex(OfferToHireIntegrityError, "not intact"):
            close_accepted_offer_to_hire(
                response=packet,
                principal=PRINCIPAL,
                command=command(),
                purpose_code="candidate_hire",
                policy=POLICY,
                authority=authority,
                mutation_port=RecordingHirePort(),
            )

        self.assertEqual(authority.calls, [])

    def test_command_and_response_tenant_must_match_before_authority(self) -> None:
        """A foreign-tenant command cannot reuse candidate response evidence."""
        authority = RecordingAuthority()

        with self.assertRaisesRegex(OfferToHireIntegrityError, "tenant"):
            close_accepted_offer_to_hire(
                response=response(),
                principal=PRINCIPAL,
                command=command(tenant_record_id=OTHER_TENANT),
                purpose_code="candidate_hire",
                policy=POLICY,
                authority=authority,
                mutation_port=RecordingHirePort(),
            )

        self.assertEqual(authority.calls, [])

    def test_untrusted_runtime_types_fail_before_authoritative_work(self) -> None:
        """Exact command/response types and one authority protocol are mandatory."""
        authority = RecordingAuthority()
        with self.assertRaisesRegex(TypeError, "response must be the exact"):
            close_accepted_offer_to_hire(
                response=object(),  # type: ignore[arg-type]
                principal=PRINCIPAL,
                command=command(),
                purpose_code="candidate_hire",
                policy=POLICY,
                authority=authority,
                mutation_port=RecordingHirePort(),
            )
        with self.assertRaisesRegex(TypeError, "command must be the exact"):
            close_accepted_offer_to_hire(
                response=response(),
                principal=PRINCIPAL,
                command=object(),  # type: ignore[arg-type]
                purpose_code="candidate_hire",
                policy=POLICY,
                authority=authority,
                mutation_port=RecordingHirePort(),
            )
        with self.assertRaisesRegex(TypeError, "authority must implement"):
            close_accepted_offer_to_hire(
                response=response(),
                principal=PRINCIPAL,
                command=command(),
                purpose_code="candidate_hire",
                policy=POLICY,
                authority=object(),  # type: ignore[arg-type]
                mutation_port=RecordingHirePort(),
            )
        self.assertEqual(authority.calls, [])

    def test_verification_runtime_subclass_cannot_cross_trust_boundary(self) -> None:
        """Caller-defined verification subtypes cannot become authoritative evidence."""
        class ForgedVerification(CandidateOfferHireVerification):
            """Represent an untrusted subtype that must be rejected."""

        class ForgedAuthority(RecordingAuthority):
            """Return a forged verification subtype."""

            def verify_offer_acceptance(self, **scope: object) -> CandidateOfferHireVerification:
                """Construct the otherwise-valid forged subtype."""
                value = super().verify_offer_acceptance(**scope)
                return ForgedVerification(
                    tenant_record_id=value.tenant_record_id,
                    candidate_profile_id=value.candidate_profile_id,
                    selection_decision_id=value.selection_decision_id,
                    offer_response_digest=value.offer_response_digest,
                    offer_approval_digest=value.offer_approval_digest,
                    offer_terms_digest=value.offer_terms_digest,
                    candidate_actor_reference=value.candidate_actor_reference,
                    authority_evidence_reference=value.authority_evidence_reference,
                    authority_evidence_digest=value.authority_evidence_digest,
                )

        with self.assertRaisesRegex(TypeError, "exact CandidateOfferHireVerification"):
            close_accepted_offer_to_hire(
                response=response(),
                principal=PRINCIPAL,
                command=command(),
                purpose_code="candidate_hire",
                policy=POLICY,
                authority=ForgedAuthority(),
                mutation_port=RecordingHirePort(),
            )

    def test_verification_constructor_rejects_malformed_authority_evidence(self) -> None:
        """Every trust-bearing authority field must fail closed before orchestration."""
        invalid_values = (
            {"tenant_record_id": UUID(int=0)},
            {"candidate_profile_id": "not-a-uuid"},
            {"selection_decision_id": UUID(int=(1 << 128) - 1)},
            {"offer_response_digest": "A" * 64},
            {"offer_approval_digest": 17},
            {"offer_terms_digest": "short"},
            {"candidate_actor_reference": "actor:wrong-owner"},
            {"candidate_actor_reference": "candidate:" + "x" * 300},
            {"authority_evidence_reference": 17},
            {"authority_evidence_reference": "offer_hire_verification:not-a-uuid"},
            {"authority_evidence_reference": "offer_hire_verification:6ba7b810-9dad-11d1-80b4-00c04fd430c8"},
            {"authority_evidence_digest": "z" * 64},
        )
        for overrides in invalid_values:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                valid_verification(**overrides)

    def test_post_construction_verification_rewrite_is_revalidated(self) -> None:
        """Frozen verification evidence rewritten with object primitives must still fail closed."""
        authority = RecordingAuthority()
        original = authority.verify_offer_acceptance(offer_response_digest=DIGEST_C)
        object.__setattr__(original, "authority_evidence_digest", "z" * 64)

        class RewrittenAuthority:
            """Return the rewritten verification object."""

            def verify_offer_acceptance(self, **scope: object) -> CandidateOfferHireVerification:
                """Ignore the current request and return the corrupted authority evidence."""
                del scope
                return original

        with self.assertRaises(ValueError):
            close_accepted_offer_to_hire(
                response=response(),
                principal=PRINCIPAL,
                command=command(),
                purpose_code="candidate_hire",
                policy=POLICY,
                authority=RewrittenAuthority(),
                mutation_port=RecordingHirePort(),
            )


if __name__ == "__main__":
    unittest.main()
