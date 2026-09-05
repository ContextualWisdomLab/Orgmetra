"""Reject post-construction rewrites at confirmed-hire consumer boundaries."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.auth import AuthenticatedPrincipal
from orgmetra_people_api.hire import (
    HireAcceptanceCommand,
    HireAcceptanceResult,
    accept_confirmed_hire,
)
from orgmetra_people_api.postgres_hire import PostgresHireAcceptancePort

TENANT = UUID("0198a412-7800-7000-8000-000000000001")
SELECTION_DECISION = UUID("0198a412-7800-7000-8000-000000000002")
PERSON = UUID("0198a412-7800-7000-8000-000000000003")
EMPLOYMENT = UUID("0198a412-7800-7000-8000-000000000004")
CONVERSION = UUID("0198a412-7800-7000-8000-000000000005")


class _ExecutableUUID(UUID):
    """Expose UUID rendering attempted before an exact runtime-type gate."""

    def __getattribute__(self, name: str) -> object:
        """Fail if a rewritten UUID is rendered before command revalidation."""
        if name == "hex":
            raise AssertionError("UUID subtype behavior executed before command revalidation")
        return super().__getattribute__(name)


class _RecordingPort:
    """Record whether a rewritten command crosses the application boundary."""

    def __init__(self) -> None:
        """Start with no durable-port invocation."""
        self.called = False

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        """Return one valid result if the application incorrectly calls the port."""
        del authorization
        self.called = True
        return HireAcceptanceResult(
            person_record_id=command.person_record_id,
            employment_record_id=command.employment_record_id,
            candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
        )


class _RewrittenResultPort:
    """Return an exact result whose identity was rewritten after construction."""

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        """Rewrite one exact result after its constructor invariant has already run."""
        del command, authorization
        result = HireAcceptanceResult(
            person_record_id=PERSON,
            employment_record_id=EMPLOYMENT,
            candidate_worker_conversion_record_id=CONVERSION,
        )
        object.__setattr__(result, "person_record_id", "not-a-uuid")
        return result


def _command() -> HireAcceptanceCommand:
    """Build one valid confirmed-hire command before deliberate low-level rewrite."""
    return HireAcceptanceCommand(
        tenant_record_id=TENANT,
        candidate_profile_id=UUID("0198a412-7800-7000-8000-000000000010"),
        selection_decision_id=SELECTION_DECISION,
        person_record_id=PERSON,
        person_name_record_id=UUID("0198a412-7800-7000-8000-000000000011"),
        employment_record_id=EMPLOYMENT,
        employment_record_version_id=UUID("0198a412-7800-7000-8000-000000000012"),
        candidate_worker_conversion_record_id=CONVERSION,
        audit_event_record_id=UUID("0198a412-7800-7000-8000-000000000013"),
        outbox_delivery_record_id=UUID("0198a412-7800-7000-8000-000000000014"),
        effective_from=date(2026, 9, 5),
        display_name="Ada Lovelace",
        idempotency_key="hire-post-construction-228",
        employment_status_code="active",
    )


def _principal() -> AuthenticatedPrincipal:
    """Return the authenticated principal for the application-boundary regression."""
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-228",
        granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    """Return the purpose-bound policy for confirmed-hire materialization."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-hire-v1",
        resource_kind="selection_decision",
        purpose_code="candidate_hire",
        operation_code="materialize_worker",
        required_scope_code="orgmetra.people.materialize_worker",
        permitted_fields=frozenset({"candidate_worker_conversion"}),
    )


def _rewrite_selection_decision(command: HireAcceptanceCommand) -> None:
    """Replace one validated UUID with executable subtype evidence after construction."""
    object.__setattr__(
        command,
        "selection_decision_id",
        _ExecutableUUID("0198a412-7800-7000-8000-0000000000ff"),
    )


def _forbidden_connection_factory() -> object:
    """Fail if a rewritten command reaches database acquisition."""
    raise AssertionError("database acquisition occurred before command revalidation")


def test_application_revalidates_rewritten_hire_command_before_authorization_rendering() -> None:
    """A rewritten command must fail before UUID rendering or the mutation port."""
    command = _command()
    _rewrite_selection_decision(command)
    port = _RecordingPort()

    with pytest.raises(ValueError, match="selection_decision_id must be an operational UUID"):
        accept_confirmed_hire(
            principal=_principal(),
            command=command,
            purpose_code="candidate_hire",
            policy=_policy(),
            mutation_port=port,
        )

    assert port.called is False


def test_application_revalidates_rewritten_exact_hire_result_before_return() -> None:
    """An exact result rewritten after construction must not leave the service boundary."""
    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        accept_confirmed_hire(
            principal=_principal(),
            command=_command(),
            purpose_code="candidate_hire",
            policy=_policy(),
            mutation_port=_RewrittenResultPort(),
        )


def test_postgres_port_revalidates_rewritten_hire_command_before_authorization_or_db() -> None:
    """Direct durable-port entry must reject rewritten evidence before callbacks or DB work."""
    command = _command()
    _rewrite_selection_decision(command)
    port = PostgresHireAcceptancePort(connection_factory=_forbidden_connection_factory)

    with pytest.raises(ValueError, match="selection_decision_id must be an operational UUID"):
        port.accept_hire(command=command, authorization=object())  # type: ignore[arg-type]
