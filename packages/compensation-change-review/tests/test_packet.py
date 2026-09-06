"""Regression coverage for governed compensation-change review evidence."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone, tzinfo
import json
import re

import pytest

from orgmetra_compensation_change_review import (
    CompensationChangeReviewPacket,
    build_compensation_change_review_packet,
)


def build_valid(valid_packet_kwargs: dict[str, object]) -> CompensationChangeReviewPacket:
    """Build one valid packet through the supported public builder."""
    return build_compensation_change_review_packet(**valid_packet_kwargs)


def test_builds_deterministic_value_minimized_packet(valid_packet_kwargs: dict[str, object]) -> None:
    """A valid packet is canonical, human-only, unresolved, and excludes protected values."""
    packet = build_valid(valid_packet_kwargs)
    canonical = json.loads(packet.canonical_json())

    assert packet.decision_authority == "human_review_only"
    assert packet.review_state == "requires_human_review"
    assert packet.scope_verification_state == "requires_authoritative_resolution"
    assert packet.mutation_state == "not_authorized_to_apply"
    assert packet.external_execution_state == "not_authorized_to_execute"
    assert packet.contains_personal_data is True
    assert packet.contains_compensation_values is False
    assert packet.contains_protected_attribute_values is False
    assert canonical["generated_at"] == "2026-08-19T06:12:13.456789Z"
    assert canonical["evidence_version"] == 1
    assert len(packet.sha256_digest()) == 64
    assert packet.sha256_digest() == build_valid(valid_packet_kwargs).sha256_digest()


def test_canonical_evidence_changes_with_governed_artifact_or_version(valid_packet_kwargs: dict[str, object]) -> None:
    """Changing exact reviewed evidence or its version changes the immutable packet digest."""
    packet = build_valid(valid_packet_kwargs)
    changed_plan = replace(packet, proposed_compensation_plan_digest="2" * 64)
    changed_policy = replace(packet, compensation_policy_digest="3" * 64)
    changed_version = replace(packet, evidence_version=2)

    assert len({packet.sha256_digest(), changed_plan.sha256_digest(), changed_policy.sha256_digest(), changed_version.sha256_digest()}) == 4


def test_repr_redacts_personal_and_compensation_correlations(valid_packet_kwargs: dict[str, object]) -> None:
    """Normal repr formatting cannot leak worker, actor, or evidence correlation identifiers."""
    packet = build_valid(valid_packet_kwargs)
    rendered = repr(packet)

    assert rendered == "CompensationChangeReviewPacket(<redacted>)"
    for sensitive in (
        packet.tenant_record_id,
        packet.person_record_reference,
        packet.employment_record_reference,
        packet.current_compensation_snapshot_reference,
        packet.proposed_compensation_plan_reference,
        packet.requester_reference,
        packet.current_compensation_snapshot_digest,
    ):
        assert sensitive not in rendered


def test_next_action_requires_identity_scope_and_evidence_before_approval(valid_packet_kwargs: dict[str, object]) -> None:
    """The canonical operator instruction orders tenant, actor, worker, and evidence checks first."""
    action = build_valid(valid_packet_kwargs).next_action
    actor_clause = "verify their resolved actor identities are distinct"
    worker_clause = "prove the Person-to-Employment binding"
    evidence_clause = "verify the current compensation snapshot"
    approval_clause = "record accountable human approval"

    assert action.startswith("Re-resolve every packet reference within tenant_record_id;")
    assert action.index(actor_clause) < action.index(worker_clause) < action.index(evidence_clause) < action.index(approval_clause)
    assert "without copying compensation or protected-attribute values" in action
    assert action.endswith("execute payroll only through its published owner contract.")


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("contains_personal_data", False, "acknowledge sensitive personal-data correlation"),
        ("contains_compensation_values", True, "must not contain compensation values"),
        ("contains_protected_attribute_values", True, "must not contain protected-attribute values"),
        ("contains_free_form_case_narrative", True, "must not contain free-form case narrative"),
        ("contains_free_form_model_output", True, "must not contain free-form model output"),
        ("human_confirmation_required", False, "human confirmation is mandatory"),
        ("decision_authority", "model_authority", "must remain human_review_only"),
        ("review_state", "approved", "must remain requires_human_review"),
        ("scope_verification_state", "resolved", "must remain requires_authoritative_resolution"),
        ("mutation_state", "authorized", "must remain not_authorized_to_apply"),
        ("external_execution_state", "executed", "must remain not_authorized_to_execute"),
        ("next_action", "Send directly to payroll.", "next_action must remain"),
    ],
)
def test_direct_constructor_and_replace_fail_closed(
    field_name: str,
    value: object,
    message: str,
    valid_packet_kwargs: dict[str, object],
) -> None:
    """Both construction paths reject attempts to weaken immutable high-impact guardrails."""
    direct_kwargs = valid_packet_kwargs.copy()
    direct_kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        CompensationChangeReviewPacket(**direct_kwargs)

    packet = build_valid(valid_packet_kwargs)
    with pytest.raises(ValueError, match=message):
        replace(packet, **{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("tenant_record_id", "not-a-uuid", "canonical UUID text"),
        ("tenant_record_id", 42, "canonical UUID text"),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000", "canonical operational UUID"),
        ("tenant_record_id", "ffffffff-ffff-ffff-ffff-ffffffffffff", "canonical operational UUID"),
        ("tenant_record_id", "11111111-1111-4111-8111-11111111111A", "canonical operational UUID"),
        ("person_record_reference", "person_record:seongho", "opaque person_record"),
        ("person_record_reference", 42, "opaque person_record"),
        ("person_record_reference", "actor:33333333-3333-4333-8333-333333333333", "opaque person_record"),
        ("person_record_reference", "person_record:00000000-0000-0000-0000-000000000000", "opaque person_record"),
        ("person_record_reference", "person_record:ffffffff-ffff-ffff-ffff-ffffffffffff", "opaque person_record"),
        ("person_record_reference", "person_record:33333333-3333-4333-8333-33333333333A", "opaque person_record"),
        ("person_record_reference", "person_record:" + "x" * 200, "opaque person_record"),
        ("current_compensation_snapshot_digest", "A" * 64, "lowercase SHA-256"),
        ("current_compensation_snapshot_digest", "a" * 63, "lowercase SHA-256"),
        ("current_compensation_snapshot_digest", 64, "lowercase SHA-256"),
        ("purpose_code", "general_hr", "purpose_code must remain"),
        ("reason_code", "medical_leave_adjustment", "approved non-sensitive compensation-review category"),
        ("proposed_effective_on", "2026-10-01", "must be a date"),
        ("proposed_effective_on", datetime(2026, 10, 1, tzinfo=timezone.utc), "must be a date"),
        ("generated_at", datetime(2026, 8, 19, 6, 12), "generated_at must be timezone-aware"),
        ("generated_at", "2026-08-19T06:12:00Z", "generated_at must be timezone-aware"),
        ("evidence_version", True, "evidence_version must be an integer"),
        ("evidence_version", 0, "evidence_version must be an integer"),
        ("evidence_version", 2_147_483_648, "evidence_version must be an integer"),
    ],
)
def test_invalid_core_inputs_fail_closed(
    field_name: str,
    value: object,
    message: str,
    valid_packet_kwargs: dict[str, object],
) -> None:
    """Malformed identity, evidence, purpose, time, and version inputs are rejected."""
    kwargs = valid_packet_kwargs.copy()
    kwargs[field_name] = value
    with pytest.raises(ValueError, match=message):
        build_compensation_change_review_packet(**kwargs)


def test_every_reference_and_digest_is_validated(valid_packet_kwargs: dict[str, object]) -> None:
    """Each trust-bearing reference and digest field is individually bound to its namespace."""
    packet = build_valid(valid_packet_kwargs)
    reference_fields = {
        "compensation_review_reference": "compensation_change_review",
        "person_record_reference": "person_record",
        "employment_record_reference": "employment_record",
        "active_assignment_snapshot_reference": "active_assignment_snapshot",
        "current_compensation_snapshot_reference": "compensation_snapshot",
        "proposed_compensation_plan_reference": "compensation_plan",
        "compensation_policy_reference": "compensation_policy",
        "pay_equity_review_reference": "pay_equity_review",
        "budget_authorization_reference": "budget_authorization",
        "payroll_handoff_plan_reference": "payroll_handoff_plan",
        "requester_reference": "actor",
        "reviewer_reference": "actor",
    }
    digest_fields = [name for name in valid_packet_kwargs if name.endswith("_digest")]

    for field_name, prefix in reference_fields.items():
        with pytest.raises(ValueError, match=re.escape(f"opaque {prefix}: reference")):
            replace(packet, **{field_name: "wrong:11111111-1111-4111-8111-111111111111"})
    for field_name in digest_fields:
        with pytest.raises(ValueError, match="lowercase SHA-256"):
            replace(packet, **{field_name: "z" * 64})


def test_same_opaque_actor_reference_is_rejected_early(valid_packet_kwargs: dict[str, object]) -> None:
    """Exact requester/reviewer reuse is denied before authoritative identity re-resolution."""
    kwargs = valid_packet_kwargs.copy()
    kwargs["reviewer_reference"] = kwargs["requester_reference"]
    with pytest.raises(ValueError, match="different actor references"):
        build_compensation_change_review_packet(**kwargs)


def test_fractional_and_offset_timestamps_preserve_distinct_instants(valid_packet_kwargs: dict[str, object]) -> None:
    """Canonical evidence preserves microseconds while normalizing equivalent offsets to UTC."""
    packet = build_valid(valid_packet_kwargs)
    later = replace(packet, generated_at=packet.generated_at.replace(microsecond=456790))
    offset = replace(
        packet,
        generated_at=datetime(2026, 8, 19, 15, 12, 13, 456789, tzinfo=timezone(timedelta(hours=9))),
    )

    assert packet.sha256_digest() != later.sha256_digest()
    assert packet.canonical_json() == offset.canonical_json()


class UnknownOffset(tzinfo):
    """Timezone fixture whose UTC offset is intentionally unknown."""

    def utcoffset(self, dt: datetime | None) -> None:
        """Return no offset so the packet must reject the timestamp."""
        return None

    def dst(self, dt: datetime | None) -> None:
        """Return no daylight-saving offset for the invalid fixture."""
        return None


def test_timezone_with_unknown_offset_is_rejected(valid_packet_kwargs: dict[str, object]) -> None:
    """A tzinfo object is insufficient when it cannot establish an actual UTC offset."""
    kwargs = valid_packet_kwargs.copy()
    kwargs["generated_at"] = datetime(2026, 8, 19, 6, 12, tzinfo=UnknownOffset())
    with pytest.raises(ValueError, match="generated_at must be timezone-aware"):
        build_compensation_change_review_packet(**kwargs)
