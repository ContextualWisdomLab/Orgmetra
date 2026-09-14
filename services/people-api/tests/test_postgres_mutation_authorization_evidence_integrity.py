"""Adversarial authorization-evidence integrity contract for PostgreSQL People mutations."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.postgres_mutations import (
    PeopleMutationIntegrityError,
    _require_authorization,
)

TENANT = UUID("0198a412-7100-7000-8000-000000000001")
RESOURCE = "employment_record:0198a412710070008000000000000030"
FIELDS = frozenset({"employment_record"})


def _decision(**overrides: object) -> AuthorizationDecision:
    """Build one exact decision while allowing focused adversarial field substitution."""
    values: dict[str, object] = {
        "allowed": True,
        "tenant_record_id": TENANT,
        "actor_reference": "keyverse_subject:operator-17",
        "resource_reference": RESOURCE,
        "policy_version_code": "people-employment-v1",
        "purpose_code": "workforce_admin",
        "operation_code": "create_record",
        "resource_kind": "employment_record",
        "requested_fields": FIELDS,
        "authorized_fields": FIELDS,
        "reason_code": "access_permitted",
        "next_action": "continue",
    }
    values.update(overrides)
    return AuthorizationDecision(**values)  # type: ignore[arg-type]


class _ExecutableText(str):
    """Tripwire for comparison before exact nested-evidence validation."""

    calls = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("authorization text comparison executed before validation")

    __hash__ = str.__hash__


class _ExecutableFields(frozenset[str]):
    """Tripwire for iteration before exact field-container validation."""

    calls = 0

    def __iter__(self):  # type: ignore[override]
        type(self).calls += 1
        raise TypeError("authorization field iteration executed before validation")


class _ExecutableInt(int):
    """Tripwire for ordering before exact UUID scalar validation."""

    calls = 0

    def __lt__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("authorization UUID ordering executed before validation")

    def __gt__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("authorization UUID ordering executed before validation")


def _require(decision: AuthorizationDecision) -> AuthorizationDecision:
    return _require_authorization(
        authorization=decision,
        tenant_record_id=TENANT,
        resource_reference=RESOURCE,
        resource_kind="employment_record",
        requested_fields=FIELDS,
    )


def test_rejects_non_boolean_allowed_evidence() -> None:
    """Reject truthy non-bool evidence instead of treating it as an allow decision."""
    with pytest.raises(PeopleMutationIntegrityError, match="authorization evidence is invalid"):
        _require(_decision(allowed=1))


def test_rejects_behavior_bearing_nested_text_before_comparison() -> None:
    """Prove persistence does not execute nested text behavior while checking authority."""
    _ExecutableText.calls = 0
    decision = _decision(resource_reference=_ExecutableText(RESOURCE))

    with pytest.raises(PeopleMutationIntegrityError, match="authorization evidence is invalid"):
        _require(decision)

    assert _ExecutableText.calls == 0


def test_rejects_behavior_bearing_field_container_before_iteration() -> None:
    """Reject a field-set subtype before its iteration behavior can run."""
    _ExecutableFields.calls = 0
    decision = _decision(requested_fields=_ExecutableFields(FIELDS))

    with pytest.raises(PeopleMutationIntegrityError, match="authorization evidence is invalid"):
        _require(decision)

    assert _ExecutableFields.calls == 0


def test_rejects_forged_uuid_payload_before_ordering() -> None:
    """Reject a forged exact UUID payload before ordering behavior can run."""
    forged = UUID(str(TENANT))
    object.__setattr__(forged, "int", _ExecutableInt(forged.int))
    _ExecutableInt.calls = 0

    with pytest.raises(PeopleMutationIntegrityError, match="authorization evidence is invalid"):
        _require(_decision(tenant_record_id=forged))

    assert _ExecutableInt.calls == 0


def test_rejects_behavior_bearing_expected_contract_before_comparison() -> None:
    """Validate the expected persistence contract before comparing authorization evidence."""
    _ExecutableText.calls = 0

    with pytest.raises(PeopleMutationIntegrityError, match="authorization contract is invalid"):
        _require_authorization(
            authorization=_decision(),
            tenant_record_id=TENANT,
            resource_reference=_ExecutableText(RESOURCE),
            resource_kind="employment_record",
            requested_fields=FIELDS,
        )

    assert _ExecutableText.calls == 0


def test_returns_detached_authorization_snapshot() -> None:
    """Keep validated evidence stable if the caller later rewrites the original decision."""
    original = _decision()
    accepted = _require(original)

    assert accepted is not original
    assert accepted.tenant_record_id == TENANT
    assert accepted.resource_reference == RESOURCE
    assert accepted.actor_reference == "keyverse_subject:operator-17"

    object.__setattr__(original, "tenant_record_id", UUID("0198a412-7100-7000-8000-000000000099"))
    object.__setattr__(original, "resource_reference", "employment_record:forged")
    object.__setattr__(original, "actor_reference", "keyverse_subject:forged")

    assert accepted.tenant_record_id == TENANT
    assert accepted.resource_reference == RESOURCE
    assert accepted.actor_reference == "keyverse_subject:operator-17"
