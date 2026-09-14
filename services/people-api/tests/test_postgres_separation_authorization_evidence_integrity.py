"""Adversarial authorization-evidence integrity for Employment separation persistence."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_people_api.postgres_separation import _require_authorization
from orgmetra_people_api.separation import EmploymentSeparationPersistenceIntegrityError
from test_postgres_employment_separation import TENANT, authorization, command


class _ExecutableText(str):
    """Tripwire for comparison before exact nested text validation."""

    calls = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("separation authorization text executed before validation")

    def __ne__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("separation authorization text executed before validation")

    __hash__ = str.__hash__


class _ExecutableFields(frozenset[str]):
    """Tripwire for comparison before exact field-container validation."""

    calls = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("separation authorization fields executed before validation")

    def __ne__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("separation authorization fields executed before validation")


class _ExecutableInt(int):
    """Tripwire for UUID scalar comparison before exact integer validation."""

    calls = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("separation authorization UUID executed before validation")

    def __ne__(self, other: object) -> bool:
        type(self).calls += 1
        raise TypeError("separation authorization UUID executed before validation")


def _require(decision: object):
    return _require_authorization(authorization=decision, command=command())


def test_rejects_non_boolean_allowed_evidence() -> None:
    """Truthy non-bool evidence must never become an allow decision."""
    with pytest.raises(EmploymentSeparationPersistenceIntegrityError, match="authorization evidence is invalid"):
        _require(authorization(allowed=1))


def test_rejects_behavior_bearing_nested_text_before_comparison() -> None:
    """Persistence must not execute caller-defined text comparison during authorization."""
    _ExecutableText.calls = 0
    decision = authorization(resource_reference=_ExecutableText(f"employment_record:{command().employment_record_id.hex}"))

    with pytest.raises(EmploymentSeparationPersistenceIntegrityError, match="authorization evidence is invalid"):
        _require(decision)

    assert _ExecutableText.calls == 0


def test_rejects_behavior_bearing_field_container_before_comparison() -> None:
    """Reject a field-set subtype before its comparison behavior can run."""
    _ExecutableFields.calls = 0
    decision = authorization(requested_fields=_ExecutableFields({"employment_record"}))

    with pytest.raises(EmploymentSeparationPersistenceIntegrityError, match="authorization evidence is invalid"):
        _require(decision)

    assert _ExecutableFields.calls == 0


def test_rejects_forged_uuid_payload_before_comparison() -> None:
    """Reject forged exact UUID scalar evidence before equality can execute it."""
    forged = UUID(str(TENANT))
    object.__setattr__(forged, "int", _ExecutableInt(forged.int))
    _ExecutableInt.calls = 0

    with pytest.raises(EmploymentSeparationPersistenceIntegrityError, match="authorization evidence is invalid"):
        _require(authorization(tenant_record_id=forged))

    assert _ExecutableInt.calls == 0


def test_returns_detached_authorization_snapshot() -> None:
    """Caller mutation after validation must not alter the evidence used by persistence."""
    original = authorization()
    accepted = _require(original)

    assert accepted is not original
    assert accepted.tenant_record_id == TENANT
    assert accepted.actor_reference == "keyverse_subject:people-operator-17"
    assert accepted.purpose_code == "workforce_admin"

    object.__setattr__(original, "tenant_record_id", UUID("0198a412-8000-7000-8000-000000000099"))
    object.__setattr__(original, "actor_reference", "keyverse_subject:forged")
    object.__setattr__(original, "purpose_code", "benefits_admin")

    assert accepted.tenant_record_id == TENANT
    assert accepted.actor_reference == "keyverse_subject:people-operator-17"
    assert accepted.purpose_code == "workforce_admin"
