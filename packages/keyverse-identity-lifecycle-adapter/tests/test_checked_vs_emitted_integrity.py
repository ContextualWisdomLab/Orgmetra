"""Regression tests that bind exported Keyverse evidence to the verified snapshot."""

from datetime import datetime, timezone
import json
from uuid import uuid4

import pytest

from orgmetra_keyverse_identity_lifecycle_adapter import (
    KeyverseIdentityDeprovisionReviewPacket,
    REVIEWED_KEYVERSE_REVISION,
)
from orgmetra_keyverse_identity_lifecycle_adapter import evidence as evidence_module


def _ref(namespace: str) -> str:
    """Return one canonical UUIDv4 namespaced test reference."""
    return f"{namespace}:{uuid4()}"


def _digest(character: str) -> str:
    """Return a deterministic lowercase SHA-256-shaped fixture."""
    return character * 64


def _values() -> dict[str, object]:
    """Return one complete valid deprovision handoff fixture."""
    return {
        "tenant_record_id": uuid4(),
        "handoff_reference": _ref("keyverse_deprovision"),
        "person_reference": _ref("person_record"),
        "employment_reference": _ref("employment_record"),
        "identity_binding_reference": _ref("identity_binding"),
        "identity_binding_digest": _digest("a"),
        "employment_evidence_digest": _digest("b"),
        "requester_actor_reference": _ref("actor"),
        "keyverse_revision": REVIEWED_KEYVERSE_REVISION,
        "evidence_version": 1,
        "recorded_at": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
    }


def _install_interleaved_mutation(
    monkeypatch: pytest.MonkeyPatch,
    handoff: KeyverseIdentityDeprovisionReviewPacket,
    changed_digest: str,
) -> None:
    """Mutate the packet immediately after the first canonical payload snapshot."""
    original_payload = evidence_module._payload
    call_count = 0

    def mutate_after_snapshot(
        envelope: KeyverseIdentityDeprovisionReviewPacket,
    ) -> dict[str, object]:
        """Return the first snapshot, then rewrite one trust-bearing live field."""
        nonlocal call_count
        payload = original_payload(envelope)
        call_count += 1
        if call_count == 1:
            object.__setattr__(handoff, "employment_evidence_digest", changed_digest)
        return payload

    monkeypatch.setattr(evidence_module, "_payload", mutate_after_snapshot)


def test_canonical_document_emits_exact_verified_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not re-read mutated fields after canonical document integrity verification."""
    handoff = KeyverseIdentityDeprovisionReviewPacket(**_values())
    original_digest = handoff.employment_evidence_digest
    _install_interleaved_mutation(monkeypatch, handoff, _digest("c"))

    document = handoff.canonical_document()

    assert document["employment_evidence_digest"] == original_digest
    with pytest.raises(ValueError, match="changed after construction"):
        handoff.canonical_document()


def test_canonical_json_emits_exact_verified_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not re-read mutated fields after canonical JSON integrity verification."""
    handoff = KeyverseIdentityDeprovisionReviewPacket(**_values())
    original_digest = handoff.employment_evidence_digest
    _install_interleaved_mutation(monkeypatch, handoff, _digest("c"))

    document = json.loads(handoff.canonical_json())

    assert document["employment_evidence_digest"] == original_digest
    with pytest.raises(ValueError, match="changed after construction"):
        handoff.canonical_json()
