from dataclasses import replace
from datetime import datetime, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_selection_review import build_selection_review_packet

TENANT = "2b37b937-c3f1-49aa-8d19-785a7b7a9917"
REF = {
    "candidate": "11111111-1111-4111-8111-111111111111",
    "job": "22222222-2222-4222-8222-222222222222",
    "evidence": "33333333-3333-4333-8333-333333333333",
    "reviewer": "44444444-4444-4444-8444-444444444444",
    "draft": "55555555-5555-4555-8555-555555555555",
    "provenance": "66666666-6666-4666-8666-666666666666",
}
DIGEST = "0" * 64
NOW = datetime.fromisoformat("2026-08-18T02:30:00+00:00")


def packet(**overrides):
    values = dict(
        tenant_record_id=TENANT,
        candidate_reference=f"candidate_profile:{REF['candidate']}",
        job_profile_reference=f"job_profile:{REF['job']}",
        decision_evidence_set_reference=f"decision_evidence_set:{REF['evidence']}",
        evidence_set_digest=DIGEST,
        reviewer_actor_reference=f"actor:{REF['reviewer']}",
        purpose_code="selection_review",
        reason_code="candidate_assessment",
        evidence_version_code="evidence_version_1",
        generated_at=NOW,
    )
    values.update(overrides)
    return build_selection_review_packet(**values)


def test_packet_is_deterministic_and_requires_human_decision():
    value = packet(
        model_draft_reference=f"model_draft:{REF['draft']}",
        model_provenance_reference=f"model_provenance:{REF['provenance']}",
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


def test_repr_redacts_candidate_reviewer_and_evidence_correlation():
    value = packet()
    rendered = repr(value)
    assert rendered == "SelectionReviewPacket(<redacted>)"
    assert value.tenant_record_id not in rendered
    assert value.candidate_reference not in rendered
    assert value.reviewer_actor_reference not in rendered
    assert value.evidence_set_digest not in rendered


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
    ("field", "prefix"),
    [
        ("candidate_reference", "candidate_profile"),
        ("job_profile_reference", "job_profile"),
        ("decision_evidence_set_reference", "decision_evidence_set"),
        ("reviewer_actor_reference", "actor"),
    ],
)
def test_references_require_expected_namespace_and_operational_uuid(field, prefix):
    for value in (
        f"wrong:{REF['candidate']}",
        f"{prefix}:Jane-Doe",
        f"{prefix}:00000000-0000-0000-0000-000000000000",
        f"{prefix}:FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
        f"{prefix}:" + "a" * 150,
    ):
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
        replace(base, model_draft_reference=f"model_draft:{REF['draft']}")
    with pytest.raises(ValueError):
        replace(base, model_provenance_reference=f"model_provenance:{REF['provenance']}")


def test_model_evidence_must_be_uuid_backed_namespaced_and_untrusted():
    base = packet(
        model_draft_reference=f"model_draft:{REF['draft']}",
        model_provenance_reference=f"model_provenance:{REF['provenance']}",
    )
    with pytest.raises(ValueError):
        replace(base, model_draft_reference="draft:wrong")
    with pytest.raises(ValueError):
        replace(base, model_draft_reference="model_draft:free-form-output")
    with pytest.raises(ValueError):
        replace(base, model_provenance_reference="model_provenance:run-01")
    with pytest.raises(ValueError):
        replace(base, model_output_status="verified")
    with pytest.raises(ValueError):
        replace(packet(), model_output_status="untrusted_draft")


def test_non_utc_input_is_canonicalized_to_utc():
    value = packet(generated_at=datetime.fromisoformat("2026-08-18T11:30:00+09:00"))
    assert json.loads(value.canonical_json())["generated_at"] == "2026-08-18T02:30:00Z"
