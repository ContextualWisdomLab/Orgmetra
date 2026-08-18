from dataclasses import replace
from datetime import datetime, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_selection_review import build_selection_review_packet

TENANT = "2b37b937-c3f1-49aa-8d19-785a7b7a9917"
DIGEST = "0" * 64
NOW = datetime.fromisoformat("2026-08-18T02:30:00+00:00")


def packet(**overrides):
    values = dict(
        tenant_record_id=TENANT,
        candidate_reference="candidate_profile:candidate-01",
        job_profile_reference="job_profile:job-01",
        decision_evidence_set_reference="decision_evidence_set:evidence-01",
        evidence_set_digest=DIGEST,
        reviewer_actor_reference="actor:reviewer-01",
        purpose_code="selection_review",
        reason_code="candidate_assessment",
        evidence_version_code="evidence_version_1",
        generated_at=NOW,
    )
    values.update(overrides)
    return build_selection_review_packet(**values)


def test_packet_is_deterministic_and_requires_human_decision():
    value = packet(
        model_draft_reference="model_draft:draft-01",
        model_provenance_reference="model_provenance:run-01",
    )
    payload = json.loads(value.canonical_json())
    assert payload["human_confirmation_required"] is True
    assert payload["review_state"] == "requires_human_decision"
    assert payload["model_output_status"] == "untrusted_draft"
    assert payload["generated_at"] == "2026-08-18T02:30:00Z"
    assert "name" not in value.canonical_json().lower()
    assert value.sha256_digest() == sha256(value.canonical_json().encode("utf-8")).hexdigest()


def test_packet_without_model_evidence_has_no_model_status():
    value = packet()
    assert value.model_draft_reference is None
    assert value.model_provenance_reference is None
    assert value.model_output_status is None


@pytest.mark.parametrize(
    "tenant",
    [
        "not-a-uuid",
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "2B37B937-C3F1-49AA-8D19-785A7B7A9917",
    ],
)
def test_tenant_must_be_canonical_operational_uuid(tenant):
    with pytest.raises(ValueError):
        packet(tenant_record_id=tenant)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_reference", "person_record:wrong"),
        ("candidate_reference", "candidate_profile:"),
        ("job_profile_reference", "job:wrong"),
        ("decision_evidence_set_reference", "decision:e1"),
        ("reviewer_actor_reference", "user:r1"),
        ("candidate_reference", "candidate_profile:" + "a" * 150),
    ],
)
def test_references_are_bounded_and_namespaced(field, value):
    with pytest.raises(ValueError):
        packet(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("purpose_code", "selection"),
        ("purpose_code", "Selection_Review"),
        ("reason_code", "candidate assessment"),
        ("evidence_version_code", "v1"),
        ("reason_code", "candidate_" + "a" * 64),
        ("evidence_version_code", "evidence_" + "a" * 64),
    ],
)
def test_governance_codes_require_bounded_descriptive_snake_case(field, value):
    with pytest.raises(ValueError):
        packet(**{field: value})


def test_packet_purpose_is_fixed_to_selection_review():
    with pytest.raises(ValueError):
        packet(purpose_code="employment_review")


@pytest.mark.parametrize("digest", ["A" * 64, "0" * 63, "z" * 64, 123])
def test_digest_must_be_lowercase_sha256(digest):
    with pytest.raises(ValueError):
        packet(evidence_set_digest=digest)


class UnknownOffset(tzinfo):
    def utcoffset(self, dt):
        return None

    def dst(self, dt):
        return None


@pytest.mark.parametrize(
    "generated_at",
    [
        datetime(2026, 8, 18, 2, 30),
        datetime(2026, 8, 18, 2, 30, tzinfo=UnknownOffset()),
        "2026-08-18T02:30:00Z",
    ],
)
def test_generated_at_requires_real_timezone_offset(generated_at):
    with pytest.raises(ValueError):
        packet(generated_at=generated_at)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("human_confirmation_required", False),
        ("human_confirmation_required", 1),
        ("review_state", "approved"),
        ("next_action", "Auto-select the candidate."),
    ],
)
def test_direct_constructor_cannot_bypass_human_review(field, value):
    base = packet()
    with pytest.raises(ValueError):
        replace(base, **{field: value})


def test_model_draft_and_provenance_must_travel_together():
    base = packet()
    with pytest.raises(ValueError):
        replace(base, model_draft_reference="model_draft:draft-01")
    with pytest.raises(ValueError):
        replace(base, model_provenance_reference="model_provenance:run-01")


def test_model_evidence_must_be_namespaced_and_untrusted():
    base = packet(
        model_draft_reference="model_draft:draft-01",
        model_provenance_reference="model_provenance:run-01",
    )
    with pytest.raises(ValueError):
        replace(base, model_draft_reference="draft:wrong")
    with pytest.raises(ValueError):
        replace(base, model_provenance_reference="provenance:wrong")
    with pytest.raises(ValueError):
        replace(base, model_output_status="verified")
    with pytest.raises(ValueError):
        replace(packet(), model_output_status="untrusted_draft")


def test_non_utc_input_is_canonicalized_to_utc():
    value = packet(generated_at=datetime.fromisoformat("2026-08-18T11:30:00+09:00"))
    assert json.loads(value.canonical_json())["generated_at"] == "2026-08-18T02:30:00Z"
