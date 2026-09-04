from dataclasses import replace
from datetime import date, datetime, timezone
import json

import pytest

from orgmetra_employment_separation_review import (
    EmploymentSeparationReviewPacket,
    build_employment_separation_review_packet,
)


def build_valid(**overrides: object) -> EmploymentSeparationReviewPacket:
    """Build an independent valid packet without importing another test module."""
    values: dict[str, object] = {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "separation_review_reference": "employment_separation_review:22222222-2222-4222-8222-222222222222",
        "person_record_reference": "person_record:33333333-3333-4333-8333-333333333333",
        "employment_record_reference": "employment_record:44444444-4444-4444-8444-444444444444",
        "active_assignment_snapshot_reference": "active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
        "active_assignment_snapshot_digest": "a" * 64,
        "separation_policy_reference": "employment_separation_policy:66666666-6666-4666-8666-666666666666",
        "separation_policy_digest": "b" * 64,
        "separation_process_reference": "employment_separation_process:77777777-7777-4777-8777-777777777777",
        "separation_process_digest": "c" * 64,
        "final_pay_handoff_reference": "final_pay_handoff:88888888-8888-4888-8888-888888888888",
        "final_pay_handoff_digest": "d" * 64,
        "benefits_handoff_reference": "benefits_handoff:99999999-9999-4999-8999-999999999999",
        "benefits_handoff_digest": "e" * 64,
        "access_deprovisioning_plan_reference": "access_deprovisioning_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "access_deprovisioning_plan_digest": "f" * 64,
        "asset_return_plan_reference": "asset_return_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "asset_return_plan_digest": "1" * 64,
        "knowledge_transfer_plan_reference": "knowledge_transfer_plan:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "knowledge_transfer_plan_digest": "2" * 64,
        "communication_plan_reference": "separation_communication_plan:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "communication_plan_digest": "3" * 64,
        "requester_reference": "actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        "reviewer_reference": "actor:ffffffff-ffff-4fff-8fff-fffffffffff0",
        "purpose_code": "employment_separation_review",
        "reason_code": "voluntary_resignation",
        "proposed_separation_on": date(2026, 9, 30),
        "generated_at": datetime(2026, 8, 19, 9, 10, 15, 123456, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return build_employment_separation_review_packet(**values)


def test_packet_carries_explicit_evidence_version() -> None:
    packet = build_valid()
    assert packet.evidence_version == 1
    assert json.loads(packet.canonical_json())["evidence_version"] == 1


def test_evidence_version_changes_canonical_evidence() -> None:
    first = build_valid()
    second = build_valid(evidence_version=2)
    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()


@pytest.mark.parametrize("version", [0, -1, True, "1", 2_147_483_648])
def test_direct_construction_rejects_invalid_evidence_version(version: object) -> None:
    with pytest.raises(ValueError, match="evidence_version"):
        replace(build_valid(), evidence_version=version)
