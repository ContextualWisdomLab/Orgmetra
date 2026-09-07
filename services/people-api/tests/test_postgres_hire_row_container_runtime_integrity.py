"""Runtime-integrity contracts for durable hire row containers."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.hire import HireAcceptanceCommand, HireDecisionIntegrityError
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


class _ExecutableBatch(list[object]):
    """Fail if a fetched row collection is consumed before exact-type validation."""

    def __bool__(self) -> bool:
        """Reject pre-gate truthiness."""
        raise TypeError("row collection truthiness executed before exact-type validation")

    def __len__(self) -> int:
        """Reject pre-gate length inspection."""
        raise AssertionError("row collection length executed before exact-type validation")

    def __getitem__(self, key: object) -> object:
        """Reject pre-gate indexed access."""
        del key
        raise IndexError("row collection indexing executed before exact-type validation")

    def __iter__(self):
        """Reject pre-gate row iteration."""
        raise AssertionError("row collection iteration executed before exact-type validation")


class _ExecutableRow(tuple):
    """Fail if a fetched fixed row is consumed before exact-type validation."""

    def __len__(self) -> int:
        """Reject pre-gate row length inspection."""
        raise AssertionError("row length executed before exact-type validation")

    def __getitem__(self, key: object) -> object:
        """Reject pre-gate row indexing."""
        del key
        raise IndexError("row indexing executed before exact-type validation")

    def __iter__(self):
        """Reject pre-gate row iteration."""
        raise AssertionError("row iteration executed before exact-type validation")


class _Cursor:
    """Serve configured bounded fetch batches and record executed SQL."""

    def __init__(self, batches: list[object]) -> None:
        """Store the exact fetch results in adapter execution order."""
        self._batches = list(batches)
        self.executions: list[str] = []

    def __enter__(self) -> _Cursor:
        """Return the same cursor for the transaction context."""
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Leave exception handling to the connection context."""
        del exc_type, exc_value, traceback

    def execute(self, statement: str, parameters: tuple[object, ...] | None = None) -> None:
        """Record SQL without evaluating durable-row contents."""
        del parameters
        self.executions.append(statement)

    def fetchmany(self, size: int) -> object:
        """Return the next configured batch without touching its runtime hooks."""
        assert size == 2
        return self._batches.pop(0)


class _Connection:
    """Provide the focused cursor through a DB-API-style context boundary."""

    def __init__(self, cursor: _Cursor) -> None:
        """Retain the one cursor used by the focused durable-row tests."""
        self._cursor = cursor

    def __enter__(self) -> _Connection:
        """Return the same transaction connection."""
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Leave exception propagation unchanged."""
        del exc_type, exc_value, traceback

    def cursor(self) -> _Cursor:
        """Return the configured focused cursor."""
        return self._cursor


def _command() -> HireAcceptanceCommand:
    """Build one deterministic valid confirmed-hire command."""
    return HireAcceptanceCommand(
        tenant_record_id=TENANT,
        candidate_profile_id=CANDIDATE,
        selection_decision_id=DECISION,
        person_record_id=PERSON,
        person_name_record_id=PERSON_NAME,
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=EMPLOYMENT_VERSION,
        candidate_worker_conversion_record_id=CONVERSION,
        audit_event_record_id=AUDIT_EVENT,
        outbox_delivery_record_id=OUTBOX_DELIVERY,
        effective_from=date(2026, 8, 18),
        display_name="Ada Lovelace",
        idempotency_key="hire-row-container-runtime-integrity",
    )


def _authorization() -> AuthorizationDecision:
    """Build the exact allow decision required for the confirmed-hire command."""
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=TENANT,
        actor_reference=ACTOR,
        resource_reference=f"selection_decision:{DECISION.hex}",
        policy_version_code="people-hire-v1",
        purpose_code=PURPOSE,
        operation_code="materialize_worker",
        resource_kind="selection_decision",
        requested_fields=frozenset({"candidate_worker_conversion"}),
        authorized_fields=frozenset({"candidate_worker_conversion"}),
        reason_code="access_permitted",
        next_action="continue",
    )


def _decision_row() -> tuple[object, ...]:
    """Build one valid durable confirmed-hire provenance row."""
    return (
        ACTOR,
        PURPOSE,
        "hire",
        CONFIRMATION,
        DECIDED_AT,
        EVIDENCE_SET,
        TRANSACTION_AT,
    )


def _port(*batches: object) -> tuple[PostgresHireAcceptancePort, _Cursor]:
    """Build a port whose cursor returns the supplied bounded batches."""
    cursor = _Cursor(list(batches))
    return PostgresHireAcceptancePort(lambda: _Connection(cursor)), cursor


def test_hire_rejects_executable_idempotency_batch_before_collection_hooks() -> None:
    """Replay lookup must reject a batch subtype before truthiness or iteration."""
    port, cursor = _port(_ExecutableBatch())

    with pytest.raises(HireDecisionIntegrityError, match="hire idempotency row is invalid"):
        port.accept_hire(command=_command(), authorization=_authorization())

    assert not any("selection_decision AS decision" in statement for statement in cursor.executions)


def test_hire_rejects_executable_idempotency_row_before_row_hooks() -> None:
    """Replay lookup must reject a row subtype before length or unpacking."""
    port, cursor = _port([_ExecutableRow((CONVERSION, "digest"))])

    with pytest.raises(HireDecisionIntegrityError, match="hire idempotency row is invalid"):
        port.accept_hire(command=_command(), authorization=_authorization())

    assert not any("selection_decision AS decision" in statement for statement in cursor.executions)


def test_hire_rejects_executable_provenance_batch_before_collection_hooks() -> None:
    """Decision lookup must reject a batch subtype before truthiness or iteration."""
    port, cursor = _port([], _ExecutableBatch([_decision_row()]))

    with pytest.raises(HireDecisionIntegrityError, match="decision provenance row has an invalid shape"):
        port.accept_hire(command=_command(), authorization=_authorization())

    assert not any("INSERT INTO public.person_record" in statement for statement in cursor.executions)


def test_hire_rejects_executable_provenance_row_before_row_hooks() -> None:
    """Decision lookup must reject a row subtype before length or unpacking."""
    port, cursor = _port([], [_ExecutableRow(_decision_row())])

    with pytest.raises(HireDecisionIntegrityError, match="decision provenance row has an invalid shape"):
        port.accept_hire(command=_command(), authorization=_authorization())

    assert not any("INSERT INTO public.person_record" in statement for statement in cursor.executions)


def test_hire_rejects_wrong_width_exact_rows_at_the_container_boundary() -> None:
    """Exact built-in rows still require their fixed SQL projection width."""
    replay_port, _ = _port([(CONVERSION,)])
    with pytest.raises(HireDecisionIntegrityError, match="hire idempotency row is invalid"):
        replay_port.accept_hire(command=_command(), authorization=_authorization())

    provenance_port, _ = _port([], [(_decision_row()[0],)])
    with pytest.raises(HireDecisionIntegrityError, match="decision provenance row has an invalid shape"):
        provenance_port.accept_hire(command=_command(), authorization=_authorization())


def test_hire_accepts_exact_builtin_batches_and_rows() -> None:
    """Default Psycopg-compatible list batches and tuple rows remain accepted."""
    port, cursor = _port([], [_decision_row()])

    result = port.accept_hire(command=_command(), authorization=_authorization())

    assert result.candidate_worker_conversion_record_id == CONVERSION
    assert any("INSERT INTO public.person_record" in statement for statement in cursor.executions)
