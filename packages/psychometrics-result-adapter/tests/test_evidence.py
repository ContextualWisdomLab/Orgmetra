"""Executable contract for value-minimized Psychometrics Commons result evidence."""

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from orgmetra_psychometrics_result_adapter import PsychometricsResultEvidenceEnvelope


OWNER_REVISION = "3bb873f02d2e1639be49e2bc9ac998c158b48d3d"
HEX_A = "a" * 64
HEX_B = "b" * 64


def _ref(namespace: str) -> str:
    return f"{namespace}:{uuid4()}"


def valid_envelope(**overrides: object) -> PsychometricsResultEvidenceEnvelope:
    values: dict[str, object] = {
        "tenant_record_id": str(uuid4()),
        "result_evidence_reference": _ref("psych_result_evidence"),
        "candidate_evidence_intake_reference": _ref("candidate_evidence_intake"),
        "candidate_evidence_intake_digest": HEX_B,
        "requesting_actor_reference": _ref("actor"),
        "reviewing_actor_reference": _ref("actor"),
        "result_snapshot_reference": "result_snapshot_alpha",
        "participant_binding_digest": HEX_A,
        "response_snapshot_reference": "response_snapshot_alpha",
        "assessment_spec_reference": "assessment_spec_alpha",
        "instrument_version_reference": "instrument_version_alpha",
        "scoring_version_reference": "scoring_version_alpha",
        "calibration_reference": "calibration_alpha",
        "norm_version_reference": "norm_version_alpha",
        "narrative_version_reference": "narrative_version_alpha",
        "consent_snapshot_set_digest": HEX_B,
        "engine_artifact_digest": f"sha256:{HEX_A}",
        "result_snapshot_digest": HEX_B,
        "requested_output_schema_version": 1,
        "result_created_at_unix_ms": 1_787_000_000_000,
        "supersedes_result_snapshot_reference": None,
        "psychometrics_commons_revision": OWNER_REVISION,
        "evidence_version": 1,
        "recorded_at": datetime(2026, 8, 23, 3, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return PsychometricsResultEvidenceEnvelope(**values)


def test_canonical_evidence_is_value_minimized_and_non_authorizing() -> None:
    envelope = valid_envelope()
    document = envelope.canonical_document()

    assert document["source_system"] == "psychometrics-commons"
    assert document["source_trust_state"] == "external_measurement_evidence"
    assert document["review_state"] == "requires_human_review"
    assert document["decision_authority_state"] == "not_authorized_for_employment_decision"
    assert document["score_handling_state"] == "score_values_not_stored"
    assert document["psychometrics_commons_revision"] == OWNER_REVISION
    assert document["requested_output_schema_version"] == 1
    assert document["candidate_evidence_intake_reference"].startswith("candidate_evidence_intake:")
    assert document["candidate_evidence_intake_digest"] == HEX_B
    assert "participant_ref" not in document
    assert "score_observations" not in document
    assert "consent_snapshot_refs" not in document
    assert "candidate name" not in envelope.canonical_json().lower()
    assert len(envelope.evidence_digest()) == 64
    assert repr(envelope) == "PsychometricsResultEvidenceEnvelope(<redacted>)"


def test_optional_norm_and_supersession_are_bound_without_raw_values() -> None:
    superseded = "result_snapshot_prior"
    envelope = valid_envelope(
        norm_version_reference=None,
        supersedes_result_snapshot_reference=superseded,
    )
    document = envelope.canonical_document()
    assert document["norm_version_reference"] is None
    assert document["supersedes_result_snapshot_reference"] == superseded


def test_requires_distinct_human_reviewer() -> None:
    actor = _ref("actor")
    with pytest.raises(ValueError, match="reviewing_actor_reference must differ"):
        valid_envelope(requesting_actor_reference=actor, reviewing_actor_reference=actor)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("tenant_record_id", "not-a-uuid"),
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("tenant_record_id", "ffffffff-ffff-ffff-ffff-ffffffffffff"),
        ("result_evidence_reference", f"wrong_namespace:{uuid4()}"),
        ("result_evidence_reference", "psych_result_evidence:not-a-uuid"),
        ("candidate_evidence_intake_reference", f"candidate_evidence_intake:{uuid4().hex}"),
        ("candidate_evidence_intake_digest", "A" * 64),
        ("requesting_actor_reference", "actor:alice_smith"),
        ("reviewing_actor_reference", "actor:employee-123"),
        ("participant_binding_digest", "A" * 64),
        ("consent_snapshot_set_digest", "b" * 63),
        ("result_snapshot_digest", "g" * 64),
        ("engine_artifact_digest", "sha256:" + "A" * 64),
        ("requested_output_schema_version", 2),
        ("result_created_at_unix_ms", 0),
        ("psychometrics_commons_revision", "0" * 40),
        ("evidence_version", 0),
        ("recorded_at", datetime(2026, 8, 23, 3, 0)),
    ],
)
def test_rejects_invalid_owned_scope_and_provenance(field_name: str, bad_value: object) -> None:
    with pytest.raises(ValueError):
        valid_envelope(**{field_name: bad_value})


@pytest.mark.parametrize(
    "field_name",
    [
        "result_snapshot_reference",
        "response_snapshot_reference",
        "assessment_spec_reference",
        "instrument_version_reference",
        "scoring_version_reference",
        "calibration_reference",
        "narrative_version_reference",
    ],
)
def test_foreign_references_must_arrive_canonical_and_control_free(field_name: str) -> None:
    with pytest.raises(ValueError):
        valid_envelope(**{field_name: "  owner_ref  "})
    with pytest.raises(ValueError):
        valid_envelope(**{field_name: "owner\nref"})


def test_accepts_foreign_reference_normalized_by_the_pinned_owner() -> None:
    owner_normalized_reference = "result\u200dsnapshot"
    envelope = valid_envelope(result_snapshot_reference=owner_normalized_reference)
    assert envelope.canonical_document()["result_snapshot_reference"] == owner_normalized_reference


def test_optional_foreign_references_are_validated_when_present() -> None:
    with pytest.raises(ValueError):
        valid_envelope(norm_version_reference=" ")
    with pytest.raises(ValueError):
        valid_envelope(supersedes_result_snapshot_reference="bad\tref")


def test_rejects_self_supersession_and_future_source_result() -> None:
    envelope = valid_envelope()
    with pytest.raises(ValueError, match="cannot supersede itself"):
        valid_envelope(supersedes_result_snapshot_reference=envelope.result_snapshot_reference)
    with pytest.raises(ValueError, match="cannot precede"):
        valid_envelope(result_created_at_unix_ms=2_000_000_000_000)


def test_exact_runtime_primitives_are_required() -> None:
    class ForgedText(str):
        pass

    class ForgedInt(int):
        pass

    with pytest.raises(ValueError):
        valid_envelope(result_snapshot_reference=ForgedText("result_snapshot_alpha"))
    with pytest.raises(ValueError):
        valid_envelope(evidence_version=ForgedInt(1))


def test_packet_is_runtime_final() -> None:
    with pytest.raises(TypeError, match="final"):
        type("DerivedEnvelope", (PsychometricsResultEvidenceEnvelope,), {})


def test_replace_cannot_reissue_changed_evidence() -> None:
    envelope = valid_envelope()
    with pytest.raises(ValueError, match="changed after construction"):
        replace(envelope, result_snapshot_digest="c" * 64)


def test_post_construction_payload_and_packet_seal_rewrite_fails_closed() -> None:
    envelope = valid_envelope()
    object.__setattr__(envelope, "result_snapshot_digest", "c" * 64)
    object.__setattr__(envelope, "_creation_seal", "d" * 64)
    with pytest.raises(ValueError, match="changed after construction"):
        envelope.canonical_json()


def test_creation_metadata_cannot_be_supplied_or_rewritten() -> None:
    with pytest.raises(ValueError, match="changed after construction"):
        valid_envelope(_creation_seal="a" * 64)
    envelope = valid_envelope()
    object.__setattr__(envelope, "_issuance_marker", object())
    with pytest.raises(ValueError, match="changed after construction"):
        envelope.evidence_digest()


def test_canonical_json_emits_the_exact_integrity_checked_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not reread live result evidence after its canonical bytes are verified."""
    envelope = valid_envelope()
    original_payload = PsychometricsResultEvidenceEnvelope._payload
    calls = 0
    forged_digest = "c" * 64

    def payload_with_interleaving(
        self: PsychometricsResultEvidenceEnvelope,
    ) -> dict[str, object]:
        """Return forged evidence only if export performs an unsafe second payload read."""
        nonlocal calls
        calls += 1
        payload = original_payload(self)
        if calls == 2:
            payload["result_snapshot_digest"] = forged_digest
        return payload

    monkeypatch.setattr(PsychometricsResultEvidenceEnvelope, "_payload", payload_with_interleaving)
    canonical = envelope.canonical_json()
    assert calls == 1
    assert f'"result_snapshot_digest":"{HEX_B}"' in canonical
    assert forged_digest not in canonical


def test_canonical_document_returns_the_exact_integrity_checked_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the verified result document instead of rebuilding it from live fields."""
    envelope = valid_envelope()
    original_payload = PsychometricsResultEvidenceEnvelope._payload
    calls = 0
    forged_digest = "c" * 64

    def payload_with_interleaving(
        self: PsychometricsResultEvidenceEnvelope,
    ) -> dict[str, object]:
        """Return forged evidence only if document export performs a second payload read."""
        nonlocal calls
        calls += 1
        payload = original_payload(self)
        if calls == 2:
            payload["result_snapshot_digest"] = forged_digest
        return payload

    monkeypatch.setattr(PsychometricsResultEvidenceEnvelope, "_payload", payload_with_interleaving)
    document = envelope.canonical_document()
    assert calls == 1
    assert document["result_snapshot_digest"] == HEX_B
