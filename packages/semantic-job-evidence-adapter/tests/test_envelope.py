from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID, uuid4

import pytest

from orgmetra_semantic_job_evidence_adapter import SemanticJobEvidenceEnvelope


def _reference(namespace: str) -> str:
    """Return one canonical opaque UUIDv4 reference for tests."""
    return f"{namespace}:{uuid4()}"


def values() -> dict[str, object]:
    """Return one valid reviewed ontology-evidence envelope payload."""
    return {
        "tenant_record_id": str(uuid4()),
        "job_analysis_reference": _reference("job_analysis"),
        "ontology_request_reference": _reference("ontology_request"),
        "requesting_actor_reference": "actor:job-analyst",
        "reviewing_actor_reference": "actor:job-analysis-reviewer",
        "resolution_use_code": "job_analysis_source_evidence",
        "query_term_digest": "a" * 64,
        "response_evidence_digest": "b" * 64,
        "source_catalog_digest": "c" * 64,
        "semantic_data_portal_revision": "e48aa13c4af7a4875d4b53e6a60b50405c265a2f",
        "api_operation": "POST /ontology/resolve",
        "evidence_version": 1,
        "recorded_at": datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
    }


def test_builds_value_minimized_non_authorizing_evidence() -> None:
    """The canonical document binds provenance without carrying raw ontology or HR values."""
    packet = SemanticJobEvidenceEnvelope(**values())

    document = packet.canonical_document()

    assert document["source_system"] == "semantic-data-portal"
    assert document["source_trust_state"] == "external_source_evidence"
    assert document["review_state"] == "requires_human_review"
    assert document["decision_authority_state"] == "not_authorized_for_job_or_employment_decision"
    assert document["recorded_at"] == "2026-08-22T12:00:00Z"
    serialized = packet.canonical_json()
    assert packet.evidence_digest() == sha256(serialized.encode("utf-8")).hexdigest()
    for forbidden in (
        "raw_query",
        "query_text",
        "raw_response",
        "person",
        "candidate",
        "worker",
        "credential",
        "score",
        "employment_decision",
    ):
        assert forbidden not in serialized.lower()


def test_requires_distinct_requester_and_human_reviewer() -> None:
    """The same actor cannot request and review imported ontology evidence."""
    candidate = values()
    candidate["reviewing_actor_reference"] = candidate["requesting_actor_reference"]
    with pytest.raises(ValueError, match="must differ"):
        SemanticJobEvidenceEnvelope(**candidate)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("tenant_record_id", str(UUID(int=0))),
        ("tenant_record_id", str(UUID(int=(1 << 128) - 1))),
        ("tenant_record_id", "not-a-uuid"),
        ("job_analysis_reference", "job_analysis:not-a-uuid"),
        ("job_analysis_reference", f"job_analysis:{UUID(int=0)}"),
        ("job_analysis_reference", f"job_analysis:{UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')}"),
        ("ontology_request_reference", "job_analysis:" + str(uuid4())),
        ("requesting_actor_reference", "actor:"),
        ("reviewing_actor_reference", "reviewer:" + str(uuid4())),
        ("query_term_digest", "A" * 64),
        ("response_evidence_digest", "f" * 63),
        ("source_catalog_digest", "x" * 64),
        ("semantic_data_portal_revision", "latest"),
        ("api_operation", "POST /search/semantic"),
        ("resolution_use_code", "automated_job_decision"),
        ("evidence_version", 0),
        ("evidence_version", 1_000_001),
        ("recorded_at", datetime(2026, 8, 22, 12, 0)),
    ],
)
def test_rejects_malformed_or_unreviewed_evidence(field_name: str, bad_value: object) -> None:
    """Malformed, unreviewed, or authority-expanding evidence fails closed."""
    candidate = values()
    candidate[field_name] = bad_value
    with pytest.raises(ValueError):
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


def test_rejects_runtime_subclasses_before_governance_comparison() -> None:
    """Caller-defined primitives cannot forge reviewed state or canonical evidence."""
    for field_name, bad_value in (
        ("resolution_use_code", ForgedText("automated_job_decision")),
        ("api_operation", ForgedText("POST /search/semantic")),
        ("evidence_version", ForgedInt(1)),
        ("recorded_at", ForgedDateTime(2026, 8, 22, tzinfo=timezone.utc)),
    ):
        candidate = values()
        candidate[field_name] = bad_value
        with pytest.raises(ValueError):
            SemanticJobEvidenceEnvelope(**candidate)


def test_rejects_post_construction_rewrite() -> None:
    """Valid-looking field replacement cannot rewrite already-issued evidence."""
    packet = SemanticJobEvidenceEnvelope(**values())
    object.__setattr__(packet, "response_evidence_digest", "d" * 64)
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()


def test_rejects_packet_seal_rewrite() -> None:
    """Rewriting the packet-owned seal cannot bypass the authoritative creation seal."""
    packet = SemanticJobEvidenceEnvelope(**values())
    object.__setattr__(packet, "_creation_seal", "0" * 64)
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_document()


def test_rejects_replacement_and_seal_reset() -> None:
    """Dataclass replacement cannot turn modified evidence into a newly issued envelope."""
    from dataclasses import replace

    packet = SemanticJobEvidenceEnvelope(**values())
    with pytest.raises(ValueError, match="changed after construction"):
        replace(packet, response_evidence_digest="d" * 64, _creation_seal=None)


def test_rejects_caller_supplied_creation_seal() -> None:
    """Callers cannot seed a pre-authorized creation seal during construction."""
    candidate = values()
    candidate["_creation_seal"] = "0" * 64
    with pytest.raises(ValueError, match="changed after construction"):
        SemanticJobEvidenceEnvelope(**candidate)


def test_rejects_post_issuance_marker_rewrite() -> None:
    """Changing the one-way issuance marker invalidates emitted evidence."""
    packet = SemanticJobEvidenceEnvelope(**values())
    object.__setattr__(packet, "_issuance_marker", object())
    with pytest.raises(ValueError, match="changed after construction"):
        packet.canonical_json()


def test_runtime_type_is_final_and_repr_is_redacted() -> None:
    """The evidence type cannot be extended and its repr omits sensitive correlations."""
    packet = SemanticJobEvidenceEnvelope(**values())
    with pytest.raises(TypeError, match="final"):
        type("DerivedEnvelope", (SemanticJobEvidenceEnvelope,), {})
    assert repr(packet) == "SemanticJobEvidenceEnvelope(<redacted>)"
