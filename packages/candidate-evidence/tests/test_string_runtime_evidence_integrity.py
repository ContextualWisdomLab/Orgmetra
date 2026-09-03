"""Reject caller-controlled string subclasses at candidate-evidence trust boundaries."""

from dataclasses import replace
from datetime import datetime, timezone
import json

import pytest

from orgmetra_candidate_evidence import build_candidate_evidence_intake_packet


TENANT = "12345678-1234-4234-8234-123456789abc"
REF = {
    "intake": "11111111-1111-4111-8111-111111111111",
    "candidate": "22222222-2222-4222-8222-222222222222",
    "requisition": "33333333-3333-4333-8333-333333333333",
    "job": "44444444-4444-4444-8444-444444444444",
    "requirements": "55555555-5555-4555-8555-555555555555",
    "evidence": "66666666-6666-4666-8666-666666666666",
    "source": "77777777-7777-4777-8777-777777777777",
    "handling": "88888888-8888-4888-8888-888888888888",
    "retention": "99999999-9999-4999-8999-999999999999",
    "actor": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
}
EXPECTED_NEXT_ACTION = (
    "Re-resolve every packet reference within tenant_record_id through its authoritative "
    "boundary; verify candidate, requisition, and Job correlation; then verify job relevance, "
    "source provenance, permitted handling, retention, and evidence completeness before "
    "requesting authoritative evidence sealing and accountable human review."
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
        """Forge the reviewed candidate namespace check."""
        if prefix == "candidate_profile:":
            return True
        return super().startswith(prefix, *args)

    def split(self, sep=None, maxsplit=-1):
        """Feed a safe candidate UUID to validation while retaining unsafe raw text."""
        if sep == ":" and maxsplit == 1:
            return ["candidate_profile", REF["candidate"]]
        return super().split(sep, maxsplit)


def _values() -> dict[str, object]:
    """Return one otherwise-valid candidate-evidence packet input mapping."""
    return {
        "tenant_record_id": TENANT,
        "intake_reference": f"candidate_evidence_intake:{REF['intake']}",
        "candidate_profile_reference": f"candidate_profile:{REF['candidate']}",
        "requisition_reference": f"requisition:{REF['requisition']}",
        "job_profile_reference": f"job_profile:{REF['job']}",
        "job_requirements_reference": f"job_requirements:{REF['requirements']}",
        "job_requirements_digest": "a" * 64,
        "evidence_set_reference": f"evidence_set:{REF['evidence']}",
        "evidence_set_digest": "b" * 64,
        "source_provenance_reference": f"source_provenance:{REF['source']}",
        "source_provenance_digest": "c" * 64,
        "handling_policy_reference": f"handling_policy:{REF['handling']}",
        "handling_policy_digest": "d" * 64,
        "retention_policy_reference": f"retention_policy:{REF['retention']}",
        "retention_policy_digest": "e" * 64,
        "actor_reference": f"actor:{REF['actor']}",
        "evidence_item_count": 5,
        "purpose_code": "candidate_evidence_intake",
        "reason_code": "requisition_candidate_review",
        "collected_at": datetime(2026, 8, 19, 1, 2, 3, 456789, tzinfo=timezone.utc),
    }


def _packet(**overrides):
    """Build one otherwise-valid candidate-evidence packet with focused overrides."""
    values = _values()
    values.update(overrides)
    return build_candidate_evidence_intake_packet(**values)


def test_rejects_tenant_text_subclass_before_uuid_parsing() -> None:
    """Ensure authoritative tenant text cannot carry caller-defined runtime behavior."""
    with pytest.raises(ValueError):
        _packet(tenant_record_id=OpaqueTextSubclass(TENANT))


def test_rejects_digest_text_subclass_before_canonical_evidence() -> None:
    """Ensure digest evidence cannot retain caller-defined string behavior."""
    with pytest.raises(ValueError):
        _packet(job_requirements_digest=OpaqueTextSubclass("a" * 64))


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        (
            "purpose_code",
            ForgedGovernanceText("shadow_intake", "candidate_evidence_intake"),
        ),
        (
            "reason_code",
            ForgedGovernanceText("employee_jane_doe", "requisition_candidate_review"),
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
    forged = ForgedReference(f"shadow_profile:{REF['candidate']}")
    with pytest.raises(ValueError):
        _packet(candidate_profile_reference=forged)


@pytest.mark.parametrize(
    ("field", "raw_value", "accepted_value"),
    [
        ("review_state", "approved", "requires_human_review"),
        ("next_action", "Auto-seal candidate evidence.", EXPECTED_NEXT_ACTION),
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
    assert payload["purpose_code"] == "candidate_evidence_intake"
    assert payload["reason_code"] == "requisition_candidate_review"
    assert payload["review_state"] == "requires_human_review"
    assert payload["next_action"] == EXPECTED_NEXT_ACTION
