"""Governed, value-minimized Psychometrics Commons result evidence for Orgmetra."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import re
import secrets
from threading import RLock
from typing import ClassVar
import unicodedata
from uuid import UUID
from weakref import finalize


_PSYCHOMETRICS_COMMONS_REVISION = "3bb873f02d2e1639be49e2bc9ac998c158b48d3d"
_PROCESS_SEAL_KEY = secrets.token_bytes(32)
_NEW_ISSUANCE_MARKER = object()
_USED_ISSUANCE_MARKER = object()
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
_CREATION_SEALS: dict[int, str] = {}
_CREATION_SEALS_LOCK = RLock()


def _discard_creation_seal(envelope_id: int) -> None:
    """Discard process-local authoritative evidence when an envelope is collected."""
    with _CREATION_SEALS_LOCK:
        _CREATION_SEALS.pop(envelope_id, None)


def _register_creation_seal(envelope: object, seal: str) -> None:
    """Bind one live envelope identity to creation evidence outside writable slots."""
    envelope_id = id(envelope)
    with _CREATION_SEALS_LOCK:
        _CREATION_SEALS[envelope_id] = seal
    finalize(envelope, _discard_creation_seal, envelope_id)


def _authoritative_creation_seal(envelope: object) -> str | None:
    """Return process-local creation evidence without trusting envelope-owned state."""
    with _CREATION_SEALS_LOCK:
        return _CREATION_SEALS.get(id(envelope))


def _require_text(value: object, field_name: str) -> str:
    """Return exact built-in non-empty text before caller-defined behavior can run."""
    if type(value) is not str or not value:
        raise ValueError(f"{field_name} must be exact non-empty text")
    return value


def _validate_operational_uuid(value: object, field_name: str) -> str:
    """Require one canonical non-sentinel operational UUID string."""
    text = _require_text(value, field_name)
    try:
        parsed = UUID(text)
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError(f"{field_name} must be a canonical operational UUID") from error
    if str(parsed) != text or parsed.int in (0, (1 << 128) - 1):
        raise ValueError(f"{field_name} must be a canonical non-sentinel operational UUID")
    return text


def _validate_owned_reference(value: object, field_name: str, namespace: str) -> str:
    """Require one bounded Orgmetra-owned namespaced UUIDv4 correlation reference."""
    text = _require_text(value, field_name)
    prefix = f"{namespace}:"
    if len(text) > 180 or not text.startswith(prefix):
        raise ValueError(f"{field_name} must be a bounded {namespace}: UUIDv4 reference")
    suffix = text[len(prefix) :]
    try:
        parsed = UUID(suffix)
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError(f"{field_name} must end in a canonical UUIDv4") from error
    if str(parsed) != suffix or parsed.version != 4:
        raise ValueError(f"{field_name} must end in a canonical UUIDv4")
    return text


def _validate_actor_reference(value: object, field_name: str) -> str:
    """Require a pseudonymous Orgmetra-local actor UUIDv4 correlation."""
    return _validate_owned_reference(value, field_name, "actor")


def _is_numeric_like(text: str) -> bool:
    """Mirror the foreign owner's rejection of references made only of numeric syntax."""
    allowed = {"+", "-", ".", ",", "e", "E", "\u066b", "\u066c", "\uff0e", "\uff0c"}
    return any(character.isnumeric() for character in text) and all(
        character.isnumeric() or character in allowed for character in text
    )


def _validate_foreign_reference(value: object, field_name: str) -> str:
    """Require an already-normalized bounded opaque Psychometrics Commons reference."""
    text = _require_text(value, field_name)
    if (
        len(text) > 256
        or text != text.strip()
        or any(unicodedata.category(character) == "Cc" for character in text)
        or _is_numeric_like(text)
    ):
        raise ValueError(f"{field_name} must be a canonical bounded foreign opaque reference")
    return text


def _validate_optional_foreign_reference(value: object, field_name: str) -> str | None:
    """Validate a nullable foreign reference without inventing an owner identifier format."""
    if value is None:
        return None
    return _validate_foreign_reference(value, field_name)


def _validate_digest(value: object, field_name: str) -> str:
    """Require one lowercase SHA-256 evidence digest without an algorithm prefix."""
    text = _require_text(value, field_name)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _validate_engine_digest(value: object) -> str:
    """Require the exact sha256-prefixed engine digest published by the owner contract."""
    text = _require_text(value, "engine_artifact_digest")
    prefix = "sha256:"
    if not text.startswith(prefix) or _DIGEST_PATTERN.fullmatch(text[len(prefix) :]) is None:
        raise ValueError("engine_artifact_digest must be canonical sha256:<64 lowercase hex>")
    return text


def _validate_recorded_at(value: object) -> datetime:
    """Require exact built-in UTC system-recorded time for immutable Orgmetra evidence."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("recorded_at must be an exact built-in UTC datetime")
    return value


def _canonical_timestamp(value: datetime) -> str:
    """Render an already-governed UTC timestamp in deterministic RFC 3339 form."""
    return value.isoformat().replace("+00:00", "Z")


def _seal(payload_json: str) -> str:
    """Bind one in-process issuance to its exact creation-time canonical payload."""
    return hmac.new(_PROCESS_SEAL_KEY, payload_json.encode("utf-8"), "sha256").hexdigest()


@dataclass(frozen=True, slots=True, repr=False, weakref_slot=True, eq=False)
class PsychometricsResultEvidenceEnvelope:
    """Bind immutable external measurement provenance without copying personal score values."""

    tenant_record_id: str
    result_evidence_reference: str
    candidate_evidence_intake_reference: str
    candidate_evidence_intake_digest: str
    requesting_actor_reference: str
    reviewing_actor_reference: str
    result_snapshot_reference: str
    participant_binding_digest: str
    response_snapshot_reference: str
    assessment_spec_reference: str
    instrument_version_reference: str
    scoring_version_reference: str
    calibration_reference: str
    norm_version_reference: str | None
    narrative_version_reference: str
    consent_snapshot_set_digest: str
    engine_artifact_digest: str
    result_snapshot_digest: str
    requested_output_schema_version: int
    result_created_at_unix_ms: int
    supersedes_result_snapshot_reference: str | None
    psychometrics_commons_revision: str
    evidence_version: int
    recorded_at: datetime
    _creation_seal: str | None = field(default=None, repr=False, compare=False)
    _issuance_marker: object = field(default=_NEW_ISSUANCE_MARKER, repr=False, compare=False)

    SOURCE_SYSTEM: ClassVar[str] = "psychometrics-commons"
    SOURCE_TRUST_STATE: ClassVar[str] = "external_measurement_evidence"
    REVIEW_STATE: ClassVar[str] = "requires_human_review"
    DECISION_AUTHORITY_STATE: ClassVar[str] = "not_authorized_for_employment_decision"
    SCORE_HANDLING_STATE: ClassVar[str] = "score_values_not_stored"

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Keep the trust-bearing evidence runtime final."""
        raise TypeError("PsychometricsResultEvidenceEnvelope is final")

    def __post_init__(self) -> None:
        """Validate the reviewed boundary and seal its exact creation-time evidence."""
        if self._issuance_marker is not _NEW_ISSUANCE_MARKER or self._creation_seal is not None:
            raise ValueError("psychometrics result evidence changed after construction")
        self._validate_fields()
        seal = _seal(self._canonical_payload_json())
        object.__setattr__(self, "_creation_seal", seal)
        object.__setattr__(self, "_issuance_marker", _USED_ISSUANCE_MARKER)
        _register_creation_seal(self, seal)

    def _validate_fields(self) -> None:
        """Fail closed on tenant scope, provenance, actor separation, and evidence time."""
        _validate_operational_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_owned_reference(
            self.result_evidence_reference,
            "result_evidence_reference",
            "psych_result_evidence",
        )
        _validate_owned_reference(
            self.candidate_evidence_intake_reference,
            "candidate_evidence_intake_reference",
            "candidate_evidence_intake",
        )
        _validate_digest(
            self.candidate_evidence_intake_digest,
            "candidate_evidence_intake_digest",
        )
        requester = _validate_actor_reference(
            self.requesting_actor_reference,
            "requesting_actor_reference",
        )
        reviewer = _validate_actor_reference(
            self.reviewing_actor_reference,
            "reviewing_actor_reference",
        )
        if requester == reviewer:
            raise ValueError("reviewing_actor_reference must differ from requesting_actor_reference")

        _validate_foreign_reference(self.result_snapshot_reference, "result_snapshot_reference")
        _validate_digest(self.participant_binding_digest, "participant_binding_digest")
        _validate_foreign_reference(self.response_snapshot_reference, "response_snapshot_reference")
        _validate_foreign_reference(self.assessment_spec_reference, "assessment_spec_reference")
        _validate_foreign_reference(self.instrument_version_reference, "instrument_version_reference")
        _validate_foreign_reference(self.scoring_version_reference, "scoring_version_reference")
        _validate_foreign_reference(self.calibration_reference, "calibration_reference")
        _validate_optional_foreign_reference(self.norm_version_reference, "norm_version_reference")
        _validate_foreign_reference(self.narrative_version_reference, "narrative_version_reference")
        _validate_digest(self.consent_snapshot_set_digest, "consent_snapshot_set_digest")
        _validate_engine_digest(self.engine_artifact_digest)
        _validate_digest(self.result_snapshot_digest, "result_snapshot_digest")

        if type(self.requested_output_schema_version) is not int or self.requested_output_schema_version != 1:
            raise ValueError("requested_output_schema_version must match reviewed owner schema version 1")
        if type(self.result_created_at_unix_ms) is not int or self.result_created_at_unix_ms <= 0:
            raise ValueError("result_created_at_unix_ms must be an exact positive integer")
        supersedes = _validate_optional_foreign_reference(
            self.supersedes_result_snapshot_reference,
            "supersedes_result_snapshot_reference",
        )
        if supersedes == self.result_snapshot_reference:
            raise ValueError("result_snapshot_reference cannot supersede itself")

        recorded_at = _validate_recorded_at(self.recorded_at)
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        recorded_delta = recorded_at - epoch
        recorded_at_unix_ms = (
            recorded_delta.days * 86_400_000
            + recorded_delta.seconds * 1_000
            + recorded_delta.microseconds // 1_000
        )
        if recorded_at_unix_ms < self.result_created_at_unix_ms:
            raise ValueError("recorded_at cannot precede the source result creation time")

        revision = _require_text(self.psychometrics_commons_revision, "psychometrics_commons_revision")
        if revision != _PSYCHOMETRICS_COMMONS_REVISION:
            raise ValueError("psychometrics_commons_revision must match the reviewed dependency revision")
        if type(self.evidence_version) is not int or not 1 <= self.evidence_version <= 1_000_000:
            raise ValueError("evidence_version must be an exact positive bounded integer")

    def _payload(self) -> dict[str, object]:
        """Return canonical governance evidence without foreign participant or score values."""
        return {
            "assessment_spec_reference": self.assessment_spec_reference,
            "calibration_reference": self.calibration_reference,
            "candidate_evidence_intake_digest": self.candidate_evidence_intake_digest,
            "candidate_evidence_intake_reference": self.candidate_evidence_intake_reference,
            "consent_snapshot_set_digest": self.consent_snapshot_set_digest,
            "decision_authority_state": self.DECISION_AUTHORITY_STATE,
            "engine_artifact_digest": self.engine_artifact_digest,
            "evidence_version": self.evidence_version,
            "instrument_version_reference": self.instrument_version_reference,
            "narrative_version_reference": self.narrative_version_reference,
            "norm_version_reference": self.norm_version_reference,
            "participant_binding_digest": self.participant_binding_digest,
            "psychometrics_commons_revision": self.psychometrics_commons_revision,
            "recorded_at": _canonical_timestamp(self.recorded_at),
            "requesting_actor_reference": self.requesting_actor_reference,
            "requested_output_schema_version": self.requested_output_schema_version,
            "response_snapshot_reference": self.response_snapshot_reference,
            "result_created_at_unix_ms": self.result_created_at_unix_ms,
            "result_evidence_reference": self.result_evidence_reference,
            "result_snapshot_digest": self.result_snapshot_digest,
            "result_snapshot_reference": self.result_snapshot_reference,
            "review_state": self.REVIEW_STATE,
            "reviewing_actor_reference": self.reviewing_actor_reference,
            "score_handling_state": self.SCORE_HANDLING_STATE,
            "scoring_version_reference": self.scoring_version_reference,
            "source_system": self.SOURCE_SYSTEM,
            "source_trust_state": self.SOURCE_TRUST_STATE,
            "supersedes_result_snapshot_reference": self.supersedes_result_snapshot_reference,
            "tenant_record_id": self.tenant_record_id,
        }

    def _canonical_payload_json(self) -> str:
        """Serialize live evidence deterministically without trusting its creation seal."""
        return json.dumps(self._payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def _assert_integrity(self) -> tuple[dict[str, object], str]:
        """Return the exact checked snapshot while rejecting post-construction rewriting."""
        self._validate_fields()
        if self._issuance_marker is not _USED_ISSUANCE_MARKER:
            raise ValueError("psychometrics result evidence changed after construction")
        packet_seal = self._creation_seal
        authoritative_seal = _authoritative_creation_seal(self)
        payload = self._payload()
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        live_seal = _seal(payload_json)
        if (
            type(packet_seal) is not str
            or type(authoritative_seal) is not str
            or not hmac.compare_digest(packet_seal, authoritative_seal)
            or not hmac.compare_digest(live_seal, authoritative_seal)
        ):
            raise ValueError("psychometrics result evidence changed after construction")
        return payload, payload_json

    def canonical_document(self) -> dict[str, object]:
        """Return the exact canonical document snapshot that passed integrity verification."""
        payload, _ = self._assert_integrity()
        return payload

    def canonical_json(self) -> str:
        """Return the exact JSON snapshot that passed integrity verification."""
        _, payload_json = self._assert_integrity()
        return payload_json

    def evidence_digest(self) -> str:
        """Return SHA-256 of the exact canonical evidence bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        """Avoid leaking tenant, candidate, actor, assessment, or result correlation into logs."""
        return "PsychometricsResultEvidenceEnvelope(<redacted>)"
