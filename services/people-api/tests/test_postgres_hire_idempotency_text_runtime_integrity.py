"""Runtime-integrity contracts for durable hire idempotency digest text."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.hire import HireAcceptanceCommand, HireDecisionIntegrityError
from orgmetra_people_api.postgres_hire import _hire_command_digest, _replayed_hire

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
ACTOR = "keyverse_subject:operator-17"
PURPOSE = "candidate_hire"


class _ExecutableText(str):
    """Expose comparison performed before exact durable-text validation."""

    def __eq__(self, other: object) -> bool:
        """Fail if untrusted text participates in trusted equality."""
        del other
        raise AssertionError("text subtype equality executed before exact-type validation")

    def __ne__(self, other: object) -> bool:
        """Fail if untrusted text participates in trusted inequality."""
        del other
        raise AssertionError("text subtype inequality executed before exact-type validation")


class _ReplayCursor:
    """Return one durable idempotency row without touching a real database."""

    def __init__(self, row: tuple[object, object]) -> None:
        """Store the single replay row returned after advisory serialization."""
        self._row = row

    def execute(self, statement: str, parameters: tuple[object, ...]) -> None:
        """Accept the two read-side SQL calls used by replay resolution."""
        assert statement
        assert parameters

    def fetchmany(self, size: int) -> list[tuple[object, object]]:
        """Return the configured row using the adapter's bounded read size."""
        assert size == 2
        return [self._row]


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
        idempotency_key="hire-idempotency-text-runtime-integrity",
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


def test_hire_replay_rejects_digest_subtype_before_comparison() -> None:
    """Database-returned digest subtypes must fail without executing comparison hooks."""
    command = _command()
    authorization = _authorization()
    digest = _ExecutableText(_hire_command_digest(command, authorization))
    cursor: Any = _ReplayCursor((CONVERSION, digest))

    with pytest.raises(HireDecisionIntegrityError, match="hire idempotency row is invalid"):
        _replayed_hire(cursor, command=command, authorization=authorization)


def test_hire_replay_accepts_exact_builtin_digest_text() -> None:
    """An exact persisted digest still replays the exact committed conversion."""
    command = _command()
    authorization = _authorization()
    digest = _hire_command_digest(command, authorization)
    cursor: Any = _ReplayCursor((CONVERSION, digest))

    result = _replayed_hire(cursor, command=command, authorization=authorization)

    assert result is not None
    assert result.candidate_worker_conversion_record_id == CONVERSION
