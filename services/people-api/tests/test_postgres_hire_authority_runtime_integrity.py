"""Adversarial runtime-integrity contracts for the PostgreSQL hire authority boundary."""

from __future__ import annotations

from datetime import date
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
ACTOR = "keyverse_subject:operator-17"
PURPOSE = "candidate_hire"


class ForgedHireAcceptanceCommand(HireAcceptanceCommand):
    """Represent a validation-bypassing caller-defined hire command subtype."""


class ForgedAuthorizationDecision(AuthorizationDecision):
    """Represent a caller-defined authorization subtype at a trust boundary."""


def _command(command_type: type[HireAcceptanceCommand] = HireAcceptanceCommand) -> HireAcceptanceCommand:
    """Build one deterministic valid hire command using the requested runtime type."""
    return command_type(
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
        idempotency_key="hire-authority-runtime-integrity",
    )


def _authorization(
    authorization_type: type[AuthorizationDecision] = AuthorizationDecision,
) -> AuthorizationDecision:
    """Build one deterministic exact-scope allow decision using the requested runtime type."""
    return authorization_type(
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


def _forbidden_connection_factory() -> object:
    """Fail the regression if untrusted runtime input reaches database work."""
    raise AssertionError("database work must not begin for forged runtime authority objects")


def test_postgres_hire_port_rejects_command_subclass_before_database_work() -> None:
    """Require the persistence authority to accept only the exact governed command type."""
    port = PostgresHireAcceptancePort(_forbidden_connection_factory)

    with pytest.raises(TypeError, match="command must be a HireAcceptanceCommand"):
        port.accept_hire(
            command=_command(ForgedHireAcceptanceCommand),
            authorization=_authorization(),
        )


def test_postgres_hire_port_rejects_authorization_subclass_before_database_work() -> None:
    """Require the persistence authority to accept only the exact governed authorization type."""
    port = PostgresHireAcceptancePort(_forbidden_connection_factory)

    with pytest.raises(HireDecisionIntegrityError, match="typed authorization decision"):
        port.accept_hire(
            command=_command(),
            authorization=_authorization(ForgedAuthorizationDecision),
        )
