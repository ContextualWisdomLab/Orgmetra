"""Reject caller-controlled runtime evidence at selection-review trust boundaries."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone, tzinfo
import json

import pytest

from orgmetra_selection_review import build_selection_review_packet


TENANT = "2b37b937-c3f1-49aa-8d19-785a7b7a9917"
CANDIDATE_UUID = "11111111-1111-4111-8111-111111111111"
JOB_UUID = "22222222-2222-4222-8222-222222222222"
EVIDENCE_UUID = "33333333-3333-4333-8333-333333333333"
REVIEWER_UUID = "44444444-4444-4444-8444-444444444444"
DRAFT_UUID = "55555555-5555-4555-8555-555555555555"
PROVENANCE_UUID = "66666666-6666-4666-8666-666666666666"
NOW = datetime.fromisoformat("2026-08-18T02:30:00+00:00")


class OpaqueTextSubclass(str):
    """Represent semantically valid text through an untrusted runtime subclass."""


class MutableOffset(tzinfo):
    """Provide caller-controlled timezone behavior that can change after construction."""

    def __init__(self) -> None:
        """Start at UTC so the first canonicalization looks ordinary."""
        self.offset = timedelta(0)

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Return the mutable offset used by datetime conversion."""
        del value
        return self.offset

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed while offset mutability is exercised."""
        del value
        return timedelta(0)


class ExplodingOffset(tzinfo):
    """Model a timezone provider that raises while its offset is resolved."""

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Raise provider behavior that must normalize to a stable ValueError."""
        del value
        raise RuntimeError("provider details must not escape")

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Return a fixed daylight-saving offset if queried."""
        del value
        return timedelta(0)


class ForgedGovernanceText(str):
    """Expose unsafe audit text while pretending to equal one reviewed value."""

    def __new__(cls, raw_value: str, accepted_value: str):
        """Store both the serialized text and the value forged during comparison."""
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
            return ["candidate_profile", CANDIDATE_UUID]
        return super().split(sep, maxsplit)


def _packet(**overrides):
    """Build one otherwise-valid human selection-review packet."""
    values = {
        "tenant_record_id": TENANT,
        "candidate_reference": f"candidate_profile:{CANDIDATE_UUID}",
        "job_profile_reference": f"job_profile:{JOB_UUID}",
        "decision_evidence_set_reference": f"decision_evidence_set:{EVIDENCE_UUID}",
        "evidence_set_digest": "0" * 64,
        "reviewer_actor_reference": f"actor:{REVIEWER_UUID}",
        "purpose_code": "selection_review",
        "reason_code": "candidate_assessment",
        "evidence_version_code": "evidence_version_1",
        "generated_at": NOW,
    }
    values.update(overrides)
    return build_selection_review_packet(**values)


def _model_packet():
    """Build one otherwise-valid packet carrying explicitly untrusted model evidence."""
    return _packet(
        model_draft_reference=f"model_draft:{DRAFT_UUID}",
        model_draft_digest="1" * 64,
        model_provenance_reference=f"model_provenance:{PROVENANCE_UUID}",
        model_provenance_digest="2" * 64,
    )


def test_rejects_tenant_text_subclass_before_uuid_parsing():
    """Ensure authoritative tenant text cannot carry caller-defined runtime behavior."""
    with pytest.raises(ValueError):
        _packet(tenant_record_id=OpaqueTextSubclass(TENANT))


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("purpose_code", ForgedGovernanceText("shadow_decision", "selection_review")),
        ("reason_code", ForgedGovernanceText("employee_jane_doe", "candidate_assessment")),
    ],
)
def test_rejects_forged_governance_code_before_canonical_evidence(field, forged):
    """Ensure reviewed code checks cannot disagree with serialized audit text."""
    with pytest.raises(ValueError):
        _packet(**{field: forged})


def test_rejects_reference_subclass_before_parser_methods_can_forge_namespace():
    """Ensure caller methods cannot validate a different reference than JSON records."""
    forged = ForgedReference(f"shadow_profile:{CANDIDATE_UUID}")
    with pytest.raises(ValueError):
        _packet(candidate_reference=forged)


@pytest.mark.parametrize(
    ("field", "raw_value", "accepted_value"),
    [
        ("review_state", "approved", "requires_human_decision"),
        (
            "next_action",
            "Auto-select the candidate.",
            "Review the evidence, confirm job relatedness and business necessity, then record the accountable human selection decision.",
        ),
    ],
)
def test_rejects_forged_fixed_human_review_text(field, raw_value, accepted_value):
    """Ensure direct construction cannot forge fixed human-review governance text."""
    base = _packet()
    forged = ForgedGovernanceText(raw_value, accepted_value)
    with pytest.raises(ValueError):
        replace(base, **{field: forged})


def test_rejects_forged_model_output_status_before_canonical_evidence():
    """Ensure model evidence cannot claim a reviewed status through equality forgery."""
    base = _model_packet()
    forged = ForgedGovernanceText("trusted_decision", "untrusted_draft")
    with pytest.raises(ValueError):
        replace(base, model_output_status=forged)


def test_detaches_mutable_timezone_before_immutable_evidence_is_stored():
    """Keep canonical JSON and its digest stable after caller timezone state mutates."""
    zone = MutableOffset()
    packet = _packet(generated_at=datetime(2026, 8, 18, 2, 30, tzinfo=zone))
    first_json = packet.canonical_json()
    first_digest = packet.sha256_digest()

    zone.offset = timedelta(hours=9)

    assert packet.generated_at.tzinfo is timezone.utc
    assert packet.canonical_json() == first_json
    assert packet.sha256_digest() == first_digest


def test_timezone_provider_exception_is_normalized_at_construction():
    """Do not leak arbitrary timezone-provider exceptions from the trust boundary."""
    with pytest.raises(ValueError, match="generated_at"):
        _packet(generated_at=datetime(2026, 8, 18, 2, 30, tzinfo=ExplodingOffset()))


def test_canonicalization_rejects_postconstruction_timezone_reinjection():
    """Fail closed if low-level mutation reintroduces executable timezone behavior."""
    packet = _packet()
    object.__setattr__(
        packet,
        "generated_at",
        datetime(2026, 8, 18, 2, 30, tzinfo=MutableOffset()),
    )
    with pytest.raises(ValueError, match="generated_at"):
        packet.canonical_json()


def test_canonicalization_rejects_builtin_non_utc_timezone_reinjection():
    """Reject a built-in fixed non-UTC offset, which is not an executable tzinfo subclass."""
    packet = _packet()
    object.__setattr__(
        packet,
        "generated_at",
        datetime(2026, 8, 18, 11, 30, tzinfo=timezone(timedelta(hours=9))),
    )
    with pytest.raises(ValueError, match="generated_at"):
        packet.canonical_json()


def test_valid_packet_still_serializes_reviewed_governance_values():
    """Preserve the normal governed packet after strict runtime-type validation."""
    payload = json.loads(_model_packet().canonical_json())
    assert payload["purpose_code"] == "selection_review"
    assert payload["reason_code"] == "candidate_assessment"
    assert payload["review_state"] == "requires_human_decision"
    assert payload["model_output_status"] == "untrusted_draft"
