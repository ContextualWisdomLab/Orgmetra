"""Contract tests for governed Employment work-capacity review evidence."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from uuid import UUID, uuid4

import pytest

from orgmetra_employment_work_capacity_review import (
    EmploymentWorkCapacityReviewPacket,
    build_employment_work_capacity_review_packet,
)

TENANT = "018f47a8-4b1c-7cc2-98b0-0123456789ab"
EMPLOYMENT = "employment_record:018f47a8-4b1c-7cc2-98b0-1123456789ab"
REQUESTER = f"actor:{uuid4()}"
REVIEWER = f"actor:{uuid4()}"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
REVIEWED = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)


def kwargs() -> dict[str, object]:
    """Return one complete valid review payload."""
    return {
        "tenant_record_id": TENANT,
        "employment_record_reference": EMPLOYMENT,
        "current_capacity_ratio": Decimal("1.0000"),
        "proposed_capacity_ratio": Decimal("0.8000"),
        "effective_on": date(2026, 9, 1),
        "employment_terms_evidence_digest": DIGEST_A,
        "capacity_policy_evidence_digest": DIGEST_B,
        "reviewer_identity_evidence_digest": DIGEST_C,
        "requester_actor_reference": REQUESTER,
        "reviewer_actor_reference": REVIEWER,
        "reason_code": "employee_agreed_change",
        "evidence_version": 1,
        "reviewed_at": REVIEWED,
    }


def build(**changes: object) -> EmploymentWorkCapacityReviewPacket:
    """Build a packet while overriding selected valid defaults."""
    values = kwargs()
    values.update(changes)
    return build_employment_work_capacity_review_packet(**values)  # type: ignore[arg-type]


def test_canonical_evidence_is_deterministic_redacted_and_non_authoritative() -> None:
    packet = build()
    document = packet.canonical_document()
    assert document["current_capacity_ratio"] == "1.0000"
    assert document["proposed_capacity_ratio"] == "0.8000"
    assert document["purpose_code"] == "employment_work_capacity_review"
    assert document["review_state"] == "reviewed_for_authoritative_resolution"
    assert document["decision_authority"] == "not_authorized_to_change_employment_or_compensation"
    assert document["human_review_required"] is True
    recorded = datetime.fromisoformat(str(document["recorded_at"]).replace("Z", "+00:00"))
    assert recorded >= REVIEWED
    assert json.loads(packet.canonical_json()) == document
    assert packet.sha256_digest() == hashlib.sha256(packet.canonical_json().encode()).hexdigest()
    assert repr(packet) == "EmploymentWorkCapacityReviewPacket(<redacted>)"
    for forbidden in ("salary", "rating", "email", "phone", "prompt", "model_output"):
        assert forbidden not in packet.canonical_json()


def test_all_reviewed_reason_codes_are_supported() -> None:
    for reason in (
        "employee_agreed_change",
        "contractual_hours_change",
        "business_schedule_change",
        "return_from_leave",
    ):
        assert build(reason_code=reason).canonical_document()["reason_code"] == reason


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("tenant_record_id", "not-a-uuid", "operational UUID"),
        ("tenant_record_id", str(UUID(int=0)), "operational UUID"),
        ("tenant_record_id", str(UUID(int=(1 << 128) - 1)), "operational UUID"),
        ("employment_record_reference", "wrong:018f47a8-4b1c-7cc2-98b0-1123456789ab", "employment_record"),
        ("employment_record_reference", "employment_record:not-a-uuid", "employment_record"),
        ("employment_record_reference", f"employment_record:{UUID(int=0)}", "employment_record"),
        ("requester_actor_reference", "actor:018f47a8-4b1c-7cc2-98b0-1123456789ab", "UUIDv4"),
        ("reviewer_actor_reference", "bad", "actor"),
        ("employment_terms_evidence_digest", "A" * 64, "SHA-256"),
        ("capacity_policy_evidence_digest", "b" * 63, "SHA-256"),
        ("reviewer_identity_evidence_digest", 7, "exact string"),
        ("reason_code", "medical_condition", "reviewed employment-capacity reason"),
        ("effective_on", datetime(2026, 9, 1, tzinfo=timezone.utc), "exact built-in date"),
        ("evidence_version", True, "integer"),
        ("evidence_version", 0, "integer"),
        ("evidence_version", 2_147_483_648, "integer"),
        ("reviewed_at", datetime(2026, 8, 23), "exact built-in UTC datetime"),
    ],
)
def test_invalid_governance_inputs_fail_closed(field: str, value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build(**{field: value})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("current_capacity_ratio", "1.0000", "exact Decimal"),
        ("proposed_capacity_ratio", Decimal("NaN"), "finite"),
        ("proposed_capacity_ratio", Decimal("-0.0001"), "between"),
        ("proposed_capacity_ratio", Decimal("-0.0000"), "negative zero"),
        ("proposed_capacity_ratio", Decimal("1.0001"), "between"),
        ("proposed_capacity_ratio", Decimal("0.8"), "four decimal"),
    ],
)
def test_capacity_ratio_shape_fails_closed(field: str, value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build(**{field: value})


def test_noop_actor_overlap_and_future_review_fail_closed() -> None:
    with pytest.raises(ValueError, match="must differ"):
        build(proposed_capacity_ratio=Decimal("1.0000"))
    with pytest.raises(ValueError, match="different actor"):
        build(reviewer_actor_reference=REQUESTER)
    with pytest.raises(ValueError, match="cannot precede"):
        build(reviewed_at=datetime.now(timezone.utc) + timedelta(days=1))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("purpose_code", "other", "purpose_code"),
        ("review_state", "approved", "review_state"),
        ("decision_authority", "authorized", "decision_authority"),
        ("human_review_required", False, "human review"),
        ("next_action", "apply now", "next_action"),
    ],
)
def test_fixed_governance_cannot_be_rewritten(field: str, value: object, message: str) -> None:
    values = kwargs()
    values[field] = value
    with pytest.raises(ValueError, match=message):
        EmploymentWorkCapacityReviewPacket(**values)  # type: ignore[arg-type]


class ForgedText(str):
    """Text subclass used to prove exact-runtime fail-closed behavior."""


class ForgedDecimal(Decimal):
    """Decimal subclass used to prove exact-runtime fail-closed behavior."""

    def __format__(self, format_spec: str) -> str:
        """Attempt to preserve the old canonical text after changing the live value."""
        return format(Decimal("1.0000"), format_spec)


def test_runtime_subclasses_fail_closed() -> None:
    with pytest.raises(ValueError, match="exact string"):
        build(tenant_record_id=ForgedText(TENANT))
    with pytest.raises(ValueError, match="exact Decimal"):
        build(proposed_capacity_ratio=ForgedDecimal("0.8000"))


def test_post_issuance_mutation_fails_closed_and_document_is_detached() -> None:
    packet = build()
    document = packet.canonical_document()
    document["reason_code"] = "business_schedule_change"
    assert packet.canonical_document()["reason_code"] == "employee_agreed_change"
    object.__setattr__(packet, "reason_code", "business_schedule_change")
    with pytest.raises(ValueError, match="modified after issuance"):
        packet.canonical_document()
    with pytest.raises(ValueError, match="modified after issuance"):
        packet.canonical_json()


def test_post_issuance_decimal_subclass_cannot_preserve_sealed_digest() -> None:
    """A hostile Decimal subtype cannot hide a changed live capacity ratio."""
    packet = build()
    object.__setattr__(packet, "current_capacity_ratio", ForgedDecimal("0.5000"))

    with pytest.raises(ValueError, match="exact Decimal"):
        packet.canonical_json()


def test_replace_creates_new_non_authoritative_evidence_with_new_digest() -> None:
    packet = build()
    changed = replace(packet, proposed_capacity_ratio=Decimal("0.6000"))
    assert changed.recorded_at >= packet.recorded_at
    assert changed.sha256_digest() != packet.sha256_digest()
    assert changed.canonical_document()["decision_authority"] == "not_authorized_to_change_employment_or_compensation"
