from dataclasses import replace
from datetime import datetime, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_requisition_review import build_requisition_review_packet

TENANT = "2b37b937-c3f1-49aa-8d19-785a7b7a9917"
DIGEST = "0" * 64
NOW = datetime.fromisoformat("2026-08-18T10:30:00+00:00")


def packet(**overrides):
    values = dict(
        tenant_record_id=TENANT,
        requisition_reference="requisition:req-01",
        job_profile_reference="job_profile:job-01",
        job_requirements_reference="job_requirements:reqs-01",
        job_requirements_digest=DIGEST,
        requirements_version_code="requirements_version_1",
        headcount_authorization_reference="headcount_authorization:hc-01",
        hiring_manager_actor_reference="actor:manager-01",
        approver_actor_reference="actor:approver-01",
        requested_opening_count=3,
        purpose_code="requisition_review",
        reason_code="approved_growth_plan",
        generated_at=NOW,
    )
    values.update(overrides)
    return build_requisition_review_packet(**values)


def test_packet_is_deterministic_and_contains_no_candidate_or_employee_values():
    value = packet()
    payload = json.loads(value.canonical_json())
    assert payload["human_confirmation_required"] is True
    assert payload["review_state"] == "requires_human_approval"
    assert payload["generated_at"] == "2026-08-18T10:30:00Z"
    assert payload["requested_opening_count"] == 3
    assert payload["position_record_reference"] is None
    assert not ({"candidate", "person", "email", "name"} & set(payload))
    assert value.sha256_digest() == sha256(value.canonical_json().encode("utf-8")).hexdigest()


def test_exact_position_seat_supports_one_opening():
    value = packet(
        requested_opening_count=1,
        position_record_reference="position_record:seat-01",
    )
    assert value.position_record_reference == "position_record:seat-01"


@pytest.mark.parametrize(
    "tenant",
    [
        "not-a-uuid",
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "2B37B937-C3F1-49AA-8D19-785A7B7A9917",
        123,
    ],
)
def test_tenant_must_be_canonical_operational_uuid(tenant):
    with pytest.raises(ValueError):
        packet(tenant_record_id=tenant)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("requisition_reference", "requisition:"),
        ("requisition_reference", "candidate_profile:wrong"),
        ("job_profile_reference", "job:wrong"),
        ("job_requirements_reference", "job_analysis:wrong"),
        ("headcount_authorization_reference", "budget:wrong"),
        ("hiring_manager_actor_reference", "user:manager"),
        ("approver_actor_reference", "reviewer:approver"),
        ("requisition_reference", "requisition:" + "a" * 150),
    ],
)
def test_references_are_bounded_and_namespaced(field, value):
    with pytest.raises(ValueError):
        packet(**{field: value})


def test_position_reference_is_optional_but_must_be_namespaced_when_present():
    with pytest.raises(ValueError):
        packet(requested_opening_count=1, position_record_reference="position:seat-01")


@pytest.mark.parametrize("opening_count", [True, False, 0, 101, 1.0, "1"])
def test_opening_count_is_bounded_exact_integer(opening_count):
    with pytest.raises(ValueError):
        packet(requested_opening_count=opening_count)


def test_exact_position_cannot_claim_multiple_openings():
    with pytest.raises(ValueError):
        packet(position_record_reference="position_record:seat-01", requested_opening_count=2)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("purpose_code", "requisition"),
        ("purpose_code", "Requisition_Review"),
        ("reason_code", "growth"),
        ("reason_code", "approved growth plan"),
        ("requirements_version_code", "v1"),
        ("reason_code", "approved_" + "a" * 64),
    ],
)
def test_governance_codes_require_bounded_descriptive_snake_case(field, value):
    with pytest.raises(ValueError):
        packet(**{field: value})


def test_packet_purpose_is_fixed_to_requisition_review():
    with pytest.raises(ValueError):
        packet(purpose_code="selection_review")


@pytest.mark.parametrize("digest", ["A" * 64, "0" * 63, "z" * 64, 123])
def test_requirements_digest_must_be_lowercase_sha256(digest):
    with pytest.raises(ValueError):
        packet(job_requirements_digest=digest)


class UnknownOffset(tzinfo):
    def utcoffset(self, dt):
        return None

    def dst(self, dt):
        return None


@pytest.mark.parametrize(
    "generated_at",
    [
        datetime(2026, 8, 18, 10, 30),
        datetime(2026, 8, 18, 10, 30, tzinfo=UnknownOffset()),
        "2026-08-18T10:30:00Z",
    ],
)
def test_generated_at_requires_real_timezone_offset(generated_at):
    with pytest.raises(ValueError):
        packet(generated_at=generated_at)


def test_non_utc_input_is_canonicalized_to_utc():
    value = packet(generated_at=datetime.fromisoformat("2026-08-18T19:30:00+09:00"))
    assert json.loads(value.canonical_json())["generated_at"] == "2026-08-18T10:30:00Z"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("human_confirmation_required", False),
        ("human_confirmation_required", 1),
        ("review_state", "approved"),
        ("next_action", "Open the requisition automatically."),
    ],
)
def test_direct_constructor_cannot_bypass_human_approval(field, value):
    base = packet()
    with pytest.raises(ValueError):
        replace(base, **{field: value})
