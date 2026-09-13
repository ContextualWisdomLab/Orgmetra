"""Runtime identity-integrity regressions for confirmed-hire contracts."""

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

TENANT = UUID("0198a412-7000-7000-8000-000000000001")


class _ForgedUUID(UUID):
    """Attempt to make immutable hire evidence render a different identity."""

    def __str__(self) -> str:
        """Render a caller-chosen UUID instead of the underlying value."""
        return "0198a412-7000-7000-8000-ffffffffffff"


class _UnvalidatedHireCommand(HireAcceptanceCommand):
    """Attempt to bypass base dataclass validation through dynamic post-init dispatch."""

    def __post_init__(self) -> None:
        """Intentionally skip the governed base validation."""


class _UnvalidatedHireResult(HireAcceptanceResult):
    """Attempt to return malformed persistence evidence through a result subclass."""

    def __post_init__(self) -> None:
        """Intentionally skip the governed base validation."""


def _command_values(**overrides: object) -> dict[str, object]:
    """Return one otherwise-valid confirmed-hire command mapping."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "candidate_profile_id": UUID("0198a412-7000-7000-8000-000000000010"),
        "selection_decision_id": UUID("0198a412-7000-7000-8000-000000000011"),
        "person_record_id": UUID("0198a412-7000-7000-8000-000000000020"),
        "person_name_record_id": UUID("0198a412-7000-7000-8000-000000000021"),
        "employment_record_id": UUID("0198a412-7000-7000-8000-000000000030"),
        "employment_record_version_id": UUID("0198a412-7000-7000-8000-000000000031"),
        "candidate_worker_conversion_record_id": UUID("0198a412-7000-7000-8000-000000000040"),
        "audit_event_record_id": UUID("0198a412-7000-7000-8000-000000000050"),
        "outbox_delivery_record_id": UUID("0198a412-7000-7000-8000-000000000051"),
        "effective_from": date(2026, 8, 21),
        "display_name": "Ada Lovelace",
        "idempotency_key": "hire-runtime-integrity-21",
        "employment_status_code": "active",
    }
    values.update(overrides)
    return values


def _command(**overrides: object) -> HireAcceptanceCommand:
    """Build one otherwise-valid confirmed-hire command."""
    return HireAcceptanceCommand(**_command_values(**overrides))  # type: ignore[arg-type]


def _principal() -> AuthenticatedPrincipal:
    """Return a principal authorized for the focused application-boundary tests."""
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse_subject:operator-21",
        granted_scope_codes=frozenset({"orgmetra.people.materialize_worker"}),
    )


def _policy() -> PurposeBoundAccessPolicy:
    """Return the exact purpose-bound policy for confirmed-hire materialization."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people-hire-v1",
        resource_kind="selection_decision",
        purpose_code="candidate_hire",
        operation_code="materialize_worker",
        required_scope_code="orgmetra.people.materialize_worker",
        permitted_fields=frozenset({"candidate_worker_conversion"}),
    )


class _RecordingPort:
    """Capture whether malformed commands cross the governed application boundary."""

    def __init__(self) -> None:
        self.called = False

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        """Return a valid opaque result while recording the call."""
        del authorization
        self.called = True
        return HireAcceptanceResult(
            person_record_id=command.person_record_id,
            employment_record_id=command.employment_record_id,
            candidate_worker_conversion_record_id=command.candidate_worker_conversion_record_id,
        )


class _MalformedResultPort:
    """Return an invalid subclass that skipped the result contract's post-init checks."""

    def accept_hire(self, *, command: HireAcceptanceCommand, authorization: object) -> HireAcceptanceResult:
        """Produce malformed result evidence after a valid authorization call."""
        del command, authorization
        return _UnvalidatedHireResult(
            person_record_id="not-a-uuid",  # type: ignore[arg-type]
            employment_record_id=UUID("0198a412-7000-7000-8000-000000000030"),
            candidate_worker_conversion_record_id=UUID("0198a412-7000-7000-8000-000000000040"),
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "tenant_record_id",
        "candidate_profile_id",
        "selection_decision_id",
        "person_record_id",
        "person_name_record_id",
        "employment_record_id",
        "employment_record_version_id",
        "candidate_worker_conversion_record_id",
        "audit_event_record_id",
        "outbox_delivery_record_id",
    ],
)
def test_hire_command_rejects_uuid_subclasses_before_idempotency_or_persistence(
    field_name: str,
) -> None:
    """Caller-controlled UUID rendering cannot rewrite confirmed-hire semantics."""
    forged = _ForgedUUID("0198a412-7000-7000-8000-000000000123")
    with pytest.raises(ValueError, match=f"{field_name} must be an operational UUID"):
        _command(**{field_name: forged})


def test_hire_result_rejects_uuid_subclasses_before_crossing_service_boundary() -> None:
    """A persistence adapter cannot return identity objects with forged rendering."""
    forged = _ForgedUUID("0198a412-7000-7000-8000-000000000123")
    with pytest.raises(ValueError, match="person_record_id must be an operational UUID"):
        HireAcceptanceResult(
            person_record_id=forged,
            employment_record_id=UUID("0198a412-7000-7000-8000-000000000030"),
            candidate_worker_conversion_record_id=UUID("0198a412-7000-7000-8000-000000000040"),
        )


def test_confirmed_hire_rejects_command_subclass_that_bypassed_post_init() -> None:
    """Only an exact validated command may cross into authoritative persistence."""
    forged = _UnvalidatedHireCommand(
        **_command_values(effective_from="not-a-business-date")  # type: ignore[arg-type]
    )
    port = _RecordingPort()

    with pytest.raises(TypeError, match="command must be a HireAcceptanceCommand"):
        accept_confirmed_hire(
            principal=_principal(),
            command=forged,
            purpose_code="candidate_hire",
            policy=_policy(),
            mutation_port=port,
        )

    assert port.called is False


def test_confirmed_hire_rejects_result_subclass_that_bypassed_post_init() -> None:
    """Only an exact validated result may leave the authoritative mutation boundary."""
    with pytest.raises(TypeError, match="mutation_port must return HireAcceptanceResult"):
        accept_confirmed_hire(
            principal=_principal(),
            command=_command(),
            purpose_code="candidate_hire",
            policy=_policy(),
            mutation_port=_MalformedResultPort(),
        )
