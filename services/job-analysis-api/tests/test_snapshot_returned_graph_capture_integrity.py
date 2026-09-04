"""Regression contract for binding returned snapshot validation to emitted evidence."""

from __future__ import annotations

from uuid import UUID

import pytest

import orgmetra_job_analysis_api.snapshot as snapshot_module
from orgmetra_hris_kernel import JobAnalysisSnapshot
from orgmetra_job_analysis_api.snapshot import (
    persist_job_analysis_snapshot,
    read_job_analysis_snapshot,
)

from fixtures import (
    ANALYSIS,
    IDEMPOTENCY_KEY,
    JOB,
    TENANT,
    clinical_psychologist_document,
    clinical_psychologist_snapshot,
    read_policy,
    read_principal,
    write_policy,
    write_principal,
)


class _ExecutableUUID(UUID):
    """Raise if evidence installed after validation reaches snapshot export."""

    def __str__(self) -> str:
        """Fail if a checked-versus-emitted gap rereads the mutated live graph."""
        raise AssertionError("post-validation UUID stringification executed")


class _ReturningWritePort:
    """Return one retained exact snapshot from the persistence boundary."""

    def __init__(self, result: JobAnalysisSnapshot) -> None:
        self.result = result

    def persist_snapshot(self, **_: object) -> JobAnalysisSnapshot:
        """Return the exact retained result without normalizing it."""
        return self.result


class _ReadPort:
    """Return one retained exact snapshot from the read boundary."""

    def __init__(self, result: JobAnalysisSnapshot) -> None:
        self.result = result

    def read_snapshot(
        self,
        *,
        tenant_record_id: UUID,
        analysis_record_id: UUID,
    ) -> JobAnalysisSnapshot:
        """Return the exact retained result without normalizing it."""
        return self.result


def _mutate_after_runtime_validation(
    monkeypatch: pytest.MonkeyPatch,
    returned: JobAnalysisSnapshot,
) -> None:
    """Inject a deterministic retained-adapter mutation after the validation pass."""
    original = snapshot_module._validate_resolved_snapshot_graph_runtime

    def validate_then_mutate(snapshot: JobAnalysisSnapshot):
        captured = original(snapshot)
        if snapshot is returned:
            object.__setattr__(snapshot, "job_record_id", _ExecutableUUID(str(JOB)))
        return captured

    monkeypatch.setattr(
        snapshot_module,
        "_validate_resolved_snapshot_graph_runtime",
        validate_then_mutate,
    )


def test_read_uses_the_exact_graph_captured_by_runtime_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not reread a retained read-port graph after it passed validation."""
    returned = clinical_psychologist_snapshot()
    expected = returned.to_snapshot()
    _mutate_after_runtime_validation(monkeypatch, returned)

    view = read_job_analysis_snapshot(
        principal=read_principal(),
        tenant_record_id=TENANT,
        analysis_record_id=ANALYSIS,
        purpose_code="job_analysis_read",
        policy=read_policy(),
        read_port=_ReadPort(returned),
    )

    assert view.snapshot == expected


def test_write_uses_the_exact_graph_captured_by_runtime_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not reread a retained write-port graph after it passed validation."""
    returned = clinical_psychologist_snapshot()
    expected = returned.to_snapshot()
    _mutate_after_runtime_validation(monkeypatch, returned)

    view = persist_job_analysis_snapshot(
        principal=write_principal(),
        tenant_record_id=TENANT,
        document=clinical_psychologist_document(),
        idempotency_key=IDEMPOTENCY_KEY,
        purpose_code="job_analysis_write",
        policy=write_policy(),
        write_port=_ReturningWritePort(returned),
    )

    assert view.snapshot == expected
