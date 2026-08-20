"""Shared 임상심리사 job-analysis fixtures for persistence contracts."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from orgmetra_hris_kernel import (
    EvidenceSource,
    FunctionalJobAnalysisProfile,
    JobAnalysisSnapshot,
    KSAORequirement,
    TaskEvidence,
    TaskKSAOLink,
)
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_job_analysis_api import AuthenticatedPrincipal

TENANT = UUID("0198a412-6000-7000-8000-000000000001")
OTHER_TENANT = UUID("0198a412-6000-7000-8000-000000000002")
JOB = UUID("0198a412-6000-7000-8000-000000000101")
POSITION = UUID("0198a412-6000-7000-8000-000000000102")
CRITERION = UUID("0198a412-6000-7000-8000-000000000103")
ANALYSIS = UUID("0198a412-6000-7000-8000-000000000201")
TASK_ASSESS = UUID("0198a412-6000-7000-8000-000000000211")
TASK_THERAPY = UUID("0198a412-6000-7000-8000-000000000212")
TASK_HUDDLE = UUID("0198a412-6000-7000-8000-000000000213")
KSAO_KNOWLEDGE = UUID("0198a412-6000-7000-8000-000000000221")
KSAO_SKILL = UUID("0198a412-6000-7000-8000-000000000222")
KSAO_ABILITY = UUID("0198a412-6000-7000-8000-000000000223")
RECORDED_AT = datetime(2026, 8, 18, 5, 0, tzinfo=timezone.utc)
REVIEWED_AT = datetime(2026, 8, 18, 4, 50, tzinfo=timezone.utc)
RETRIEVED_AT = datetime(2026, 8, 18, 3, 0, tzinfo=timezone.utc)
ONET_DIGEST = "b" * 64
DOT_DIGEST = "c" * 64
IDEMPOTENCY_KEY = "idempotency-clinical-psych-01"


def onet_source() -> EvidenceSource:
    """Return current O*NET 30.3 provenance for the clinical psychologist job."""
    return EvidenceSource(
        source_uri="https://www.onetcenter.org/database.html",
        source_title="O*NET 30.3 Clinical and Counseling Psychologists",
        source_version_code="onet:30.3",
        retrieved_at=RETRIEVED_AT,
        content_digest_sha256=ONET_DIGEST,
        origin_code="authoritative_occupation_source",
    )


def sme_source() -> EvidenceSource:
    """Return hospital SME provenance for local 임상심리사 duties."""
    return EvidenceSource(
        source_uri="https://www.opm.gov/policy-data-oversight/assessment-and-selection/job-analysis/",
        source_title="Hospital clinical-psychologist SME review",
        source_version_code="sme:2026-08",
        retrieved_at=RETRIEVED_AT,
        content_digest_sha256=ONET_DIGEST,
        origin_code="supervisor_sme",
    )


def clinical_psychologist_snapshot() -> JobAnalysisSnapshot:
    """Return a realistic validated 임상심리사 snapshot used for round-trip tests."""
    return JobAnalysisSnapshot(
        analysis_record_id=ANALYSIS,
        tenant_record_id=TENANT,
        job_record_id=JOB,
        analysis_version_code="clinical-psychologist:v1",
        status_code="analysis_validated",
        effective_from=date(2026, 8, 1),
        recorded_at=RECORDED_AT,
        tasks=(
            TaskEvidence(
                tenant_record_id=TENANT,
                job_record_id=JOB,
                task_record_id=TASK_ASSESS,
                task_statement="표준화된 심리검사를 실시하고 결과를 해석하여 진단 가설을 정리한다.",
                importance_level=5,
                difficulty_level=4,
                source=onet_source(),
            ),
            TaskEvidence(
                tenant_record_id=TENANT,
                job_record_id=JOB,
                task_record_id=TASK_THERAPY,
                task_statement="근거기반 심리치료를 계획하고 회기별 개입을 수행한다.",
                importance_level=5,
                difficulty_level=5,
                source=sme_source(),
            ),
            TaskEvidence(
                tenant_record_id=TENANT,
                job_record_id=JOB,
                task_record_id=TASK_HUDDLE,
                task_statement="다학제 사례회의에서 평가 근거와 위험 요인을 보고한다.",
                importance_level=4,
                difficulty_level=3,
                source=sme_source(),
            ),
        ),
        ksao_requirements=(
            KSAORequirement(
                tenant_record_id=TENANT,
                job_record_id=JOB,
                ksao_record_id=KSAO_KNOWLEDGE,
                category_code="knowledge_requirement",
                requirement_statement="DSM-5-TR 진단 기준과 심리측정 이론에 대한 지식.",
                importance_level=5,
                proficiency_level=4,
                source=onet_source(),
            ),
            KSAORequirement(
                tenant_record_id=TENANT,
                job_record_id=JOB,
                ksao_record_id=KSAO_SKILL,
                category_code="skill_requirement",
                requirement_statement="임상면담과 표준화 검사 배터리를 구성하는 기술.",
                importance_level=5,
                proficiency_level=5,
                source=sme_source(),
            ),
            KSAORequirement(
                tenant_record_id=TENANT,
                job_record_id=JOB,
                ksao_record_id=KSAO_ABILITY,
                category_code="ability_requirement",
                requirement_statement="복합 사례를 개념화하고 평가 근거를 연결하는 능력.",
                importance_level=5,
                proficiency_level=4,
                source=sme_source(),
            ),
        ),
        task_ksao_links=(
            TaskKSAOLink(TASK_ASSESS, KSAO_KNOWLEDGE, 5, True),
            TaskKSAOLink(TASK_ASSESS, KSAO_SKILL, 5, True),
            TaskKSAOLink(TASK_THERAPY, KSAO_SKILL, 5, True),
            TaskKSAOLink(TASK_THERAPY, KSAO_ABILITY, 4, True),
            TaskKSAOLink(TASK_HUDDLE, KSAO_KNOWLEDGE, 4, True),
            TaskKSAOLink(TASK_HUDDLE, KSAO_ABILITY, 5, True),
        ),
        fja_profile=FunctionalJobAnalysisProfile(
            tenant_record_id=TENANT,
            job_record_id=JOB,
            data_function_code=1,
            people_function_code=0,
            things_function_code=7,
            source=EvidenceSource(
                source_uri="https://www.dol.gov/agencies/oalj/PUBLIC/DOT/REFERENCES/DOTAPPB",
                source_title="Dictionary of Occupational Titles Appendix B",
                source_version_code="dot:1991",
                retrieved_at=RETRIEVED_AT,
                content_digest_sha256=DOT_DIGEST,
                origin_code="authoritative_occupation_source",
            ),
        ),
        reviewed_by_reference="keyverse_subject:01JCLINICALSME",
        reviewed_at=REVIEWED_AT,
    )


def clinical_psychologist_document() -> dict[str, object]:
    """Return the posted payload buyers persist for 임상심리사 직무분석."""
    return clinical_psychologist_snapshot().to_snapshot()


def write_principal() -> AuthenticatedPrincipal:
    """Return one actor authorized to persist job-analysis evidence."""
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:actor-ja-1",
        granted_scope_codes=frozenset({"orgmetra.job_architecture.write"}),
    )


def read_principal() -> AuthenticatedPrincipal:
    """Return one actor authorized to read job-analysis evidence."""
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:actor-ja-1",
        granted_scope_codes=frozenset({"orgmetra.job_architecture.read"}),
    )


def write_policy() -> PurposeBoundAccessPolicy:
    """Return the purpose-bound write policy for job-analysis snapshots."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="ja-write-v1",
        resource_kind="job_analysis_snapshot",
        purpose_code="job_analysis_write",
        operation_code="write_record",
        required_scope_code="orgmetra.job_architecture.write",
        permitted_fields=frozenset(
            {
                "analysis_record_id",
                "tenant_record_id",
                "job_record_id",
                "analysis_version_code",
                "status_code",
                "effective_from",
                "recorded_at",
                "tasks",
                "ksao_requirements",
                "task_ksao_links",
                "fja_profile",
                "reviewed_by_reference",
                "reviewed_at",
                "idempotency_key",
            }
        ),
    )


def read_policy() -> PurposeBoundAccessPolicy:
    """Return the purpose-bound read policy for job-analysis snapshots."""
    return PurposeBoundAccessPolicy(
        tenant_record_id=TENANT,
        policy_version_code="ja-read-v1",
        resource_kind="job_analysis_snapshot",
        purpose_code="job_analysis_read",
        operation_code="read_record",
        required_scope_code="orgmetra.job_architecture.read",
        permitted_fields=frozenset(
            {
                "analysis_record_id",
                "tenant_record_id",
                "job_record_id",
                "analysis_version_code",
                "status_code",
                "effective_from",
                "recorded_at",
                "tasks",
                "ksao_requirements",
                "task_ksao_links",
                "fja_profile",
                "reviewed_by_reference",
                "reviewed_at",
            }
        ),
    )
