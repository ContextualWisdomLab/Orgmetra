"""Runtime-type integrity for canonical job-analysis evidence."""

from __future__ import annotations

from datetime import date, datetime, timezone
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
RECORDED_AT = datetime(2026, 8, 21, 5, 15, tzinfo=timezone.utc)


class _ForgedUUID(UUID):
    """Attempt to forge an identity written into canonical job-analysis evidence."""

    def __str__(self) -> str:
        """Render a different identity from the underlying UUID value."""
        return "00000000-0000-4000-8000-ffffffffffff"


class _ForgedDate(date):
    """Attempt to forge the business date written into canonical evidence."""

    def isoformat(self) -> str:
        """Render a different business date from the underlying value."""
        return "2099-01-01"


class _ForgedDateTime(datetime):
    """Attempt to forge a recorded instant written into canonical evidence."""

    def astimezone(self, tz=None):  # noqa: ANN001
        """Preserve the hostile runtime type through UTC normalization."""
        return self

    def isoformat(self, sep="T", timespec="auto") -> str:  # noqa: ARG002
        """Render a different recorded instant from the underlying value."""
        return "2099-01-01T00:00:00+00:00"


def _source(retrieved_at: datetime) -> EvidenceSource:
    """Build one governed source record."""
    return EvidenceSource(
        source_uri="https://www.onetcenter.org/database.html",
        source_title="O*NET Database",
        source_version_code="onet:30.3",
        retrieved_at=retrieved_at,
        content_digest_sha256="b" * 64,
        origin_code="authoritative_occupation_source",
    )


def _snapshot(*, effective_from: date, recorded_at: datetime, reviewed_at: datetime) -> JobAnalysisSnapshot:
    """Build one otherwise-valid validated snapshot around supplied temporal evidence."""
    source = _source(datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc))
    return JobAnalysisSnapshot(
        analysis_record_id=ANALYSIS_ID,
        tenant_record_id=TENANT_ID,
        job_record_id=JOB_ID,
        analysis_version_code="analysis:v1",
        status_code="analysis_validated",
        effective_from=effective_from,
        recorded_at=recorded_at,
        tasks=(
            TaskEvidence(
                tenant_record_id=TENANT_ID,
                job_record_id=JOB_ID,
                task_record_id=TASK_ID,
                task_statement="Analyze governed workforce evidence and document findings.",
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
                requirement_statement="Knowledge of governed workforce evidence and traceability.",
                importance_level=5,
                proficiency_level=4,
                source=source,
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
            source=source,
        ),
        reviewed_by_reference="keyverse_subject:01JIOPSYCH",
        reviewed_at=reviewed_at,
    )


def test_job_analysis_rejects_uuid_subclasses_before_identity_canonicalization() -> None:
    """Caller-controlled UUID rendering cannot rewrite task/link evidence identity."""
    forged = _ForgedUUID("00000000-0000-4000-8000-000000002004")
    with pytest.raises(ValueError, match="task_record_id must be a UUID"):
        TaskKSAOLink(
            task_record_id=forged,
            ksao_record_id=KSAO_ID,
            relationship_strength=5,
            essential_for_task=True,
        )


def test_evidence_source_rejects_datetime_subclass_before_provenance_canonicalization() -> None:
    """Reject caller-controlled timestamp rendering at the source-provenance boundary."""
    forged = _ForgedDateTime(2026, 8, 21, 5, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="retrieved_at must be a datetime"):
        _source(forged)


@pytest.mark.parametrize(
    ("effective_from", "recorded_at", "reviewed_at"),
    [
        (_ForgedDate(2026, 8, 1), RECORDED_AT, RECORDED_AT),
        (date(2026, 8, 1), _ForgedDateTime(2026, 8, 21, 5, 15, tzinfo=timezone.utc), RECORDED_AT),
        (date(2026, 8, 1), RECORDED_AT, _ForgedDateTime(2026, 8, 21, 5, 15, tzinfo=timezone.utc)),
    ],
)
def test_snapshot_rejects_temporal_subclasses_before_canonicalization(
    effective_from: date,
    recorded_at: datetime,
    reviewed_at: datetime,
) -> None:
    """Reject business/recorded-time objects whose methods can rewrite immutable evidence."""
    with pytest.raises(ValueError):
        _snapshot(
            effective_from=effective_from,
            recorded_at=recorded_at,
            reviewed_at=reviewed_at,
        )
