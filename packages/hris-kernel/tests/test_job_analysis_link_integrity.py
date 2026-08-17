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

TENANT_ID = UUID("00000000-0000-4000-8000-000000003001")
JOB_ID = UUID("00000000-0000-4000-8000-000000003002")
ANALYSIS_ID = UUID("00000000-0000-4000-8000-000000003003")
TASK_ID = UUID("00000000-0000-4000-8000-000000003004")
KSAO_ID = UUID("00000000-0000-4000-8000-000000003005")
RECORDED_AT = datetime(2026, 8, 17, 4, 0, tzinfo=timezone.utc)


def _source() -> EvidenceSource:
    return EvidenceSource(
        source_uri="https://www.onetcenter.org/database.html",
        source_title="O*NET 30.3 Database",
        source_version_code="onet:30.3",
        retrieved_at=RECORDED_AT - timedelta(hours=1),
        content_digest_sha256="c" * 64,
        origin_code="authoritative_occupation_source",
    )


def _validated_snapshot(*, links: tuple[TaskKSAOLink, ...]) -> JobAnalysisSnapshot:
    source = _source()
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
                source=source,
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
                source=source,
            ),
        ),
        task_ksao_links=links,
        fja_profile=FunctionalJobAnalysisProfile(
            tenant_record_id=TENANT_ID,
            job_record_id=JOB_ID,
            data_function_code=2,
            people_function_code=1,
            things_function_code=7,
            source=source,
        ),
        reviewed_by_reference="keyverse_subject:01JIOPSYCH",
        reviewed_at=RECORDED_AT - timedelta(minutes=1),
    )


def test_validated_snapshot_rejects_duplicate_task_ksao_relationships():
    duplicate = TaskKSAOLink(
        task_record_id=TASK_ID,
        ksao_record_id=KSAO_ID,
        relationship_strength=5,
        essential_for_task=True,
    )

    with pytest.raises(ValueError, match="task_ksao_links must not duplicate a task and KSAO pair"):
        _validated_snapshot(links=(duplicate, duplicate))
