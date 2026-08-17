import json
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

TENANT_ID = UUID("00000000-0000-4000-8000-000000001001")
JOB_ID = UUID("00000000-0000-4000-8000-000000001002")
ANALYSIS_ID = UUID("00000000-0000-4000-8000-000000001003")
TASK_ID = UUID("00000000-0000-4000-8000-000000001004")
KSAO_ID = UUID("00000000-0000-4000-8000-000000001005")
OTHER_ID = UUID("00000000-0000-4000-8000-000000001006")
RECORDED_AT = datetime(2026, 8, 17, 4, 0, tzinfo=timezone.utc)
DIGEST = "a" * 64


def _source(**overrides):
    values = {
        "source_uri": "https://www.onetcenter.org/database.html",
        "source_title": "O*NET 30.3 Database",
        "source_version_code": "onet:30.3",
        "retrieved_at": RECORDED_AT - timedelta(hours=1),
        "content_digest_sha256": DIGEST,
        "origin_code": "authoritative_occupation_source",
    }
    values.update(overrides)
    return EvidenceSource(**values)


def _task(**overrides):
    values = {
        "tenant_record_id": TENANT_ID,
        "job_record_id": JOB_ID,
        "task_record_id": TASK_ID,
        "task_statement": "Analyze governed workforce data and document decision evidence.",
        "importance_level": 5,
        "difficulty_level": 4,
        "source": _source(),
    }
    values.update(overrides)
    return TaskEvidence(**values)


def _ksao(**overrides):
    values = {
        "tenant_record_id": TENANT_ID,
        "job_record_id": JOB_ID,
        "ksao_record_id": KSAO_ID,
        "category_code": "knowledge_requirement",
        "requirement_statement": "Knowledge of data governance controls and evidence traceability.",
        "importance_level": 5,
        "proficiency_level": 4,
        "source": _source(),
    }
    values.update(overrides)
    return KSAORequirement(**values)


def _fja(**overrides):
    values = {
        "tenant_record_id": TENANT_ID,
        "job_record_id": JOB_ID,
        "data_function_code": 2,
        "people_function_code": 1,
        "things_function_code": 7,
        "source": _source(
            source_uri="https://www.dol.gov/agencies/oalj/PUBLIC/DOT/REFERENCES/DOTAPPB",
            source_title="Dictionary of Occupational Titles Appendix B",
            source_version_code="dot:1991",
        ),
    }
    values.update(overrides)
    return FunctionalJobAnalysisProfile(**values)


def _link(**overrides):
    values = {
        "task_record_id": TASK_ID,
        "ksao_record_id": KSAO_ID,
        "relationship_strength": 5,
        "essential_for_task": True,
    }
    values.update(overrides)
    return TaskKSAOLink(**values)


def _snapshot(**overrides):
    values = {
        "analysis_record_id": ANALYSIS_ID,
        "tenant_record_id": TENANT_ID,
        "job_record_id": JOB_ID,
        "analysis_version_code": "analysis:v1",
        "status_code": "analysis_validated",
        "effective_from": date(2026, 8, 1),
        "recorded_at": RECORDED_AT,
        "tasks": (_task(),),
        "ksao_requirements": (_ksao(),),
        "task_ksao_links": (_link(),),
        "fja_profile": _fja(),
        "reviewed_by_reference": "keyverse_subject:01JIOPSYCH",
        "reviewed_at": RECORDED_AT - timedelta(minutes=1),
    }
    values.update(overrides)
    return JobAnalysisSnapshot(**values)


def test_validated_snapshot_is_deterministic_and_evidence_complete():
    snapshot = _snapshot()
    document = snapshot.to_snapshot()

    assert document["status_code"] == "analysis_validated"
    assert document["tasks"][0]["importance_level"] == 5
    assert document["ksao_requirements"][0]["category_code"] == "knowledge_requirement"
    assert document["fja_profile"] == {
        "data_function_code": 2,
        "people_function_code": 1,
        "things_function_code": 7,
        "source": {
            "source_uri": "https://www.dol.gov/agencies/oalj/PUBLIC/DOT/REFERENCES/DOTAPPB",
            "source_title": "Dictionary of Occupational Titles Appendix B",
            "source_version_code": "dot:1991",
            "retrieved_at": "2026-08-17T03:00:00Z",
            "content_digest_sha256": DIGEST,
            "origin_code": "authoritative_occupation_source",
        },
    }
    assert document["reviewed_by_reference"] == "keyverse_subject:01JIOPSYCH"
    assert document["reviewed_at"] == "2026-08-17T03:59:00Z"
    assert json.loads(snapshot.canonical_json()) == document
    assert len(snapshot.content_digest()) == 64
    assert snapshot.content_digest() == snapshot.content_digest()


def test_canonical_snapshot_sorts_semantically_identical_inputs():
    task_two = _task(
        task_record_id=OTHER_ID,
        task_statement="Review job-analysis evidence with accountable subject-matter experts.",
    )
    ksao_two = _ksao(
        ksao_record_id=OTHER_ID,
        category_code="skill_requirement",
        requirement_statement="Skill in evaluating evidence quality and job relevance.",
    )
    links = (
        _link(task_record_id=OTHER_ID, ksao_record_id=OTHER_ID),
        _link(),
    )
    forward = _snapshot(
        tasks=(_task(), task_two),
        ksao_requirements=(_ksao(), ksao_two),
        task_ksao_links=links,
    )
    reverse = _snapshot(
        tasks=(task_two, _task()),
        ksao_requirements=(ksao_two, _ksao()),
        task_ksao_links=tuple(reversed(links)),
    )
    assert forward.canonical_json() == reverse.canonical_json()


def test_draft_snapshot_can_hold_untrusted_llm_evidence_without_human_review():
    draft_source = _source(origin_code="llm_draft")
    snapshot = _snapshot(
        status_code="analysis_draft",
        tasks=(_task(source=draft_source),),
        reviewed_by_reference=None,
        reviewed_at=None,
    )
    document = snapshot.to_snapshot()

    assert "reviewed_by_reference" not in document
    assert "reviewed_at" not in document
    assert document["tasks"][0]["source"]["origin_code"] == "llm_draft"


def test_validated_snapshot_rejects_llm_origin_from_any_evidence_lane():
    llm_source = _source(origin_code="llm_draft")
    variants = [
        {"tasks": (_task(source=llm_source),)},
        {"ksao_requirements": (_ksao(source=llm_source),)},
        {"fja_profile": _fja(source=llm_source)},
    ]
    for overrides in variants:
        with pytest.raises(ValueError, match="LLM-origin"):
            _snapshot(**overrides)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"reviewed_by_reference": None, "reviewed_at": None}, "human review"),
        ({"tasks": (_task(tenant_record_id=OTHER_ID),)}, "tenant_record_id"),
        ({"ksao_requirements": (_ksao(job_record_id=OTHER_ID),)}, "job_record_id"),
        ({"fja_profile": _fja(tenant_record_id=OTHER_ID)}, "tenant_record_id"),
        ({"tasks": (_task(), _task())}, "task_record_id values must be unique"),
        ({"ksao_requirements": (_ksao(), _ksao())}, "ksao_record_id values must be unique"),
        ({"task_ksao_links": (_link(task_record_id=OTHER_ID),)}, "unknown task_record_id"),
        ({"task_ksao_links": (_link(ksao_record_id=OTHER_ID),)}, "unknown ksao_record_id"),
        ({"tasks": (_task(), _task(task_record_id=OTHER_ID, task_statement="Document another important observable work behavior for this job.")), "task_ksao_links": (_link(),)}, "link every task"),
        ({"ksao_requirements": (_ksao(), _ksao(ksao_record_id=OTHER_ID, category_code="skill_requirement", requirement_statement="Skill in another important work requirement for this job.")), "task_ksao_links": (_link(),)}, "link every KSAO"),
    ],
)
def test_validated_snapshot_fails_closed_on_scope_or_linkage_gaps(overrides, message):
    with pytest.raises(ValueError, match=message):
        _snapshot(**overrides)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"analysis_record_id": str(ANALYSIS_ID)}, "must be a UUID"),
        ({"analysis_record_id": UUID(int=0)}, "nil UUID"),
        ({"analysis_record_id": UUID(int=(1 << 128) - 1)}, "max UUID"),
        ({"analysis_version_code": "analysis version 1"}, "version token"),
        ({"analysis_version_code": 7}, "must be a string"),
        ({"status_code": "validated"}, "snake_case"),
        ({"status_code": "analysis_retired"}, "allowed analysis status"),
        ({"effective_from": RECORDED_AT}, "must be a date"),
        ({"recorded_at": "now"}, "must be a datetime"),
        ({"recorded_at": datetime(2026, 8, 17, 4, 0)}, "timezone-aware"),
        ({"tasks": []}, "non-empty tuple"),
        ({"tasks": ()}, "non-empty tuple"),
        ({"ksao_requirements": []}, "non-empty tuple"),
        ({"task_ksao_links": []}, "non-empty tuple"),
        ({"fja_profile": "2-1-7"}, "FunctionalJobAnalysisProfile"),
        ({"task_ksao_links": ("bad",)}, "TaskKSAOLink"),
        ({"reviewed_by_reference": None}, "supplied together"),
        ({"reviewed_at": None}, "supplied together"),
        ({"reviewed_by_reference": "Ada Lovelace"}, "opaque reference"),
        ({"reviewed_by_reference": 7}, "must be a string"),
        ({"reviewed_at": RECORDED_AT + timedelta(seconds=1)}, "not be later"),
    ],
)
def test_snapshot_rejects_ambiguous_or_malformed_contract_material(overrides, message):
    values = {
        "reviewed_by_reference": "keyverse_subject:01JIOPSYCH",
        "reviewed_at": RECORDED_AT - timedelta(minutes=1),
    }
    values.update(overrides)
    with pytest.raises(ValueError, match=message):
        _snapshot(**values)


@pytest.mark.parametrize(
    ("builder", "overrides", "message"),
    [
        (_source, {"source_uri": 7}, "must be a string"),
        (_source, {"source_uri": "http://example.com/source"}, "absolute HTTPS"),
        (_source, {"source_uri": "https://user:secret@example.com/source"}, "must not contain credentials"),
        (_source, {"source_title": "  "}, "too short"),
        (_source, {"source_title": 7}, "must be a string"),
        (_source, {"source_version_code": "version 1"}, "version token"),
        (_source, {"retrieved_at": "now"}, "must be a datetime"),
        (_source, {"content_digest_sha256": 7}, "must be a string"),
        (_source, {"content_digest_sha256": "A" * 64}, "64 lowercase"),
        (_source, {"origin_code": "manual"}, "snake_case"),
        (_source, {"origin_code": "unknown_source"}, "allowed job-analysis evidence origin"),
        (_task, {"task_statement": "short"}, "too short"),
        (_task, {"importance_level": True}, "must be an integer"),
        (_task, {"difficulty_level": 6}, "between 1 and 5"),
        (_task, {"source": "O*NET"}, "EvidenceSource"),
        (_ksao, {"category_code": "Knowledge"}, "snake_case"),
        (_ksao, {"category_code": 7}, "must be a string"),
        (_ksao, {"category_code": "physical_requirement"}, "allowed KSAO"),
        (_ksao, {"requirement_statement": "short"}, "too short"),
        (_ksao, {"proficiency_level": 0}, "between 1 and 5"),
        (_ksao, {"source": None}, "EvidenceSource"),
        (_fja, {"data_function_code": True}, "must be an integer"),
        (_fja, {"data_function_code": 7}, "between 0 and 6"),
        (_fja, {"people_function_code": 9}, "between 0 and 8"),
        (_fja, {"things_function_code": 8}, "between 0 and 7"),
        (_fja, {"source": None}, "EvidenceSource"),
        (_link, {"relationship_strength": 0}, "between 1 and 5"),
        (_link, {"essential_for_task": 1}, "must be a bool"),
    ],
)
def test_component_contracts_reject_invalid_evidence(builder, overrides, message):
    with pytest.raises(ValueError, match=message):
        builder(**overrides)


def test_source_title_normalizes_whitespace_without_altering_words():
    source = _source(source_title="  O*NET   30.3\nDatabase  ")
    assert source.source_title == "O*NET 30.3 Database"


def test_job_analysis_accepts_all_supported_ksao_categories_and_fja_boundaries():
    categories = (
        "knowledge_requirement",
        "skill_requirement",
        "ability_requirement",
        "other_characteristic",
    )
    for category in categories:
        assert _ksao(category_code=category).category_code == category

    low = _fja(data_function_code=0, people_function_code=0, things_function_code=0)
    high = _fja(data_function_code=6, people_function_code=8, things_function_code=7)
    assert (low.data_function_code, low.people_function_code, low.things_function_code) == (0, 0, 0)
    assert (high.data_function_code, high.people_function_code, high.things_function_code) == (6, 8, 7)


def test_unresolved_timezone_is_rejected_for_source_snapshot_and_review():
    class UnresolvedTimezone(tzinfo):
        def utcoffset(self, dt):
            return None

    bad_time = datetime(2026, 8, 17, 4, 0, tzinfo=UnresolvedTimezone())
    with pytest.raises(ValueError, match="resolve to a UTC offset"):
        _source(retrieved_at=bad_time)
    with pytest.raises(ValueError, match="resolve to a UTC offset"):
        _snapshot(recorded_at=bad_time)
    with pytest.raises(ValueError, match="resolve to a UTC offset"):
        _snapshot(reviewed_at=bad_time)
