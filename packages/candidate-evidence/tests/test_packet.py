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
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
EXPECTED_NEXT_ACTION = (
    "Verify job relevance, source provenance, permitted handling, retention, and evidence "
    "completeness; then request authoritative evidence sealing and accountable human review."
)


def values():
    return dict(
        tenant_record_id=TENANT,
        intake_reference="candidate_evidence_intake:intake-2026-001",
        candidate_profile_reference="candidate_profile:candidate-001",
        requisition_reference="requisition:req-2026-001",
        job_profile_reference="job_profile:job-001",
        job_requirements_reference="job_requirements:requirements-v3",
        job_requirements_digest=DIGEST_A,
        evidence_set_reference="evidence_set:evidence-v2",
        evidence_set_digest=DIGEST_B,
        source_provenance_reference="source_provenance:manifest-v4",
        source_provenance_digest=DIGEST_C,
        handling_policy_reference="handling_policy:recruiting-candidate-v2",
        handling_policy_digest=DIGEST_D,
        retention_policy_reference="retention_policy:recruiting-2026-v1",
        retention_policy_digest=DIGEST_E,
        actor_reference="actor:recruiter-007",
        evidence_item_count=5,
        purpose_code="candidate_evidence_intake",
        reason_code="requisition_candidate_review",
        collected_at=datetime(2026, 8, 19, 1, 2, 3, 456789, tzinfo=timezone.utc),
    )


def test_builds_reference_only_deterministic_packet():
    packet = build_candidate_evidence_intake_packet(**values())
    payload = json.loads(packet.canonical_json())
    assert payload["review_state"] == "requires_human_review"
    assert payload["human_confirmation_required"] is True
    assert payload["next_action"] == EXPECTED_NEXT_ACTION
    assert payload["collected_at"].endswith(".456789Z")
    assert payload["candidate_profile_reference"] == "candidate_profile:candidate-001"
    forbidden = ("candidate_name", "email", "demographic", "assessment_value", "raw_evidence", "model_output")
    assert all(name not in payload for name in forbidden)
    assert packet.sha256_digest() == sha256(packet.canonical_json().encode("utf-8")).hexdigest()
    assert packet == CandidateEvidenceIntakePacket(**values())


@pytest.mark.parametrize("field,bad", [
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
])
def test_rejects_invalid_scalar_contract(field, bad):
    data = values()
    data[field] = bad
    with pytest.raises((ValueError, TypeError)):
        CandidateEvidenceIntakePacket(**data)


@pytest.mark.parametrize("count", [True, 0, 101, 1.0])
def test_rejects_invalid_evidence_item_count(count):
    data = values()
    data["evidence_item_count"] = count
    with pytest.raises(ValueError, match="evidence_item_count"):
        CandidateEvidenceIntakePacket(**data)


class UnknownOffset(tzinfo):
    def utcoffset(self, dt):
        return None

    def dst(self, dt):
        return None


def test_rejects_timezone_with_unknown_offset():
    data = values()
    data["collected_at"] = datetime(2026, 8, 19, tzinfo=UnknownOffset())
    with pytest.raises(ValueError, match="timezone-aware"):
        CandidateEvidenceIntakePacket(**data)


def test_canonicalizes_non_utc_offset_and_preserves_fractional_precision():
    data = values()
    data["collected_at"] = datetime(
        2026, 8, 19, 10, 2, 3, 456789, tzinfo=timezone(timedelta(hours=9))
    )
    payload = json.loads(CandidateEvidenceIntakePacket(**data).canonical_json())
    assert payload["collected_at"] == "2026-08-19T01:02:03.456789Z"


def test_distinct_subsecond_instants_produce_distinct_evidence():
    first = CandidateEvidenceIntakePacket(**values())
    data = values()
    data["collected_at"] = data["collected_at"].replace(microsecond=456790)
    second = CandidateEvidenceIntakePacket(**data)
    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()


def test_direct_replace_is_revalidated():
    packet = CandidateEvidenceIntakePacket(**values())
    with pytest.raises(ValueError, match="retention_policy_digest"):
        replace(packet, retention_policy_digest="not-a-digest")
