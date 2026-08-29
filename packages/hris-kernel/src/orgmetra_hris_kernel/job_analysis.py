"""Versioned, evidence-grounded job-analysis contracts for Orgmetra.

The contract keeps Job distinct from Position and Assignment. It captures
observable tasks, KSAO requirements, Functional Job Analysis (FJA) worker
functions, and explicit task-to-KSAO linkages without making an employment
decision. LLM-origin material may exist only in draft snapshots; validated
snapshots require accountable human review and non-LLM evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from urllib.parse import urlsplit
from uuid import UUID

_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9._~-]+$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_ORIGINS = frozenset(
    {
        "authoritative_occupation_source",
        "job_incumbent",
        "supervisor_sme",
        "occupational_expert",
        "web_research",
        "llm_draft",
    }
)
_ALLOWED_KSAO_CATEGORIES = frozenset(
    {
        "knowledge_requirement",
        "skill_requirement",
        "ability_requirement",
        "other_characteristic",
    }
)
_ALLOWED_STATUS_CODES = frozenset({"analysis_draft", "analysis_validated"})


def _validate_uuid(value: object, field_name: str) -> UUID:
    """Return a durable UUID or reject type-confused and sentinel identities."""
    if type(value) is not UUID:
        raise ValueError(f"{field_name} must be a UUID")
    if value.int == 0:
        raise ValueError(f"{field_name} must not be the nil UUID")
    if value.int == (1 << 128) - 1:
        raise ValueError(f"{field_name} must not be the max UUID")
    return value


def _validate_code(value: object, field_name: str) -> str:
    """Return a two-or-more-word lower snake_case contract code."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string")
    if not _CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a two-or-more-word snake_case code")
    return value


def _validate_reference(value: object, field_name: str) -> str:
    """Return a namespaced opaque reference instead of human-readable identity data."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string")
    if not _REFERENCE_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a namespaced opaque reference")
    return value


def _validate_version(value: object, field_name: str) -> str:
    """Return a compact immutable version token."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string")
    if not _VERSION_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a compact version token")
    return value


def _validate_text(value: object, field_name: str, *, minimum: int = 1) -> str:
    """Return normalized nonblank explanatory text without changing its meaning."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string")
    normalized = " ".join(value.split())
    if len(normalized) < minimum:
        raise ValueError(f"{field_name} is too short")
    return normalized


def _validate_level(value: object, field_name: str) -> int:
    """Return an ordinal 1..5 job-analysis rating."""
    if type(value) is not int:
        raise ValueError(f"{field_name} must be an integer")
    if not 1 <= value <= 5:
        raise ValueError(f"{field_name} must be between 1 and 5")
    return value


def _validate_aware_datetime(value: object, field_name: str) -> datetime:
    """Detach one exact offset-aware instant as immutable UTC evidence."""
    if type(value) is not datetime:
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    try:
        offset = value.utcoffset()
    except Exception as exc:  # noqa: BLE001 - normalize provider behavior at trust boundary.
        raise ValueError(f"{field_name} must resolve to a UTC offset") from exc
    if offset is None or type(offset) is not timedelta:
        raise ValueError(f"{field_name} must resolve to a UTC offset")
    try:
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except OverflowError as exc:
        raise ValueError(f"{field_name} must be a representable timezone-aware datetime") from exc


def _utc_text(value: datetime) -> str:
    """Serialize a previously detached built-in UTC instant as canonical text."""
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError("datetime must be an exact timezone-aware datetime")
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """Immutable provenance for one external or human job-analysis evidence item."""

    source_uri: str
    source_title: str
    source_version_code: str
    retrieved_at: datetime
    content_digest_sha256: str
    origin_code: str

    def __post_init__(self) -> None:
        """Reject ambiguous, credential-bearing, mutable, or untyped provenance."""
        if type(self.source_uri) is not str:
            raise ValueError("source_uri must be a string")
        parsed = urlsplit(self.source_uri)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("source_uri must be an absolute HTTPS URI")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("source_uri must not contain credentials")
        object.__setattr__(
            self,
            "source_title",
            _validate_text(self.source_title, "source_title", minimum=3),
        )
        _validate_version(self.source_version_code, "source_version_code")
        object.__setattr__(
            self,
            "retrieved_at",
            _validate_aware_datetime(self.retrieved_at, "retrieved_at"),
        )
        if type(self.content_digest_sha256) is not str:
            raise ValueError("content_digest_sha256 must be a string")
        if not _SHA256_PATTERN.fullmatch(self.content_digest_sha256):
            raise ValueError("content_digest_sha256 must be 64 lowercase hexadecimal characters")
        _validate_code(self.origin_code, "origin_code")
        if self.origin_code not in _ALLOWED_ORIGINS:
            raise ValueError("origin_code is not an allowed job-analysis evidence origin")


@dataclass(frozen=True, slots=True)
class TaskEvidence:
    """One observable job task with importance, difficulty, and provenance."""

    tenant_record_id: UUID
    job_record_id: UUID
    task_record_id: UUID
    task_statement: str
    importance_level: int
    difficulty_level: int
    source: EvidenceSource

    def __post_init__(self) -> None:
        """Validate task identity, readable behavior text, ratings, and evidence."""
        _validate_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_uuid(self.job_record_id, "job_record_id")
        _validate_uuid(self.task_record_id, "task_record_id")
        object.__setattr__(
            self,
            "task_statement",
            _validate_text(self.task_statement, "task_statement", minimum=10),
        )
        _validate_level(self.importance_level, "importance_level")
        _validate_level(self.difficulty_level, "difficulty_level")
        if type(self.source) is not EvidenceSource:
            raise ValueError("source must be EvidenceSource")


@dataclass(frozen=True, slots=True)
class KSAORequirement:
    """One knowledge, skill, ability, or other-characteristic requirement."""

    tenant_record_id: UUID
    job_record_id: UUID
    ksao_record_id: UUID
    category_code: str
    requirement_statement: str
    importance_level: int
    proficiency_level: int
    source: EvidenceSource

    def __post_init__(self) -> None:
        """Validate KSAO identity, category, operational statement, and ratings."""
        _validate_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_uuid(self.job_record_id, "job_record_id")
        _validate_uuid(self.ksao_record_id, "ksao_record_id")
        _validate_code(self.category_code, "category_code")
        if self.category_code not in _ALLOWED_KSAO_CATEGORIES:
            raise ValueError("category_code is not an allowed KSAO category")
        object.__setattr__(
            self,
            "requirement_statement",
            _validate_text(self.requirement_statement, "requirement_statement", minimum=10),
        )
        _validate_level(self.importance_level, "importance_level")
        _validate_level(self.proficiency_level, "proficiency_level")
        if type(self.source) is not EvidenceSource:
            raise ValueError("source must be EvidenceSource")


@dataclass(frozen=True, slots=True)
class FunctionalJobAnalysisProfile:
    """Historical FJA-compatible Data/People/Things worker-function profile.

    Lower worker-function numbers indicate the broader/more complex function in
    the archived U.S. Department of Labor DOT vocabulary. The profile is kept
    as a compatibility descriptor, not as a substitute for current O*NET data.
    """

    tenant_record_id: UUID
    job_record_id: UUID
    data_function_code: int
    people_function_code: int
    things_function_code: int
    source: EvidenceSource

    def __post_init__(self) -> None:
        """Validate the archived DOT worker-function code ranges and provenance."""
        _validate_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_uuid(self.job_record_id, "job_record_id")
        for value, field_name, maximum in (
            (self.data_function_code, "data_function_code", 6),
            (self.people_function_code, "people_function_code", 8),
            (self.things_function_code, "things_function_code", 7),
        ):
            if type(value) is not int:
                raise ValueError(f"{field_name} must be an integer")
            if not 0 <= value <= maximum:
                raise ValueError(f"{field_name} must be between 0 and {maximum}")
        if type(self.source) is not EvidenceSource:
            raise ValueError("source must be EvidenceSource")


@dataclass(frozen=True, slots=True)
class TaskKSAOLink:
    """Evidence that one KSAO supports performance of one observable task."""

    task_record_id: UUID
    ksao_record_id: UUID
    relationship_strength: int
    essential_for_task: bool

    def __post_init__(self) -> None:
        """Validate link identities and the explicit 1..5 relationship rating."""
        _validate_uuid(self.task_record_id, "task_record_id")
        _validate_uuid(self.ksao_record_id, "ksao_record_id")
        _validate_level(self.relationship_strength, "relationship_strength")
        if type(self.essential_for_task) is not bool:
            raise ValueError("essential_for_task must be a bool")


@dataclass(frozen=True, slots=True)
class JobAnalysisSnapshot:
    """One immutable, reviewable version of evidence about a Job.

    A validated snapshot is suitable as evidence input to later selection-
    validity work. It is not itself a hiring, promotion, termination, or other
    high-impact employment decision.
    """

    analysis_record_id: UUID
    tenant_record_id: UUID
    job_record_id: UUID
    analysis_version_code: str
    status_code: str
    effective_from: date
    recorded_at: datetime
    tasks: tuple[TaskEvidence, ...]
    ksao_requirements: tuple[KSAORequirement, ...]
    task_ksao_links: tuple[TaskKSAOLink, ...]
    fja_profile: FunctionalJobAnalysisProfile
    reviewed_by_reference: str | None = None
    reviewed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Enforce tenant/job scope, linkage completeness, and review governance."""
        _validate_uuid(self.analysis_record_id, "analysis_record_id")
        _validate_uuid(self.tenant_record_id, "tenant_record_id")
        _validate_uuid(self.job_record_id, "job_record_id")
        _validate_version(self.analysis_version_code, "analysis_version_code")
        _validate_code(self.status_code, "status_code")
        if self.status_code not in _ALLOWED_STATUS_CODES:
            raise ValueError("status_code is not an allowed analysis status")
        if type(self.effective_from) is not date:
            raise ValueError("effective_from must be a date")
        recorded_at = _validate_aware_datetime(self.recorded_at, "recorded_at")
        object.__setattr__(self, "recorded_at", recorded_at)
        if type(self.tasks) is not tuple or not self.tasks:
            raise ValueError("tasks must be a non-empty tuple")
        if type(self.ksao_requirements) is not tuple or not self.ksao_requirements:
            raise ValueError("ksao_requirements must be a non-empty tuple")
        if type(self.task_ksao_links) is not tuple or not self.task_ksao_links:
            raise ValueError("task_ksao_links must be a non-empty tuple")
        if type(self.fja_profile) is not FunctionalJobAnalysisProfile:
            raise ValueError("fja_profile must be FunctionalJobAnalysisProfile")

        for task in self.tasks:
            if type(task) is not TaskEvidence:
                raise ValueError("tasks must contain TaskEvidence values")
        for item in self.ksao_requirements:
            if type(item) is not KSAORequirement:
                raise ValueError("ksao_requirements must contain KSAORequirement values")

        for item in (*self.tasks, *self.ksao_requirements, self.fja_profile):
            if item.tenant_record_id != self.tenant_record_id:
                raise ValueError("all job-analysis evidence must share tenant_record_id")
            if item.job_record_id != self.job_record_id:
                raise ValueError("all job-analysis evidence must share job_record_id")

        sources = [
            *(task.source for task in self.tasks),
            *(item.source for item in self.ksao_requirements),
            self.fja_profile.source,
        ]
        if any(source.retrieved_at > recorded_at for source in sources):
            raise ValueError("retrieved_at must not be later than recorded_at")

        task_ids = [task.task_record_id for task in self.tasks]
        ksao_ids = [item.ksao_record_id for item in self.ksao_requirements]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("task_record_id values must be unique")
        if len(ksao_ids) != len(set(ksao_ids)):
            raise ValueError("ksao_record_id values must be unique")

        task_id_set = set(task_ids)
        ksao_id_set = set(ksao_ids)
        link_pairs: set[tuple[UUID, UUID]] = set()
        for link in self.task_ksao_links:
            if type(link) is not TaskKSAOLink:
                raise ValueError("task_ksao_links must contain TaskKSAOLink values")
            if link.task_record_id not in task_id_set:
                raise ValueError("task_ksao_links contains an unknown task_record_id")
            if link.ksao_record_id not in ksao_id_set:
                raise ValueError("task_ksao_links contains an unknown ksao_record_id")
            link_pair = (link.task_record_id, link.ksao_record_id)
            if link_pair in link_pairs:
                raise ValueError("task_ksao_links must not duplicate a task and KSAO pair")
            link_pairs.add(link_pair)

        review_pair_present = (
            self.reviewed_by_reference is not None,
            self.reviewed_at is not None,
        )
        if review_pair_present[0] != review_pair_present[1]:
            raise ValueError("reviewed_by_reference and reviewed_at must be supplied together")
        if self.reviewed_by_reference is not None:
            _validate_reference(self.reviewed_by_reference, "reviewed_by_reference")
            reviewed_at = _validate_aware_datetime(self.reviewed_at, "reviewed_at")
            object.__setattr__(self, "reviewed_at", reviewed_at)
            if reviewed_at > recorded_at:
                raise ValueError("reviewed_at must not be later than recorded_at")
            if any(source.retrieved_at > reviewed_at for source in sources):
                raise ValueError("reviewed_at must not be earlier than evidence retrieval")

        if self.status_code == "analysis_validated":
            if self.reviewed_by_reference is None:
                raise ValueError("validated analysis requires accountable human review")
            linked_task_ids = {link.task_record_id for link in self.task_ksao_links}
            linked_ksao_ids = {link.ksao_record_id for link in self.task_ksao_links}
            if linked_task_ids != task_id_set:
                raise ValueError("validated analysis must link every task to at least one KSAO")
            if linked_ksao_ids != ksao_id_set:
                raise ValueError("validated analysis must link every KSAO to at least one task")
            if any(source.origin_code == "llm_draft" for source in sources):
                raise ValueError("LLM-origin evidence must remain analysis_draft")

    def to_snapshot(self) -> dict[str, object]:
        """Return a deterministic, provenance-complete job-analysis document."""
        tasks = sorted(self.tasks, key=lambda item: str(item.task_record_id))
        ksaos = sorted(self.ksao_requirements, key=lambda item: str(item.ksao_record_id))
        links = sorted(
            self.task_ksao_links,
            key=lambda item: (str(item.task_record_id), str(item.ksao_record_id)),
        )
        document: dict[str, object] = {
            "analysis_record_id": str(self.analysis_record_id),
            "tenant_record_id": str(self.tenant_record_id),
            "job_record_id": str(self.job_record_id),
            "analysis_version_code": self.analysis_version_code,
            "status_code": self.status_code,
            "effective_from": self.effective_from.isoformat(),
            "recorded_at": _utc_text(self.recorded_at),
            "tasks": [
                {
                    "task_record_id": str(task.task_record_id),
                    "task_statement": task.task_statement,
                    "importance_level": task.importance_level,
                    "difficulty_level": task.difficulty_level,
                    "source": _source_document(task.source),
                }
                for task in tasks
            ],
            "ksao_requirements": [
                {
                    "ksao_record_id": str(item.ksao_record_id),
                    "category_code": item.category_code,
                    "requirement_statement": item.requirement_statement,
                    "importance_level": item.importance_level,
                    "proficiency_level": item.proficiency_level,
                    "source": _source_document(item.source),
                }
                for item in ksaos
            ],
            "task_ksao_links": [
                {
                    "task_record_id": str(link.task_record_id),
                    "ksao_record_id": str(link.ksao_record_id),
                    "relationship_strength": link.relationship_strength,
                    "essential_for_task": link.essential_for_task,
                }
                for link in links
            ],
            "fja_profile": {
                "data_function_code": self.fja_profile.data_function_code,
                "people_function_code": self.fja_profile.people_function_code,
                "things_function_code": self.fja_profile.things_function_code,
                "source": _source_document(self.fja_profile.source),
            },
        }
        if self.reviewed_by_reference is not None:
            document["reviewed_by_reference"] = self.reviewed_by_reference
            document["reviewed_at"] = _utc_text(self.reviewed_at)
        return document

    def canonical_json(self) -> str:
        """Return the exact deterministic UTF-8 JSON text used for version evidence."""
        return json.dumps(
            self.to_snapshot(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def content_digest(self) -> str:
        """Return SHA-256 for the exact canonical job-analysis snapshot bytes."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _source_document(source: EvidenceSource) -> dict[str, object]:
    """Return deterministic source provenance without copying external source content."""
    return {
        "source_uri": source.source_uri,
        "source_title": source.source_title,
        "source_version_code": source.source_version_code,
        "retrieved_at": _utc_text(source.retrieved_at),
        "content_digest_sha256": source.content_digest_sha256,
        "origin_code": source.origin_code,
    }
