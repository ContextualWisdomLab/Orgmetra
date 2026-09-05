"""Regression contract for returned Job Analysis ownership coherence."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_hris_kernel import JobAnalysisSnapshot
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIntegrityError,
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

_OTHER_TENANT = UUID("0198a412-6000-7000-8000-000000000491")
_OTHER_JOB = UUID("0198a412-6000-7000-8000-000000000492")


class _ReadPort:
    """Return one exact snapshot without repairing low-level ownership drift."""

    def __init__(self, snapshot: JobAnalysisSnapshot) -> None:
        self.snapshot = snapshot

    def read_snapshot(self, **_: object) -> JobAnalysisSnapshot:
        """Return the configured snapshot exactly as durable evidence supplied it."""
        return self.snapshot


class _WritePort:
    """Return one exact snapshot without repairing low-level ownership drift."""

    def __init__(self, snapshot: JobAnalysisSnapshot) -> None:
        self.snapshot = snapshot

    def persist_snapshot(self, **_: object) -> JobAnalysisSnapshot:
        """Return the configured snapshot exactly as durable evidence supplied it."""
        return self.snapshot


def _read(snapshot: JobAnalysisSnapshot) -> None:
    """Execute the governed read path for one contradictory returned graph."""
    read_job_analysis_snapshot(
        principal=read_principal(),
        tenant_record_id=TENANT,
        analysis_record_id=ANALYSIS,
        purpose_code="job_analysis_read",
        policy=read_policy(),
        read_port=_ReadPort(snapshot),
    )


def test_read_rejects_task_tenant_drift_before_canonicalization() -> None:
    """A Task cannot be silently re-parented to the snapshot tenant during export."""
    snapshot = clinical_psychologist_snapshot()
    object.__setattr__(snapshot.tasks[0], "tenant_record_id", _OTHER_TENANT)

    with pytest.raises(JobAnalysisIntegrityError, match="ownership"):
        _read(snapshot)


def test_read_rejects_ksao_job_drift_before_canonicalization() -> None:
    """A KSAO cannot be silently re-parented to the snapshot Job during export."""
    snapshot = clinical_psychologist_snapshot()
    object.__setattr__(snapshot.ksao_requirements[0], "job_record_id", _OTHER_JOB)

    with pytest.raises(JobAnalysisIntegrityError, match="ownership"):
        _read(snapshot)


def test_read_rejects_fja_tenant_drift_before_canonicalization() -> None:
    """The FJA profile must retain the exact returned snapshot tenant ownership."""
    snapshot = clinical_psychologist_snapshot()
    object.__setattr__(snapshot.fja_profile, "tenant_record_id", _OTHER_TENANT)

    with pytest.raises(JobAnalysisIntegrityError, match="ownership"):
        _read(snapshot)


def test_write_rejects_fja_job_drift_before_posted_document_comparison() -> None:
    """Write-result capture must reject FJA ownership drift instead of normalizing it."""
    snapshot = clinical_psychologist_snapshot()
    object.__setattr__(snapshot.fja_profile, "job_record_id", _OTHER_JOB)

    with pytest.raises(JobAnalysisIntegrityError, match="persisted snapshot graph"):
        persist_job_analysis_snapshot(
            principal=write_principal(),
            tenant_record_id=TENANT,
            document=clinical_psychologist_document(),
            idempotency_key=IDEMPOTENCY_KEY,
            purpose_code="job_analysis_write",
            policy=write_policy(),
            write_port=_WritePort(snapshot),
        )
