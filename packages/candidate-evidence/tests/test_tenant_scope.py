"""Tenant-scope regressions for governed candidate-evidence intake."""

from datetime import datetime, timezone

from orgmetra_candidate_evidence import build_candidate_evidence_intake_packet


def _packet():
    """Build one valid candidate-evidence packet for boundary assertions."""
    return build_candidate_evidence_intake_packet(
        tenant_record_id="12345678-1234-4234-8234-123456789abc",
        intake_reference="candidate_evidence_intake:11111111-1111-4111-8111-111111111111",
        candidate_profile_reference="candidate_profile:22222222-2222-4222-8222-222222222222",
        requisition_reference="requisition:33333333-3333-4333-8333-333333333333",
        job_profile_reference="job_profile:44444444-4444-4444-8444-444444444444",
        job_requirements_reference="job_requirements:55555555-5555-4555-8555-555555555555",
        job_requirements_digest="a" * 64,
        evidence_set_reference="evidence_set:66666666-6666-4666-8666-666666666666",
        evidence_set_digest="b" * 64,
        source_provenance_reference="source_provenance:77777777-7777-4777-8777-777777777777",
        source_provenance_digest="c" * 64,
        handling_policy_reference="handling_policy:88888888-8888-4888-8888-888888888888",
        handling_policy_digest="d" * 64,
        retention_policy_reference="retention_policy:99999999-9999-4999-8999-999999999999",
        retention_policy_digest="e" * 64,
        actor_reference="actor:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        evidence_item_count=5,
        purpose_code="candidate_evidence_intake",
        reason_code="requisition_candidate_review",
        collected_at=datetime(2026, 8, 19, 1, 2, 3, 456789, tzinfo=timezone.utc),
    )


def test_sealing_requires_every_reference_to_resolve_in_exact_tenant() -> None:
    """Prevent cross-tenant evidence mixing behind syntactically valid opaque references."""
    action = _packet().next_action
    tenant_clause = "re-resolve every packet reference within tenant_record_id"
    correlation_clause = "verify candidate, requisition, and Job correlation"
    provenance_clause = "verify job relevance, source provenance"
    sealing_clause = "authoritative evidence sealing"

    assert tenant_clause in action
    assert action.index(tenant_clause) < action.index(correlation_clause)
    assert action.index(correlation_clause) < action.index(provenance_clause)
    assert action.index(provenance_clause) < action.index(sealing_clause)
