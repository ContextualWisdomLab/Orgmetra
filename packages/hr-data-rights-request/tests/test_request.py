"""Executable privacy contract for value-minimized HR data-rights request evidence."""

from copy import copy
from datetime import datetime, timedelta, timezone
import json

import pytest

from orgmetra_hr_data_rights_request import (
    HrDataRightsRequestPacket,
    build_hr_data_rights_request_packet,
)


TENANT = "018f2f65-9a8b-7c6d-8e5f-1234567890ab"
REQUEST = "data_rights_request:12345678-1234-4234-8234-1234567890ab"
PERSON = "person_record:person_8mTq4W8r"
REQUESTER = "actor:11111111-1111-4111-8111-111111111111"
POLICY = "data_rights_policy:22222222-2222-4222-8222-222222222222"
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
    assert document["requester_role_code"] == "data_subject"
    assert document["requested_action_code"] == "access_copy"
    assert document["request_state"] == "request_recorded"
    assert document["eligibility_state"] == "requires_authoritative_policy_review"
    assert document["disclosure_state"] == "not_authorized_to_disclose"
    assert document["mutation_state"] == "not_authorized_to_modify_hr_data"
    assert document["contains_hr_data"] is False
    assert document["contains_credentials"] is False
    assert document["submitted_at"] == "2026-08-23T00:40:00Z"
    assert document["recorded_at"] == "2026-08-23T00:41:00Z"
    assert len(packet.sha256_digest()) == 64
    assert repr(packet) == "HrDataRightsRequestPacket(<redacted>)"


def test_supports_policy_neutral_request_intents_without_claiming_entitlement() -> None:
    """Route common request intents while keeping every request pending authoritative review."""
    for action in (
        "access_copy",
        "correct_record",
        "delete_record",
        "restrict_processing",
    ):
        document = build(requested_action_code=action).canonical_document()
        assert document["requested_action_code"] == action
        assert document["eligibility_state"] == "requires_authoritative_policy_review"
        assert document["disclosure_state"] == "not_authorized_to_disclose"
        assert document["mutation_state"] == "not_authorized_to_modify_hr_data"


def test_supports_data_subject_or_authorized_representative_intake() -> None:
    """Record requester role without treating either role label as proof of authority."""
    for role in ("data_subject", "authorized_representative"):
        document = build(requester_role_code=role).canonical_document()
        assert document["requester_role_code"] == role
        assert document["eligibility_state"] == "requires_authoritative_policy_review"


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


@pytest.mark.parametrize(
    "tenant",
    ["not-a-uuid", "00000000-0000-0000-0000-000000000000", "ffffffff-ffff-ffff-ffff-ffffffffffff"],
)
def test_rejects_noncanonical_or_sentinel_tenants(tenant: str) -> None:
    """Require one canonical operational tenant UUID without imposing a UUID version."""
    with pytest.raises(ValueError, match="tenant_record_id"):
        build(tenant_record_id=tenant)


@pytest.mark.parametrize(
    "reference",
    [
        "wrong:12345678-1234-4234-8234-1234567890ab",
        "data_rights_request:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "data_rights_request:not-a-uuid",
    ],
)
def test_rejects_invalid_packet_owned_request_references(reference: str) -> None:
    """Require a packet-owned opaque UUIDv4 request correlation."""
    with pytest.raises(ValueError, match="data_rights_request_reference"):
        build(data_rights_request_reference=reference)


@pytest.mark.parametrize(
    "reference",
    ["person:abc", "person_record:", "person_record:bad value", "person_record:/root"],
)
def test_rejects_invalid_person_record_references(reference: str) -> None:
    """Require an opaque Person reference without inventing a foreign identifier format."""
    with pytest.raises(ValueError, match="person_record_reference"):
        build(person_record_reference=reference)


@pytest.mark.parametrize(
    "actor",
    ["worker-123", "actor:", "actor:alice_smith", "actor:employee-123", "other:12345678-1234-4234-8234-1234567890ab"],
)
def test_rejects_identifying_or_malformed_requester_actor_references(actor: str) -> None:
    """Keep durable requester correlation pseudonymous after identity resolution."""
    with pytest.raises(ValueError, match="requester_actor_reference"):
        build(requester_actor_reference=actor)


@pytest.mark.parametrize(
    "field",
    [
        "requester_identity_evidence_digest",
        "submission_evidence_digest",
        "applicable_policy_digest",
    ],
)
def test_rejects_invalid_sha256_evidence(field: str) -> None:
    """Require lowercase SHA-256 digests for reviewed external evidence."""
    with pytest.raises(ValueError, match=field):
        build(**{field: "not-a-digest"})


@pytest.mark.parametrize("version", [True, 0, 2_147_483_648])
def test_rejects_invalid_evidence_versions(version: object) -> None:
    """Reject booleans and out-of-range evidence versions."""
    with pytest.raises(ValueError, match="evidence_version"):
        build(evidence_version=version)


def test_requires_exact_utc_submission_and_recorded_times() -> None:
    """Reject naive, non-UTC, and subclass-driven timestamp semantics."""
    with pytest.raises(ValueError, match="submitted_at"):
        build(submitted_at=datetime(2026, 8, 23, 0, 40))
    with pytest.raises(ValueError, match="submitted_at"):
        build(submitted_at=datetime(2026, 8, 23, 9, 40, tzinfo=timezone(timedelta(hours=9))))
    with pytest.raises(ValueError, match="recorded_at"):
        build(recorded_at=datetime(2026, 8, 23, 0, 41))


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


def test_rejects_direct_governance_state_drift() -> None:
    """Keep the request packet non-authorizing under direct construction."""
    payload = values()
    with pytest.raises(ValueError, match="eligibility_state"):
        HrDataRightsRequestPacket(**payload, eligibility_state="approved")
    with pytest.raises(ValueError, match="disclosure_state"):
        HrDataRightsRequestPacket(**payload, disclosure_state="authorized_to_disclose")
    with pytest.raises(ValueError, match="mutation_state"):
        HrDataRightsRequestPacket(**payload, mutation_state="authorized_to_delete")
    with pytest.raises(ValueError, match="contains_hr_data"):
        HrDataRightsRequestPacket(**payload, contains_hr_data=True)


def test_detects_post_construction_rewrite_and_unregistered_copy() -> None:
    """Reject field rewrites and copied evidence that did not cross the issuance boundary."""
    packet = build()
    object.__setattr__(packet, "requested_action_code", "delete_record")
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()

    copied = copy(build())
    with pytest.raises(ValueError, match="not registered"):
        copied.canonical_json()


def test_checked_payload_is_the_payload_emitted_to_callers() -> None:
    """Ensure canonical export does not reread live fields after integrity verification."""
    packet = build()
    original_validate = packet._validate

    def mutate_after_validation() -> None:
        """Mutate a trust field after the normal live-field validation step."""
        original_validate()
        object.__setattr__(packet, "requested_action_code", "delete_record")

    object.__setattr__(packet, "_validate", mutate_after_validation)
    with pytest.raises((AttributeError, ValueError, TypeError)):
        packet.canonical_document()


def test_public_api_has_beginner_readable_docstrings() -> None:
    """Keep the public privacy request API understandable to new maintainers."""
    assert HrDataRightsRequestPacket.__doc__
    assert build_hr_data_rights_request_packet.__doc__
