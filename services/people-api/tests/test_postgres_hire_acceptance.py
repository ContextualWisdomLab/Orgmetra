"""Executable contracts for atomic PostgreSQL hire materialization."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDecision, PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.hire import (
    HireAcceptanceCommand,
    HireAcceptanceResult,
    HireDecisionIntegrityError,
    HireDecisionNotFound,
    accept_confirmed_hire,
)
from orgmetra_people_api.postgres_hire import PostgresHireAcceptancePort

TENANT = UUID("0198a412-7100-7000-8000-000000000001")
CANDIDATE = UUID("0198a412-7100-7000-8000-000000000010")
DECISION = UUID("0198a412-7100-7000-8000-000000000011")
PERSON = UUID("0198a412-7100-7000-8000-000000000020")
PERSON_NAME = UUID("0198a412-7100-7000-8000-000000000021")
EMPLOYMENT = UUID("0198a412-7100-7000-8000-000000000030")
EMPLOYMENT_VERSION = UUID("0198a412-7100-7000-8000-000000000031")
CONVERSION = UUID("0198a412-7100-7000-8000-000000000040")
AUDIT_EVENT = UUID("0198a412-7100-7000-8000-000000000050")
OUTBOX_DELIVERY = UUID("0198a412-7100-7000-8000-000000000051")
EVIDENCE_SET = UUID("0198a412-7100-7000-8000-000000000060")
DECIDED_AT = datetime(2026, 8, 18, 0, 0, tzinfo=timezone.utc)
TRANSACTION_AT = datetime(2026, 8, 18, 0, 1, tzinfo=timezone.utc)
ACTOR = "keyverse_subject:operator-17"
PURPOSE = "candidate_hire"
CONFIRMATION = "human_confirmation:review-88"


def command(**overrides: object) -> HireAcceptanceCommand:
    """Build one deterministic hire command."""
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
        "effective_from": DECIDED_AT.date(),
        "display_name": "Ada Lovelace",
        "employment_status_code": "active",
    }
    values.update(overrides)
    return HireAcceptanceCommand(**values)  # type: ignore[arg-type]


def decision_row(**overrides: object) -> tuple[object, ...]:
    """Return one confirmed, sealed hire-decision provenance row."""
    values: dict[str, object] = {
        "actor_reference": ACTOR,
        "purpose_code": PURPOSE,
        "decision_code": "hire",
        "confirmation_reference": CONFIRMATION,
        "decided_at": DECIDED_AT,
        "decision_evidence_set_id": EVIDENCE_SET,
        "transaction_recorded_at": TRANSACTION_AT,
    }
    values.update(overrides)
    return tuple(values[key] for key in values)


def policy() -> PurposeBoundAccessPolicy:
    """Return the exact materialize-worker authorization policy."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-hire-v1",
        resource_kind="selection_decision",
        purpose_code=PURPOSE,
        operation_code="materialize_worker",
        required_scope_code="orgmetra.people.materialize_worker",
        permitted_fields=frozenset({"candidate_worker_conversion"}),
    )


PRINCIPAL = AuthenticatedPrincipal(
    tenant_record_id=TENANT,
    actor_reference=ACTOR,
    granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
)


class FakeCursor:
    """Capture SQL and serve a deterministic decision-provenance result."""

    def __init__(self, decision_rows: list[tuple[object, ...]]) -> None:
        self.decision_rows = decision_rows
        self.executions: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetch_sizes: list[int] = []

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, sql: str, parameters: tuple[object, ...] | None = None) -> None:
        self.executions.append((sql, parameters))

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        self.fetch_sizes.append(size)
        return self.decision_rows[:size]


class FakeConnection:
    """Model one transaction context whose exception exit represents rollback."""

    def __init__(self, cursor: FakeCursor) -> None:
        self.cursor_instance = cursor
        self.enter_count = 0
        self.exit_count = 0
        self.exit_exception: type[BaseException] | None = None

    def __enter__(self) -> FakeConnection:
        self.enter_count += 1
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.exit_count += 1
        self.exit_exception = exc_type if isinstance(exc_type, type) and issubclass(exc_type, BaseException) else None
        return None

    def cursor(self) -> FakeCursor:
        return self.cursor_instance


class PostgresHireAcceptanceTests(unittest.TestCase):
    """Prove one tenant-bound transaction owns HRIS, audit, outbox, and conversion writes."""

    def _port(
        self,
        rows: list[tuple[object, ...]],
    ) -> tuple[PostgresHireAcceptancePort, FakeConnection, FakeCursor]:
        cursor = FakeCursor(rows)
        connection = FakeConnection(cursor)
        return PostgresHireAcceptancePort(lambda: connection), connection, cursor

    def test_materializes_confirmed_hire_and_pii_minimized_audit_atomically(self) -> None:
        port, connection, cursor = self._port([decision_row()])
        request = command()

        result = accept_confirmed_hire(
            principal=PRINCIPAL,
            command=request,
            purpose_code=PURPOSE,
            policy=policy(),
            mutation_port=port,
        )

        self.assertEqual(
            result,
            HireAcceptanceResult(
                person_record_id=PERSON,
                employment_record_id=EMPLOYMENT,
                candidate_worker_conversion_record_id=CONVERSION,
            ),
        )
        self.assertEqual((connection.enter_count, connection.exit_count), (1, 1))
        self.assertIsNone(connection.exit_exception)
        self.assertEqual(cursor.fetch_sizes, [2])
        self.assertEqual(cursor.executions[0], ("SET TRANSACTION READ WRITE", None))
        self.assertEqual(
            cursor.executions[1],
            (
                "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)",
                (str(TENANT),),
            ),
        )
        provenance_sql, provenance_parameters = cursor.executions[2]
        self.assertIn("public.selection_decision", provenance_sql)
        self.assertIn("public.decision_evidence_set", provenance_sql)
        self.assertIn("public.selection_decision_evidence", provenance_sql)
        self.assertIn("pg_catalog.transaction_timestamp()", provenance_sql)
        self.assertEqual(provenance_parameters, (TENANT, DECISION, CANDIDATE))

        expected_tables = (
            "public.person_record",
            "public.person_name_record",
            "public.employment_record",
            "public.employment_record_version",
        )
        for execution, table_name in zip(cursor.executions[3:7], expected_tables, strict=True):
            self.assertIn(table_name, execution[0])
        self.assertEqual(cursor.executions[4][1][3], "Ada Lovelace")

        audit_sql, audit_parameters = cursor.executions[7]
        self.assertEqual(audit_sql, "SELECT public.record_audit_outbox_event(%s, %s, %s, %s, %s, %s)")
        self.assertIsNotNone(audit_parameters)
        assert audit_parameters is not None
        self.assertEqual(audit_parameters[:3], (TENANT, AUDIT_EVENT, OUTBOX_DELIVERY))
        envelope_text = audit_parameters[3]
        digest = audit_parameters[4]
        self.assertIsInstance(envelope_text, str)
        self.assertEqual(digest, sha256(envelope_text.encode("utf-8")).hexdigest())
        self.assertEqual(audit_parameters[5], "orgmetra_domain_events")
        envelope = json.loads(envelope_text)
        self.assertEqual(envelope["type"], "orgmetra.candidate.worker_converted")
        self.assertEqual(envelope["subject"], f"candidate_worker_conversion_record:{CONVERSION}")
        self.assertEqual(envelope["orgmetraactor"], ACTOR)
        self.assertEqual(envelope["orgmetrapurpose"], PURPOSE)
        self.assertEqual(envelope["orgmetrareason"], "candidate_hire_confirmed")
        self.assertEqual(envelope["orgmetraevidence"], f"decision_evidence_set:{EVIDENCE_SET}")
        self.assertEqual(envelope["orgmetraconfirmation"], CONFIRMATION)
        self.assertEqual(envelope["data"], {"high_impact": True, "result_code": "worker_created"})
        self.assertEqual(envelope["time"], "2026-08-18T00:01:00Z")
        self.assertNotIn("Ada Lovelace", envelope_text)

        conversion_sql, conversion_parameters = cursor.executions[8]
        self.assertIn("public.candidate_worker_conversion_record", conversion_sql)
        self.assertEqual(
            conversion_parameters,
            (TENANT, CONVERSION, CANDIDATE, PERSON, EMPLOYMENT, DECISION, AUDIT_EVENT, DECIDED_AT.date(), TRANSACTION_AT),
        )

    def test_missing_or_ambiguous_decision_fails_before_business_insert(self) -> None:
        scenarios = (
            ([], HireDecisionNotFound),
            ([decision_row(), decision_row()], HireDecisionIntegrityError),
        )
        for rows, error_type in scenarios:
            with self.subTest(error_type=error_type):
                port, connection, cursor = self._port(rows)
                with self.assertRaises(error_type):
                    accept_confirmed_hire(
                        principal=PRINCIPAL,
                        command=command(),
                        purpose_code=PURPOSE,
                        policy=policy(),
                        mutation_port=port,
                    )
                self.assertEqual(len(cursor.executions), 3)
                self.assertIs(connection.exit_exception, error_type)

    def test_decision_must_match_authorized_actor_purpose_and_hire_semantics(self) -> None:
        invalid_rows = (
            decision_row(actor_reference="keyverse_subject:other-operator"),
            decision_row(purpose_code="benefits_admin"),
            decision_row(decision_code="reject"),
            decision_row(confirmation_reference=""),
            decision_row(decision_evidence_set_id=UUID(int=0)),
            decision_row(transaction_recorded_at="not-a-datetime"),
            decision_row(decided_at=TRANSACTION_AT.replace(minute=2)),
        )
        for row in invalid_rows:
            with self.subTest(row=row):
                port, _, cursor = self._port([row])
                with self.assertRaises(HireDecisionIntegrityError):
                    accept_confirmed_hire(
                        principal=PRINCIPAL,
                        command=command(),
                        purpose_code=PURPOSE,
                        policy=policy(),
                        mutation_port=port,
                    )
                self.assertEqual(len(cursor.executions), 3)

    def test_effective_date_cannot_precede_confirmed_decision(self) -> None:
        port, _, cursor = self._port([decision_row()])
        with self.assertRaisesRegex(HireDecisionIntegrityError, "effective date"):
            accept_confirmed_hire(
                principal=PRINCIPAL,
                command=command(effective_from=date(2026, 8, 17)),
                purpose_code=PURPOSE,
                policy=policy(),
                mutation_port=port,
            )
        self.assertEqual(len(cursor.executions), 3)

    def test_forged_authorization_is_rejected_before_connection(self) -> None:
        calls = 0

        def factory() -> FakeConnection:
            nonlocal calls
            calls += 1
            return FakeConnection(FakeCursor([decision_row()]))

        port = PostgresHireAcceptancePort(factory)
        forged = AuthorizationDecision(
            allowed=False,
            tenant_record_id=TENANT,
            actor_reference=ACTOR,
            resource_reference=f"selection_decision:{DECISION.hex}",
            policy_version_code="people-hire-v1",
            purpose_code=PURPOSE,
            operation_code="materialize_worker",
            resource_kind="selection_decision",
            requested_fields=frozenset({"candidate_worker_conversion"}),
            authorized_fields=frozenset(),
            reason_code="access_denied",
            next_action="stop",
        )
        with self.assertRaisesRegex(HireDecisionIntegrityError, "authorization"):
            port.accept_hire(command=command(), authorization=forged)
        self.assertEqual(calls, 0)

    def test_connection_factory_must_be_callable(self) -> None:
        with self.assertRaisesRegex(TypeError, "connection_factory must be callable"):
            PostgresHireAcceptancePort(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
