"""Privacy regressions for opaque candidate-evidence trust references."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from orgmetra_candidate_evidence import build_candidate_evidence_intake_packet

UUID1_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
UUID7_TENANT = "10000000-0000-7000-8000-000000000001"


def valid_kwargs() -> dict[str, object]:
    """Return one complete packet whose trust references use opaque UUIDv4 suffixes."""
    return {
        "tenant_record_id": "12345678-1234-4234-8234-123456789abc",
        "intake_reference": "candidate_evidence_intake:11111111-1111-4111-8111-111111111111",
        "candidate_profile_reference": "candidate_profile:22222222-2222-4222-8222-222222222222",
        "requisition_reference": "requisition:33333333-3333-4333-8333-333333333333",
        "job_profile_reference": "job_profile:44444444-4444-4444-8444-444444444444",
        "job_requirements_reference": "job_requirements:55555555-5555-4555-8555-555555555555",
        "job_requirements_digest": "a" * 64,
        "evidence_set_reference": "evidence_set:66666666-6666-4666-8666-666666666666",
        "evidence_set_digest": "b" * 64,
        "source_provenance_reference": "source_provenance:77777777-7777-4777-8777-777777777777",
        "source_provenance_digest": "c" * 64,
        "handling_policy_reference": "handling_policy:88888888-8888-4888-8888-888888888888",
        "handling_policy_digest": "d" * 64,
        "retention_policy_reference": "retention_policy:99999999-9999-4999-8999-999999999999",
        "retention_policy_digest": "e" * 64,
        "actor_reference": "actor:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "evidence_item_count": 5,
        "purpose_code": "candidate_evidence_intake",
        "reason_code": "requisition_candidate_review",
        "collected_at": datetime(2026, 8, 19, 1, 2, 3, 456789, tzinfo=timezone.utc),
    }


@pytest.mark.parametrize(
    ("field_name", "prefix"),
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
def test_uuid1_trust_reference_is_rejected_by_builder_and_replace(
    field_name: str,
    prefix: str,
) -> None:
    """UUIDv1 timestamp/node metadata must never enter an opaque trust-reference field."""
    value = f"{prefix}:{UUID1_ID}"
    kwargs = valid_kwargs()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=field_name):
        build_candidate_evidence_intake_packet(**kwargs)

    packet = build_candidate_evidence_intake_packet(**valid_kwargs())
    with pytest.raises(ValueError, match=field_name):
        replace(packet, **{field_name: value})


def test_authoritative_uuid7_tenant_identity_is_accepted_by_builder_and_replace() -> None:
    """The leaf packet must accept tenant UUIDs already valid in authoritative Orgmetra core."""
    kwargs = valid_kwargs()
    kwargs["tenant_record_id"] = UUID7_TENANT

    packet = build_candidate_evidence_intake_packet(**kwargs)
    replaced = replace(build_candidate_evidence_intake_packet(**valid_kwargs()), tenant_record_id=UUID7_TENANT)

    assert packet.tenant_record_id == UUID7_TENANT
    assert replaced.tenant_record_id == UUID7_TENANT
