"""Adversarial coverage for release-publication validation and recovery edges."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from orgmetra_release_publication import ReleasePlatformReceipt, ReleasePublicationError
from orgmetra_release_publication import publication as publication_module
from orgmetra_release_publication import execution as execution_module

_DIGEST = "1" * 64
_CANDIDATE = "a" * 40
_REFERENCE = "release_publication:44444444-4444-4444-8444-444444444444"
_STARTED = datetime(2026, 8, 26, 8, 0, 3, tzinfo=timezone.utc)


class _CanonicalReceipt:
    """Expose caller-controlled canonical JSON for internal boundary regressions."""

    def __init__(self, payload: object | None = None, *, error: Exception | None = None) -> None:
        """Configure one canonical payload or an evidence-read failure."""
        self.payload = payload
        self.error = error

    def canonical_json(self) -> str:
        """Return configured JSON or raise the configured evidence failure."""
        if self.error is not None:
            raise self.error
        return json.dumps(self.payload, sort_keys=True, separators=(",", ":"))


class _ReconcileFailure:
    """Model a publisher whose lookup-only reconciliation transport fails."""

    def reconcile_release(self, **kwargs: object) -> object:
        """Fail reconciliation without attempting a publication."""
        assert kwargs["candidate_revision_sha"] == _CANDIDATE
        raise RuntimeError("lookup unavailable")


def _valid_platform_receipt(**overrides: object) -> ReleasePlatformReceipt:
    """Build one valid platform receipt and apply controlled field overrides."""
    values: dict[str, object] = {
        "authorization_evidence_digest_sha256": _DIGEST,
        "candidate_revision_sha": _CANDIDATE,
        "tag_name": "v1.2.3",
        "publication_reference": _REFERENCE,
        "platform_release_digest_sha256": "2" * 64,
        "audit_event_envelope_digest_sha256": "3" * 64,
        "published_at": _STARTED + timedelta(seconds=1),
    }
    values.update(overrides)
    return ReleasePlatformReceipt(**values)


def _valid_authorization_document(**overrides: object) -> dict[str, object]:
    """Build the minimal parent authorization document consumed by this package."""
    payload: dict[str, object] = {
        "release_authority": "authorized_for_exact_release_operation",
        "publication_state": "not_published",
        "evidence_version": 1,
        "candidate_revision_sha": _CANDIDATE,
        "tag_name": "v1.2.3",
        "audit_recorded_at": "2026-08-26T08:00:02Z",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: publication_module._exact_text(1, "field"), "exact string"),
        (lambda: publication_module._digest("A" * 64, "digest"), "lower-case SHA-256"),
        (lambda: publication_module._revision("g" * 40, "revision"), "40 lower-case"),
        (lambda: publication_module._tag("v01.2.3"), "canonical"),
        (lambda: publication_module._publication_reference("release_publication:not-a-uuid"), "publication_reference"),
        (
            lambda: publication_module._timestamp(
                datetime(2026, 8, 26, 8, 0, tzinfo=timezone(timedelta(hours=1))),
                "timestamp",
            ),
            "timezone.utc",
        ),
    ],
)
def test_primitive_validators_reject_noncanonical_runtime_evidence(call: object, message: str) -> None:
    """Reject malformed or polymorphic trust evidence before comparison or serialization."""
    with pytest.raises(ReleasePublicationError, match=message):
        call()  # type: ignore[operator]


@pytest.mark.parametrize(
    "value",
    [
        "2026-08-26T08:00:02+00:00",
        "not-a-timestampZ",
        "2026-08-26T08:00:02.000000Z",
    ],
)
def test_parent_timestamp_parser_rejects_alternate_or_invalid_forms(value: str) -> None:
    """Require one deterministic parent RFC 3339 UTC representation."""
    with pytest.raises(ReleasePublicationError, match="canonical RFC 3339 UTC"):
        publication_module._parse_canonical_timestamp(value, "audit_recorded_at")


def test_platform_receipt_is_final() -> None:
    """Prevent host-evidence subclasses from overriding trust-bearing semantics."""
    with pytest.raises(TypeError, match="final trust-bearing"):

        class _ForgedPlatformReceipt(ReleasePlatformReceipt):
            """Attempt to override host receipt semantics."""


def test_publication_receipt_requires_factory_and_is_final() -> None:
    """Prevent direct issuance and subtype overrides of publication evidence."""
    with pytest.raises(TypeError, match="factory-issued"):
        publication_module.ReleasePublicationReceipt(
            authorization_evidence_digest_sha256=_DIGEST,
            candidate_revision_sha=_CANDIDATE,
            tag_name="v1.2.3",
            publication_reference=_REFERENCE,
            platform_release_digest_sha256="2" * 64,
            audit_event_envelope_digest_sha256="3" * 64,
            publication_started_at=_STARTED,
            published_at=_STARTED + timedelta(seconds=1),
        )
    with pytest.raises(TypeError, match="final trust-bearing"):

        class _ForgedPublicationReceipt(publication_module.ReleasePublicationReceipt):
            """Attempt to override factory-issued receipt semantics."""


def test_authorization_snapshot_normalizes_evidence_failures() -> None:
    """Convert unreadable parent evidence into one stable fail-closed error."""
    with pytest.raises(ReleasePublicationError, match="authorization evidence is invalid"):
        publication_module._authorization_snapshot(_CanonicalReceipt(error=ValueError("tampered")))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "canonical object"),
        (_valid_authorization_document(release_authority="not_authorized"), "does not grant"),
        (_valid_authorization_document(publication_state="published"), "already been consumed"),
        (_valid_authorization_document(evidence_version=2), "evidence_version"),
    ],
)
def test_authorization_snapshot_rejects_wrong_governance_state(payload: object, message: str) -> None:
    """Reject parent evidence whose authority, consumption, or version state is wrong."""
    with pytest.raises(ReleasePublicationError, match=message):
        publication_module._authorization_snapshot(_CanonicalReceipt(payload))  # type: ignore[arg-type]


def test_matching_platform_snapshot_rejects_malformed_mutated_receipt() -> None:
    """Treat post-construction malformed host evidence as ambiguous instead of trusted."""
    receipt = _valid_platform_receipt()
    object.__setattr__(receipt, "platform_release_digest_sha256", "not-a-digest")
    assert publication_module._matching_platform_snapshot(
        receipt,
        authorization_digest=_DIGEST,
        candidate_revision=_CANDIDATE,
        tag_name="v1.2.3",
        publication_reference=_REFERENCE,
        publication_started_at=_STARTED,
    ) is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"authorization_evidence_digest_sha256": "9" * 64},
        {"candidate_revision_sha": "b" * 40},
        {"tag_name": "v1.2.4"},
        {"publication_reference": "release_publication:55555555-5555-4555-8555-555555555555"},
        {"published_at": _STARTED - timedelta(microseconds=1)},
    ],
)
def test_matching_platform_snapshot_requires_every_exact_scope_binding(overrides: dict[str, object]) -> None:
    """Reject otherwise-valid host evidence when any exact publication binding differs."""
    receipt = _valid_platform_receipt(**overrides)
    assert publication_module._matching_platform_snapshot(
        receipt,
        authorization_digest=_DIGEST,
        candidate_revision=_CANDIDATE,
        tag_name="v1.2.3",
        publication_reference=_REFERENCE,
        publication_started_at=_STARTED,
    ) is None


def test_reconciliation_transport_failure_is_indeterminate() -> None:
    """Never convert a failed lookup into permission to republish."""
    with pytest.raises(publication_module.ReleasePublicationIndeterminateError, match="do not republish"):
        publication_module._reconcile_or_raise(
            _ReconcileFailure(),  # type: ignore[arg-type]
            authorization_digest=_DIGEST,
            candidate_revision=_CANDIDATE,
            tag_name="v1.2.3",
            publication_reference=_REFERENCE,
            publication_started_at=_STARTED,
        )


def test_publication_core_normalizes_clock_transport_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail before release side effects when the host clock itself raises unexpectedly."""
    authorization = _CanonicalReceipt(_valid_authorization_document())

    class _NeverPublisher:
        """Fail the test if publication is reached after a clock failure."""

        def publish_release(self, **kwargs: object) -> object:
            """Reject unexpected publication work."""
            raise AssertionError(kwargs)

        def reconcile_release(self, **kwargs: object) -> object:
            """Reject unexpected reconciliation work."""
            raise AssertionError(kwargs)

    monkeypatch.setattr(publication_module, "ReleaseAuthorizationReceipt", _CanonicalReceipt)
    with pytest.raises(ReleasePublicationError, match="clock failed"):
        publication_module.publish_authorized_release(
            authorization_receipt=authorization,
            publication_reference=_REFERENCE,
            publisher=_NeverPublisher(),
            clock=lambda: (_ for _ in ()).throw(RuntimeError("clock unavailable")),
        )


def test_publication_core_preserves_governed_clock_type_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Preserve the stable validation error when the clock returns a non-datetime value."""
    authorization = _CanonicalReceipt(_valid_authorization_document())
    monkeypatch.setattr(publication_module, "ReleaseAuthorizationReceipt", _CanonicalReceipt)
    with pytest.raises(ReleasePublicationError, match="publication_started_at"):
        publication_module.publish_authorized_release(
            authorization_receipt=authorization,
            publication_reference=_REFERENCE,
            publisher=_ReconcileFailure(),  # type: ignore[arg-type]
            clock=lambda: "not-a-time",
        )


def test_publication_core_rejects_start_before_authorization_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject a publication clock that would place the side effect before its audit authority."""
    authorization = _CanonicalReceipt(_valid_authorization_document())
    monkeypatch.setattr(publication_module, "ReleaseAuthorizationReceipt", _CanonicalReceipt)
    with pytest.raises(ReleasePublicationError, match="cannot precede"):
        publication_module.publish_authorized_release(
            authorization_receipt=authorization,
            publication_reference=_REFERENCE,
            publisher=_ReconcileFailure(),  # type: ignore[arg-type]
            clock=lambda: datetime(2026, 8, 26, 8, 0, 1, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"audit_recorded_at": 7},
        {"audit_recorded_at": "not-a-timeZ"},
    ],
)
def test_execution_guard_normalizes_invalid_parent_audit_time(payload: dict[str, object]) -> None:
    """Reject unreadable authorization chronology before invoking the publication core."""
    with pytest.raises(ReleasePublicationError, match="audit time is invalid"):
        execution_module._authorization_audit_time(_CanonicalReceipt(payload))  # type: ignore[arg-type]
