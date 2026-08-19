"""Regression coverage for governed candidate-evidence intake packets."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_candidate_evidence import (
    CandidateEvidenceIntakePacket,
    build_candidate_evidence_intake_packet,
)

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
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
EXPECTED_NEXT_ACTION = (
    "Verify job relevance, source provenance, permitted handling, retention, and evidence "
    "completeness; then request authoritative evidence sealing and accountable human review."
)


def values() -> dict[str, object]:
    """Return one valid candidate-evidence packet input mapping for focused overrides."""
    return dict(
        tenant_record_id=TENANT,
        intake_reference=f"candidate_evidence_intake:{REF['intake']}",
        candidate_profile_reference=f"candidate_profile:{REF['candidate']}",
        requisition_reference=f"requisition:{REF['requisition']}",
        job_profile_reference=f"job_profile:{REF['job']}",
        job_requirements_reference=f"job_requirements:{REF['requirements']}",
        job_requirements_digest=DIGEST_A,
        evidence_set_reference=f"evidence_set:{REF['evidence']}",
        evidence_set_digest=DIGEST_B,
        source_provenance_reference=f"source_provenance:{REF['source']}",
        source_provenance_digest=DIGEST_C,
        handling_policy_reference=f"handling_policy:{REF['handling']}",
        handling_policy_digest=DIGEST_D,
        retention_policy_reference=f"retention_policy:{REF['retention']}",
        retention_policy_digest=DIGEST_E,
        actor_reference=f"actor:{REF['actor']}",
        evidence_item_count=5,
        purpose_code="candidate_evidence_intake",
        reason_code="requisition_candidate_review",
        collected_at=datetime(2026, 8, 19, 1, 2, 3, 456789, tzinfo=timezone.utc),
    )


def test_builds_reference_only_deterministic_packet() -> None:
    """Build deterministic reference-only evidence without candidate value duplication."""
    packet = build_candidate_evidence_intake_packet(**values())
    payload = json.loads(packet.canonical_json())
    assert payload["review_state"] == "requires_human_review"
    assert payload["human_confirmation_required"] is True
    assert payload["next_action"] == EXPECTED_NEXT_ACTION
    assert payload["collected_at"].endswith(".456789Z")
    assert payload["candidate_profile_reference"] == f"candidate_profile:{REF['candidate']}"
    forbidden = (
        "candidate_name",
        "email",
        "demographic",
        "assessment_value",
        "raw_evidence",
        "model_output",
    )
    assert all(name not in payload for name in forbidden)
    assert packet.sha256_digest() == sha256(packet.canonical_json().encode("utf-8")).hexdigest()
    assert packet == CandidateEvidenceIntakePacket(**values())


@pytest.mark.parametrize(
    "field,bad",
    [
        ("tenant_record_id", "not-a-uuid"),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("tenant_record_id", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"),
        ("intake_reference", "wrong:intake"),
        ("candidate_profile_reference", "wrong:candidate"),
        ("requisition_reference", "wrong:req"),
        ("job_profile_reference", "wrong:job"),
        ("job_requirements_reference", "wrong:reqs"),
        ("evidence_set_reference", "wrong:evidence"),
        ("source_provenance_reference", "wrong:source"),
        ("handling_policy_reference", "wrong:handling"),
        ("retention_policy_reference", "wrong:retention"),
        ("actor_reference", "wrong:actor"),
        ("job_requirements_digest", "A" * 64),
        ("evidence_set_digest", "b" * 63),
        ("source_provenance_digest", "C" * 64),
        ("handling_policy_digest", "d" * 63),
        ("retention_policy_digest", 7),
        ("purpose_code", "wrong_purpose"),
        ("purpose_code", "bad"),
        ("reason_code", "Bad Reason"),
        ("reason_code", "a_" + "b" * 64),
        ("collected_at", datetime(2026, 8, 19, 1, 2, 3)),
        ("human_confirmation_required", False),
        ("human_confirmation_required", 1),
        ("review_state", "approved"),
        ("next_action", "Skip human review"),
    ],
)
def test_rejects_invalid_scalar_contract(field: str, bad: object) -> None:
    """Reject malformed scalar governance metadata and attempts to bypass review state."""
    data = values()
    data[field] = bad
    with pytest.raises((ValueError, TypeError)):
        CandidateEvidenceIntakePacket(**data)


@pytest.mark.parametrize(
    ("field", "prefix"),
    [
        ("intake_reference", "candidate_evidence_intake"),
        ("candidate_profile_reference", "candidate_profile"),
        ("requisition_reference", "requisition"),
        ("job_profile_reference", "job_profile"),
        ("job_requirements_reference", "job_requirements"),
        ("evidence_set_reference", "evidence_set"),
        ("source_provenance_reference", "source_provenance"),
        ("handling_policy_reference", "handling_policy"),
        ("retention_policy_reference", "retention_policy"),
        ("actor_reference", "actor"),
    ],
)
def test_reference_suffixes_are_opaque_canonical_operational_uuids(
    field: str, prefix: str
) -> None:
    """Reject semantic, sentinel, and noncanonical values in opaque reference suffixes."""
    packet = CandidateEvidenceIntakePacket(**values())
    for suffix in (
        "Jane-Doe",
        "00000000-0000-0000-0000-000000000000",
        "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
    ):
        with pytest.raises(ValueError):
            replace(packet, **{field: f"{prefix}:{suffix}"})


def test_repr_redacts_candidate_correlation_and_evidence() -> None:
    """Keep candidate correlation, actor identity, and evidence digests out of repr output."""
    packet = CandidateEvidenceIntakePacket(**values())
    rendered = repr(packet)
    assert rendered == "CandidateEvidenceIntakePacket(<redacted>)"
    assert packet.tenant_record_id not in rendered
    assert packet.candidate_profile_reference not in rendered
    assert packet.actor_reference not in rendered
    assert packet.evidence_set_digest not in rendered


@pytest.mark.parametrize("count", [True, 0, 101, 1.0])
def test_rejects_invalid_evidence_item_count(count: object) -> None:
    """Require a bounded true integer count rather than booleans or numeric lookalikes."""
    data = values()
    data["evidence_item_count"] = count
    with pytest.raises(ValueError, match="evidence_item_count"):
        CandidateEvidenceIntakePacket(**data)


class UnknownOffset(tzinfo):
    """Timezone fixture whose UTC offset cannot be resolved."""

    def utcoffset(self, dt: datetime | None) -> None:
        """Return an unknown offset to exercise fail-closed timestamp validation."""
        return None

    def dst(self, dt: datetime | None) -> None:
        """Return no daylight-saving offset for the unknown-offset fixture."""
        return None


def test_rejects_timezone_with_unknown_offset() -> None:
    """Reject datetime values whose timezone object cannot resolve an absolute instant."""
    data = values()
    data["collected_at"] = datetime(2026, 8, 19, tzinfo=UnknownOffset())
    with pytest.raises(ValueError, match="timezone-aware"):
        CandidateEvidenceIntakePacket(**data)


def test_canonicalizes_non_utc_offset_and_preserves_fractional_precision() -> None:
    """Normalize an aware local instant to UTC without dropping microsecond evidence."""
    data = values()
    data["collected_at"] = datetime(
        2026, 8, 19, 10, 2, 3, 456789, tzinfo=timezone(timedelta(hours=9))
    )
    payload = json.loads(CandidateEvidenceIntakePacket(**data).canonical_json())
    assert payload["collected_at"] == "2026-08-19T01:02:03.456789Z"


def test_distinct_subsecond_instants_produce_distinct_evidence() -> None:
    """Preserve digest separation for valid evidence timestamps one microsecond apart."""
    first = CandidateEvidenceIntakePacket(**values())
    data = values()
    collected_at = data["collected_at"]
    assert isinstance(collected_at, datetime)
    data["collected_at"] = collected_at.replace(microsecond=456790)
    second = CandidateEvidenceIntakePacket(**data)
    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()


def test_direct_replace_is_revalidated() -> None:
    """Re-run invariant validation when an immutable packet is copied with new fields."""
    packet = CandidateEvidenceIntakePacket(**values())
    with pytest.raises(ValueError, match="retention_policy_digest"):
        replace(packet, retention_policy_digest="not-a-digest")
