"""Regression coverage for Orgmetra-scoped TEPP idempotency semantics."""

from __future__ import annotations

from dataclasses import replace

import pytest

from test_analysis import build_valid


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("tenant_record_id", "44444444-4444-4444-8444-444444444444"),
        (
            "validation_study_reference",
            "validation_study:55555555-5555-4555-8555-555555555555",
        ),
        ("requested_by_actor_reference", "actor:66666666-6666-4666-8666-666666666666"),
        ("snapshot_digest", "b" * 64),
        ("evidence_version", 2),
    ),
)
def test_same_tepp_request_key_cannot_replay_across_governance_scope(
    field_name: str,
    replacement: object,
) -> None:
    """Treat same-key reuse across local tenant/study/actor/evidence scope as conflict."""
    packet = build_valid()
    rebound = replace(packet, **{field_name: replacement})

    assert packet.request_digest() == rebound.request_digest()
    assert not packet.is_idempotent_retry_of(rebound)
    assert packet.idempotency_conflicts_with(rebound)


def test_governance_evidence_carries_the_key_required_for_durable_retry_control() -> None:
    """Keep the durable audit/outbox evidence self-sufficient for retry/conflict checks."""
    packet = build_valid()

    evidence = packet.governance_evidence()

    assert evidence["idempotency_key"] == packet.idempotency_key
    assert evidence["tepp_request_digest"] == packet.request_digest()
    assert evidence["governance_scope_digest"] == packet.governance_scope_digest()
