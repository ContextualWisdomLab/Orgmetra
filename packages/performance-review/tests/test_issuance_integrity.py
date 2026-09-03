"""Regression tests for immutable performance-review issuance evidence."""

from __future__ import annotations

from datetime import date

import pytest

from orgmetra_performance_review import build_performance_review_packet
from orgmetra_performance_review import packet as packet_module


def _build_packet():
    """Build one valid issued performance-review packet for tamper regressions."""
    return build_performance_review_packet(
        tenant_record_id="11111111-1111-4111-8111-111111111111",
        performance_review_reference="performance_review:22222222-2222-4222-8222-222222222222",
        person_record_reference="person_record:33333333-3333-4333-8333-333333333333",
        employment_record_reference="employment_record:44444444-4444-4444-8444-444444444444",
        job_profile_reference="job_profile:55555555-5555-4555-8555-555555555555",
        performance_cycle_reference="performance_cycle:66666666-6666-4666-8666-666666666666",
        criterion_set_reference="criterion_set:77777777-7777-4777-8777-777777777777",
        criterion_set_digest="a" * 64,
        goal_plan_reference="performance_goal_plan:88888888-8888-4888-8888-888888888888",
        goal_plan_digest="b" * 64,
        criterion_observation_snapshot_reference="criterion_observation_snapshot:99999999-9999-4999-8999-999999999999",
        criterion_observation_snapshot_digest="c" * 64,
        development_plan_reference="development_plan:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        development_plan_digest="d" * 64,
        reviewer_reference="actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        purpose_code="performance_review",
        reason_code="scheduled_cycle_review",
        review_period_start=date(2026, 1, 1),
        review_period_end=date(2026, 6, 30),
    )


def test_post_issuance_valid_value_rewrite_cannot_emit_new_canonical_truth() -> None:
    """Reject a valid digest rewrite after the governed packet has been issued."""
    packet = _build_packet()
    original = packet.canonical_json()

    object.__setattr__(packet, "goal_plan_digest", "f" * 64)

    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.sha256_digest()
    assert original != packet_module._canonical_packet_json_unchecked(packet)


def test_missing_process_local_issuance_evidence_fails_closed() -> None:
    """Reject canonical export when process-local issuance evidence is unavailable."""
    packet = _build_packet()
    packet_module._discard_packet_seal(id(packet))

    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        packet.canonical_json()


def test_seal_loss_cannot_reset_live_issuance_lifecycle() -> None:
    """Keep a live packet single-issued even after its process-local seal is lost."""
    packet = _build_packet()
    original = packet.canonical_json()

    packet_module._discard_packet_seal(id(packet))
    object.__setattr__(packet, "goal_plan_digest", "f" * 64)

    with pytest.raises(ValueError, match="issuance evidence already exists"):
        packet.__post_init__()
    with pytest.raises(ValueError, match="issuance evidence is unavailable"):
        packet.canonical_json()
    assert original != packet_module._canonical_packet_json_unchecked(packet)


def test_reinitialization_cannot_renew_issuance_evidence_after_valid_value_rewrite() -> None:
    """Keep one live packet identity bound to its original construction evidence."""
    packet = _build_packet()
    original = packet.canonical_json()

    object.__setattr__(packet, "goal_plan_digest", "f" * 64)

    with pytest.raises(ValueError, match="issuance evidence already exists"):
        packet.__post_init__()
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()
    assert original != packet_module._canonical_packet_json_unchecked(packet)
