from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel.job_analysis import (
    EvidenceSource,
    FunctionalJobAnalysisProfile,
    JobAnalysisSnapshot,
    KSAORequirement,
    TaskEvidence,
    TaskKSAOLink,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000002001")
JOB_ID = UUID("00000000-0000-4000-8000-000000002002")
ANALYSIS_ID = UUID("00000000-0000-4000-8000-000000002003")
TASK_ID = UUID("00000000-0000-4000-8000-000000002004")
KSAO_ID = UUID("00000000-0000-4000-8000-000000002005")
RECORDED_AT = datetime(2026, 8, 17, 4, 0, tzinfo=timezone.utc)


def _source(retrieved_at: datetime) -> EvidenceSource:
    return EvidenceSource(
        source_uri="https://www.onetcenter.org/database.html",
        source_title="O*NET 30.3 Database",
        source_version_code="onet:30.3",
        retrieved_at=retrieved_at,
        content_digest_sha256="b" * 64,
        origin_code="authoritative_occupation_source",
    )


def _snapshot_with_sources(*, task_source, ksao_source, fja_source) -> JobAnalysisSnapshot:
    return JobAnalysisSnapshot(
        analysis_record_id=ANALYSIS_ID,
        tenant_record_id=TENANT_ID,
        job_record_id=JOB_ID,
        analysis_version_code="analysis:v1",
        status_code="analysis_validated",
        effective_from=date(2026, 8, 1),
        recorded_at=RECORDED_AT,
        tasks=(
            TaskEvidence(
                tenant_record_id=TENANT_ID,
                job_record_id=JOB_ID,
                task_record_id=TASK_ID,
                task_statement="Analyze governed workforce data and document decision evidence.",
                importance_level=5,
                difficulty_level=4,
                source=task_source,
            ),
        ),
        ksao_requirements=(
            KSAORequirement(
                tenant_record_id=TENANT_ID,
                job_record_id=JOB_ID,
                ksao_record_id=KSAO_ID,
                category_code="knowledge_requirement",
                requirement_statement="Knowledge of data governance controls and evidence traceability.",
                importance_level=5,
                proficiency_level=4,
                source=ksao_source,
            ),
        ),
        task_ksao_links=(
            TaskKSAOLink(
                task_record_id=TASK_ID,
                ksao_record_id=KSAO_ID,
                relationship_strength=5,
                essential_for_task=True,
            ),
        ),
        fja_profile=FunctionalJobAnalysisProfile(
            tenant_record_id=TENANT_ID,
            job_record_id=JOB_ID,
            data_function_code=2,
            people_function_code=1,
            things_function_code=7,
            source=fja_source,
        ),
        reviewed_by_reference="keyverse_subject:01JIOPSYCH",
        reviewed_at=RECORDED_AT - timedelta(minutes=1),
    )


@pytest.mark.parametrize("future_lane", ("task", "ksao", "fja"))
def test_snapshot_rejects_evidence_retrieved_after_its_recorded_instant(future_lane):
    known = _source(RECORDED_AT - timedelta(hours=1))
    future = _source(RECORDED_AT + timedelta(seconds=1))
    sources = {"task_source": known, "ksao_source": known, "fja_source": known}
    sources[f"{future_lane}_source"] = future

    with pytest.raises(ValueError, match="retrieved_at must not be later than recorded_at"):
        _snapshot_with_sources(**sources)


def test_snapshot_accepts_evidence_retrieved_exactly_at_recorded_instant():
    source = _source(RECORDED_AT)
    snapshot = _snapshot_with_sources(
        task_source=source,
        ksao_source=source,
        fja_source=source,
    )

    assert snapshot.recorded_at == RECORDED_AT
