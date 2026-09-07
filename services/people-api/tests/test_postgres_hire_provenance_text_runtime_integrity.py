"""Runtime-integrity contracts for durable hire decision-provenance text."""

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


class _ExecutableText(str):
    """Expose comparison performed before exact durable-text validation."""

    def __eq__(self, other: object) -> bool:
        """Fail if durable-row validation executes subtype equality."""
        del other
        raise AssertionError("provenance text equality executed before exact-type validation")

    def __ne__(self, other: object) -> bool:
        """Fail if durable-row validation executes subtype inequality."""
        del other
        raise AssertionError("provenance text inequality executed before exact-type validation")


class _Cursor:
    """Serve one idempotency miss followed by one decision-provenance row."""

    def __init__(self, decision_row: tuple[object, ...]) -> None:
        """Store the row and initialize transaction-observation state."""
        self._batches = [[], [decision_row]]
        self.executions: list[str] = []

    def __enter__(self) -> _Cursor:
        """Return the same cursor for the transaction context."""
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Leave exception handling to the connection context."""
        del exc_type, exc_value, traceback

    def execute(self, statement: str, parameters: tuple[object, ...] | None = None) -> None:
        """Record SQL without evaluating trust-bearing row values."""
        del parameters
        self.executions.append(statement)

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        """Return each bounded batch in adapter execution order."""
        assert size == 2
        return self._batches.pop(0)[:size]


class _Connection:
    """Provide the focused cursor through a DB-API-style context boundary."""

    def __init__(self, cursor: _Cursor) -> None:
        """Retain the one cursor used by the focused durable-row test."""
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
        idempotency_key="hire-provenance-text-runtime-integrity",
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


def _decision_row(**overrides: object) -> tuple[object, ...]:
    """Build one durable confirmed-hire provenance row in SQL column order."""
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
    return (
        values["actor_reference"],
        values["purpose_code"],
        values["decision_code"],
        values["confirmation_reference"],
        values["decided_at"],
        values["decision_evidence_set_id"],
        values["transaction_recorded_at"],
    )


@pytest.mark.parametrize(
    "field,value",
    (
        ("actor_reference", _ExecutableText(ACTOR)),
        ("purpose_code", _ExecutableText(PURPOSE)),
        ("decision_code", _ExecutableText("hire")),
        ("confirmation_reference", _ExecutableText(CONFIRMATION)),
    ),
)
def test_hire_rejects_provenance_text_subtype_before_business_write(field: str, value: object) -> None:
    """Database provenance text must be exact built-in text before semantic use."""
    cursor = _Cursor(_decision_row(**{field: value}))
    port = PostgresHireAcceptancePort(lambda: _Connection(cursor))

    with pytest.raises(HireDecisionIntegrityError, match="selection decision provenance text is invalid"):
        port.accept_hire(command=_command(), authorization=_authorization())

    assert not any("INSERT INTO public.person_record" in statement for statement in cursor.executions)


def test_hire_accepts_exact_builtin_provenance_text() -> None:
    """Exact Psycopg-compatible text remains valid durable decision provenance."""
    cursor = _Cursor(_decision_row())
    port = PostgresHireAcceptancePort(lambda: _Connection(cursor))

    result = port.accept_hire(command=_command(), authorization=_authorization())

    assert result.candidate_worker_conversion_record_id == CONVERSION
    assert any("INSERT INTO public.person_record" in statement for statement in cursor.executions)
