"""Reject caller-controlled string subclasses at requisition-review trust boundaries."""

from dataclasses import replace
from datetime import datetime
import json

import pytest

from orgmetra_requisition_review import build_requisition_review_packet


TENANT = "2b37b937-c3f1-49aa-8d19-785a7b7a9917"
REQUISITION_UUID = "11111111-1111-4111-8111-111111111111"
JOB_UUID = "22222222-2222-4222-8222-222222222222"
REQUIREMENTS_UUID = "33333333-3333-4333-8333-333333333333"
HEADCOUNT_UUID = "44444444-4444-4444-8444-444444444444"
MANAGER_UUID = "55555555-5555-4555-8555-555555555555"
APPROVER_UUID = "66666666-6666-4666-8666-666666666666"
NOW = datetime.fromisoformat("2026-08-18T10:30:00+00:00")
EXPECTED_NEXT_ACTION = (
    "Within tenant_record_id, re-resolve hiring_manager_actor_reference and "
    "approver_actor_reference through the authoritative actor boundary and verify their "
    "resolved actor identities are distinct; then confirm the opening is tied to the "
    "approved Job requirements and authorized headcount before recording accountable human "
    "requisition approval."
)


class OpaqueTextSubclass(str):
    """Represent semantically valid text through an untrusted runtime subclass."""


class ForgedGovernanceText(str):
    """Expose unsafe audit text while pretending to equal one reviewed value."""

    def __new__(cls, raw_value: str, accepted_value: str):
        """Store serialized text and the reviewed value forged during comparison."""
        instance = super().__new__(cls, raw_value)
        instance.accepted_value = accepted_value
        return instance

    def __eq__(self, other: object) -> bool:
        """Pretend the unsafe text equals the reviewed governance value."""
        return other == self.accepted_value

    def __ne__(self, other: object) -> bool:
        """Pretend the unsafe text never differs from the reviewed value."""
        return other != self.accepted_value

    def __hash__(self) -> int:
        """Place the forged text in the reviewed value's hash bucket."""
        return hash(self.accepted_value)


class ForgedReference(str):
    """Expose one namespace while feeding another namespace to parser methods."""

    def startswith(self, prefix, *args):
        """Forge the reviewed requisition namespace check."""
        if prefix == "requisition:":
            return True
        return super().startswith(prefix, *args)

    def __getitem__(self, key):
        """Feed a safe requisition UUID to validation while retaining unsafe raw text."""
        if isinstance(key, slice) and key.start == len("requisition:"):
            return REQUISITION_UUID
        return super().__getitem__(key)


def _packet(**overrides):
    """Build one otherwise-valid requisition-review packet with focused overrides."""
    values = {
        "tenant_record_id": TENANT,
        "requisition_reference": f"requisition:{REQUISITION_UUID}",
        "job_profile_reference": f"job_profile:{JOB_UUID}",
        "job_requirements_reference": f"job_requirements:{REQUIREMENTS_UUID}",
        "job_requirements_digest": "0" * 64,
        "requirements_version_code": "requirements_version_1",
        "headcount_authorization_reference": f"headcount_authorization:{HEADCOUNT_UUID}",
        "hiring_manager_actor_reference": f"actor:{MANAGER_UUID}",
        "approver_actor_reference": f"actor:{APPROVER_UUID}",
        "requested_opening_count": 3,
        "purpose_code": "requisition_review",
        "reason_code": "approved_growth_plan",
        "generated_at": NOW,
    }
    values.update(overrides)
    return build_requisition_review_packet(**values)


def test_rejects_tenant_text_subclass_before_uuid_parsing() -> None:
    """Ensure authoritative tenant text cannot carry caller-defined runtime behavior."""
    with pytest.raises(ValueError):
        _packet(tenant_record_id=OpaqueTextSubclass(TENANT))


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        (
            "purpose_code",
            ForgedGovernanceText("shadow_review", "requisition_review"),
        ),
        (
            "reason_code",
            ForgedGovernanceText("employee_jane_doe", "approved_growth_plan"),
        ),
    ],
)
def test_rejects_forged_governance_code_before_canonical_evidence(
    field: str, forged: str
) -> None:
    """Ensure reviewed code checks cannot disagree with serialized audit text."""
    with pytest.raises(ValueError):
        _packet(**{field: forged})


def test_rejects_reference_subclass_before_parser_methods_can_forge_namespace() -> None:
    """Ensure caller methods cannot validate a different reference than JSON records."""
    forged = ForgedReference(f"shadow_request:{REQUISITION_UUID}")
    with pytest.raises(ValueError):
        _packet(requisition_reference=forged)


@pytest.mark.parametrize(
    ("field", "raw_value", "accepted_value"),
    [
        ("review_state", "approved", "requires_human_approval"),
        ("next_action", "Open the requisition automatically.", EXPECTED_NEXT_ACTION),
    ],
)
def test_rejects_forged_fixed_human_review_text(
    field: str, raw_value: str, accepted_value: str
) -> None:
    """Ensure direct construction cannot forge fixed human-review governance text."""
    base = _packet()
    forged = ForgedGovernanceText(raw_value, accepted_value)
    with pytest.raises(ValueError):
        replace(base, **{field: forged})


def test_valid_packet_still_serializes_reviewed_governance_values() -> None:
    """Preserve normal canonical evidence after strict runtime-type validation."""
    payload = json.loads(_packet().canonical_json())
    assert payload["purpose_code"] == "requisition_review"
    assert payload["reason_code"] == "approved_growth_plan"
    assert payload["review_state"] == "requires_human_approval"
    assert payload["next_action"] == EXPECTED_NEXT_ACTION


def test_rejects_digest_text_subclass_before_pattern_match() -> None:
    """Ensure digest text cannot carry caller-defined runtime behavior into evidence."""
    with pytest.raises(ValueError):
        _packet(job_requirements_digest=OpaqueTextSubclass("0" * 64))


def test_rejects_requirements_version_code_text_subclass() -> None:
    """Ensure requirements version text cannot carry caller-defined runtime behavior."""
    with pytest.raises(ValueError):
        _packet(requirements_version_code=OpaqueTextSubclass("requirements_version_1"))


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("human_confirmation_required", False),
        ("review_state", "approved"),
        ("approver_actor_reference", f"actor:{MANAGER_UUID}"),
    ],
)
def test_rejects_postconstruction_governance_mutation_before_evidence(
    field: str, replacement: object
) -> None:
    """Ensure retained packet mutation cannot rewrite human-review audit evidence."""
    packet = _packet()
    object.__setattr__(packet, field, replacement)

    with pytest.raises(ValueError):
        packet.canonical_json()


def test_canonical_evidence_emits_the_same_snapshot_that_was_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prevent an interleaving mutation from changing fields after validation."""
    packet = _packet()
    packet_type = type(packet)
    original_validate = packet_type._validate_human_review_fields

    def validate_then_mutate(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Reproduce another thread changing live state after validation returns."""
        original_validate(self, *args, **kwargs)
        object.__setattr__(self, "review_state", "approved")

    monkeypatch.setattr(
        packet_type,
        "_validate_human_review_fields",
        validate_then_mutate,
    )

    payload = json.loads(packet.canonical_json())
    assert payload["review_state"] == "requires_human_approval"
