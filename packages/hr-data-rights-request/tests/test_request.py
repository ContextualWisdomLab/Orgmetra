"""Executable privacy contract for value-minimized HR data-rights request evidence."""

from copy import copy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from orgmetra_hr_data_rights_request import (
    HrDataRightsRequestPacket,
    build_hr_data_rights_request_packet,
)


TENANT = "018f2f65-9a8b-7c6d-8e5f-1234567890ab"
REQUEST = "data_rights_request:12345678-1234-4234-8234-1234567890ac"
PERSON = "person_record:person_8mTq4W8r"
REQUESTER = "actor:11111111-1111-4111-8111-111111111111"
POLICY = "data_rights_policy:policy_7dYk9Q"
IDENTITY_DIGEST = "1" * 64
SUBMISSION_DIGEST = "2" * 64
POLICY_DIGEST = "3" * 64
SUBMITTED_AT = datetime(2026, 8, 23, 0, 40, tzinfo=timezone.utc)
RECORDED_AT = datetime(2026, 8, 23, 0, 41, tzinfo=timezone.utc)


def values() -> dict[str, object]:
    """Return one valid value-minimized request input set."""
    return {
        "tenant_record_id": TENANT,
        "data_rights_request_reference": REQUEST,
        "person_record_reference": PERSON,
        "requester_actor_reference": REQUESTER,
        "requester_identity_evidence_digest": IDENTITY_DIGEST,
        "submission_evidence_digest": SUBMISSION_DIGEST,
        "applicable_policy_reference": POLICY,
        "applicable_policy_digest": POLICY_DIGEST,
        "requester_role_code": "data_subject",
        "requested_action_code": "access_copy",
        "source_channel_code": "self_service",
        "submitted_at": SUBMITTED_AT,
        "recorded_at": RECORDED_AT,
        "evidence_version": 1,
    }


def build(**overrides: object) -> HrDataRightsRequestPacket:
    """Build one request packet with optional test overrides."""
    payload = values()
    payload.update(overrides)
    return build_hr_data_rights_request_packet(**payload)


def test_builds_value_minimized_non_authorizing_request_evidence() -> None:
    """Bind request provenance without granting disclosure, mutation, or deletion authority."""
    packet = build()
    document = packet.canonical_document()
    assert document["purpose_code"] == "hr_data_rights_request_intake"
    assert document["requester_role_code"] == "data_subject"
    assert document["requested_action_code"] == "access_copy"
    assert document["request_state"] == "request_recorded"
    assert document["eligibility_state"] == "requires_authoritative_policy_review"
    assert document["disclosure_state"] == "not_authorized_to_disclose"
    assert document["mutation_state"] == "not_authorized_to_modify_hr_data"
    assert document["contains_hr_data"] is False
    assert document["contains_credentials"] is False
    assert document["human_review_required"] is True
    assert document["submitted_at"] == "2026-08-23T00:40:00Z"
    assert document["recorded_at"] == "2026-08-23T00:41:00Z"
    assert repr(packet) == "HrDataRightsRequestPacket(<redacted>)"


def test_canonical_json_and_digest_are_deterministic() -> None:
    """Bind the exact canonical UTF-8 bytes to a stable SHA-256 audit correlation."""
    packet = build()
    first = packet.canonical_json()
    second = packet.canonical_json()
    assert first == second
    assert packet.sha256_digest() == sha256(first.encode("utf-8")).hexdigest()
    assert json.loads(first) == packet.canonical_document()


def test_supports_policy_neutral_request_intents_without_claiming_entitlement() -> None:
    """Route common request intents while keeping every request pending authoritative review."""
    for action in ("access_copy", "correct_record", "delete_record", "restrict_processing"):
        document = build(requested_action_code=action).canonical_document()
        assert document["requested_action_code"] == action
        assert document["eligibility_state"] == "requires_authoritative_policy_review"
        assert document["disclosure_state"] == "not_authorized_to_disclose"
        assert document["mutation_state"] == "not_authorized_to_modify_hr_data"


def test_supports_reviewed_requester_roles_and_channels() -> None:
    """Record narrow routing metadata without treating it as identity or entitlement proof."""
    for role in ("data_subject", "authorized_representative"):
        assert build(requester_role_code=role).requester_role_code == role
    for channel in ("self_service", "hr_service_desk", "privacy_office"):
        assert build(source_channel_code=channel).source_channel_code == channel


def test_binds_policy_identity_and_source_provenance_without_raw_contents() -> None:
    """Keep digests and opaque references while excluding raw HR and request contents."""
    rendered = build().canonical_json()
    document = json.loads(rendered)
    assert document["requester_identity_evidence_digest"] == IDENTITY_DIGEST
    assert document["submission_evidence_digest"] == SUBMISSION_DIGEST
    assert document["applicable_policy_digest"] == POLICY_DIGEST
    assert document["applicable_policy_reference"] == POLICY
    for forbidden in (
        "employee_name",
        "email_address",
        "phone_number",
        "salary_amount",
        "request_text",
        "password",
        "access_token",
    ):
        assert forbidden not in rendered.lower()


def test_requires_system_recording_not_before_submission() -> None:
    """Keep system-recorded time at or after the submitted request instant."""
    with pytest.raises(ValueError, match="recorded_at"):
        build(recorded_at=SUBMITTED_AT - timedelta(microseconds=1))
    assert build(recorded_at=SUBMITTED_AT).recorded_at == SUBMITTED_AT


@pytest.mark.parametrize(
    "action",
    ["", "approve_delete", "hire", "ACCESS_COPY", "export_everything"],
)
def test_rejects_actions_that_escape_the_request_only_vocabulary(action: str) -> None:
    """Do not let intake evidence become a disclosure, deletion, or employment command."""
    with pytest.raises(ValueError, match="requested_action_code"):
        build(requested_action_code=action)


@pytest.mark.parametrize("role", ["", "manager", "hr_admin", "DATA_SUBJECT"])
def test_rejects_unreviewed_requester_roles(role: str) -> None:
    """Keep requester role in the narrow intake vocabulary."""
    with pytest.raises(ValueError, match="requester_role_code"):
        build(requester_role_code=role)


@pytest.mark.parametrize("channel", ["", "email", "chat", "SELF_SERVICE"])
def test_rejects_unreviewed_source_channels(channel: str) -> None:
    """Keep source channel as bounded operational metadata rather than free text."""
    with pytest.raises(ValueError, match="source_channel_code"):
        build(source_channel_code=channel)


def test_rejects_overlong_otherwise_well_formed_codes() -> None:
    """Exercise the explicit code-size budget before allow-list lookup."""
    with pytest.raises(ValueError, match="requested_action_code"):
        build(requested_action_code="access_" + "a" * 64)


@pytest.mark.parametrize(
    "tenant",
    [
        "not-a-uuid",
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "018F2F65-9A8B-7C6D-8E5F-1234567890AB",
    ],
)
def test_rejects_noncanonical_or_sentinel_tenants(tenant: str) -> None:
    """Require one canonical operational tenant UUID without imposing a UUID version."""
    with pytest.raises(ValueError, match="tenant_record_id"):
        build(tenant_record_id=tenant)


def test_accepts_current_operational_tenant_uuid_versions() -> None:
    """Keep authoritative tenant identity independent of packet-owned UUIDv4 references."""
    assert build().tenant_record_id == TENANT


@pytest.mark.parametrize(
    "reference",
    [
        "wrong:12345678-1234-4234-8234-1234567890ab",
        "data_rights_request:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "data_rights_request:not-a-uuid",
        "data_rights_request:12345678-1234-4234-8234-1234567890AB",
        "data_rights_request:" + "a" * 150,
    ],
)
def test_rejects_invalid_packet_owned_request_references(reference: str) -> None:
    """Require a bounded packet-owned opaque UUIDv4 request correlation."""
    with pytest.raises(ValueError, match="data_rights_request_reference"):
        build(data_rights_request_reference=reference)


@pytest.mark.parametrize(
    ("field", "reference"),
    [
        ("person_record_reference", "person:abc"),
        ("person_record_reference", "person_record:"),
        ("person_record_reference", "person_record:bad value"),
        ("person_record_reference", "person_record:/root"),
        ("person_record_reference", "person_record:" + "a" * 150),
        ("applicable_policy_reference", "policy:abc"),
        ("applicable_policy_reference", "data_rights_policy:"),
    ],
)
def test_rejects_invalid_opaque_resource_or_policy_references(field: str, reference: str) -> None:
    """Require bounded namespaced opaque references without inventing foreign identifier syntax."""
    with pytest.raises(ValueError, match=field):
        build(**{field: reference})


@pytest.mark.parametrize(
    "actor",
    [
        "worker-123",
        "actor:",
        "actor:alice_smith",
        "actor:employee-123",
        "other:12345678-1234-4234-8234-1234567890ab",
        "actor:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    ],
)
def test_rejects_identifying_or_malformed_requester_actor_references(actor: str) -> None:
    """Keep durable requester correlation pseudonymous after identity resolution."""
    with pytest.raises(ValueError, match="requester_actor_reference"):
        build(requester_actor_reference=actor)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("requester_identity_evidence_digest", "not-a-digest"),
        ("submission_evidence_digest", "A" * 64),
        ("applicable_policy_digest", 7),
    ],
)
def test_rejects_invalid_sha256_evidence(field: str, value: object) -> None:
    """Require exact lowercase SHA-256 text for every reviewed evidence snapshot."""
    with pytest.raises(ValueError, match=field):
        build(**{field: value})


@pytest.mark.parametrize("version", [True, 0, 2_147_483_648, 1.0, "1"])
def test_rejects_invalid_evidence_versions(version: object) -> None:
    """Reject booleans, non-integers, and out-of-range evidence versions."""
    with pytest.raises(ValueError, match="evidence_version"):
        build(evidence_version=version)


class ForgedDateTime(datetime):
    """Adversarial datetime subtype rejected before timezone behavior can be trusted."""


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("submitted_at", datetime(2026, 8, 23, 0, 40)),
        ("submitted_at", datetime(2026, 8, 23, 9, 40, tzinfo=timezone(timedelta(hours=9)))),
        ("recorded_at", datetime(2026, 8, 23, 0, 41)),
        ("recorded_at", ForgedDateTime(2026, 8, 23, 0, 41, tzinfo=timezone.utc)),
    ],
)
def test_requires_exact_builtin_utc_submission_and_recorded_times(
    field: str,
    value: datetime,
) -> None:
    """Reject naive, non-UTC, and subtype-driven timestamp semantics."""
    with pytest.raises(ValueError, match=field):
        build(**{field: value})


class ForgedText(str):
    """Adversarial string whose equality and hash can lie to governance checks."""

    def __eq__(self, other: object) -> bool:
        """Pretend to equal any reviewed code."""
        return True

    def __hash__(self) -> int:
        """Pretend to hash like one reviewed code."""
        return hash("access_copy")


def test_rejects_hostile_runtime_string_subclasses() -> None:
    """Validate exact built-in text before lookup, comparison, parsing, or serialization."""
    with pytest.raises(ValueError, match="requested_action_code"):
        build(requested_action_code=ForgedText("approve_delete"))
    with pytest.raises(ValueError, match="person_record_reference"):
        build(person_record_reference=ForgedText(PERSON))
    with pytest.raises(ValueError, match="tenant_record_id"):
        build(tenant_record_id=ForgedText(TENANT))
    with pytest.raises(ValueError, match="submission_evidence_digest"):
        build(submission_evidence_digest=ForgedText(SUBMISSION_DIGEST))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("purpose_code", "hr_data_export"),
        ("contains_hr_data", True),
        ("contains_credentials", True),
        ("human_review_required", False),
        ("request_state", "fulfilled"),
        ("eligibility_state", "approved"),
        ("disclosure_state", "authorized_to_disclose"),
        ("mutation_state", "authorized_to_delete"),
        ("next_action", "Delete immediately."),
    ],
)
def test_rejects_direct_governance_state_drift(field: str, value: object) -> None:
    """Keep the request packet non-authorizing under direct construction."""
    payload = values()
    with pytest.raises(ValueError, match=field):
        HrDataRightsRequestPacket(**payload, **{field: value})


def test_rejects_post_construction_evidence_rewrite() -> None:
    """Fail closed when a valid trust-bearing value is rewritten after issuance."""
    packet = build()
    object.__setattr__(packet, "requested_action_code", "delete_record")
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()


def test_packet_runtime_is_final() -> None:
    """Governed request behavior cannot be replaced through subclass overrides."""
    with pytest.raises(TypeError, match="is final"):
        type("ForgedPacket", (HrDataRightsRequestPacket,), {})


def test_rejects_unregistered_copy() -> None:
    """Do not let a shallow copy inherit process-local issuance evidence."""
    copied = copy(build())
    with pytest.raises(ValueError, match="not registered"):
        copied.canonical_document()


def test_checked_payload_is_exactly_the_payload_emitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove canonical export never rereads live fields after verifying a payload snapshot."""
    packet = build()
    original_payload = HrDataRightsRequestPacket._payload
    call_count = 0

    def one_shot_payload(self: HrDataRightsRequestPacket) -> dict[str, object]:
        """Return a changed local snapshot only if production asks for a second read."""
        nonlocal call_count
        call_count += 1
        payload = original_payload(self)
        if call_count > 1:
            payload["requested_action_code"] = "delete_record"
        return payload

    monkeypatch.setattr(HrDataRightsRequestPacket, "_payload", one_shot_payload)
    document = packet.canonical_document()
    assert call_count == 1
    assert document["requested_action_code"] == "access_copy"

    call_count = 0
    rendered = packet.canonical_json()
    assert call_count == 1
    assert json.loads(rendered)["requested_action_code"] == "access_copy"


def test_public_api_has_beginner_readable_docstrings() -> None:
    """Keep the public privacy request API understandable to new maintainers."""
    assert HrDataRightsRequestPacket.__doc__
    assert build_hr_data_rights_request_packet.__doc__
