"""Executable contract for value-minimized Contextual Orchestrator draft evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from orgmetra_contextual_orchestrator_adapter import DraftEvidenceEnvelope


TENANT = "01890f62-3e1a-4db1-8b42-bf7537b88e10"
REQUEST = "orchestration_request:9d0c8c0f-c217-4cb5-a91d-36e8d5091190"
TARGET = "job_analysis:597f2467-d2f0-4cc3-9854-79c60854a25e"
REQUESTER = "actor:7efdf9f8-c4b3-42d2-b22c-50b2f6e5950b"
REVIEWER = "actor:8b6ef498-9589-4099-953b-bd7a9322c97d"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
REVISION = "e226e1197bdfc890c9d8e5b9b648c78857d7e465"


def values() -> dict[str, object]:
    """Return one valid, PII-free draft-evidence envelope input."""
    return {
        "tenant_record_id": TENANT,
        "orchestration_request_reference": REQUEST,
        "evidence_target_reference": TARGET,
        "requesting_actor_reference": REQUESTER,
        "reviewing_actor_reference": REVIEWER,
        "draft_use_code": "job_analysis_draft",
        "requested_model": "contextual-auto",
        "input_evidence_digest": DIGEST_A,
        "response_evidence_digest": DIGEST_B,
        "provenance_evidence_digest": DIGEST_C,
        "contextual_orchestrator_revision": REVISION,
        "api_operation": "POST /v1/responses",
        "evidence_version": 1,
    }


def build() -> DraftEvidenceEnvelope:
    """Build one valid, PII-free envelope through the public issuance constructor."""
    return DraftEvidenceEnvelope(**values())


def test_builds_value_minimized_untrusted_human_review_evidence() -> None:
    """Bind provenance without turning model output into an employment decision."""
    before = datetime.now(timezone.utc)
    envelope = build()
    after = datetime.now(timezone.utc)
    document = envelope.canonical_document()
    assert document["output_trust_state"] == "untrusted_draft"
    assert document["review_state"] == "requires_human_review"
    assert document["decision_authority_state"] == "not_authorized_for_employment_decision"
    assert document["contextual_orchestrator_revision"] == REVISION
    assert document["api_contract_id"] == "contextual-orchestrator.openapi.v0.1.0"
    assert document["api_operation"] == "POST /v1/responses"
    assert document["draft_evidence_reference"].startswith("draft_evidence:")
    assert before <= envelope.recorded_at <= after
    assert envelope.recorded_at.tzinfo is timezone.utc
    assert "prompt" not in document
    assert "output" not in document
    assert "candidate_name" not in document
    assert len(envelope.evidence_digest()) == 64
    assert repr(envelope) == "DraftEvidenceEnvelope(<redacted>)"


def test_canonical_json_is_deterministic_for_one_issuance() -> None:
    """Render one reviewed issuance to identical canonical bytes on repeated reads."""
    envelope = build()
    assert envelope.canonical_json() == envelope.canonical_json()
    assert envelope.evidence_digest() == envelope.evidence_digest()


@pytest.mark.parametrize(
    ("field_name", "bad_value", "message"),
    [
        ("tenant_record_id", "not-a-uuid", "tenant_record_id"),
        ("orchestration_request_reference", "request:not-a-uuid", "orchestration_request_reference"),
        ("evidence_target_reference", "salary:597f2467-d2f0-4cc3-9854-79c60854a25e", "evidence_target_reference"),
        ("requesting_actor_reference", "actor:", "requesting_actor_reference"),
        ("reviewing_actor_reference", "employee:abc", "reviewing_actor_reference"),
        ("draft_use_code", "hire_candidate", "draft_use_code"),
        ("requested_model", "model with spaces", "requested_model"),
        ("requested_model", "", "requested_model"),
        ("input_evidence_digest", "A" * 64, "input_evidence_digest"),
        ("response_evidence_digest", "b" * 63, "response_evidence_digest"),
        ("provenance_evidence_digest", "g" * 64, "provenance_evidence_digest"),
        ("contextual_orchestrator_revision", "0" * 40, "contextual_orchestrator_revision"),
        ("api_operation", "POST /v1/chat/completions", "api_operation"),
        ("evidence_version", 0, "evidence_version"),
    ],
)
def test_rejects_invalid_governance_evidence(field_name: str, bad_value: object, message: str) -> None:
    """Fail closed before invalid governance or provenance can be serialized."""
    kwargs = values()
    kwargs[field_name] = bad_value
    with pytest.raises(ValueError, match=message):
        DraftEvidenceEnvelope(**kwargs)


def test_rejects_noncanonical_and_sentinel_tenants() -> None:
    """Reject correlating noncanonical or reserved tenant UUID representations."""
    for bad_tenant in (TENANT.upper(), "00000000-0000-0000-0000-000000000000"):
        kwargs = values()
        kwargs["tenant_record_id"] = bad_tenant
        with pytest.raises(ValueError, match="tenant_record_id"):
            DraftEvidenceEnvelope(**kwargs)


def test_rejects_malformed_noncanonical_and_non_v4_request_references() -> None:
    """Exercise every bounded UUIDv4 reference failure boundary."""
    bad_references = (
        "x" * 181,
        "orchestration_request",
        "orchestration_request:not-a-uuid",
        "orchestration_request:9D0C8C0F-C217-4CB5-A91D-36E8D5091190",
        "orchestration_request:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    )
    for bad_reference in bad_references:
        kwargs = values()
        kwargs["orchestration_request_reference"] = bad_reference
        with pytest.raises(ValueError, match="orchestration_request_reference"):
            DraftEvidenceEnvelope(**kwargs)


def test_requires_requester_reviewer_separation() -> None:
    """Prevent the requesting actor from self-confirming a model-assisted draft."""
    kwargs = values()
    kwargs["reviewing_actor_reference"] = REQUESTER
    with pytest.raises(ValueError, match="reviewing_actor_reference"):
        DraftEvidenceEnvelope(**kwargs)


class ForgedText(str):
    """Represent caller-controlled string behavior that must not cross the boundary."""

    def __eq__(self, other: object) -> bool:
        """Pretend to equal every reviewed value."""
        return True

    def __hash__(self) -> int:
        """Pretend to hash like a safe constant."""
        return hash("job_analysis_draft")


class ForgedInt(int):
    """Represent caller-controlled numeric comparison behavior."""

    def __ge__(self, other: object) -> bool:
        """Pretend to satisfy every lower bound."""
        return True

    def __le__(self, other: object) -> bool:
        """Pretend to satisfy every upper bound."""
        return True

    def __lt__(self, other: object) -> bool:
        """Pretend every strict upper-bound comparison succeeds."""
        return True

    def __gt__(self, other: object) -> bool:
        """Pretend every strict lower-bound comparison succeeds."""
        return True


def test_rejects_runtime_subclasses_before_reviewed_operations() -> None:
    """Reject hostile string and integer subclasses before equality or bounds checks."""
    kwargs = values()
    kwargs["draft_use_code"] = ForgedText("hire_candidate")
    with pytest.raises(ValueError, match="draft_use_code"):
        DraftEvidenceEnvelope(**kwargs)
    kwargs = values()
    kwargs["evidence_version"] = ForgedInt(0)
    with pytest.raises(ValueError, match="evidence_version"):
        DraftEvidenceEnvelope(**kwargs)


def test_runtime_type_is_final() -> None:
    """Disallow subclasses that could override derived governance state."""
    with pytest.raises(TypeError, match="final"):
        type("ForgedEnvelope", (DraftEvidenceEnvelope,), {})


def test_post_construction_rewrite_fails_closed() -> None:
    """Detect object-level rewriting before one issuance document can be exported again."""
    envelope = build()
    object.__setattr__(envelope, "response_evidence_digest", "d" * 64)
    with pytest.raises(ValueError, match="changed after construction"):
        envelope.canonical_json()


def test_system_recorded_time_rewrite_fails_closed() -> None:
    """Detect any attempt to rewrite the trusted system-recorded issuance instant."""
    envelope = build()
    object.__setattr__(envelope, "recorded_at", datetime(2025, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="changed after construction"):
        envelope.canonical_json()


def test_generated_evidence_reference_rewrite_fails_closed() -> None:
    """Detect rewriting of the system-generated issuance correlation reference."""
    envelope = build()
    object.__setattr__(
        envelope,
        "draft_evidence_reference",
        "draft_evidence:d4154329-c78f-4f35-9b04-bc6d7928ff52",
    )
    with pytest.raises(ValueError, match="changed after construction"):
        envelope.canonical_json()


def test_seal_rewrite_fails_closed() -> None:
    """Detect removal of the process-local accidental-change snapshot before export."""
    envelope = build()
    object.__setattr__(envelope, "_creation_seal", None)
    with pytest.raises(ValueError, match="changed after construction"):
        envelope.canonical_json()


def test_direct_constructor_rejects_caller_supplied_creation_state() -> None:
    """Keep system-recorded time and internal change-detection state outside constructor input."""
    with pytest.raises(TypeError):
        DraftEvidenceEnvelope(**values(), recorded_at=datetime.now(timezone.utc))
    with pytest.raises(TypeError):
        DraftEvidenceEnvelope(**values(), _creation_seal="forged")


def test_replacement_is_a_distinct_system_recorded_issuance() -> None:
    """Treat dataclass replacement as new evidence with new correlation and recorded time."""
    envelope = build()
    replacement = replace(envelope, response_evidence_digest="d" * 64)
    assert replacement.draft_evidence_reference != envelope.draft_evidence_reference
    assert replacement.recorded_at >= envelope.recorded_at
    assert replacement.evidence_digest() != envelope.evidence_digest()


def test_canonical_json_emits_the_exact_snapshot_that_passed_integrity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never reread live fields after the creation seal has validated one canonical snapshot."""
    envelope = build()
    original_payload = DraftEvidenceEnvelope._payload
    calls = 0
    forged_digest = "d" * 64

    def payload_with_interleaving(self: DraftEvidenceEnvelope) -> dict[str, object]:
        """Return forged evidence only if export performs an unsafe second live-field read."""
        nonlocal calls
        calls += 1
        payload = original_payload(self)
        if calls == 2:
            payload["response_evidence_digest"] = forged_digest
        return payload

    monkeypatch.setattr(DraftEvidenceEnvelope, "_payload", payload_with_interleaving)
    canonical = envelope.canonical_json()
    assert calls == 1
    assert f'"response_evidence_digest":"{DIGEST_B}"' in canonical
    assert forged_digest not in canonical


def test_canonical_document_returns_the_verified_snapshot_without_rereading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the verified document snapshot instead of reading mutable fields again after validation."""
    envelope = build()
    original_payload = DraftEvidenceEnvelope._payload
    calls = 0
    forged_digest = "d" * 64

    def payload_with_interleaving(self: DraftEvidenceEnvelope) -> dict[str, object]:
        """Return forged evidence only if document export performs a second live-field read."""
        nonlocal calls
        calls += 1
        payload = original_payload(self)
        if calls == 2:
            payload["response_evidence_digest"] = forged_digest
        return payload

    monkeypatch.setattr(DraftEvidenceEnvelope, "_payload", payload_with_interleaving)
    document = envelope.canonical_document()
    assert calls == 1
    assert document["response_evidence_digest"] == DIGEST_B
