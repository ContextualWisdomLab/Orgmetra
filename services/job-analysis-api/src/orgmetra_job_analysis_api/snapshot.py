"""Governed persist and read path for one job-analysis snapshot.

Authorization happens before the write or read port is invoked. The posted
document is rebuilt through ``JobAnalysisSnapshot`` so kernel evidence rules
cannot be bypassed by persistence. The write port must receive the caller
Idempotency-Key; a replay with a different digest fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from orgmetra_hris_kernel import (
    AuditOutboxEvent,
    EvidenceSource,
    FunctionalJobAnalysisProfile,
    JobAnalysisSnapshot,
    KSAORequirement,
    TaskEvidence,
    TaskKSAOLink,
)
from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy

from orgmetra_job_analysis_api.auth import AuthenticatedPrincipal
from orgmetra_job_analysis_api.authorization import authorize_resource_fields

_MAX_UUID_INT = (1 << 128) - 1
_IDEMPOTENCY_MIN = 16
_IDEMPOTENCY_MAX = 200
_MAX_TASKS = 500
_MAX_KSAOS = 500
_MAX_TASK_KSAO_LINKS = 5000
_SNAPSHOT_FIELDS = frozenset(
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
)
_SOURCE_FIELDS = frozenset(
    {
        "source_uri",
        "source_title",
        "source_version_code",
        "retrieved_at",
        "content_digest_sha256",
        "origin_code",
    }
)
_TASK_FIELDS = frozenset(
    {
        "task_record_id",
        "task_statement",
        "importance_level",
        "difficulty_level",
        "source",
    }
)
_KSAO_FIELDS = frozenset(
    {
        "ksao_record_id",
        "category_code",
        "requirement_statement",
        "importance_level",
        "proficiency_level",
        "source",
    }
)
_TASK_KSAO_LINK_FIELDS = frozenset(
    {
        "task_record_id",
        "ksao_record_id",
        "relationship_strength",
        "essential_for_task",
    }
)
_FJA_FIELDS = frozenset(
    {
        "data_function_code",
        "people_function_code",
        "things_function_code",
        "source",
    }
)
_WRITE_FIELDS = _SNAPSHOT_FIELDS | frozenset({"idempotency_key"})


class JobAnalysisSnapshotNotFound(LookupError):
    """Indicate that the authorized snapshot target has no persisted record."""


class JobAnalysisIntegrityError(RuntimeError):
    """Indicate that persistence returned data outside the authorized snapshot."""


class JobAnalysisScopeMissing(LookupError):
    """Indicate that a required job, position, or criterion parent is absent."""


class JobAnalysisIdempotencyConflict(ValueError):
    """Indicate that an Idempotency-Key is already bound to different content."""


def _reject_unknown_fields(
    boundary_name: str,
    value: dict[object, object],
    allowed_fields: frozenset[str],
) -> None:
    """Reject object members that the published evidence contract does not own."""
    if any(type(key) is not str for key in value):
        raise ValueError(f"{boundary_name} field names must be exact built-in text.")
    unknown_fields = sorted(key for key in value if key not in allowed_fields)
    if unknown_fields:
        raise ValueError(
            f"{boundary_name} contains unsupported fields: {', '.join(unknown_fields)}."
        )


def _exact_text(field_name: str, value: object) -> str:
    """Return inert caller text before domain validators may normalize or match it."""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be exact built-in text.")
    return value


def _exact_integer(field_name: str, value: object) -> int:
    """Return an inert integer before domain validators perform ordinal comparisons."""
    if type(value) is not int:
        raise ValueError(f"{field_name} must be an exact built-in integer.")
    return value


def _exact_boolean(field_name: str, value: object) -> bool:
    """Return an exact boolean for a trust-bearing posted flag."""
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be an exact built-in boolean.")
    return value


def validate_operational_uuid(field_name: str, value: object) -> UUID:
    """Return a detached exact UUID after validating operational identity evidence."""
    if type(value) is not UUID:
        raise ValueError(f"{field_name} must be an operational UUID.")
    value_int = value.int
    if type(value_int) is not int or not 0 < value_int < _MAX_UUID_INT:
        raise ValueError(f"{field_name} must be an operational UUID.")
    return UUID(int=value_int)


def _validate_idempotency_key(value: object) -> str:
    """Require the exact caller Idempotency-Key that must reach the write port."""
    if type(value) is not str or not (_IDEMPOTENCY_MIN <= len(value) <= _IDEMPOTENCY_MAX):
        raise ValueError("idempotency_key must be 16 to 200 characters.")
    if any(ord(character) < 0x21 or ord(character) > 0x7E for character in value):
        raise ValueError("idempotency_key must be printable ASCII.")
    return value


def _parse_uuid(field_name: str, value: object) -> UUID:
    """Parse one posted UUID string or reject a non-operational identity."""
    if type(value) is UUID:
        return validate_operational_uuid(field_name, value)
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a UUID string.")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a UUID string.") from error
    return validate_operational_uuid(field_name, parsed)


def _parse_aware_datetime(field_name: str, value: object) -> datetime:
    """Parse one posted UTC instant used as evidence time."""
    if type(value) is datetime:
        if value.tzinfo is None:
            raise ValueError(f"{field_name} must be timezone-aware.")
        if type(value.tzinfo) is not timezone:
            raise ValueError(f"{field_name} must use a fixed UTC offset.")
        if value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware.")
        return value
    if type(value) is not str:
        raise ValueError(f"{field_name} must be an ISO-8601 datetime.")
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO-8601 datetime.") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return parsed


def _parse_business_date(field_name: str, value: object) -> date:
    """Parse one posted business date without accepting a datetime."""
    if type(value) is datetime:
        raise ValueError(f"{field_name} must be a date.")
    if type(value) is date:
        return value
    if type(value) is not str:
        raise ValueError(f"{field_name} must be an ISO business date.")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO business date.") from error


def _parse_source(value: object) -> EvidenceSource:
    """Rebuild one evidence source from posted provenance fields."""
    if type(value) is not dict:
        raise ValueError("source must be an object.")
    _reject_unknown_fields("source", value, _SOURCE_FIELDS)
    return EvidenceSource(
        source_uri=_exact_text("source_uri", value.get("source_uri")),
        source_title=_exact_text("source_title", value.get("source_title")),
        source_version_code=_exact_text(
            "source_version_code",
            value.get("source_version_code"),
        ),
        retrieved_at=_parse_aware_datetime("retrieved_at", value.get("retrieved_at")),
        content_digest_sha256=_exact_text(
            "content_digest_sha256",
            value.get("content_digest_sha256"),
        ),
        origin_code=_exact_text("origin_code", value.get("origin_code")),
    )


def snapshot_from_document(
    document: object,
    *,
    tenant_record_id: UUID,
) -> JobAnalysisSnapshot:
    """Rebuild one kernel snapshot from a posted JSON document.

    The posted tenant must match the authorized route tenant. Kernel constructors
    then enforce linkage completeness, provenance, and review governance.
    """
    if type(document) is not dict:
        raise ValueError("snapshot document must be an object.")
    _reject_unknown_fields("snapshot document", document, _SNAPSHOT_FIELDS)
    posted_tenant = _parse_uuid("tenant_record_id", document.get("tenant_record_id"))
    if posted_tenant != tenant_record_id:
        raise ValueError("snapshot tenant_record_id must match the authorized tenant.")
    job_record_id = _parse_uuid("job_record_id", document.get("job_record_id"))
    raw_tasks = document.get("tasks")
    raw_ksaos = document.get("ksao_requirements")
    raw_links = document.get("task_ksao_links")
    raw_fja = document.get("fja_profile")
    if type(raw_tasks) is not list or not raw_tasks:
        raise ValueError("tasks must be a non-empty list.")
    if len(raw_tasks) > _MAX_TASKS:
        raise ValueError(f"tasks must contain at most {_MAX_TASKS} items.")
    if type(raw_ksaos) is not list or not raw_ksaos:
        raise ValueError("ksao_requirements must be a non-empty list.")
    if len(raw_ksaos) > _MAX_KSAOS:
        raise ValueError(f"ksao_requirements must contain at most {_MAX_KSAOS} items.")
    if type(raw_links) is not list or not raw_links:
        raise ValueError("task_ksao_links must be a non-empty list.")
    if len(raw_links) > _MAX_TASK_KSAO_LINKS:
        raise ValueError(
            f"task_ksao_links must contain at most {_MAX_TASK_KSAO_LINKS} items."
        )
    if type(raw_fja) is not dict:
        raise ValueError("fja_profile must be an object.")
    _reject_unknown_fields("fja_profile", raw_fja, _FJA_FIELDS)
    tasks = []
    for item in raw_tasks:
        if type(item) is not dict:
            raise ValueError("tasks must contain objects.")
        _reject_unknown_fields("task", item, _TASK_FIELDS)
        tasks.append(
            TaskEvidence(
                tenant_record_id=tenant_record_id,
                job_record_id=job_record_id,
                task_record_id=_parse_uuid("task_record_id", item.get("task_record_id")),
                task_statement=_exact_text("task_statement", item.get("task_statement")),
                importance_level=_exact_integer(
                    "importance_level",
                    item.get("importance_level"),
                ),
                difficulty_level=_exact_integer(
                    "difficulty_level",
                    item.get("difficulty_level"),
                ),
                source=_parse_source(item.get("source")),
            )
        )
    ksaos = []
    for item in raw_ksaos:
        if type(item) is not dict:
            raise ValueError("ksao_requirements must contain objects.")
        _reject_unknown_fields("ksao_requirement", item, _KSAO_FIELDS)
        ksaos.append(
            KSAORequirement(
                tenant_record_id=tenant_record_id,
                job_record_id=job_record_id,
                ksao_record_id=_parse_uuid("ksao_record_id", item.get("ksao_record_id")),
                category_code=_exact_text("category_code", item.get("category_code")),
                requirement_statement=_exact_text(
                    "requirement_statement",
                    item.get("requirement_statement"),
                ),
                importance_level=_exact_integer(
                    "importance_level",
                    item.get("importance_level"),
                ),
                proficiency_level=_exact_integer(
                    "proficiency_level",
                    item.get("proficiency_level"),
                ),
                source=_parse_source(item.get("source")),
            )
        )
    links = []
    for item in raw_links:
        if type(item) is not dict:
            raise ValueError("task_ksao_links must contain objects.")
        _reject_unknown_fields("task_ksao_link", item, _TASK_KSAO_LINK_FIELDS)
        links.append(
            TaskKSAOLink(
                task_record_id=_parse_uuid("task_record_id", item.get("task_record_id")),
                ksao_record_id=_parse_uuid("ksao_record_id", item.get("ksao_record_id")),
                relationship_strength=_exact_integer(
                    "relationship_strength",
                    item.get("relationship_strength"),
                ),
                essential_for_task=_exact_boolean(
                    "essential_for_task",
                    item.get("essential_for_task"),
                ),
            )
        )
    reviewed_by_reference = document.get("reviewed_by_reference")
    reviewed_at = document.get("reviewed_at")
    return JobAnalysisSnapshot(
        analysis_record_id=_parse_uuid("analysis_record_id", document.get("analysis_record_id")),
        tenant_record_id=tenant_record_id,
        job_record_id=job_record_id,
        analysis_version_code=_exact_text(
            "analysis_version_code",
            document.get("analysis_version_code"),
        ),
        status_code=_exact_text("status_code", document.get("status_code")),
        effective_from=_parse_business_date("effective_from", document.get("effective_from")),
        recorded_at=_parse_aware_datetime("recorded_at", document.get("recorded_at")),
        tasks=tuple(tasks),
        ksao_requirements=tuple(ksaos),
        task_ksao_links=tuple(links),
        fja_profile=FunctionalJobAnalysisProfile(
            tenant_record_id=tenant_record_id,
            job_record_id=job_record_id,
            data_function_code=_exact_integer(
                "data_function_code",
                raw_fja.get("data_function_code"),
            ),
            people_function_code=_exact_integer(
                "people_function_code",
                raw_fja.get("people_function_code"),
            ),
            things_function_code=_exact_integer(
                "things_function_code",
                raw_fja.get("things_function_code"),
            ),
            source=_parse_source(raw_fja.get("source")),
        ),
        reviewed_by_reference=(
            None
            if reviewed_by_reference is None
            else _exact_text("reviewed_by_reference", reviewed_by_reference)
        ),
        reviewed_at=None if reviewed_at is None else _parse_aware_datetime("reviewed_at", reviewed_at),
    )


def command_digest(
    *,
    snapshot: JobAnalysisSnapshot,
    position_record_id: UUID | None,
    criterion_blueprint_id: UUID | None,
) -> str:
    """Return SHA-256 over the exact snapshot bytes plus optional scope identities."""
    if type(snapshot) is not JobAnalysisSnapshot:
        raise TypeError("snapshot must be an exact JobAnalysisSnapshot")
    payload = {
        "criterion_blueprint_id": None if criterion_blueprint_id is None else str(criterion_blueprint_id),
        "position_record_id": None if position_record_id is None else str(position_record_id),
        "snapshot": json.loads(snapshot.canonical_json()),
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _optional_scope_id(field_name: str, value: object) -> UUID | None:
    """Accept an omitted optional parent identity or require an operational UUID."""
    if value is None:
        return None
    return _parse_uuid(field_name, value)


def _resolved_exact(field_name: str, value: object, expected_type: type[object]) -> object:
    """Require one inert exact runtime value returned by a snapshot read adapter."""
    if type(value) is not expected_type:
        raise JobAnalysisIntegrityError(
            f"resolved snapshot graph has invalid runtime evidence at {field_name}"
        )
    return value


def _resolved_uuid(field_name: str, value: object) -> UUID:
    """Require one operational exact UUID before snapshot export can stringify it."""
    try:
        return validate_operational_uuid(field_name, value)
    except ValueError as error:
        raise JobAnalysisIntegrityError(
            f"resolved snapshot graph has invalid runtime evidence at {field_name}"
        ) from error


def _resolved_datetime(field_name: str, value: object) -> datetime:
    """Require an exact standard-library datetime before canonicalization can use it."""
    resolved = _resolved_exact(field_name, value, datetime)
    assert type(resolved) is datetime
    if type(resolved.tzinfo) not in (timezone, ZoneInfo):
        raise JobAnalysisIntegrityError(
            f"resolved snapshot graph has invalid runtime evidence at {field_name}"
        )
    return resolved


def _resolved_datetime_text(field_name: str, value: object) -> str:
    """Capture one inert returned instant as the kernel's canonical UTC text."""
    resolved = _resolved_datetime(field_name, value)
    return resolved.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_resolved_source_runtime(
    field_name: str,
    value: object,
) -> dict[str, object]:
    """Capture one returned provenance object into validated inert evidence."""
    source = _resolved_exact(field_name, value, EvidenceSource)
    assert type(source) is EvidenceSource
    source_uri = _resolved_exact(f"{field_name}.source_uri", source.source_uri, str)
    source_title = _resolved_exact(f"{field_name}.source_title", source.source_title, str)
    source_version_code = _resolved_exact(
        f"{field_name}.source_version_code",
        source.source_version_code,
        str,
    )
    retrieved_at = _resolved_datetime_text(
        f"{field_name}.retrieved_at",
        source.retrieved_at,
    )
    content_digest_sha256 = _resolved_exact(
        f"{field_name}.content_digest_sha256",
        source.content_digest_sha256,
        str,
    )
    origin_code = _resolved_exact(f"{field_name}.origin_code", source.origin_code, str)
    return {
        "source_uri": source_uri,
        "source_title": source_title,
        "source_version_code": source_version_code,
        "retrieved_at": retrieved_at,
        "content_digest_sha256": content_digest_sha256,
        "origin_code": origin_code,
    }


def _validate_resolved_owner_runtime(
    field_name: str,
    *,
    tenant_record_id: object,
    job_record_id: object,
    expected_tenant_record_id: UUID,
    expected_job_record_id: UUID,
) -> None:
    """Require returned nested evidence to retain the detached root ownership pair."""
    resolved_tenant_record_id = _resolved_uuid(
        f"{field_name}.tenant_record_id",
        tenant_record_id,
    )
    resolved_job_record_id = _resolved_uuid(
        f"{field_name}.job_record_id",
        job_record_id,
    )
    if (
        resolved_tenant_record_id != expected_tenant_record_id
        or resolved_job_record_id != expected_job_record_id
    ):
        raise JobAnalysisIntegrityError(
            f"resolved snapshot graph ownership mismatch at {field_name}"
        )


def _validate_resolved_snapshot_graph_runtime(
    snapshot: JobAnalysisSnapshot,
) -> tuple[UUID, UUID, dict[str, object]]:
    """Capture target/root ownership and validated evidence into the document to emit."""
    tenant_record_id = _resolved_uuid("tenant_record_id", snapshot.tenant_record_id)
    analysis_record_id = _resolved_uuid("analysis_record_id", snapshot.analysis_record_id)
    job_record_id = _resolved_uuid("job_record_id", snapshot.job_record_id)
    analysis_version_code = _resolved_exact(
        "analysis_version_code",
        snapshot.analysis_version_code,
        str,
    )
    status_code = _resolved_exact("status_code", snapshot.status_code, str)
    effective_from = _resolved_exact("effective_from", snapshot.effective_from, date)
    assert type(effective_from) is date
    recorded_at = _resolved_datetime_text("recorded_at", snapshot.recorded_at)

    tasks = _resolved_exact("tasks", snapshot.tasks, tuple)
    ksaos = _resolved_exact("ksao_requirements", snapshot.ksao_requirements, tuple)
    links = _resolved_exact("task_ksao_links", snapshot.task_ksao_links, tuple)
    assert type(tasks) is tuple
    assert type(ksaos) is tuple
    assert type(links) is tuple

    task_entries: list[tuple[str, dict[str, object]]] = []
    for index, task_value in enumerate(tasks):
        task = _resolved_exact(f"tasks[{index}]", task_value, TaskEvidence)
        assert type(task) is TaskEvidence
        _validate_resolved_owner_runtime(
            f"tasks[{index}]",
            tenant_record_id=task.tenant_record_id,
            job_record_id=task.job_record_id,
            expected_tenant_record_id=tenant_record_id,
            expected_job_record_id=job_record_id,
        )
        task_record_id = _resolved_uuid(
            f"tasks[{index}].task_record_id",
            task.task_record_id,
        )
        task_statement = _resolved_exact(
            f"tasks[{index}].task_statement",
            task.task_statement,
            str,
        )
        importance_level = _resolved_exact(
            f"tasks[{index}].importance_level",
            task.importance_level,
            int,
        )
        difficulty_level = _resolved_exact(
            f"tasks[{index}].difficulty_level",
            task.difficulty_level,
            int,
        )
        task_record_id_text = str(task_record_id)
        task_entries.append(
            (
                task_record_id_text,
                {
                    "task_record_id": task_record_id_text,
                    "task_statement": task_statement,
                    "importance_level": importance_level,
                    "difficulty_level": difficulty_level,
                    "source": _validate_resolved_source_runtime(
                        f"tasks[{index}].source",
                        task.source,
                    ),
                },
            )
        )

    ksao_entries: list[tuple[str, dict[str, object]]] = []
    for index, ksao_value in enumerate(ksaos):
        ksao = _resolved_exact(
            f"ksao_requirements[{index}]",
            ksao_value,
            KSAORequirement,
        )
        assert type(ksao) is KSAORequirement
        _validate_resolved_owner_runtime(
            f"ksao_requirements[{index}]",
            tenant_record_id=ksao.tenant_record_id,
            job_record_id=ksao.job_record_id,
            expected_tenant_record_id=tenant_record_id,
            expected_job_record_id=job_record_id,
        )
        ksao_record_id = _resolved_uuid(
            f"ksao_requirements[{index}].ksao_record_id",
            ksao.ksao_record_id,
        )
        category_code = _resolved_exact(
            f"ksao_requirements[{index}].category_code",
            ksao.category_code,
            str,
        )
        requirement_statement = _resolved_exact(
            f"ksao_requirements[{index}].requirement_statement",
            ksao.requirement_statement,
            str,
        )
        importance_level = _resolved_exact(
            f"ksao_requirements[{index}].importance_level",
            ksao.importance_level,
            int,
        )
        proficiency_level = _resolved_exact(
            f"ksao_requirements[{index}].proficiency_level",
            ksao.proficiency_level,
            int,
        )
        ksao_record_id_text = str(ksao_record_id)
        ksao_entries.append(
            (
                ksao_record_id_text,
                {
                    "ksao_record_id": ksao_record_id_text,
                    "category_code": category_code,
                    "requirement_statement": requirement_statement,
                    "importance_level": importance_level,
                    "proficiency_level": proficiency_level,
                    "source": _validate_resolved_source_runtime(
                        f"ksao_requirements[{index}].source",
                        ksao.source,
                    ),
                },
            )
        )

    link_entries: list[tuple[tuple[str, str], dict[str, object]]] = []
    for index, link_value in enumerate(links):
        link = _resolved_exact(
            f"task_ksao_links[{index}]",
            link_value,
            TaskKSAOLink,
        )
        assert type(link) is TaskKSAOLink
        task_record_id = _resolved_uuid(
            f"task_ksao_links[{index}].task_record_id",
            link.task_record_id,
        )
        ksao_record_id = _resolved_uuid(
            f"task_ksao_links[{index}].ksao_record_id",
            link.ksao_record_id,
        )
        relationship_strength = _resolved_exact(
            f"task_ksao_links[{index}].relationship_strength",
            link.relationship_strength,
            int,
        )
        essential_for_task = _resolved_exact(
            f"task_ksao_links[{index}].essential_for_task",
            link.essential_for_task,
            bool,
        )
        task_record_id_text = str(task_record_id)
        ksao_record_id_text = str(ksao_record_id)
        link_entries.append(
            (
                (task_record_id_text, ksao_record_id_text),
                {
                    "task_record_id": task_record_id_text,
                    "ksao_record_id": ksao_record_id_text,
                    "relationship_strength": relationship_strength,
                    "essential_for_task": essential_for_task,
                },
            )
        )

    fja = _resolved_exact("fja_profile", snapshot.fja_profile, FunctionalJobAnalysisProfile)
    assert type(fja) is FunctionalJobAnalysisProfile
    _validate_resolved_owner_runtime(
        "fja_profile",
        tenant_record_id=fja.tenant_record_id,
        job_record_id=fja.job_record_id,
        expected_tenant_record_id=tenant_record_id,
        expected_job_record_id=job_record_id,
    )
    data_function_code = _resolved_exact(
        "fja_profile.data_function_code",
        fja.data_function_code,
        int,
    )
    people_function_code = _resolved_exact(
        "fja_profile.people_function_code",
        fja.people_function_code,
        int,
    )
    things_function_code = _resolved_exact(
        "fja_profile.things_function_code",
        fja.things_function_code,
        int,
    )
    fja_source = _validate_resolved_source_runtime("fja_profile.source", fja.source)

    reviewed_by_reference = snapshot.reviewed_by_reference
    reviewed_at = snapshot.reviewed_at
    document: dict[str, object] = {
        "job_record_id": str(job_record_id),
        "analysis_version_code": analysis_version_code,
        "status_code": status_code,
        "effective_from": effective_from.isoformat(),
        "recorded_at": recorded_at,
        "tasks": [
            item_document
            for _, item_document in sorted(task_entries, key=lambda item: item[0])
        ],
        "ksao_requirements": [
            item_document
            for _, item_document in sorted(ksao_entries, key=lambda item: item[0])
        ],
        "task_ksao_links": [
            item_document
            for _, item_document in sorted(link_entries, key=lambda item: item[0])
        ],
        "fja_profile": {
            "data_function_code": data_function_code,
            "people_function_code": people_function_code,
            "things_function_code": things_function_code,
            "source": fja_source,
        },
    }
    if reviewed_by_reference is not None:
        document["reviewed_by_reference"] = _resolved_exact(
            "reviewed_by_reference",
            reviewed_by_reference,
            str,
        )
    if reviewed_at is not None:
        document["reviewed_at"] = _resolved_datetime_text("reviewed_at", reviewed_at)
    return tenant_record_id, analysis_record_id, document


@runtime_checkable
class JobAnalysisWritePort(Protocol):
    """Persist one authorized snapshot and its Idempotency-Key in one transaction."""

    def persist_snapshot(
        self,
        *,
        snapshot: JobAnalysisSnapshot,
        idempotency_key: str,
        request_digest: str,
        actor_reference: str,
        purpose_code: str,
        position_record_id: UUID | None,
        criterion_blueprint_id: UUID | None,
        audit_event: AuditOutboxEvent,
        outbox_delivery_record_id: UUID,
        write_command_id: UUID,
    ) -> JobAnalysisSnapshot:
        """Write the snapshot or return the prior snapshot for the same command digest."""


@runtime_checkable
class JobAnalysisReadPort(Protocol):
    """Read one persisted snapshot under the caller's tenant transaction."""

    def read_snapshot(
        self,
        *,
        tenant_record_id: UUID,
        analysis_record_id: UUID,
    ) -> JobAnalysisSnapshot | None:
        """Resolve one snapshot by durable analysis identity."""


@dataclass(frozen=True, slots=True)
class PersistedJobAnalysisView:
    """Customer response containing the exact persisted snapshot document."""

    resource_reference: str
    snapshot: dict[str, object]


def persist_job_analysis_snapshot(
    *,
    principal: AuthenticatedPrincipal,
    tenant_record_id: UUID,
    document: object,
    idempotency_key: str,
    purpose_code: str,
    position_record_id: object = None,
    criterion_blueprint_id: object = None,
    policy: PurposeBoundAccessPolicy,
    write_port: JobAnalysisWritePort,
) -> PersistedJobAnalysisView:
    """Authorize, validate, and persist one snapshot without masking job evidence.

    The Idempotency-Key is validated here and passed unchanged to the write port.
    Job-analysis rows are occupational evidence, not person PII, so the authorized
    field set is the snapshot document itself rather than a masked subset.
    """
    tenant_record_id = validate_operational_uuid("tenant_record_id", tenant_record_id)
    key = _validate_idempotency_key(idempotency_key)
    snapshot = snapshot_from_document(document, tenant_record_id=tenant_record_id)
    position_id = _optional_scope_id("position_record_id", position_record_id)
    criterion_id = _optional_scope_id("criterion_blueprint_id", criterion_blueprint_id)
    resource_reference = f"job_analysis_snapshot:{snapshot.analysis_record_id.hex}"
    decision = authorize_resource_fields(
        principal=principal,
        tenant_record_id=tenant_record_id,
        resource_tenant_record_id=snapshot.tenant_record_id,
        resource_reference=resource_reference,
        purpose_code=purpose_code,
        operation_code="write_record",
        resource_kind="job_analysis_snapshot",
        requested_fields=_WRITE_FIELDS,
        policy=policy,
    )
    audit_event = AuditOutboxEvent(
        event_id=uuid4(),
        tenant_record_id=tenant_record_id,
        source_service="job_analysis_api",
        event_type="orgmetra.job_architecture.snapshot_recorded",
        resource_reference=resource_reference,
        actor_reference=principal.actor_reference,
        purpose_code=purpose_code,
        reason_code="snapshot_persisted",
        evidence_version_code=snapshot.analysis_version_code,
        result_code="recorded",
        occurred_at=datetime.now(timezone.utc),
        high_impact=False,
    )
    authorized_snapshot = snapshot.to_snapshot()
    authorized_analysis_record_id = validate_operational_uuid(
        "authorized snapshot analysis_record_id",
        snapshot.analysis_record_id,
    )
    persisted = write_port.persist_snapshot(
        snapshot=snapshot,
        idempotency_key=key,
        request_digest=command_digest(
            snapshot=snapshot,
            position_record_id=position_id,
            criterion_blueprint_id=criterion_id,
        ),
        actor_reference=principal.actor_reference,
        purpose_code=purpose_code,
        position_record_id=position_id,
        criterion_blueprint_id=criterion_id,
        audit_event=audit_event,
        outbox_delivery_record_id=uuid4(),
        write_command_id=uuid4(),
    )
    if type(persisted) is not JobAnalysisSnapshot:
        raise JobAnalysisIntegrityError("persisted snapshot has an invalid runtime type")
    try:
        persisted_tenant_record_id = validate_operational_uuid(
            "persisted snapshot tenant_record_id",
            persisted.tenant_record_id,
        )
        persisted_analysis_record_id = validate_operational_uuid(
            "persisted snapshot analysis_record_id",
            persisted.analysis_record_id,
        )
    except ValueError as error:
        raise JobAnalysisIntegrityError(
            "persisted snapshot graph has invalid runtime evidence"
        ) from error
    if (
        persisted_tenant_record_id != tenant_record_id
        or persisted_analysis_record_id != authorized_analysis_record_id
    ):
        raise JobAnalysisIntegrityError("persisted snapshot escaped posted payload")
    try:
        (
            captured_tenant_record_id,
            captured_analysis_record_id,
            persisted_graph,
        ) = _validate_resolved_snapshot_graph_runtime(persisted)
        if (
            captured_tenant_record_id != persisted_tenant_record_id
            or captured_analysis_record_id != persisted_analysis_record_id
        ):
            raise JobAnalysisIntegrityError(
                "persisted snapshot target changed during graph capture"
            )
    except JobAnalysisIntegrityError as error:
        raise JobAnalysisIntegrityError(
            "persisted snapshot graph has invalid runtime evidence"
        ) from error
    persisted_document = {
        "analysis_record_id": str(persisted_analysis_record_id),
        "tenant_record_id": str(persisted_tenant_record_id),
        **persisted_graph,
    }
    try:
        governed_persisted = snapshot_from_document(
            persisted_document,
            tenant_record_id=tenant_record_id,
        )
    except (TypeError, ValueError) as error:
        raise JobAnalysisIntegrityError(
            "persisted snapshot graph violates governed evidence contract"
        ) from error
    governed_document = governed_persisted.to_snapshot()
    if governed_document != persisted_document:
        raise JobAnalysisIntegrityError(
            "persisted snapshot graph changes under governed reconstruction"
        )
    if governed_document != authorized_snapshot:
        raise JobAnalysisIntegrityError("persisted snapshot escaped posted payload")
    return PersistedJobAnalysisView(
        resource_reference=decision.resource_reference,
        snapshot=authorized_snapshot,
    )


def read_job_analysis_snapshot(
    *,
    principal: AuthenticatedPrincipal,
    tenant_record_id: UUID,
    analysis_record_id: UUID,
    purpose_code: str,
    policy: PurposeBoundAccessPolicy,
    read_port: JobAnalysisReadPort,
) -> PersistedJobAnalysisView:
    """Authorize an exact snapshot target before reconstructing persisted evidence."""
    tenant_record_id = validate_operational_uuid("tenant_record_id", tenant_record_id)
    analysis_record_id = validate_operational_uuid("analysis_record_id", analysis_record_id)
    resource_reference = f"job_analysis_snapshot:{analysis_record_id.hex}"
    decision = authorize_resource_fields(
        principal=principal,
        tenant_record_id=tenant_record_id,
        resource_tenant_record_id=tenant_record_id,
        resource_reference=resource_reference,
        purpose_code=purpose_code,
        operation_code="read_record",
        resource_kind="job_analysis_snapshot",
        requested_fields=_SNAPSHOT_FIELDS,
        policy=policy,
    )
    snapshot = read_port.read_snapshot(
        tenant_record_id=tenant_record_id,
        analysis_record_id=analysis_record_id,
    )
    if snapshot is None:
        raise JobAnalysisSnapshotNotFound("job-analysis snapshot is unavailable")
    if type(snapshot) is not JobAnalysisSnapshot:
        raise JobAnalysisIntegrityError("resolved snapshot has an invalid runtime type")
    try:
        resolved_tenant_record_id = validate_operational_uuid(
            "resolved snapshot tenant_record_id",
            snapshot.tenant_record_id,
        )
        resolved_analysis_record_id = validate_operational_uuid(
            "resolved snapshot analysis_record_id",
            snapshot.analysis_record_id,
        )
    except ValueError as error:
        raise JobAnalysisIntegrityError("resolved snapshot target identity is invalid") from error
    if (
        resolved_tenant_record_id != tenant_record_id
        or resolved_analysis_record_id != analysis_record_id
    ):
        raise JobAnalysisIntegrityError("resolved snapshot does not match authorized target")

    (
        captured_tenant_record_id,
        captured_analysis_record_id,
        resolved_graph,
    ) = _validate_resolved_snapshot_graph_runtime(snapshot)
    if (
        captured_tenant_record_id != resolved_tenant_record_id
        or captured_analysis_record_id != resolved_analysis_record_id
    ):
        raise JobAnalysisIntegrityError("resolved snapshot target changed during graph capture")
    resolved_document = {
        "analysis_record_id": str(resolved_analysis_record_id),
        "tenant_record_id": str(resolved_tenant_record_id),
        **resolved_graph,
    }
    try:
        governed_snapshot = snapshot_from_document(
            resolved_document,
            tenant_record_id=tenant_record_id,
        )
    except (TypeError, ValueError) as error:
        raise JobAnalysisIntegrityError(
            "resolved snapshot graph violates governed evidence contract"
        ) from error
    governed_document = governed_snapshot.to_snapshot()
    if governed_document != resolved_document:
        raise JobAnalysisIntegrityError(
            "resolved snapshot graph changes under governed reconstruction"
        )
    return PersistedJobAnalysisView(
        resource_reference=decision.resource_reference,
        snapshot=governed_document,
    )
