"""Executable contract for governed performance-goal plan activation evidence."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone, tzinfo
import gc
import json
from uuid import uuid4
from weakref import ref as weak_ref

import pytest

from orgmetra_performance_goal_plan import (
    PerformanceGoalPlanPacket,
    build_performance_goal_plan_packet,
)

TENANT = "01890f3d-4d6a-7cc0-8a9d-9a83bb1cc001"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def ref(prefix: str) -> str:
    """Return one canonical UUIDv4 namespaced reference for a test."""
    return f"{prefix}:{uuid4()}"


def values() -> dict[str, object]:
    """Return one valid evidence payload."""
    return {
        "tenant_record_id": TENANT,
        "performance_goal_plan_reference": ref("performance_goal_plan"),
        "employment_record_reference": ref("employment_record"),
        "job_profile_reference": ref("job_profile"),
        "performance_cycle_reference": ref("performance_cycle"),
        "goal_set_digest": DIGEST_A,
        "measurement_definition_digest": DIGEST_B,
        "goal_count": 3,
        "feedback_cadence_code": "monthly_check_in",
        "requester_reference": ref("actor"),
        "reviewer_reference": ref("actor"),
        "purpose_code": "performance_goal_plan_review",
        "reason_code": "goal_plan_activation_review",
        "generated_at": datetime(2026, 8, 23, 1, 0, tzinfo=timezone.utc),
        "evidence_version": 1,
    }


def packet(**overrides: object) -> PerformanceGoalPlanPacket:
    """Build one valid packet with optional field overrides."""
    data = values()
    data.update(overrides)
    return build_performance_goal_plan_packet(**data)  # type: ignore[arg-type]


def test_builds_value_minimized_goal_plan_evidence() -> None:
    """A valid plan binds reviewed provenance without storing goal text or ratings."""
    item = packet()
    document = json.loads(item.canonical_json())
    assert repr(item) == "PerformanceGoalPlanPacket(<redacted>)"
    assert document["goal_count"] == 3
    assert document["review_state"] == "requires_human_review"
    assert document["decision_authority"] == "not_authorized_for_performance_rating"
    assert document["employment_decision_authority"] == "not_authorized_for_employment_decision"
    assert document["contains_goal_text"] is False
    assert document["contains_performance_rating"] is False
    assert document["contains_employment_decision"] is False
    assert "goal_text" not in document
    assert len(item.sha256_digest()) == 64


def test_canonicalizes_non_utc_timestamp_without_losing_precision() -> None:
    """Audit evidence normalizes offsets to UTC and preserves fractional precision."""
    instant = datetime(2026, 8, 23, 10, 30, 0, 123456, tzinfo=timezone(timedelta(hours=9)))
    document = json.loads(packet(generated_at=instant).canonical_json())
    assert document["generated_at"] == "2026-08-23T01:30:00.123456Z"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("tenant_record_id", "not-a-uuid"),
        ("performance_goal_plan_reference", "performance_goal_plan:6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
        ("employment_record_reference", "employment_record:not-a-uuid"),
        ("job_profile_reference", "wrong_namespace:01890f3d-4d6a-7cc0-8a9d-9a83bb1cc001"),
        ("performance_cycle_reference", "performance_cycle:00000000-0000-0000-0000-000000000000"),
        ("requester_reference", "actor:6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
        ("goal_set_digest", "A" * 64),
        ("measurement_definition_digest", "short"),
    ],
)
def test_rejects_invalid_identity_and_provenance_values(field_name: str, value: object) -> None:
    """Identity and digest evidence fails closed before canonical audit emission."""
    with pytest.raises(ValueError):
        packet(**{field_name: value})


@pytest.mark.parametrize("goal_count", [True, 0, 21])
def test_rejects_invalid_goal_count(goal_count: object) -> None:
    """A reviewed plan carries between one and twenty structured goals."""
    with pytest.raises(ValueError):
        packet(goal_count=goal_count)


@pytest.mark.parametrize("feedback_cadence_code", ["weekly", "monthly-check-in", "shadow_mode"])
def test_rejects_unreviewed_feedback_cadence(feedback_cadence_code: object) -> None:
    """Only the reviewed feedback cadence vocabulary enters durable evidence."""
    with pytest.raises(ValueError):
        packet(feedback_cadence_code=feedback_cadence_code)


def test_requires_distinct_requester_and_reviewer() -> None:
    """The accountable human reviewer must differ from the requester."""
    actor = ref("actor")
    with pytest.raises(ValueError):
        packet(requester_reference=actor, reviewer_reference=actor)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("purpose_code", "performance_rating_review"),
        ("reason_code", "goal_plan_auto_activation"),
        ("human_review_required", False),
        ("review_state", "human_review_complete"),
        ("decision_authority", "automated_rating"),
        ("employment_decision_authority", "authorized_for_termination"),
        ("contains_goal_text", True),
        ("contains_performance_rating", True),
        ("contains_employment_decision", True),
        ("next_action", "activate automatically"),
    ],
)
def test_rejects_governance_drift(field_name: str, value: object) -> None:
    """Direct construction cannot weaken human review or decision separation."""
    data = values()
    data[field_name] = value
    with pytest.raises(ValueError):
        PerformanceGoalPlanPacket(**data)  # type: ignore[arg-type]


@pytest.mark.parametrize("evidence_version", [True, 0, 2_147_483_648])
def test_rejects_invalid_evidence_version(evidence_version: object) -> None:
    """Evidence versions are positive bounded built-in integers."""
    with pytest.raises(ValueError):
        packet(evidence_version=evidence_version)


class OffsetlessTimezone(tzinfo):
    """Timezone fixture whose offset is deliberately undefined."""

    def utcoffset(self, dt: datetime | None) -> None:
        """Return no offset so the timestamp is not actually aware."""
        return None

    def dst(self, dt: datetime | None) -> None:
        """Return no daylight-saving offset."""
        return None


def test_rejects_naive_and_offsetless_timestamps() -> None:
    """System-recorded evidence requires a real timezone offset."""
    with pytest.raises(ValueError):
        packet(generated_at=datetime(2026, 8, 23, 1, 0))
    with pytest.raises(ValueError):
        packet(generated_at=datetime(2026, 8, 23, 1, 0, tzinfo=OffsetlessTimezone()))


class ForgedText(str):
    """Hostile string subclass that lies to equality and hashing operations."""

    def __eq__(self, other: object) -> bool:
        """Pretend to equal any compared governance string."""
        return True

    def __hash__(self) -> int:
        """Reuse a benign governance-code hash."""
        return hash("monthly_check_in")


def test_rejects_hostile_runtime_string_subclasses() -> None:
    """Validation sees the exact value later serialized into canonical evidence."""
    with pytest.raises(ValueError):
        packet(tenant_record_id=ForgedText(TENANT))
    with pytest.raises(ValueError):
        packet(feedback_cadence_code=ForgedText("shadow_mode"))
    with pytest.raises(ValueError):
        packet(goal_set_digest=ForgedText(DIGEST_A))
    with pytest.raises(ValueError):
        packet(requester_reference=ForgedText(ref("actor")))


def test_rejects_conflicting_live_reissuance_of_same_plan_reference() -> None:
    """A live plan reference cannot be rebound to different reviewed evidence."""
    original = packet()
    with pytest.raises(ValueError):
        replace(original, goal_count=4)
    duplicate = replace(original)
    assert duplicate.canonical_json() == original.canonical_json()
    del duplicate
    gc.collect()
    with pytest.raises(ValueError):
        replace(original, goal_count=4)


def test_releases_plan_reference_after_the_last_packet_is_gone() -> None:
    """Allow a new evidence binding only after every prior live packet is gone."""
    original = packet()
    original_reference = weak_ref(original)
    del original
    gc.collect()
    assert original_reference() is None

    replacement = packet(goal_count=4)
    assert json.loads(replacement.canonical_json())["goal_count"] == 4


def test_detects_post_construction_evidence_mutation() -> None:
    """Canonical export fails closed if a frozen packet is rewritten through object internals."""
    item = packet()
    object.__setattr__(item, "goal_count", 4)
    with pytest.raises(ValueError):
        item.canonical_json()


def test_packet_runtime_is_final() -> None:
    """Governed packet behavior cannot be replaced through subclass overrides."""
    with pytest.raises(TypeError, match="is final"):
        type("ForgedPacket", (PerformanceGoalPlanPacket,), {})


def test_accepts_operational_non_v4_core_references() -> None:
    """Authoritative core HRIS references are not incorrectly restricted to UUIDv4."""
    core = "01890f3d-4d6a-7cc0-8a9d-9a83bb1cc001"
    item = packet(
        employment_record_reference=f"employment_record:{core}",
        job_profile_reference=f"job_profile:{core}",
        performance_cycle_reference=f"performance_cycle:{core}",
    )
    assert json.loads(item.canonical_json())["employment_record_reference"].endswith(core)


def test_unregistered_instance_exports_as_governance_error() -> None:
    """Fail closed with the governance error when export runs off-lifecycle."""
    built = packet()
    restored = object.__new__(type(built))
    for field_name in PerformanceGoalPlanPacket.__slots__:
        if field_name.startswith("__"):
            continue
        object.__setattr__(restored, field_name, getattr(built, field_name))
    with pytest.raises(ValueError, match="governed constructor"):
        restored.canonical_json()
