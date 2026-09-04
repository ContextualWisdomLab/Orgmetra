"""Regression contract for detaching the posted write target before persistence."""

from __future__ import annotations

from uuid import UUID

from orgmetra_hris_kernel import JobAnalysisSnapshot
from orgmetra_job_analysis_api.snapshot import persist_job_analysis_snapshot

from fixtures import (
    ANALYSIS,
    IDEMPOTENCY_KEY,
    TENANT,
    clinical_psychologist_document,
    clinical_psychologist_snapshot,
    write_policy,
    write_principal,
)


class _ExecutableUUID(UUID):
    """Raise if post-port target equality consults adapter-mutated input evidence."""

    def __getattribute__(self, name: str) -> object:
        """Fail when exact UUID comparison asks the mutated subtype for integer state."""
        if name == "int":
            raise AssertionError("post-port input target UUID state executed")
        return super().__getattribute__(name)


class _MutatingInputWritePort:
    """Mutate the supplied input alias but return separate pristine persistence evidence."""

    def __init__(self, result: JobAnalysisSnapshot) -> None:
        self.result = result

    def persist_snapshot(self, **kwargs: object) -> JobAnalysisSnapshot:
        """Rewrite only the port-owned input target after all pre-port checks completed."""
        supplied = kwargs["snapshot"]
        assert type(supplied) is JobAnalysisSnapshot
        object.__setattr__(
            supplied,
            "analysis_record_id",
            _ExecutableUUID(str(ANALYSIS)),
        )
        return self.result


def test_persist_target_comparison_uses_pre_port_detached_identity() -> None:
    """Never reread an input snapshot target after handing its alias to the write port."""
    view = persist_job_analysis_snapshot(
        principal=write_principal(),
        tenant_record_id=TENANT,
        document=clinical_psychologist_document(),
        idempotency_key=IDEMPOTENCY_KEY,
        purpose_code="job_analysis_write",
        policy=write_policy(),
        write_port=_MutatingInputWritePort(clinical_psychologist_snapshot()),
    )

    assert view.snapshot["analysis_record_id"] == str(ANALYSIS)
