"""Behavioral and adversarial contract tests for Keyverse deprovision handoff evidence."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from uuid import UUID, uuid4

import pytest

from orgmetra_keyverse_identity_lifecycle_adapter import (
    KeyverseIdentityDeprovisionReviewPacket,
    REVIEWED_KEYVERSE_OPERATION,
    REVIEWED_KEYVERSE_REVISION,
)
from orgmetra_keyverse_identity_lifecycle_adapter import evidence as evidence_module


def ref(namespace: str) -> str:
    """Return one canonical UUIDv4 namespaced test reference."""
    return f"{namespace}:{uuid4()}"


def digest(character: str) -> str:
    """Return a deterministic lowercase SHA-256-shaped fixture."""
    return character * 64


def values() -> dict[str, object]:
    """Return one complete valid deprovision handoff fixture."""
    return {
        "tenant_record_id": uuid4(),
        "handoff_reference": ref("keyverse_deprovision"),
        "person_reference": ref("person_record"),
        "employment_reference": ref("employment_record"),
        "identity_binding_reference": ref("identity_binding"),
        "identity_binding_digest": digest("a"),
        "employment_evidence_digest": digest("b"),
        "requester_actor_reference": ref("actor"),
        "keyverse_revision": REVIEWED_KEYVERSE_REVISION,
        "evidence_version": 1,
        "recorded_at": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
    }


def test_emits_value_minimized_non_executing_deprovision_evidence() -> None:
    """Bind exact scope and provenance without HR values or execution authority."""
    handoff = KeyverseIdentityDeprovisionReviewPacket(**values())
    document = handoff.canonical_document()
    assert document["requested_action"] == "deactivate_identity"
    assert document["purpose_code"] == "employment_identity_deprovisioning"
    assert document["keyverse_operation"] == REVIEWED_KEYVERSE_OPERATION
    assert document["scope_state"] == "requires_authoritative_employment_and_identity_resolution"
    assert document["execution_state"] == "not_sent_to_keyverse"
    assert document["authority_state"] == "not_authorized_to_modify_identity"
    assert document["review_state"] == "requires_human_review"
    assert "user_id" not in document
    assert "email" not in document
    assert "userName" not in document
    assert handoff.evidence_digest() == handoff.evidence_digest()
    assert repr(handoff) == "KeyverseIdentityDeprovisionReviewPacket(<redacted>)"


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("handoff_reference", "person_record:" + str(uuid4())),
        ("person_reference", "person_record:00000000-0000-0000-0000-000000000000"),
        ("employment_reference", object()),
        ("identity_binding_reference", "identity_binding:not-a-uuid"),
        ("requester_actor_reference", "actor:" + str(UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"))),
    ],
)
def test_rejects_invalid_owned_references(field: str, bad_value: object) -> None:
    """Reject wrong namespace, sentinel, runtime type, malformed and non-v4 references."""
    payload = values()
    payload[field] = bad_value
    with pytest.raises(ValueError):
        KeyverseIdentityDeprovisionReviewPacket(**payload)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("identity_binding_digest", "A" * 64),
        ("employment_evidence_digest", "a" * 63),
    ],
)
def test_rejects_invalid_digests(field: str, bad_value: object) -> None:
    """Require exact lowercase SHA-256 evidence digests."""
    payload = values()
    payload[field] = bad_value
    with pytest.raises(ValueError):
        KeyverseIdentityDeprovisionReviewPacket(**payload)


@pytest.mark.parametrize("revision", ["z" * 40, "a" * 39, "0" * 40])
def test_requires_exact_reviewed_keyverse_revision(revision: str) -> None:
    """Reject malformed or merely well-shaped but unreviewed Keyverse revisions."""
    payload = values()
    payload["keyverse_revision"] = revision
    with pytest.raises(ValueError):
        KeyverseIdentityDeprovisionReviewPacket(**payload)


@pytest.mark.parametrize("version", [True, 0, 1_000_001])
def test_rejects_invalid_evidence_versions(version: object) -> None:
    """Require a bounded exact integer evidence version."""
    payload = values()
    payload["evidence_version"] = version
    with pytest.raises(ValueError):
        KeyverseIdentityDeprovisionReviewPacket(**payload)


def test_requires_exact_utc_recorded_time() -> None:
    """Reject naive and non-canonical UTC runtime evidence."""
    for value in (
        datetime(2026, 1, 1, 12, 0),
        datetime(2026, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC")),
    ):
        payload = values()
        payload["recorded_at"] = value
        with pytest.raises(ValueError):
            KeyverseIdentityDeprovisionReviewPacket(**payload)


def test_rejects_future_system_recorded_time() -> None:
    """Do not seal system-recorded evidence whose issuance time has not occurred yet."""
    payload = values()
    payload["recorded_at"] = datetime.now(timezone.utc) + timedelta(minutes=5)
    with pytest.raises(ValueError, match="must not be in the future"):
        KeyverseIdentityDeprovisionReviewPacket(**payload)


def test_export_does_not_reenter_issuance_time_freshness(monkeypatch: pytest.MonkeyPatch) -> None:
    """Already sealed evidence must not depend on later wall-clock freshness checks."""
    handoff = KeyverseIdentityDeprovisionReviewPacket(**values())

    def reject_read_time_freshness(field_name: str, value: object) -> None:
        """Represent a wall-clock-dependent issuance validator that must not run on export."""
        raise AssertionError(f"read path re-entered issuance validation for {field_name}: {value!r}")

    monkeypatch.setattr(evidence_module, "_validate_timestamp", reject_read_time_freshness)
    assert handoff.canonical_document()["recorded_at"] == "2026-01-01T12:00:00Z"


def test_rejects_non_uuid_or_reserved_tenant_identity() -> None:
    """Fail closed on non-UUID and reserved tenant identity values."""
    for bad_value in (str(uuid4()), UUID(int=0), UUID(int=(1 << 128) - 1)):
        payload = values()
        payload["tenant_record_id"] = bad_value
        with pytest.raises(ValueError):
            KeyverseIdentityDeprovisionReviewPacket(**payload)


def test_runtime_is_final() -> None:
    """Reject validation-bypassing subclasses of the governed evidence type."""
    with pytest.raises(TypeError, match="is final"):
        type("DerivedHandoff", (KeyverseIdentityDeprovisionReviewPacket,), {})


def test_post_construction_mutation_fails_closed() -> None:
    """Do not let a holder rewrite valid evidence after the review boundary."""
    handoff = KeyverseIdentityDeprovisionReviewPacket(**values())
    object.__setattr__(handoff, "employment_evidence_digest", digest("c"))
    with pytest.raises(ValueError, match="changed after construction"):
        handoff.canonical_json()


def test_dataclass_replace_creates_only_a_new_non_authorizing_packet() -> None:
    """A changed copy remains non-authorizing and has distinct evidence bytes."""
    handoff = KeyverseIdentityDeprovisionReviewPacket(**values())
    replaced = replace(handoff, employment_evidence_digest=digest("c"))
    assert replaced.evidence_digest() != handoff.evidence_digest()
    assert replaced.canonical_document()["authority_state"] == "not_authorized_to_modify_identity"


def test_missing_process_local_seal_fails_closed() -> None:
    """Canonical export requires the process-local integrity seal for this exact object."""
    handoff = KeyverseIdentityDeprovisionReviewPacket(**values())
    with evidence_module._SEAL_LOCK:
        evidence_module._SEALS.pop(id(handoff))
    with pytest.raises(ValueError, match="changed after construction"):
        handoff.canonical_document()
