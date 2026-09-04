"""Adversarial contract tests for governed Semantic Data Portal source evidence."""

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid1, uuid4

import pytest

from orgmetra_semantic_job_evidence_adapter import SemanticJobEvidenceEnvelope


def test_canonical_evidence_is_value_minimized_and_deterministic(
    semantic_values: dict[str, object],
) -> None:
    """Canonical evidence contains governance/provenance only and has stable bytes."""
    packet = SemanticJobEvidenceEnvelope(**semantic_values)
    document = packet.canonical_document()

    assert document["source_system"] == "semantic-data-portal"
    assert document["source_trust_state"] == "external_source_evidence"
    assert document["review_state"] == "requires_human_review"
    assert document["decision_authority_state"] == "not_authorized_for_job_or_employment_decision"
    assert document["recorded_at"] == "2026-08-22T14:50:12.123456Z"
    assert "query_term" not in document
    assert "response" not in document
    assert "person" not in document
    expected_json = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert packet.canonical_json() == expected_json
    assert packet.evidence_digest() == sha256(expected_json.encode("utf-8")).hexdigest()
    assert repr(packet) == "SemanticJobEvidenceEnvelope(<redacted>)"


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("tenant_record_id", "not-a-uuid"),
        ("tenant_record_id", str(uuid4()).upper()),
        ("job_analysis_reference", f"job_analysis:{uuid1()}"),
        ("job_analysis_reference", f"person:{uuid4()}"),
        ("job_analysis_reference", "job_analysis:" + "a" * 181),
        ("ontology_request_reference", f"ontology_request:{uuid1()}"),
        ("ontology_request_reference", "ontology_request:not-a-uuid"),
        ("requesting_actor_reference", "staff:analyst"),
        ("requesting_actor_reference", "actor:hr-analyst"),
        ("reviewing_actor_reference", "actor:has space"),
        ("query_term_digest", "A" * 64),
        ("response_evidence_digest", "b" * 63),
        ("source_catalog_digest", "not-a-digest"),
        ("semantic_data_portal_revision", "0" * 40),
        ("api_operation", "POST /search/semantic"),
        ("api_operation", ""),
        ("resolution_use_code", "automated_job_decision"),
        ("evidence_version", 0),
        ("evidence_version", 1_000_001),
        ("evidence_version", True),
        ("recorded_at", datetime(2026, 8, 22, 14, 50, 12)),
    ],
)
def test_rejects_invalid_governance_evidence(
    semantic_values: dict[str, object], field_name: str, bad_value: object
) -> None:
    """Malformed, unsafe, or unreviewed evidence fails closed at construction."""
    candidate = semantic_values.copy()
    candidate[field_name] = bad_value
    with pytest.raises(ValueError):
        SemanticJobEvidenceEnvelope(**candidate)


def test_rejects_same_requester_and_reviewer(semantic_values: dict[str, object]) -> None:
    """One actor cannot self-review ontology evidence for Job Analysis."""
    candidate = semantic_values.copy()
    candidate["reviewing_actor_reference"] = candidate["requesting_actor_reference"]
    with pytest.raises(ValueError, match="must differ"):
        SemanticJobEvidenceEnvelope(**candidate)


class ForgedText(str):
    """Simulate caller text that lies during reviewed equality/hash operations."""

    def __eq__(self, other: object) -> bool:
        """Pretend every comparison is equal."""
        return True

    def __ne__(self, other: object) -> bool:
        """Pretend every comparison is not unequal."""
        return False

    def __hash__(self) -> int:
        """Pretend to hash like an approved use code."""
        return hash("job_analysis_source_evidence")


class ForgedInt(int):
    """Simulate caller numeric evidence that lies during bounds checks."""

    def __le__(self, other: object) -> bool:
        """Forge less-than-or-equal comparisons."""
        return True

    def __ge__(self, other: object) -> bool:
        """Forge greater-than-or-equal comparisons."""
        return True

    def __lt__(self, other: object) -> bool:
        """Forge strict less-than comparisons."""
        return False

    def __gt__(self, other: object) -> bool:
        """Forge strict greater-than comparisons."""
        return False


class ForgedDateTime(datetime):
    """Represent caller-executable temporal behavior at the trust boundary."""


def test_rejects_runtime_subclasses_before_governance_comparison(
    semantic_values: dict[str, object],
) -> None:
    """Caller-defined primitives cannot forge reviewed state or canonical evidence."""
    for field_name, bad_value in (
        ("resolution_use_code", ForgedText("automated_job_decision")),
        ("api_operation", ForgedText("POST /search/semantic")),
        ("evidence_version", ForgedInt(1)),
        ("recorded_at", ForgedDateTime(2026, 8, 22, tzinfo=timezone.utc)),
    ):
        candidate = semantic_values.copy()
        candidate[field_name] = bad_value
        with pytest.raises(ValueError):
            SemanticJobEvidenceEnvelope(**candidate)


def test_rejects_post_construction_rewrite(semantic_values: dict[str, object]) -> None:
    """Valid-looking field replacement cannot rewrite already-issued evidence."""
    packet = SemanticJobEvidenceEnvelope(**semantic_values)
    object.__setattr__(packet, "response_evidence_digest", "d" * 64)
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()


def test_replace_cannot_reseal_changed_evidence(semantic_values: dict[str, object]) -> None:
    """Dataclass replacement cannot reset the issuance seal and create new authority."""
    packet = SemanticJobEvidenceEnvelope(**semantic_values)
    with pytest.raises(ValueError, match="changed after construction"):
        replace(packet, response_evidence_digest="d" * 64, _creation_seal=None)


def test_rejects_caller_supplied_seal_and_marker_rewrite(
    semantic_values: dict[str, object],
) -> None:
    """Private seal and issuance marker fields remain fail-closed under hostile access."""
    candidate = semantic_values.copy()
    candidate["_creation_seal"] = "0" * 64
    with pytest.raises(ValueError, match="changed after construction"):
        SemanticJobEvidenceEnvelope(**candidate)

    packet = SemanticJobEvidenceEnvelope(**semantic_values)
    object.__setattr__(packet, "_issuance_marker", object())
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_document()


def test_rejects_creation_seal_rewrite_even_when_payload_is_unchanged(
    semantic_values: dict[str, object],
) -> None:
    """The authoritative in-process seal cannot be replaced independently."""
    packet = SemanticJobEvidenceEnvelope(**semantic_values)
    object.__setattr__(packet, "_creation_seal", object())
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()


def test_canonical_export_reuses_the_exact_integrity_checked_snapshot(
    semantic_values: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mutation after the checked snapshot cannot leak different canonical evidence."""
    packet = SemanticJobEvidenceEnvelope(**semantic_values)
    expected_json = packet.canonical_json()
    original_payload = SemanticJobEvidenceEnvelope._payload
    mutated = False

    def mutate_after_snapshot(self: SemanticJobEvidenceEnvelope) -> dict[str, object]:
        """Mutate the live packet immediately after returning one payload snapshot."""
        nonlocal mutated
        payload = original_payload(self)
        if not mutated:
            mutated = True
            object.__setattr__(self, "response_evidence_digest", "d" * 64)
        return payload

    monkeypatch.setattr(SemanticJobEvidenceEnvelope, "_payload", mutate_after_snapshot)

    assert packet.canonical_json() == expected_json
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()


def test_runtime_type_is_final() -> None:
    """Subclasses cannot override derived trust state on the governed envelope."""
    with pytest.raises(TypeError, match="final"):
        type("DerivedEnvelope", (SemanticJobEvidenceEnvelope,), {})
