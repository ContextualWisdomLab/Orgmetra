"""Runtime-type integrity regressions for purpose-bound authorization."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_keyverse_adapter.authorization import (
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    evaluate_purpose_bound_access,
)

TENANT = UUID("10000000-0000-7000-8000-000000000501")


class _ForgedUUID(UUID):
    """Attempt to render a tenant identity different from its underlying UUID."""

    def __str__(self) -> str:
        """Return caller-controlled identity text."""
        return "10000000-0000-7000-8000-ffffffffffff"


class _ForgedText(str):
    """Attempt to carry caller-controlled runtime behavior through text validation."""


class _ForgedFieldSet(frozenset[str]):
    """Attempt to bypass field containment with a validation-passing set subclass."""

    def issubset(self, other: object) -> bool:
        """Claim every requested field set is permitted."""
        return True


class _ForgedScopeSet(frozenset[str]):
    """Attempt to bypass required-scope membership with a set subclass."""

    def __contains__(self, item: object) -> bool:
        """Claim every required scope is present."""
        return True


class _UnvalidatedPolicy(PurposeBoundAccessPolicy):
    """Attempt to bypass immutable policy validation through subclass dispatch."""

    def __post_init__(self) -> None:
        """Intentionally skip the governed base validation."""


class _UnvalidatedRequest(PurposeBoundAccessRequest):
    """Attempt to bypass immutable request validation through subclass dispatch."""

    def __post_init__(self) -> None:
        """Intentionally skip the governed base validation."""


def _policy(**overrides: object) -> PurposeBoundAccessPolicy:
    """Build one exact governed People PII access policy."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "policy_version_code": "people_pii_v1",
        "resource_kind": "person_record",
        "purpose_code": "hr_operations",
        "operation_code": "read_person_pii",
        "required_scope_code": "orgmetra.people.read",
        "permitted_fields": frozenset({"legal_name", "work_email"}),
    }
    values.update(overrides)
    return PurposeBoundAccessPolicy(**values)  # type: ignore[arg-type]


def _request(**overrides: object) -> PurposeBoundAccessRequest:
    """Build one exact governed People PII access request."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "actor_tenant_record_id": TENANT,
        "resource_tenant_record_id": TENANT,
        "actor_reference": "keyverse_subject:sub_jordan_hale",
        "resource_reference": "person_record:per_01J5EXACTTARGET",
        "purpose_code": "hr_operations",
        "operation_code": "read_person_pii",
        "resource_kind": "person_record",
        "requested_fields": frozenset({"work_email"}),
        "granted_scope_codes": frozenset({"orgmetra.people.read"}),
    }
    values.update(overrides)
    return PurposeBoundAccessRequest(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    ["tenant_record_id", "actor_tenant_record_id", "resource_tenant_record_id"],
)
def test_access_request_rejects_uuid_subclasses(field_name: str) -> None:
    """Tenant isolation cannot depend on a UUID object with caller-controlled rendering."""
    forged = _ForgedUUID("10000000-0000-7000-8000-000000000501")
    with pytest.raises(ValueError, match=f"{field_name} must be a UUID"):
        _request(**{field_name: forged})


def test_access_policy_rejects_uuid_subclasses() -> None:
    """Persisted policy identity must use the exact built-in UUID contract."""
    forged = _ForgedUUID("10000000-0000-7000-8000-000000000501")
    with pytest.raises(ValueError, match="tenant_record_id must be a UUID"):
        _policy(tenant_record_id=forged)


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("policy_version_code", _ForgedText("people_pii_v1")),
        ("resource_kind", _ForgedText("person_record")),
        ("purpose_code", _ForgedText("hr_operations")),
        ("operation_code", _ForgedText("read_person_pii")),
        ("required_scope_code", _ForgedText("orgmetra.people.read")),
    ],
)
def test_access_policy_rejects_string_subclasses(field_name: str, forged_value: str) -> None:
    """Policy semantics cannot depend on caller-defined string runtime behavior."""
    with pytest.raises(ValueError):
        _policy(**{field_name: forged_value})


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    [
        ("actor_reference", _ForgedText("keyverse_subject:sub_jordan_hale")),
        ("resource_reference", _ForgedText("person_record:per_01J5EXACTTARGET")),
        ("purpose_code", _ForgedText("hr_operations")),
        ("operation_code", _ForgedText("read_person_pii")),
        ("resource_kind", _ForgedText("person_record")),
    ],
)
def test_access_request_rejects_string_subclasses(field_name: str, forged_value: str) -> None:
    """Request authorization cannot depend on caller-defined string runtime behavior."""
    with pytest.raises(ValueError):
        _request(**{field_name: forged_value})


def test_access_policy_rejects_frozenset_subclass_for_permitted_fields() -> None:
    """A field-set subclass cannot control later policy containment semantics."""
    forged = _ForgedFieldSet({"legal_name", "work_email"})
    with pytest.raises(ValueError, match="permitted_fields must be a frozenset"):
        _policy(permitted_fields=forged)


def test_access_request_rejects_frozenset_subclass_that_can_widen_fields() -> None:
    """A requested-field set cannot override ``issubset`` and authorize a forbidden field."""
    forged = _ForgedFieldSet({"compensation_amount"})
    with pytest.raises(ValueError, match="requested_fields must be a frozenset"):
        _request(requested_fields=forged)


def test_access_request_rejects_frozenset_subclass_that_can_forge_scope_membership() -> None:
    """A scope set cannot override membership and fabricate the required operation scope."""
    forged = _ForgedScopeSet({"orgmetra.people.other"})
    with pytest.raises(ValueError, match="granted_scope_codes must be a frozenset"):
        _request(granted_scope_codes=forged)


def test_access_policy_rejects_string_subclass_inside_field_set() -> None:
    """Field identifiers themselves must be exact immutable built-in strings."""
    forged = frozenset({_ForgedText("work_email")})
    with pytest.raises(ValueError, match="permitted_fields must contain only"):
        _policy(permitted_fields=forged)


def test_access_request_rejects_string_subclass_inside_scope_set() -> None:
    """Scope identifiers themselves must be exact immutable built-in strings."""
    forged = frozenset({_ForgedText("orgmetra.people.read")})
    with pytest.raises(ValueError, match="granted_scope_codes must contain only"):
        _request(granted_scope_codes=forged)


def test_evaluator_rejects_policy_subclass_that_skipped_validation() -> None:
    """A subclass cannot widen immutable policy attributes by skipping post-init checks."""
    forged = _UnvalidatedPolicy(
        tenant_record_id=TENANT,
        policy_version_code="people_pii_v1",
        resource_kind="person_record",
        purpose_code="hr_operations",
        operation_code="read_person_pii",
        required_scope_code="orgmetra.people.read",
        permitted_fields={"work_email"},  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="policy must be a PurposeBoundAccessPolicy"):
        evaluate_purpose_bound_access(request=_request(), policy=forged)


def test_evaluator_rejects_request_subclass_that_skipped_validation() -> None:
    """A subclass cannot present mutable token scopes as validated authorization input."""
    forged = _UnvalidatedRequest(
        tenant_record_id=TENANT,
        actor_tenant_record_id=TENANT,
        resource_tenant_record_id=TENANT,
        actor_reference="keyverse_subject:sub_jordan_hale",
        resource_reference="person_record:per_01J5EXACTTARGET",
        purpose_code="hr_operations",
        operation_code="read_person_pii",
        resource_kind="person_record",
        requested_fields=frozenset({"work_email"}),
        granted_scope_codes={"orgmetra.people.read"},  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="request must be a PurposeBoundAccessRequest"):
        evaluate_purpose_bound_access(request=forged, policy=_policy())
