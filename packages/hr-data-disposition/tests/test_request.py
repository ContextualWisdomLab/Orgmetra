"""Executable contract for governed HR data disposition execution requests."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json

import pytest

from orgmetra_hr_data_disposition import HrDataDispositionExecutionRequest


TENANT = "018f7f76-8b7b-7c74-8f4d-1c91262926ba"
DISPOSITION = "disposition_request:55555555-5555-4555-8555-555555555555"
RETENTION_REVIEW = "retention_review:66666666-6666-4666-8666-666666666666"
RESOURCE = "person_record:77777777-7777-4777-8777-777777777777"
POLICY = "retention_policy:88888888-8888-4888-8888-888888888888"
REQUESTER = "actor:99999999-9999-4999-8999-999999999999"
REVIEWER = "actor:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def request(**overrides: object) -> HrDataDispositionExecutionRequest:
    """Build one valid post-retention request and apply focused overrides."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "disposition_request_reference": DISPOSITION,
        "retention_review_reference": RETENTION_REVIEW,
        "retention_review_digest": DIGEST_A,
        "resource_kind": "person_record",
        "resource_reference": RESOURCE,
        "record_category_code": "worker_personnel_record",
        "retention_policy_reference": POLICY,
        "retention_policy_digest": DIGEST_B,
        "retention_due_on": date(2026, 7, 31),
        "reviewed_on": date(2026, 8, 1),
        "legal_hold_state": "clear",
        "requested_disposition_action": "delete_application_record",
        "requester_actor_reference": REQUESTER,
        "reviewer_actor_reference": REVIEWER,
        "evidence_version": 1,
        "recorded_at": datetime(2026, 8, 1, 10, 30, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return HrDataDispositionExecutionRequest(**values)


def test_request_is_explicitly_non_authorizing_and_value_minimized() -> None:
    """A valid request describes the next approval step without claiming execution."""
    packet = request()
    document = packet.canonical_document()

    assert packet.purpose_code == "hr_data_disposition_execution_request"
    assert packet.human_review_required is True
    assert packet.scope_verification_state == "requires_authoritative_resolution"
    assert packet.execution_authorization_state == "not_authorized_to_execute"
    assert packet.media_sanitization_state == "not_claimed"
    assert "separate human execution approval" in packet.next_action
    assert "not_authorized_to_execute" in packet.canonical_json()
    assert "password" not in document
    assert repr(packet) == "HrDataDispositionExecutionRequest(<redacted>)"
    assert len(packet.evidence_digest()) == 64
    assert json.loads(packet.canonical_json()) == document
    assert document["recorded_at"] == "2026-08-01T10:30:00Z"
    assert document["retention_due_on"] == "2026-07-31"
    assert document["reviewed_on"] == "2026-08-01"


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("tenant_record_id", "", "tenant_record_id must not be empty"),
        ("tenant_record_id", "x" * 201, "tenant_record_id must be at most 200 characters"),
        ("tenant_record_id", 7, "tenant_record_id must be exact built-in str"),
        ("tenant_record_id", "not-a-uuid", "tenant_record_id must be a canonical UUID"),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000", "canonical non-sentinel"),
        ("tenant_record_id", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF", "canonical non-sentinel"),
        ("disposition_request_reference", "wrong:55555555-5555-4555-8555-555555555555", "namespace"),
        ("disposition_request_reference", "disposition_request:not-a-uuid", "canonical UUIDv4"),
        ("disposition_request_reference", "disposition_request:55555555-5555-1555-8555-555555555555", "canonical UUIDv4"),
        ("disposition_request_reference", "disposition_request:55555555-5555-4555-8555-55555555555A", "canonical UUIDv4"),
        ("retention_review_digest", "A" * 64, "lowercase SHA-256"),
        ("retention_review_digest", "a" * 63, "lowercase SHA-256"),
        ("resource_kind", "shadow_person", "allowed reviewed value"),
        ("record_category_code", "shadow_record", "allowed reviewed value"),
        ("requested_disposition_action", "hard_delete_now", "allowed reviewed value"),
        ("upstream_retention_window_state", "retain_until_due", "allowed reviewed value"),
        ("upstream_disposition_authorization_state", "authorized_to_delete", "allowed reviewed value"),
    ],
)
def test_rejects_malformed_or_unreviewed_text_evidence(
    field_name: str,
    value: object,
    message: str,
) -> None:
    """Malformed identity, digest, and governance text fails closed."""
    with pytest.raises(ValueError, match=message):
        request(**{field_name: value})


@pytest.mark.parametrize(
    "resource_kind",
    [
        "candidate_profile",
        "person_record",
        "employment_record",
        "selection_decision",
        "criterion_observation",
        "compensation_record",
    ],
)
def test_accepts_each_reviewed_resource_kind(resource_kind: str) -> None:
    """Each closed resource kind accepts only its matching UUIDv4 namespace."""
    packet = request(
        resource_kind=resource_kind,
        resource_reference=f"{resource_kind}:77777777-7777-4777-8777-777777777777",
    )
    assert packet.resource_kind == resource_kind


@pytest.mark.parametrize(
    "record_category_code",
    [
        "candidate_employment_record",
        "worker_personnel_record",
        "selection_evidence_record",
        "performance_criterion_record",
        "compensation_governance_record",
    ],
)
def test_accepts_each_reviewed_record_category(record_category_code: str) -> None:
    """The request supports the reviewed HR retention record categories."""
    assert request(record_category_code=record_category_code).record_category_code == record_category_code


@pytest.mark.parametrize(
    "requested_disposition_action",
    ["delete_application_record", "pseudonymize_derived_record"],
)
def test_accepts_only_reviewed_disposition_actions(requested_disposition_action: str) -> None:
    """Reviewed actions remain requests and do not grant destructive authority."""
    packet = request(requested_disposition_action=requested_disposition_action)
    assert packet.requested_disposition_action == requested_disposition_action
    assert packet.execution_authorization_state == "not_authorized_to_execute"


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("retention_due_on", datetime(2026, 7, 31, tzinfo=timezone.utc), "exact built-in date"),
        ("reviewed_on", datetime(2026, 8, 1, tzinfo=timezone.utc), "exact built-in date"),
        ("reviewed_on", date(2026, 7, 31), "after retention_due_on"),
        ("reviewed_on", date(2026, 7, 30), "after retention_due_on"),
        ("legal_hold_state", "active", "allowed reviewed value"),
        ("evidence_version", True, "exact built-in int"),
        ("evidence_version", 0, "between 1 and 2147483647"),
        ("evidence_version", 2_147_483_648, "between 1 and 2147483647"),
        ("recorded_at", date(2026, 8, 1), "exact built-in datetime"),
        ("recorded_at", datetime(2026, 8, 1, 10, 30), "datetime.timezone.utc exactly"),
        (
            "recorded_at",
            datetime(2026, 8, 1, 10, 30, tzinfo=timezone(timedelta(hours=9))),
            "datetime.timezone.utc exactly",
        ),
        (
            "recorded_at",
            datetime(2026, 7, 31, 23, 59, tzinfo=timezone.utc),
            "cannot precede reviewed_on",
        ),
        (
            "recorded_at",
            datetime(2099, 8, 1, 10, 30, tzinfo=timezone.utc),
            "cannot be in the future",
        ),
    ],
)
def test_rejects_invalid_chronology_hold_or_scalar_evidence(
    field_name: str,
    value: object,
    message: str,
) -> None:
    """Chronology, legal-hold, evidence-version, and time evidence fail closed."""
    with pytest.raises(ValueError, match=message):
        request(**{field_name: value})


def test_requires_distinct_requester_and_reviewer() -> None:
    """One actor cannot request and review the same disposition request."""
    with pytest.raises(ValueError, match="must differ"):
        request(reviewer_actor_reference=REQUESTER)


def test_reference_namespace_must_follow_resource_kind() -> None:
    """A valid UUID in the wrong resource namespace cannot cross the boundary."""
    with pytest.raises(ValueError, match="person_record: namespace"):
        request(resource_reference="employment_record:77777777-7777-4777-8777-777777777777")


def test_canonical_document_is_stable_for_equivalent_construction() -> None:
    """Equivalent reviewed inputs yield the same canonical evidence and digest."""
    first = request()
    second = request()
    assert first.canonical_json() == second.canonical_json()
    assert first.evidence_digest() == second.evidence_digest()


class ForgedText(str):
    """Expose caller-defined equality and hashing while retaining different raw text."""

    def __eq__(self, other: object) -> bool:
        """Pretend to equal reviewed values."""
        return True

    def __ne__(self, other: object) -> bool:
        """Pretend never to differ from reviewed values."""
        return False

    def __hash__(self) -> int:
        """Forge the hash of a reviewed legal-hold state."""
        return hash("clear")


class ForgedInt(int):
    """Expose caller-defined ordering around an unsafe integer."""

    def __le__(self, other: object) -> bool:
        """Pretend to satisfy upper-bound checks."""
        return True

    def __ge__(self, other: object) -> bool:
        """Pretend to satisfy lower-bound checks."""
        return True

    def __lt__(self, other: object) -> bool:
        """Pretend never to be below a lower bound."""
        return False

    def __gt__(self, other: object) -> bool:
        """Pretend never to be above an upper bound."""
        return False


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("legal_hold_state", ForgedText("active")),
        ("requested_disposition_action", ForgedText("hard_delete_now")),
        ("tenant_record_id", ForgedText(TENANT)),
        ("resource_reference", ForgedText(RESOURCE)),
        ("retention_review_digest", ForgedText(DIGEST_A)),
        ("evidence_version", ForgedInt(0)),
    ],
)
def test_rejects_caller_defined_scalar_subclasses(field_name: str, value: object) -> None:
    """Caller-defined scalar behavior cannot forge reviewed or canonical evidence."""
    with pytest.raises(ValueError):
        request(**{field_name: value})


def test_revalidates_live_state_before_serialization() -> None:
    """Low-level mutation cannot turn an already-built request into forged audit evidence."""
    packet = request()
    object.__setattr__(packet, "legal_hold_state", "active")
    with pytest.raises(ValueError):
        packet.canonical_json()


def test_revalidates_recorded_time_before_digesting() -> None:
    """A post-construction noncanonical timestamp cannot enter the evidence digest."""
    packet = request()
    object.__setattr__(packet, "recorded_at", datetime(2026, 8, 1, 10, 30))
    with pytest.raises(ValueError):
        packet.evidence_digest()


def test_rejects_valid_post_construction_evidence_replacement() -> None:
    """A different valid policy digest cannot rewrite issued request evidence."""
    packet = request()
    object.__setattr__(packet, "retention_policy_digest", "c" * 64)
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()


def test_creation_seal_is_not_packet_writable() -> None:
    """A caller cannot replace an in-object seal because creation evidence is external."""
    packet = request()
    with pytest.raises(AttributeError):
        object.__setattr__(packet, "_creation_evidence_digest", "f" * 64)


def test_replace_cannot_bypass_post_due_or_actor_separation() -> None:
    """Dataclass replacement follows the same governed validation boundary."""
    packet = request()
    with pytest.raises(ValueError, match="after retention_due_on"):
        replace(packet, reviewed_on=packet.retention_due_on)
    with pytest.raises(ValueError, match="must differ"):
        replace(packet, reviewer_actor_reference=packet.requester_actor_reference)
