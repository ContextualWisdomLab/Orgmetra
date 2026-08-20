"""Contract, privacy, and evidence regressions for the Orgmetra → TEPP adapter."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone, tzinfo
import json
from uuid import uuid1

import pytest

from orgmetra_tepp_adapter import (
    TEPP_ANALYSIS_RUN_CONTRACT_VERSION,
    TEPP_PROTECTED_REVISION,
    TeppAnalysisRequestPacket,
    build_tepp_analysis_request_packet,
)


def values() -> dict[str, object]:
    """Return one valid, non-PII workforce-validation request."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "validation_study_reference": "validation_study:22222222-2222-4222-8222-222222222222",
        "requested_by_actor_reference": "actor:33333333-3333-4333-8333-333333333333",
        "tepp_workspace_id": "workspace-opaque-8e9f1d",
        "tepp_snapshot_id": "snapshot-opaque-2f6c91",
        "snapshot_digest": "a" * 64,
        "idempotency_key": "orgmetra-tepp-20260820-0001",
        "knowledge_cutoff": datetime(2026, 8, 20, 16, 45, 12, 345678, tzinfo=timezone(timedelta(hours=9))),
        "model_contract_version": "temporal-event-v1",
        "output_profile": "validation-report",
        "generated_at": datetime(2026, 8, 20, 7, 50, 1, 123456, tzinfo=timezone.utc),
    }


def build_valid() -> TeppAnalysisRequestPacket:
    """Build a valid packet through the public builder."""
    return build_tepp_analysis_request_packet(**values())


def test_request_matches_exact_tepp_v1_wire_shape_and_is_deterministic() -> None:
    packet = build_valid()
    request = packet.tepp_request()

    assert request == {
        "contract_version": 1,
        "idempotency_key": "orgmetra-tepp-20260820-0001",
        "tenant_workspace_id": "workspace-opaque-8e9f1d",
        "snapshot_id": "snapshot-opaque-2f6c91",
        "knowledge_cutoff": "2026-08-20T07:45:12.345678Z",
        "model_contract_version": "temporal-event-v1",
        "output_profile": "validation-report",
    }
    assert TEPP_ANALYSIS_RUN_CONTRACT_VERSION == 1
    assert TEPP_PROTECTED_REVISION == "7c29e7c971d7940e1fb3def1ed3aae2d1bc8ad4a"
    assert json.loads(packet.canonical_tepp_json()) == request
    assert len(packet.request_digest()) == 64
    assert packet.request_digest() == build_valid().request_digest()


def test_retry_comparison_detects_exact_replays_and_same_key_conflicts() -> None:
    packet = build_valid()
    same = build_valid()
    changed_values = values()
    changed_values["tepp_snapshot_id"] = "snapshot-opaque-different"
    conflict = TeppAnalysisRequestPacket(**changed_values)
    different_key_values = values()
    different_key_values["idempotency_key"] = "orgmetra-tepp-20260820-0002"
    different_key = TeppAnalysisRequestPacket(**different_key_values)

    assert packet.is_idempotent_retry_of(same)
    assert not packet.idempotency_conflicts_with(same)
    assert not packet.is_idempotent_retry_of(conflict)
    assert packet.idempotency_conflicts_with(conflict)
    assert not packet.is_idempotent_retry_of(different_key)
    assert not packet.idempotency_conflicts_with(different_key)
    assert not packet.is_idempotent_retry_of(object())
    assert not packet.idempotency_conflicts_with(object())


def test_governance_evidence_is_value_minimized_and_actionable() -> None:
    packet = build_valid()
    evidence = packet.governance_evidence()

    assert evidence["tenant_record_id"] == packet.tenant_record_id
    assert evidence["validation_study_reference"] == packet.validation_study_reference
    assert evidence["requested_by_actor_reference"] == packet.requested_by_actor_reference
    assert evidence["tepp_workspace_id"] == packet.tepp_workspace_id
    assert evidence["tepp_snapshot_id"] == packet.tepp_snapshot_id
    assert evidence["snapshot_digest"] == "a" * 64
    assert evidence["generated_at"] == "2026-08-20T07:50:01.123456Z"
    assert evidence["tepp_contract_version"] == 1
    assert evidence["tepp_protected_revision"] == TEPP_PROTECTED_REVISION
    assert evidence["tepp_request_digest"] == packet.request_digest()
    assert evidence["transport_state"] == "requires_published_tepp_service_contract"
    assert evidence["decision_authority"] == "human_scientific_review_only"
    assert evidence["llm_output_authority"] == "untrusted_draft_evidence"
    assert evidence["contains_personal_data"] is True
    assert evidence["contains_direct_identity_values"] is False
    assert evidence["human_confirmation_required"] is True
    assert "source_text" not in evidence
    assert "credentials" not in evidence
    assert "salary" not in json.dumps(evidence)
    assert "executable TEPP service contract is actually published before transport" in packet.next_action
    assert "human scientific review" in packet.next_action


def test_repr_and_immutability_protect_correlation_values() -> None:
    packet = build_valid()
    rendered = repr(packet)

    assert rendered == "TeppAnalysisRequestPacket(<redacted>)"
    assert packet.tenant_record_id not in rendered
    assert packet.validation_study_reference not in rendered
    assert packet.snapshot_digest not in rendered
    with pytest.raises(FrozenInstanceError):
        packet.tepp_workspace_id = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("tenant_record_id", str(uuid1()), "UUIDv4"),
        ("tenant_record_id", "11111111-1111-4111-8111-11111111111A", "UUIDv4"),
        ("tenant_record_id", 1, "UUIDv4"),
        ("validation_study_reference", "wrong:22222222-2222-4222-8222-222222222222", "validation_study"),
        ("validation_study_reference", f"validation_study:{uuid1()}", "UUIDv4"),
        ("requested_by_actor_reference", "actor:not-a-uuid", "UUIDv4"),
        ("snapshot_digest", "A" * 64, "lowercase SHA-256"),
        ("snapshot_digest", 1, "lowercase SHA-256"),
        ("evidence_version", 0, "1 through"),
        ("evidence_version", True, "1 through"),
        ("evidence_version", 2_147_483_648, "1 through"),
    ],
)
def test_local_authority_and_evidence_identifiers_fail_closed(field_name: str, value: object, message: str) -> None:
    kwargs = values()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        TeppAnalysisRequestPacket(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("tepp_workspace_id", "", "bounded opaque"),
        ("tepp_workspace_id", "a" * 257, "bounded opaque"),
        ("tepp_workspace_id", "workspace with space", "visible ASCII"),
        ("tepp_workspace_id", "sk-secret-looking-token", "credential-shaped"),
        ("tepp_snapshot_id", "github_pat_secretlooking", "credential-shaped"),
        ("tepp_workspace_id", 7, "bounded opaque"),
        ("tepp_snapshot_id", "snapshot\nvalue", "visible ASCII"),
        ("idempotency_key", "short", "16 through 128"),
        ("idempotency_key", "a" * 129, "16 through 128"),
        ("idempotency_key", "valid-length-but space", "16 through 128"),
        ("idempotency_key", "sk-secret-looking-idempotency", "credential-shaped"),
        ("idempotency_key", 7, "16 through 128"),
        ("model_contract_version", "Temporal Event", "governed machine code"),
        ("model_contract_version", "", "governed machine code"),
        ("model_contract_version", 1, "governed machine code"),
        ("output_profile", "x" * 129, "governed machine code"),
    ],
)
def test_foreign_contract_tokens_are_bounded_without_inventing_foreign_authority(
    field_name: str, value: object, message: str
) -> None:
    kwargs = values()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        TeppAnalysisRequestPacket(**kwargs)


class NullOffsetTz(tzinfo):
    """Timezone object whose offset is intentionally unusable."""

    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None

    def tzname(self, dt: datetime | None) -> str:
        return "NULL"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("knowledge_cutoff", datetime(2026, 8, 20, 7, 45)),
        ("knowledge_cutoff", "2026-08-20T07:45:00Z"),
        ("generated_at", datetime(2026, 8, 20, 7, 50).replace(tzinfo=NullOffsetTz())),
    ],
)
def test_temporal_evidence_requires_real_timezone_aware_instants(field_name: str, value: object) -> None:
    kwargs = values()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match="timezone-aware"):
        TeppAnalysisRequestPacket(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("purpose_code", "selection_decision", "workforce_validation_analysis"),
        ("tepp_contract_version", 2, "remain 1"),
        ("tepp_protected_revision", "0" * 40, "reviewed protected revision"),
        ("transport_state", "ready_to_send", "requires_published_tepp_service_contract"),
        ("decision_authority", "automated", "human_scientific_review_only"),
        ("llm_output_authority", "authoritative", "untrusted_draft_evidence"),
        ("contains_personal_data", False, "must remain true"),
        ("contains_direct_identity_values", True, "must remain false"),
        ("contains_source_text", True, "must remain false"),
        ("contains_credentials", True, "must remain false"),
        ("human_confirmation_required", False, "must remain true"),
        ("next_action", "Send immediately.", "governed TEPP handoff"),
    ],
)
def test_direct_construction_and_replace_cannot_expand_authority(
    field_name: str, value: object, message: str
) -> None:
    kwargs = values()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        TeppAnalysisRequestPacket(**kwargs)

    with pytest.raises(ValueError, match=message):
        replace(build_valid(), **{field_name: value})
