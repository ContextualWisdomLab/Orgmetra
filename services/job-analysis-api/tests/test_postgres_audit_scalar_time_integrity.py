"""Regression coverage for inert Job Analysis durable-audit scalar/time evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from uuid import UUID

import pytest

from orgmetra_hris_kernel import AuditOutboxEvent
from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import command_digest
from fixtures import ANALYSIS, IDEMPOTENCY_KEY, TENANT, clinical_psychologist_snapshot

_ACTOR_REFERENCE = "keyverse:actor-ja-1"
_PURPOSE_CODE = "job_analysis_write"
_RESOURCE_REFERENCE = f"job_analysis_snapshot:{ANALYSIS.hex}"


class _TripwireTimezone(tzinfo):
    """Fail if durable validation executes caller-defined timezone behavior."""

    def __init__(self) -> None:
        self.calls = 0

    def utcoffset(self, value: datetime | None) -> timedelta:
        del value
        self.calls += 1
        raise AssertionError("audit occurred_at timezone callback executed before rejection")

    def dst(self, value: datetime | None) -> timedelta:
        del value
        return timedelta(0)

    def tzname(self, value: datetime | None) -> str:
        del value
        return "TRIPWIRE"


class _ExecutableConfirmationReference(str):
    """Trip if optional confirmation text reaches equality before exact-type rejection."""

    def __eq__(self, other: object) -> bool:
        del other
        raise AssertionError("confirmation_reference equality executed before rejection")

    def __ne__(self, other: object) -> bool:
        del other
        raise AssertionError("confirmation_reference inequality executed before rejection")

    __hash__ = str.__hash__


def _audit_event() -> AuditOutboxEvent:
    """Build one valid exact audit envelope before low-level adversarial rewriting."""
    snapshot = clinical_psychologist_snapshot()
    return AuditOutboxEvent(
        event_id=UUID("0198a412-6000-7000-8000-000000000411"),
        tenant_record_id=TENANT,
        source_service="job_analysis_api",
        event_type="orgmetra.job_architecture.snapshot_recorded",
        resource_reference=_RESOURCE_REFERENCE,
        actor_reference=_ACTOR_REFERENCE,
        purpose_code=_PURPOSE_CODE,
        reason_code="snapshot_persisted",
        evidence_version_code=snapshot.analysis_version_code,
        result_code="recorded",
        occurred_at=datetime(2026, 8, 18, 5, 1, tzinfo=timezone.utc),
        high_impact=False,
    )


def _never_connect() -> object:
    """Prove malformed audit evidence is rejected before database acquisition."""
    raise AssertionError("database acquired before durable audit scalar/time validation")


def _persist_with_audit(audit_event: AuditOutboxEvent) -> None:
    """Invoke the durable write boundary with one otherwise-valid command."""
    snapshot = clinical_psychologist_snapshot()
    PostgresJobAnalysisPort(_never_connect).persist_snapshot(
        snapshot=snapshot,
        idempotency_key=IDEMPOTENCY_KEY,
        request_digest=command_digest(
            snapshot=snapshot,
            position_record_id=None,
            criterion_blueprint_id=None,
        ),
        actor_reference=_ACTOR_REFERENCE,
        purpose_code=_PURPOSE_CODE,
        position_record_id=None,
        criterion_blueprint_id=None,
        audit_event=audit_event,
        outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000412"),
        write_command_id=UUID("0198a412-6000-7000-8000-000000000413"),
    )


def test_durable_audit_rejects_executable_occurred_at_timezone_before_callback() -> None:
    """Canonicalization must never execute a caller-defined durable-audit timezone."""
    audit_event = _audit_event()
    tripwire = _TripwireTimezone()
    object.__setattr__(
        audit_event,
        "occurred_at",
        datetime(2026, 8, 18, 5, 1, tzinfo=tripwire),
    )

    with pytest.raises(
        ValueError,
        match="occurred_at must be an exact timezone-aware datetime",
    ):
        _persist_with_audit(audit_event)

    assert tripwire.calls == 0


def test_durable_audit_rejects_non_boolean_high_impact_before_canonicalization() -> None:
    """Low-level rewrites cannot make non-boolean audit semantics reach serialization."""
    audit_event = _audit_event()
    tripwire = _TripwireTimezone()
    object.__setattr__(audit_event, "high_impact", 0)
    object.__setattr__(
        audit_event,
        "occurred_at",
        datetime(2026, 8, 18, 5, 1, tzinfo=tripwire),
    )

    with pytest.raises(ValueError, match="high_impact must be a boolean"):
        _persist_with_audit(audit_event)

    assert tripwire.calls == 0


def test_durable_audit_rejects_executable_confirmation_before_canonicalization() -> None:
    """Optional confirmation evidence must be inert exact text before serialization."""
    audit_event = _audit_event()
    tripwire = _TripwireTimezone()
    object.__setattr__(
        audit_event,
        "confirmation_reference",
        _ExecutableConfirmationReference("review:job-analysis-1"),
    )
    object.__setattr__(
        audit_event,
        "occurred_at",
        datetime(2026, 8, 18, 5, 1, tzinfo=tripwire),
    )

    with pytest.raises(ValueError, match="confirmation_reference must be a string when supplied"):
        _persist_with_audit(audit_event)

    assert tripwire.calls == 0
