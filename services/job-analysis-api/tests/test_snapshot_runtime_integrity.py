"""Regression coverage for executable snapshot subtypes at Job Analysis durable boundaries."""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel import AuditOutboxEvent, JobAnalysisSnapshot
from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIntegrityError,
    command_digest,
    persist_job_analysis_snapshot,
    read_job_analysis_snapshot,
)
from fixtures import (
    ANALYSIS,
    IDEMPOTENCY_KEY,
    TENANT,
    clinical_psychologist_document,
    clinical_psychologist_snapshot,
    read_policy,
    read_principal,
    write_policy,
    write_principal,
)

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

    def to_snapshot(self) -> dict[str, object]:
        """Reject document export if a service consumes subtype behavior before validation."""
        raise AssertionError("snapshot subtype to_snapshot consumed before exact-type rejection")


class _ReturningWritePort:
    """Return a configured persistence result without consuming it."""

    def __init__(self, result: JobAnalysisSnapshot) -> None:
        self.result = result

    def persist_snapshot(self, **_: object) -> JobAnalysisSnapshot:
        """Return the adversarial value exactly as a compromised adapter could."""
        return self.result


class _ReturningReadPort:
    """Return a configured read result without consuming it."""

    def __init__(self, result: JobAnalysisSnapshot) -> None:
        self.result = result

    def read_snapshot(self, **_: object) -> JobAnalysisSnapshot:
        """Return the adversarial value exactly as a compromised adapter could."""
        return self.result


class _MutatingWritePort:
    """Mutate the exact canonical snapshot supplied by the service and return the alias."""

    def persist_snapshot(self, **kwargs: object) -> JobAnalysisSnapshot:
        """Simulate a defective adapter that rewrites evidence through low-level mutation."""
        snapshot = kwargs["snapshot"]
        assert type(snapshot) is JobAnalysisSnapshot
        object.__setattr__(snapshot, "analysis_version_code", "clinical-psychologist:mutated")
        return snapshot


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


def test_persist_use_case_rejects_write_port_snapshot_subtype_before_export() -> None:
    """The service must reject an executable persistence result before document export."""
    with pytest.raises(
        JobAnalysisIntegrityError,
        match="persisted snapshot has an invalid runtime type",
    ):
        persist_job_analysis_snapshot(
            principal=write_principal(),
            tenant_record_id=TENANT,
            document=clinical_psychologist_document(),
            idempotency_key=IDEMPOTENCY_KEY,
            purpose_code=_PURPOSE_CODE,
            policy=write_policy(),
            write_port=_ReturningWritePort(_snapshot_subtype()),
        )


def test_persist_use_case_detects_exact_snapshot_mutation_by_write_port() -> None:
    """Compare persistence to evidence detached before the port can mutate the supplied object."""
    with pytest.raises(JobAnalysisIntegrityError, match="escaped posted payload"):
        persist_job_analysis_snapshot(
            principal=write_principal(),
            tenant_record_id=TENANT,
            document=clinical_psychologist_document(),
            idempotency_key=IDEMPOTENCY_KEY,
            purpose_code=_PURPOSE_CODE,
            policy=write_policy(),
            write_port=_MutatingWritePort(),
        )


def test_read_use_case_rejects_read_port_snapshot_subtype_before_fields_or_export() -> None:
    """The service must reject an executable repository result before authority-field access."""
    with pytest.raises(
        JobAnalysisIntegrityError,
        match="resolved snapshot has an invalid runtime type",
    ):
        read_job_analysis_snapshot(
            principal=read_principal(),
            tenant_record_id=TENANT,
            analysis_record_id=ANALYSIS,
            purpose_code="job_analysis_read",
            policy=read_policy(),
            read_port=_ReturningReadPort(_snapshot_subtype()),
        )
