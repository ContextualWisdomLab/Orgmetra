from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_offer_approval import (
    OfferApprovalPacket,
    build_offer_approval_packet,
)


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
OFFER_ID = "10000000-0000-4000-8000-000000000001"
CANDIDATE_ID = "10000000-0000-4000-8000-000000000002"
REQUISITION_ID = "10000000-0000-4000-8000-000000000003"
JOB_ID = "10000000-0000-4000-8000-000000000004"
POSITION_ID = "10000000-0000-4000-8000-000000000005"
DECISION_ID = "10000000-0000-4000-8000-000000000006"
COMPENSATION_ID = "10000000-0000-4000-8000-000000000007"
TERMS_ID = "10000000-0000-4000-8000-000000000008"
REQUESTER_ID = "10000000-0000-4000-8000-000000000009"
APPROVER_ID = "10000000-0000-4000-8000-00000000000a"


def valid_kwargs() -> dict[str, object]:
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "offer_approval_reference": f"offer_approval:{OFFER_ID}",
        "candidate_profile_reference": f"candidate_profile:{CANDIDATE_ID}",
        "requisition_reference": f"requisition:{REQUISITION_ID}",
        "job_profile_reference": f"job_profile:{JOB_ID}",
        "position_record_reference": f"position_record:{POSITION_ID}",
        "selection_decision_reference": f"selection_decision:{DECISION_ID}",
        "selection_decision_digest": DIGEST_A,
        "compensation_package_reference": f"compensation_package:{COMPENSATION_ID}",
        "compensation_package_digest": DIGEST_B,
        "offer_terms_reference": f"offer_terms:{TERMS_ID}",
        "offer_terms_digest": DIGEST_C,
        "requester_reference": f"actor:{REQUESTER_ID}",
        "approver_reference": f"actor:{APPROVER_ID}",
        "purpose_code": "offer_approval_review",
        "reason_code": "selected_candidate_offer_review",
        "generated_at": datetime(2026, 8, 19, 5, 10, 0, 123456, tzinfo=timezone.utc),
    }


def build_valid() -> OfferApprovalPacket:
    return build_offer_approval_packet(**valid_kwargs())


def test_builds_value_free_human_offer_approval_packet() -> None:
    packet = build_valid()

    assert packet.contains_candidate_pii is False
    assert packet.contains_compensation_values is False
    assert packet.human_confirmation_required is True
    assert packet.decision_authority == "human_approval_only"
    assert packet.review_state == "requires_human_approval"
    assert packet.delivery_state == "not_authorized_to_send"
    assert "authoritative offer workflow" in packet.next_action
    assert "communicating or executing the offer" in packet.next_action


def test_position_reference_is_optional_without_collapsing_job_scope() -> None:
    kwargs = valid_kwargs()
    kwargs["position_record_reference"] = None
    packet = build_offer_approval_packet(**kwargs)
    payload = json.loads(packet.canonical_json())

    assert packet.job_profile_reference == f"job_profile:{JOB_ID}"
    assert payload["position_record_reference"] is None


def test_canonical_json_and_digest_are_deterministic_and_value_free() -> None:
    packet = build_valid()
    payload = json.loads(packet.canonical_json())

    assert payload["generated_at"] == "2026-08-19T05:10:00.123456Z"
    assert payload["candidate_profile_reference"] == f"candidate_profile:{CANDIDATE_ID}"
    assert "candidate_name" not in payload
    assert "candidate_email" not in payload
    assert "salary" not in payload
    assert "compensation_value" not in payload
    assert "assessment_score" not in payload
    assert "model_output" not in payload
    assert packet.sha256_digest() == sha256(packet.canonical_json().encode("utf-8")).hexdigest()


def test_repr_redacts_candidate_compensation_and_actor_correlation() -> None:
    packet = build_valid()
    rendered = repr(packet)

    assert rendered == "OfferApprovalPacket(<redacted>)"
    assert packet.tenant_record_id not in rendered
    assert packet.candidate_profile_reference not in rendered
    assert packet.compensation_package_reference not in rendered
    assert packet.compensation_package_digest not in rendered
    assert packet.requester_reference not in rendered
    assert packet.approver_reference not in rendered


def test_fractional_seconds_remain_distinct_evidence() -> None:
    first = build_valid()
    second = replace(first, generated_at=first.generated_at + timedelta(microseconds=1))

    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("tenant_record_id", "not-a-uuid"),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("tenant_record_id", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"),
        ("tenant_record_id", None),
    ],
)
def test_rejects_nonoperational_tenant_identity(field_name: str, value: object) -> None:
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_offer_approval_packet(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("offer_approval_reference", f"offer:{OFFER_ID}", "offer_approval"),
        ("candidate_profile_reference", f"candidate:{CANDIDATE_ID}", "candidate_profile"),
        ("requisition_reference", f"request:{REQUISITION_ID}", "requisition"),
        ("job_profile_reference", f"job:{JOB_ID}", "job_profile"),
        ("position_record_reference", f"position:{POSITION_ID}", "position_record"),
        ("selection_decision_reference", f"decision:{DECISION_ID}", "selection_decision"),
        ("compensation_package_reference", f"compensation:{COMPENSATION_ID}", "compensation_package"),
        ("offer_terms_reference", f"terms:{TERMS_ID}", "offer_terms"),
        ("requester_reference", f"person:{REQUESTER_ID}", "actor"),
        ("approver_reference", f"reviewer:{APPROVER_ID}", "actor"),
        ("requester_reference", "actor:", "actor"),
        ("requester_reference", 1, "actor"),
        ("requester_reference", "actor:" + "a" * 155, "actor"),
    ],
)
def test_rejects_bad_opaque_references(
    field_name: str,
    value: object,
    message: str,
) -> None:
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        build_offer_approval_packet(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("candidate_profile_reference", "candidate_profile:Jane-Doe", "opaque candidate_profile"),
        ("compensation_package_reference", "compensation_package:120000", "opaque compensation_package"),
        ("offer_terms_reference", "offer_terms:remote-two-days", "opaque offer_terms"),
        ("requester_reference", "actor:seonghobae", "opaque actor"),
        ("candidate_profile_reference", "candidate_profile:00000000-0000-0000-0000-000000000000", "opaque candidate_profile"),
        ("candidate_profile_reference", "candidate_profile:FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF", "opaque candidate_profile"),
    ],
)
def test_rejects_value_bearing_or_noncanonical_reference_suffixes(
    field_name: str,
    value: object,
    message: str,
) -> None:
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        build_offer_approval_packet(**kwargs)

    packet = build_valid()
    with pytest.raises(ValueError, match=message):
        replace(packet, **{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "selection_decision_digest",
        "compensation_package_digest",
        "offer_terms_digest",
    ],
)
@pytest.mark.parametrize("value", ["A" * 64, "a" * 63, 1])
def test_rejects_malformed_digests(field_name: str, value: object) -> None:
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        build_offer_approval_packet(**kwargs)


def test_approver_must_be_distinct_from_requester() -> None:
    kwargs = valid_kwargs()
    kwargs["approver_reference"] = kwargs["requester_reference"]
    with pytest.raises(ValueError, match="different accountable actor"):
        build_offer_approval_packet(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("purpose_code", "selection_review", "offer_approval_review"),
        ("purpose_code", "OfferApprovalReview", "lower snake_case"),
        ("purpose_code", "a_" + "b" * 64, "lower snake_case"),
        ("purpose_code", 1, "lower snake_case"),
        ("reason_code", "offer", "lower snake_case"),
        ("reason_code", "Offer_Review", "lower snake_case"),
        ("reason_code", 1, "lower snake_case"),
    ],
)
def test_rejects_bad_governance_codes(
    field_name: str,
    value: object,
    message: str,
) -> None:
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        build_offer_approval_packet(**kwargs)


class NullOffsetTz(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None

    def tzname(self, dt: datetime | None) -> str:
        return "NULL"


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 8, 19, 5, 10),
        "2026-08-19T05:10:00Z",
        1,
        datetime(2026, 8, 19, 5, 10).replace(tzinfo=NullOffsetTz()),
    ],
)
def test_rejects_nonaware_generation_time(value: object) -> None:
    kwargs = valid_kwargs()
    kwargs["generated_at"] = value
    with pytest.raises(ValueError, match="timezone-aware"):
        build_offer_approval_packet(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("contains_candidate_pii", True, "candidate PII"),
        ("contains_candidate_pii", 0, "candidate PII"),
        ("contains_compensation_values", True, "compensation values"),
        ("contains_compensation_values", 0, "compensation values"),
        ("human_confirmation_required", False, "human confirmation"),
        ("human_confirmation_required", 1, "human confirmation"),
        ("decision_authority", "automated", "human_approval_only"),
        ("review_state", "approved", "requires_human_approval"),
        ("delivery_state", "ready_to_send", "not_authorized_to_send"),
        ("next_action", "Send the offer.", "governed offer-approval instruction"),
    ],
)
def test_direct_constructor_and_replace_fail_closed(
    field_name: str,
    value: object,
    message: str,
) -> None:
    direct_kwargs = valid_kwargs()
    direct_kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        OfferApprovalPacket(**direct_kwargs)

    packet = build_valid()
    with pytest.raises(ValueError, match=message):
        replace(packet, **{field_name: value})


def test_frozen_packet_rejects_mutation() -> None:
    packet = build_valid()
    with pytest.raises(FrozenInstanceError):
        packet.review_state = "approved"


def test_timezone_is_normalized_without_losing_precision() -> None:
    kwargs = valid_kwargs()
    kwargs["generated_at"] = datetime(
        2026,
        8,
        19,
        14,
        10,
        0,
        654321,
        tzinfo=timezone(timedelta(hours=9)),
    )
    packet = build_offer_approval_packet(**kwargs)

    payload = json.loads(packet.canonical_json())
    assert payload["generated_at"] == "2026-08-19T05:10:00.654321Z"
