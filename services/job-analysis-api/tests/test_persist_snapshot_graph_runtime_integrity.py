"""Regression contract for inert Job Analysis write-port result graphs."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_hris_kernel import JobAnalysisSnapshot
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIntegrityError,
    persist_job_analysis_snapshot,
)

from fixtures import (
    IDEMPOTENCY_KEY,
    JOB,
    TENANT,
    clinical_psychologist_document,
    clinical_psychologist_snapshot,
    write_policy,
    write_principal,
)


class _ExecutableUUID(UUID):
    """Raise if comparison export stringifies unvalidated persistence evidence."""

    def __str__(self) -> str:
        """Fail if the write-port result reaches `to_snapshot()` before validation."""
        raise AssertionError("write-port result UUID stringification executed")


class _ReturningWritePort:
    """Return one configured exact persistence result without normalizing it."""

    def __init__(self, result: JobAnalysisSnapshot) -> None:
        self.result = result

    def persist_snapshot(self, **_: object) -> JobAnalysisSnapshot:
        """Return the configured result exactly as a defective adapter could."""
        return self.result


def test_persist_result_graph_is_validated_before_comparison_export() -> None:
    """Reject executable nested evidence before serializing a write-port result."""
    persisted = clinical_psychologist_snapshot()
    object.__setattr__(persisted, "job_record_id", _ExecutableUUID(str(JOB)))

    with pytest.raises(JobAnalysisIntegrityError, match="persisted snapshot graph"):
        persist_job_analysis_snapshot(
            principal=write_principal(),
            tenant_record_id=TENANT,
            document=clinical_psychologist_document(),
            idempotency_key=IDEMPOTENCY_KEY,
            purpose_code="job_analysis_write",
            policy=write_policy(),
            write_port=_ReturningWritePort(persisted),
        )
