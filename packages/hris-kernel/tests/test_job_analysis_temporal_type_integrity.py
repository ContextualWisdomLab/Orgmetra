"""Runtime-type integrity for canonical job-analysis evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone, tzinfo
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


class _ForgedStatusCode(str):
    """Masquerade an ungoverned status as an allow-listed draft status."""

    def __hash__(self) -> int:
        """Route membership lookup to the allowed draft-status bucket."""
        return hash("analysis_draft")

    def __eq__(self, other: object) -> bool:
        """Claim equality with the allowed draft status despite different text."""
        if other == "analysis_draft":
            return True
        return str.__eq__(self, other)


class _ForgedOriginCode(str):
    """Masquerade ungoverned provenance as an allow-listed evidence origin."""

    def __hash__(self) -> int:
        """Route membership lookup to the authoritative-origin bucket."""
        return hash("authoritative_occupation_source")

    def __eq__(self, other: object) -> bool:
        """Claim equality with an authoritative origin despite different text."""
        if other == "authoritative_occupation_source":
            return True
        return str.__eq__(self, other)


class _ForgedLevel(int):
    """Masquerade an out-of-range ordinal as an allowed job-analysis level."""

    def __ge__(self, other: object) -> bool:
        """Forge the lower-bound comparison used by the level validator."""
        return True

    def __le__(self, other: object) -> bool:
        """Forge the upper-bound comparison used by the level validator."""
        return True

    def __lt__(self, other: object) -> bool:
        """Keep adversarial ordering behavior internally consistent."""
        return True

    def __gt__(self, other: object) -> bool:
        """Keep adversarial ordering behavior internally consistent."""
        return True


class _OpaqueText(str):
    """Represent valid evidence text through an untrusted runtime subclass."""


class _TaskEvidenceSubclass(TaskEvidence):
    """Represent a valid task through an untrusted runtime subclass."""


class _KSAORequirementSubclass(KSAORequirement):
    """Represent a valid KSAO requirement through an untrusted runtime subclass."""


class _MutableOffset(tzinfo):
    """Expose timezone state that can change after evidence construction."""

    def __init__(self) -> None:
        """Start with a UTC offset."""
        self.offset = timedelta(0)

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Return the currently configured offset."""
        del value
        return self.offset

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed."""
        del value
        return timedelta(0)


class _ExplodingOffset(tzinfo):
    """Raise arbitrary provider behavior while an evidence instant is resolved."""

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Force the trust boundary to normalize provider failures."""
        del value
        raise RuntimeError("provider details must not escape")

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed if queried."""
        del value
        return timedelta(0)


class _OversizedOffset(tzinfo):
    """Return an extreme offset that cannot be detached from year one."""

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Force UTC detachment outside representable datetime values."""
        del value
        return timedelta(hours=23, minutes=59)

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed."""
        del value
        return timedelta(0)


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
    ("field_name", "value"),
    [
        ("source_uri", _OpaqueText("https://www.onetcenter.org/database.html")),
        ("source_title", _OpaqueText("O*NET Database")),
        ("source_version_code", _OpaqueText("onet:30.3")),
        ("content_digest_sha256", _OpaqueText("b" * 64)),
    ],
)
def test_evidence_source_rejects_string_subclasses_before_canonicalization(
    field_name: str, value: str
) -> None:
    """Reject caller-controlled string behavior in source provenance fields."""
    source = _source(datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="must be"):
        replace(source, **{field_name: value})


def test_snapshot_rejects_reference_string_subclasses_before_canonicalization() -> None:
    """Reject caller-controlled runtime behavior in accountable review references."""
    snapshot = _snapshot(
        effective_from=date(2026, 8, 1),
        recorded_at=RECORDED_AT,
        reviewed_at=RECORDED_AT,
    )
    with pytest.raises(ValueError, match="reviewed_by_reference must be a string"):
        replace(snapshot, reviewed_by_reference=_OpaqueText("keyverse_subject:01JIOPSYCH"))


def test_snapshot_rejects_task_and_ksao_subclasses_before_canonicalization() -> None:
    """Reject nested evidence subclasses before their fields reach canonical serialization."""
    snapshot = _snapshot(
        effective_from=date(2026, 8, 1),
        recorded_at=RECORDED_AT,
        reviewed_at=RECORDED_AT,
    )
    task = snapshot.tasks[0]
    forged_task = _TaskEvidenceSubclass(
        tenant_record_id=task.tenant_record_id,
        job_record_id=task.job_record_id,
        task_record_id=task.task_record_id,
        task_statement=task.task_statement,
        importance_level=task.importance_level,
        difficulty_level=task.difficulty_level,
        source=task.source,
    )
    with pytest.raises(ValueError, match="tasks must contain TaskEvidence"):
        replace(snapshot, tasks=(forged_task,))

    ksao = snapshot.ksao_requirements[0]
    forged_ksao = _KSAORequirementSubclass(
        tenant_record_id=ksao.tenant_record_id,
        job_record_id=ksao.job_record_id,
        ksao_record_id=ksao.ksao_record_id,
        category_code=ksao.category_code,
        requirement_statement=ksao.requirement_statement,
        importance_level=ksao.importance_level,
        proficiency_level=ksao.proficiency_level,
        source=ksao.source,
    )
    with pytest.raises(ValueError, match="ksao_requirements must contain KSAORequirement"):
        replace(snapshot, ksao_requirements=(forged_ksao,))


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


def test_snapshot_rejects_status_subclass_that_forges_allow_list_membership() -> None:
    """An ungoverned status cannot masquerade as draft while serializing different text."""
    snapshot = _snapshot(
        effective_from=date(2026, 8, 1),
        recorded_at=RECORDED_AT,
        reviewed_at=RECORDED_AT,
    )
    with pytest.raises(ValueError, match="status_code must be a string"):
        replace(snapshot, status_code=_ForgedStatusCode("shadow_state"))


def test_evidence_source_rejects_origin_subclass_that_forges_allow_list_membership() -> None:
    """Provenance classification cannot pass as authoritative under different serialized text."""
    source = _source(datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="origin_code must be a string"):
        replace(source, origin_code=_ForgedOriginCode("shadow_origin"))


def test_evidence_source_detaches_mutable_timezone_state() -> None:
    """Keep source provenance chronology stable after timezone state mutates."""
    zone = _MutableOffset()
    source = _source(datetime(2026, 8, 21, 5, 0, tzinfo=zone))
    first = source.retrieved_at

    zone.offset = timedelta(hours=9)

    assert source.retrieved_at == first
    assert source.retrieved_at.tzinfo is timezone.utc


def test_snapshot_detaches_mutable_timezone_state() -> None:
    """Keep snapshot chronology stable after caller-owned timezone state mutates."""
    zone = _MutableOffset()
    snapshot = _snapshot(
        effective_from=date(2026, 8, 1),
        recorded_at=datetime(2026, 8, 21, 5, 15, tzinfo=zone),
        reviewed_at=RECORDED_AT,
    )
    first = snapshot.to_snapshot()

    zone.offset = timedelta(hours=9)

    assert snapshot.recorded_at.tzinfo is timezone.utc
    assert snapshot.to_snapshot() == first


def test_evidence_source_normalizes_timezone_provider_exceptions() -> None:
    """Do not leak arbitrary timezone-provider exceptions from source construction."""
    with pytest.raises(ValueError, match="retrieved_at must resolve to a UTC offset"):
        _source(datetime(2026, 8, 21, 5, 0, tzinfo=_ExplodingOffset()))


def test_evidence_source_normalizes_offset_overflow_to_value_error() -> None:
    """Fail closed when UTC detachment exceeds representable datetime values."""
    with pytest.raises(ValueError, match="retrieved_at must be a representable"):
        _source(datetime(1, 1, 1, 0, 0, tzinfo=_OversizedOffset()))


def test_snapshot_canonicalization_rejects_reintroduced_timezone_behavior() -> None:
    """Fail closed if low-level mutation reintroduces executable timezone behavior."""
    snapshot = _snapshot(
        effective_from=date(2026, 8, 1),
        recorded_at=RECORDED_AT,
        reviewed_at=RECORDED_AT,
    )
    object.__setattr__(
        snapshot,
        "recorded_at",
        datetime(2026, 8, 21, 5, 15, tzinfo=_MutableOffset()),
    )
    with pytest.raises(ValueError, match="exact timezone-aware datetime"):
        snapshot.to_snapshot()


def test_task_rejects_integer_subclass_that_forges_level_bounds() -> None:
    """Out-of-range ordinal evidence cannot override comparisons and serialize as valid."""
    source = _source(datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="importance_level must be an integer"):
        TaskEvidence(
            tenant_record_id=TENANT_ID,
            job_record_id=JOB_ID,
            task_record_id=TASK_ID,
            task_statement="Analyze governed workforce evidence and document findings.",
            importance_level=_ForgedLevel(99),
            difficulty_level=4,
            source=source,
        )
