"""Executable contract for value-minimized Contextual Orchestrator draft evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from orgmetra_contextual_orchestrator_adapter import DraftEvidenceEnvelope


TENANT = "01890f62-3e1a-4db1-8b42-bf7537b88e10"
REQUEST = "orchestration_request:9d0c8c0f-c217-4cb5-a91d-36e8d5091190"
TARGET = "job_analysis:597f2467-d2f0-4cc3-9854-79c60854a25e"
REQUESTER = "actor:hr-analyst-01"
REVIEWER = "actor:job-analysis-sme-02"
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
        "recorded_at": datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
    }


def build() -> DraftEvidenceEnvelope:
    """Build one valid envelope through the public constructor."""
    return DraftEvidenceEnvelope(**values())


def test_builds_value_minimized_untrusted_human_review_evidence() -> None:
    """Bind provenance without turning model output into an employment decision."""
    envelope = build()
    document = envelope.canonical_document()
    assert document["output_trust_state"] == "untrusted_draft"
    assert document["review_state"] == "requires_human_review"
    assert document["decision_authority_state"] == "not_authorized_for_employment_decision"
    assert document["contextual_orchestrator_revision"] == REVISION
    assert document["api_contract_id"] == "contextual-orchestrator.openapi.v0.1.0"
    assert document["api_operation"] == "POST /v1/responses"
    assert "prompt" not in document
    assert "output" not in document
    assert "candidate_name" not in document
    assert len(envelope.evidence_digest()) == 64
    assert repr(envelope) == "DraftEvidenceEnvelope(<redacted>)"


def test_canonical_json_is_deterministic() -> None:
    """Render identical reviewed evidence to identical canonical bytes."""
    assert build().canonical_json() == build().canonical_json()
    assert build().evidence_digest() == build().evidence_digest()


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
        ("recorded_at", datetime(2026, 8, 22, 12, 0), "recorded_at"),
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


def test_rejects_non_utc_and_datetime_subclass() -> None:
    """Keep recorded evidence on one exact non-executable UTC representation."""
    class ForgedDateTime(datetime):
        """Represent a caller-defined datetime implementation."""

    kwargs = values()
    kwargs["recorded_at"] = ForgedDateTime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="recorded_at"):
        DraftEvidenceEnvelope(**kwargs)


def test_runtime_type_is_final() -> None:
    """Disallow subclasses that could override derived governance state."""
    with pytest.raises(TypeError, match="final"):
        type("ForgedEnvelope", (DraftEvidenceEnvelope,), {})


def test_post_construction_rewrite_fails_closed() -> None:
    """Prevent object-level rewriting from minting a new reviewed evidence document."""
    envelope = build()
    object.__setattr__(envelope, "response_evidence_digest", "d" * 64)
    with pytest.raises(ValueError, match="changed after construction"):
        envelope.canonical_json()


def test_seal_rewrite_fails_closed() -> None:
    """Reject removal of the process-local creation seal before evidence serialization."""
    envelope = build()
    object.__setattr__(envelope, "_creation_seal", None)
    with pytest.raises(ValueError, match="changed after construction"):
        envelope.canonical_json()


def test_replacement_cannot_bypass_creation_evidence() -> None:
    """Reject dataclass replacement because it is a new issuance boundary."""
    envelope = build()
    with pytest.raises(ValueError, match="changed after construction"):
        replace(envelope, response_evidence_digest="d" * 64).canonical_json()
