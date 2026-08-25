"""Executable contract for privacy-minimized performance-context evidence."""

from datetime import date, datetime, timedelta, timezone
import gc
from hashlib import sha256
import json
from uuid import UUID

import pytest

from orgmetra_performance_context_evidence import (
    PerformanceContextEvidencePacket,
    build_performance_context_evidence,
)

TENANT = "11111111-1111-4111-8111-111111111111"
PACKET = "performance_context_evidence:21111111-1111-4111-8111-111111111111"
EMPLOYMENT = "employment_record:31111111-1111-4111-8111-111111111111"
JOB = "job_profile:41111111-1111-4111-8111-111111111111"
CYCLE = "performance_cycle:51111111-1111-4111-8111-111111111111"
ASSIGNMENTS = (
    "assignment_record:61111111-1111-4111-8111-111111111111",
    "assignment_record:71111111-1111-4111-8111-111111111111",
)
ORGANIZATIONS = (
    "organization_unit:81111111-1111-4111-8111-111111111111",
    "organization_unit:91111111-1111-4111-8111-111111111111",
)
REQUESTER = "actor:a1111111-1111-4111-8111-111111111111"
REVIEWER = "actor:b1111111-1111-4111-8111-111111111111"
DIGESTS = ("a" * 64, "b" * 64, "c" * 64, "d" * 64)


@pytest.fixture(autouse=True)
def unique_packet_reference(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Give each test one deterministic packet reference while preserving within-test conflicts."""
    packet_bytes = bytearray(sha256(request.node.nodeid.encode("utf-8")).digest()[:16])
    packet_bytes[6] = (packet_bytes[6] & 0x0F) | 0x40
    packet_bytes[8] = (packet_bytes[8] & 0x3F) | 0x80
    packet_uuid = UUID(bytes=bytes(packet_bytes))
    monkeypatch.setitem(globals(), "PACKET", f"performance_context_evidence:{packet_uuid}")


def values(**overrides: object) -> dict[str, object]:
    """Return one valid performance-context packet argument set."""
    base: dict[str, object] = {
        "tenant_record_id": TENANT,
        "performance_context_evidence_reference": PACKET,
        "employment_record_reference": EMPLOYMENT,
        "job_profile_reference": JOB,
        "performance_cycle_reference": CYCLE,
        "assignment_record_references": ASSIGNMENTS,
        "organization_unit_references": ORGANIZATIONS,
        "context_effective_from": date(2026, 1, 1),
        "context_effective_to": date(2026, 4, 1),
        "opportunity_to_perform_digest": DIGESTS[0],
        "work_context_digest": DIGESTS[1],
        "manager_context_digest": DIGESTS[2],
        "membership_weight_digest": DIGESTS[3],
        "requester_reference": REQUESTER,
        "reviewer_reference": REVIEWER,
        "purpose_code": "performance_context_review",
        "reason_code": "criterion_context_evidence_review",
        "generated_at": datetime(2026, 8, 23, 3, 0, tzinfo=timezone.utc),
        "evidence_version": 1,
    }
    base.update(overrides)
    return base


def build(**overrides: object) -> PerformanceContextEvidencePacket:
    """Build one valid packet with optional targeted overrides."""
    return build_performance_context_evidence(**values(**overrides))  # type: ignore[arg-type]


def test_builds_value_minimized_human_review_evidence() -> None:
    """A valid packet exposes only bounded context provenance and no HR values."""
    packet = build()
    document = json.loads(packet.canonical_json())
    assert document["analysis_use_state"] == "context_covariate_evidence_only"
    assert document["review_state"] == "requires_human_review"
    assert document["decision_authority"] == "not_authorized_for_performance_rating"
    assert document["employment_decision_authority"] == "not_authorized_for_employment_decision"
    assert document["contains_performance_rating"] is False
    assert document["contains_manager_identity"] is False
    assert document["contains_hr_values"] is False
    assert document["human_review_required"] is True
    assert document["assignment_record_references"] == list(ASSIGNMENTS)
    assert document["organization_unit_references"] == list(ORGANIZATIONS)
    assert document["context_effective_from"] == "2026-01-01"
    assert document["context_effective_to"] == "2026-04-01"
    assert "manager_reference" not in document
    assert "performance_rating" not in document
    assert len(packet.sha256_digest()) == 64
    assert repr(packet) == "PerformanceContextEvidencePacket(<redacted>)"


def test_normalizes_fixed_offset_time_to_utc() -> None:
    """System-recorded evidence keeps one deterministic UTC representation."""
    packet = build(
        generated_at=datetime(
            2026,
            8,
            23,
            12,
            30,
            45,
            123456,
            tzinfo=timezone(timedelta(hours=9)),
        )
    )
    assert json.loads(packet.canonical_json())["generated_at"] == "2026-08-23T03:30:45.123456Z"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_record_id", "00000000-0000-0000-0000-000000000000"),
        ("performance_context_evidence_reference", "performance_context_evidence:not-a-uuid"),
        ("employment_record_reference", "employment_record:not-a-uuid"),
        ("job_profile_reference", "job_profile:not-a-uuid"),
        ("performance_cycle_reference", "performance_cycle:not-a-uuid"),
        ("requester_reference", "actor:not-a-uuid"),
        ("reviewer_reference", "actor:not-a-uuid"),
    ],
)
def test_rejects_noncanonical_identity_evidence(field: str, value: str) -> None:
    """Every identity boundary rejects malformed or reserved correlation evidence."""
    with pytest.raises(ValueError):
        build(**{field: value})


def test_packet_owned_reference_requires_uuid4_but_operational_refs_do_not() -> None:
    """Packet identity is UUIDv4 while authoritative HRIS identities stay version-neutral."""
    with pytest.raises(ValueError):
        build(
            performance_context_evidence_reference=(
                "performance_context_evidence:6ba7b810-9dad-11d1-80b4-00c04fd430c8"
            )
        )
    packet = build(employment_record_reference="employment_record:01890f18-9f7b-7a2f-8c1b-123456789abc")
    assert packet.employment_record_reference.endswith("123456789abc")


@pytest.mark.parametrize("field", ["assignment_record_references", "organization_unit_references"])
def test_requires_nonempty_sorted_unique_exact_reference_tuples(field: str) -> None:
    """Context memberships are deterministic bounded tuples, not caller-defined collections."""
    prefix = "assignment_record" if field.startswith("assignment") else "organization_unit"
    first = f"{prefix}:61111111-1111-4111-8111-111111111111"
    second = f"{prefix}:71111111-1111-4111-8111-111111111111"
    for invalid in ([], (), (second, first), (first, first)):
        with pytest.raises(ValueError):
            build(**{field: invalid})
    too_many = tuple(
        f"{prefix}:{index:08x}-1111-4111-8111-111111111111" for index in range(1, 18)
    )
    with pytest.raises(ValueError):
        build(**{field: too_many})


@pytest.mark.parametrize(
    "field",
    [
        "opportunity_to_perform_digest",
        "work_context_digest",
        "manager_context_digest",
        "membership_weight_digest",
    ],
)
def test_rejects_non_sha256_context_provenance(field: str) -> None:
    """Every reviewed context source is bound by lowercase SHA-256 evidence."""
    with pytest.raises(ValueError):
        build(**{field: "A" * 64})


def test_requires_half_open_business_context_window() -> None:
    """Context exposure uses a nonempty half-open business-time interval."""
    with pytest.raises(ValueError):
        build(context_effective_to=date(2026, 1, 1))
    with pytest.raises(ValueError):
        build(context_effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ValueError):
        build(context_effective_to=datetime(2026, 4, 1, tzinfo=timezone.utc))


def test_requester_and_reviewer_must_be_distinct() -> None:
    """One actor cannot request and independently review the same context evidence."""
    with pytest.raises(ValueError):
        build(reviewer_reference=REQUESTER)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("purpose_code", "selection_decision"),
        ("reason_code", "manager_override"),
        ("evidence_version", 0),
        ("evidence_version", True),
    ],
)
def test_rejects_unreviewed_governance_values(field: str, value: object) -> None:
    """Closed governance metadata cannot be repurposed into a decision shortcut."""
    with pytest.raises(ValueError):
        build(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contains_performance_rating", True),
        ("contains_manager_identity", True),
        ("contains_hr_values", True),
        ("human_review_required", False),
        ("analysis_use_state", "performance_rating_adjustment"),
        ("review_state", "approved"),
        ("decision_authority", "authorized_for_performance_rating"),
        ("employment_decision_authority", "authorized_for_employment_decision"),
        ("next_action", "Apply the context adjustment automatically."),
    ],
)
def test_direct_construction_cannot_weaken_governance(field: str, value: object) -> None:
    """Default-only governance state remains fail-closed under direct construction."""
    kwargs = values()
    kwargs[field] = value
    with pytest.raises(ValueError):
        PerformanceContextEvidencePacket(**kwargs)  # type: ignore[arg-type]


def test_rejects_invalid_system_recorded_time() -> None:
    """System-recorded evidence rejects naive and subclassed datetime primitives."""
    class ForgedDateTime(datetime):
        """Caller-defined datetime subclass used to exercise exact runtime rejection."""

    with pytest.raises(ValueError):
        build(generated_at=datetime(2026, 8, 23, 3, 0))
    with pytest.raises(ValueError):
        build(generated_at=ForgedDateTime(2026, 8, 23, 3, 0, tzinfo=timezone.utc))


class ForgedCode(str):
    """String subclass that forges equality and hashing while retaining unsafe text."""

    def __eq__(self, other: object) -> bool:
        """Pretend unsafe text equals any reviewed code."""
        return True

    def __ne__(self, other: object) -> bool:
        """Keep inequality consistent with forged equality."""
        return False

    def __hash__(self) -> int:
        """Return a stable hash that callers might otherwise exploit in allow-lists."""
        return hash("performance_context_review")


def test_rejects_hostile_runtime_subclasses_before_reviewed_operations() -> None:
    """Caller-defined text and tuple behavior cannot forge reviewed evidence."""
    with pytest.raises(ValueError):
        build(purpose_code=ForgedCode("selection_decision"))
    with pytest.raises(ValueError):
        build(opportunity_to_perform_digest=ForgedCode("a" * 64))
    with pytest.raises(ValueError):
        build(requester_reference=ForgedCode(REQUESTER))


class CustomTuple(tuple):
    """Caller-defined tuple subtype used to exercise exact collection rejection."""


def test_rejects_collection_subclasses() -> None:
    """Membership collection semantics cannot be caller-overridden."""
    with pytest.raises(ValueError):
        build(assignment_record_references=CustomTuple(ASSIGNMENTS))


def test_detects_post_issuance_evidence_mutation() -> None:
    """Valid-looking mutation after issuance cannot produce new canonical evidence."""
    packet = build()
    object.__setattr__(packet, "manager_context_digest", "e" * 64)
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()


def test_conflicting_live_packet_reference_cannot_be_reissued() -> None:
    """One live tenant-qualified packet reference cannot represent conflicting evidence."""
    packet = build()
    duplicate = build()
    assert duplicate.canonical_json() == packet.canonical_json()
    with pytest.raises(ValueError, match="bound to different live evidence"):
        build(work_context_digest="e" * 64)


def test_live_reference_binding_survives_idempotent_duplicate_collection() -> None:
    """Collecting a duplicate cannot erase another live packet's reference binding."""
    original = build()
    duplicate = build()
    assert duplicate.canonical_json() == original.canonical_json()
    del duplicate
    gc.collect()

    with pytest.raises(ValueError, match="bound to different live evidence"):
        build(work_context_digest="e" * 64)
    assert original.canonical_json()


def test_packet_runtime_is_final() -> None:
    """Trust-bearing packet behavior cannot be overridden through subclassing."""
    with pytest.raises(TypeError):
        type("ForgedPacket", (PerformanceContextEvidencePacket,), {})


def test_next_action_requires_authoritative_context_resolution() -> None:
    """Customer-facing guidance directs context evidence to the next governed boundary."""
    packet = build()
    assert "re-resolve" in packet.next_action
    assert "opportunity-to-perform" in packet.next_action
    assert "Do not adjust an individual performance rating" in packet.next_action


def test_unregistered_instance_exports_as_governance_error() -> None:
    """Fail closed with the governance error when export runs off-lifecycle."""
    packet = build()
    restored = object.__new__(type(packet))
    dataclass_fields = [
        name for name in PerformanceContextEvidencePacket.__slots__ if not name.startswith("__")
    ]
    for field_name in dataclass_fields:
        object.__setattr__(restored, field_name, getattr(packet, field_name))
    with pytest.raises(ValueError, match="governed constructor"):
        restored.canonical_json()
