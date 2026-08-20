"""Regression contracts for current People mutation review findings.

These tests intentionally exercise the public/application boundaries rather than
accepting review narration as evidence. They cover complete evidence-version
validation, exact assignment precision, serialized durable idempotency, the
confirmed-hire idempotency contract, shared HTTP header preconditions,
fail-closed route/command dispatch typing, and published mutation-security
scope.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast
import unittest
from uuid import UUID

from orgmetra_people_api.hire import HireAcceptanceCommand
from orgmetra_people_api.hire_http import (
    _UnsupportedMediaType,
    _parse_idempotency_key,
    _require_json_content_type,
)
from orgmetra_people_api.mutation_http import (
    PeopleMutationAsgiApp,
    _InvalidHttpRequest,
    _dispatch_mutation,
    _evidence_version,
)
from orgmetra_people_api.postgres_mutations import _LOOKUP_IDEMPOTENCY_SQL
from test_people_mutations import (
    PRINCIPAL,
    assignment_command,
    employment_command,
    position_command,
)


class CurrentReviewRegressionTests(unittest.TestCase):
    """Pin the exact data-integrity boundaries identified by current review."""

    def test_every_evidence_reference_requires_a_string_version(self) -> None:
        """Do not admit trailing unversioned or malformed evidence references."""
        valid_first = {"evidence_version_code": "decision_evidence_set:v1"}
        invalid_references = (
            {},
            {"evidence_version_code": 17},
            "not-a-mapping",
        )
        for invalid in invalid_references:
            with self.subTest(invalid=invalid), self.assertRaises(_InvalidHttpRequest):
                _evidence_version(
                    {
                        "evidence_references": [valid_first, invalid],
                    }
                )

    def test_assignment_command_rejects_more_than_four_decimal_places(self) -> None:
        """Prevent semantic digests from carrying precision the database cannot store."""
        with self.assertRaises(ValueError):
            assignment_command(allocation_ratio=Decimal("0.12345"))

    def test_idempotency_lookup_serializes_same_key_transactions(self) -> None:
        """The pre-write lookup must hold a transaction lock for one command key."""
        normalized = " ".join(_LOOKUP_IDEMPOTENCY_SQL.lower().split())
        self.assertIn("pg_advisory_xact_lock", normalized)
        self.assertIn("hashtextextended", normalized)
        self.assertIn("tenant_record_id", normalized)
        self.assertIn("command_route", normalized)
        self.assertIn("idempotency_key", normalized)

    def test_confirmed_hire_command_carries_validated_idempotency_key(self) -> None:
        """Confirmed-hire retries need the same durable key boundary as other writes."""
        command = HireAcceptanceCommand(
            tenant_record_id=UUID("0198a412-8000-7000-8000-000000000001"),
            candidate_profile_id=UUID("0198a412-8000-7000-8000-000000000002"),
            selection_decision_id=UUID("0198a412-8000-7000-8000-000000000003"),
            person_record_id=UUID("0198a412-8000-7000-8000-000000000004"),
            person_name_record_id=UUID("0198a412-8000-7000-8000-000000000005"),
            employment_record_id=UUID("0198a412-8000-7000-8000-000000000006"),
            employment_record_version_id=UUID("0198a412-8000-7000-8000-000000000007"),
            candidate_worker_conversion_record_id=UUID("0198a412-8000-7000-8000-000000000008"),
            audit_event_record_id=UUID("0198a412-8000-7000-8000-000000000009"),
            outbox_delivery_record_id=UUID("0198a412-8000-7000-8000-00000000000a"),
            effective_from=date(2026, 8, 18),
            display_name="Regression Worker",
            employment_status_code="active",
            idempotency_key="hire-idempotency-key-17",
        )
        self.assertEqual(command.idempotency_key, "hire-idempotency-key-17")
        with self.assertRaises(ValueError):
            HireAcceptanceCommand(
                tenant_record_id=command.tenant_record_id,
                candidate_profile_id=command.candidate_profile_id,
                selection_decision_id=command.selection_decision_id,
                person_record_id=command.person_record_id,
                person_name_record_id=command.person_name_record_id,
                employment_record_id=command.employment_record_id,
                employment_record_version_id=command.employment_record_version_id,
                candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
                audit_event_record_id=command.audit_event_record_id,
                outbox_delivery_record_id=command.outbox_delivery_record_id,
                effective_from=command.effective_from,
                display_name=command.display_name,
                employment_status_code=command.employment_status_code,
                idempotency_key="short",
            )

    def test_shared_json_content_type_helper_fails_closed_on_malformed_header_containers(self) -> None:
        """Cover defensive helper branches unreachable after validated idempotency headers."""
        malformed_headers = (
            {b"content-type": b"application/json"},
            [(b"content-type",)],
            [("content-type", "application/json")],
        )
        for headers in malformed_headers:
            with self.subTest(headers=headers), self.assertRaises(_UnsupportedMediaType):
                _require_json_content_type({"headers": headers})

    def test_idempotency_key_fails_closed_on_malformed_header_shape_and_types(self) -> None:
        """Reject malformed ASGI header containers before accepting a retry identity."""
        malformed_headers: tuple[object, ...] = (
            {b"idempotency-key": b"idempotency-key-17xx"},
            [(b"idempotency-key",)],
            [("idempotency-key", b"idempotency-key-17xx")],
            [(b"idempotency-key", "idempotency-key-17xx")],
        )
        for headers in malformed_headers:
            with self.subTest(headers=headers), self.assertRaises(_InvalidHttpRequest):
                _parse_idempotency_key({"headers": headers})

    def test_dispatch_rejects_commands_for_a_different_route(self) -> None:
        """Do not let a valid command type cross into another mutation route."""
        unreachable_app = cast(PeopleMutationAsgiApp, object())
        mismatches = (
            (
                "employment-records",
                position_command(),
                "employment route requires EmploymentMutationCommand",
            ),
            (
                "position-records",
                assignment_command(),
                "position route requires PositionMutationCommand",
            ),
            (
                "assignment-records",
                employment_command(),
                "assignment route requires AssignmentMutationCommand",
            ),
        )
        for route, command, error_message in mismatches:
            with self.subTest(route=route), self.assertRaisesRegex(TypeError, error_message):
                _dispatch_mutation(
                    route=route,
                    principal=PRINCIPAL,
                    command=command,
                    purpose_code="workforce_admin",
                    app=unreachable_app,
                )

    def test_security_contract_matches_published_openapi_header_scope(self) -> None:
        """Keep published command scope distinct from currently executable handlers."""
        repository_root = Path(__file__).resolve().parents[3]
        security_contract = (repository_root / "docs/SECURITY.md").read_text(encoding="utf-8")
        api_contract = (repository_root / "docs/API_CONTRACT.md").read_text(encoding="utf-8")
        openapi_contract = (repository_root / "schemas/openapi.yaml").read_text(encoding="utf-8")

        published_scope = (
            "The published OpenAPI employment, position, assignment, person, job-profile, "
            "and selection-decision command families require `X-Tenant-Reference`, "
            "`X-Actor-Reference`, and `X-Purpose-Code`"
        )
        executable_scope = (
            "The executable People mutation handlers added on this branch currently implement "
            "employment, position, and assignment creation with those headers."
        )
        self.assertIn(published_scope, security_contract)
        self.assertIn(executable_scope, security_contract)
        self.assertIn(
            "Employment, position, assignment, person, job-profile, and selection-decision commands",
            api_contract,
        )
        for operation_id in (
            "createEmploymentRecord",
            "createPositionRecord",
            "createAssignmentRecord",
            "createPersonRecord",
            "createJobProfile",
            "recordSelectionDecision",
        ):
            with self.subTest(operation_id=operation_id):
                self.assertIn(f"operationId: {operation_id}", openapi_contract)


if __name__ == "__main__":
    unittest.main()
