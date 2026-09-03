"""Regression coverage for executable snapshot subtypes at Job Analysis durable boundaries."""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel import AuditOutboxEvent, JobAnalysisSnapshot
from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import command_digest
from fixtures import ANALYSIS, IDEMPOTENCY_KEY, TENANT, clinical_psychologist_snapshot

_ACTOR_REFERENCE = "keyverse:actor-ja-1"
_PURPOSE_CODE = "job_analysis_write"


class _SnapshotSubtype(JobAnalysisSnapshot):
    """Trip if command or persistence code consumes caller-defined snapshot behavior."""

    _TRIPWIRE_FIELDS = frozenset({"analysis_record_id", "tenant_record_id", "job_record_id"})

    def __getattribute__(self, name: str) -> object:
        """Reject authority-field reads once the adversarial fixture is armed."""
        if name in _SnapshotSubtype._TRIPWIRE_FIELDS:
            try:
                armed = object.__getattribute__(self, "_tripwire_armed")
            except AttributeError:
                armed = False
            if armed:
                raise AssertionError(f"snapshot subtype field consumed before exact-type rejection: {name}")
        return super().__getattribute__(name)

    def canonical_json(self) -> str:
        """Reject canonical serialization if command validation is reordered."""
        raise AssertionError("snapshot subtype canonical_json consumed before exact-type rejection")

    def content_digest(self) -> str:
        """Reject digest serialization if persistence validation is reordered."""
        raise AssertionError("snapshot subtype content_digest consumed before exact-type rejection")


def _snapshot_subtype() -> JobAnalysisSnapshot:
    """Clone one valid kernel snapshot into a caller-defined runtime subtype and arm it."""
    snapshot = clinical_psychologist_snapshot()
    values = {
        field.name: getattr(snapshot, field.name)
        for field in fields(JobAnalysisSnapshot)
        if field.init
    }
    subtype = _SnapshotSubtype(**values)
    object.__setattr__(subtype, "_tripwire_armed", True)
    return subtype


def _audit_event(snapshot: JobAnalysisSnapshot) -> AuditOutboxEvent:
    """Build the canonical audit envelope for the otherwise-valid durable write."""
    return AuditOutboxEvent(
        event_id=UUID("0198a412-6000-7000-8000-000000000411"),
        tenant_record_id=TENANT,
        source_service="job_analysis_api",
        event_type="orgmetra.job_architecture.snapshot_recorded",
        resource_reference=f"job_analysis_snapshot:{ANALYSIS.hex}",
        actor_reference=_ACTOR_REFERENCE,
        purpose_code=_PURPOSE_CODE,
        reason_code="snapshot_persisted",
        evidence_version_code=snapshot.analysis_version_code,
        result_code="recorded",
        occurred_at=datetime(2026, 8, 18, 5, 1, tzinfo=timezone.utc),
        high_impact=False,
    )


def _never_connect() -> object:
    """Prove invalid snapshot runtime types fail before database acquisition."""
    raise AssertionError("database acquired before exact JobAnalysisSnapshot rejection")


def test_command_digest_rejects_snapshot_subtype_before_serialization() -> None:
    """Semantic idempotency must not execute caller-defined snapshot serialization."""
    with pytest.raises(TypeError, match="snapshot must be an exact JobAnalysisSnapshot"):
        command_digest(
            snapshot=_snapshot_subtype(),
            position_record_id=None,
            criterion_blueprint_id=None,
        )


def test_postgres_rejects_snapshot_subtype_before_fields_or_database() -> None:
    """Persistence must reject executable snapshot subtypes before field access or DB I/O."""
    base_snapshot = clinical_psychologist_snapshot()
    port = PostgresJobAnalysisPort(_never_connect)

    with pytest.raises(TypeError, match="snapshot must be an exact JobAnalysisSnapshot"):
        port.persist_snapshot(
            snapshot=_snapshot_subtype(),
            idempotency_key=IDEMPOTENCY_KEY,
            request_digest=command_digest(
                snapshot=base_snapshot,
                position_record_id=None,
                criterion_blueprint_id=None,
            ),
            actor_reference=_ACTOR_REFERENCE,
            purpose_code=_PURPOSE_CODE,
            position_record_id=None,
            criterion_blueprint_id=None,
            audit_event=_audit_event(base_snapshot),
            outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000412"),
            write_command_id=UUID("0198a412-6000-7000-8000-000000000413"),
        )
