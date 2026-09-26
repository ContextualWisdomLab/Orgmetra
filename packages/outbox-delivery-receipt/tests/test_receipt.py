from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from uuid import UUID, uuid4

import pytest

from orgmetra_outbox_delivery_receipt import (
    ExternalDeliveryReceiptEvidence,
    build_external_delivery_receipt_evidence,
    verify_exact_delivery_attempt,
)


class _MutableTimezone(tzinfo):
    def __init__(self, offset: timedelta) -> None:
        self.offset = offset

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return self.offset

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)


class _EqualityForgingStr(str):
    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = str.__hash__


def _uuid() -> str:
    return str(uuid4())


def _reference(prefix: str) -> str:
    return f"{prefix}:{uuid4()}"


def _kwargs() -> dict[str, object]:
    return {
        "tenant_record_id": _uuid(),
        "outbox_delivery_record_id": _uuid(),
        "audit_event_record_id": _uuid(),
        "delivery_target_code": "naruon_calendar",
        "delivery_attempt_count": 2,
        "transport_provider_code": "calendar_gateway",
        "transport_receipt_reference": _reference("transport_receipt"),
        "transport_receipt_digest": "a" * 64,
        "transport_delivered_at": datetime(2026, 8, 29, 1, 2, 3, 456789, tzinfo=timezone.utc),
        "observed_at": datetime(2026, 8, 29, 1, 2, 4, tzinfo=timezone.utc),
        "evidence_version": 1,
    }


def test_builds_value_minimized_untrusted_transport_evidence() -> None:
    evidence = build_external_delivery_receipt_evidence(**_kwargs())

    assert evidence.contains_hr_payload is False
    assert evidence.contains_destination is False
    assert evidence.contains_credentials is False
    assert evidence.delivery_outcome_code == "transport_reported_delivered"
    assert evidence.trust_state == "untrusted_transport_evidence"
    assert evidence.reconciliation_state == "requires_exact_attempt_reconciliation"
    assert evidence.mutation_authority == "not_authorized_to_mutate_delivery_state"
    assert "reconcile" in evidence.next_action.lower()
    assert repr(evidence) == "ExternalDeliveryReceiptEvidence(<redacted>)"

    payload = evidence.canonical_json()
    assert '"contains_hr_payload":false' in payload
    assert '"transport_receipt_digest":"' + "a" * 64 + '"' in payload
    assert "destination" in payload
    assert evidence.sha256_digest() == evidence.sha256_digest()
    assert len(evidence.sha256_digest()) == 64


def test_canonicalizes_aware_timestamps_to_utc_without_losing_precision() -> None:
    values = _kwargs()
    values["transport_delivered_at"] = datetime(
        2026, 8, 29, 10, 2, 3, 456789, tzinfo=timezone(timedelta(hours=9))
    )
    values["observed_at"] = datetime(
        2026, 8, 29, 10, 2, 4, 123, tzinfo=timezone(timedelta(hours=9))
    )
    evidence = build_external_delivery_receipt_evidence(**values)

    assert evidence.transport_delivered_at_utc == "2026-08-29T01:02:03.456789Z"
    assert evidence.observed_at_utc == "2026-08-29T01:02:04.000123Z"


def test_freezes_caller_owned_timezone_before_evidence_is_retained() -> None:
    mutable_timezone = _MutableTimezone(timedelta(hours=9))
    values = _kwargs()
    values["transport_delivered_at"] = datetime(
        2026, 8, 29, 10, 2, 3, 456789, tzinfo=mutable_timezone
    )
    evidence = build_external_delivery_receipt_evidence(**values)
    original_json = evidence.canonical_json()
    original_digest = evidence.sha256_digest()

    mutable_timezone.offset = timedelta(0)

    assert evidence.transport_delivered_at.tzinfo is timezone.utc
    assert evidence.canonical_json() == original_json
    assert evidence.sha256_digest() == original_digest


def test_rejects_string_subclass_that_can_forge_exact_attempt_equality() -> None:
    values = _kwargs()
    values["delivery_target_code"] = _EqualityForgingStr("naruon_calendar")

    with pytest.raises(ValueError, match="delivery_target_code"):
        build_external_delivery_receipt_evidence(**values)


def test_rejects_string_subclass_that_can_forge_fixed_trust_state() -> None:
    values = _kwargs()
    values["trust_state"] = _EqualityForgingStr("trusted_transport_evidence")

    with pytest.raises(ValueError, match="trust_state"):
        ExternalDeliveryReceiptEvidence(**values)


def test_verifies_only_the_exact_outbox_attempt() -> None:
    evidence = build_external_delivery_receipt_evidence(**_kwargs())

    digest = verify_exact_delivery_attempt(
        evidence,
        tenant_record_id=evidence.tenant_record_id,
        outbox_delivery_record_id=evidence.outbox_delivery_record_id,
        audit_event_record_id=evidence.audit_event_record_id,
        delivery_target_code=evidence.delivery_target_code,
        delivery_attempt_count=evidence.delivery_attempt_count,
    )
    assert digest == evidence.sha256_digest()

    with pytest.raises(ValueError, match="exact outbox delivery attempt"):
        verify_exact_delivery_attempt(
            evidence,
            tenant_record_id=evidence.tenant_record_id,
            outbox_delivery_record_id=evidence.outbox_delivery_record_id,
            audit_event_record_id=evidence.audit_event_record_id,
            delivery_target_code=evidence.delivery_target_code,
            delivery_attempt_count=evidence.delivery_attempt_count + 1,
        )

    with pytest.raises(TypeError, match="ExternalDeliveryReceiptEvidence"):
        verify_exact_delivery_attempt(
            object(),
            tenant_record_id=evidence.tenant_record_id,
            outbox_delivery_record_id=evidence.outbox_delivery_record_id,
            audit_event_record_id=evidence.audit_event_record_id,
            delivery_target_code=evidence.delivery_target_code,
            delivery_attempt_count=evidence.delivery_attempt_count,
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("tenant_record_id", "not-a-uuid"),
        ("outbox_delivery_record_id", "00000000-0000-0000-0000-000000000000"),
        ("audit_event_record_id", "ffffffff-ffff-ffff-ffff-ffffffffffff"),
        ("tenant_record_id", UUID("12345678-1234-5678-9234-567812345678")),
    ],
)
def test_rejects_non_operational_or_noncanonical_uuid_identity(
    field_name: str, bad_value: object
) -> None:
    values = _kwargs()
    values[field_name] = bad_value
    with pytest.raises(ValueError, match=field_name):
        build_external_delivery_receipt_evidence(**values)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("delivery_target_code", "calendar"),
        ("delivery_target_code", "Calendar_Gateway"),
        ("delivery_target_code", 3),
        ("delivery_target_code", "a_" + "b" * 64),
        ("transport_provider_code", "provider"),
        ("transport_provider_code", "bad-provider"),
    ],
)
def test_rejects_unbounded_or_free_form_codes(field_name: str, bad_value: object) -> None:
    values = _kwargs()
    values[field_name] = bad_value
    with pytest.raises(ValueError, match=field_name):
        build_external_delivery_receipt_evidence(**values)


@pytest.mark.parametrize(
    "bad_value",
    [
        "receipt:550e8400-e29b-41d4-a716-446655440000",
        "transport_receipt:not-a-uuid",
        "transport_receipt:550e8400-e29b-11d4-a716-446655440000",
        5,
        "transport_receipt:" + "x" * 200,
    ],
)
def test_requires_host_normalized_opaque_transport_receipt_reference(bad_value: object) -> None:
    values = _kwargs()
    values["transport_receipt_reference"] = bad_value
    with pytest.raises(ValueError, match="transport_receipt_reference"):
        build_external_delivery_receipt_evidence(**values)


@pytest.mark.parametrize("bad_value", ["A" * 64, "a" * 63, 7])
def test_requires_lowercase_sha256_receipt_digest(bad_value: object) -> None:
    values = _kwargs()
    values["transport_receipt_digest"] = bad_value
    with pytest.raises(ValueError, match="transport_receipt_digest"):
        build_external_delivery_receipt_evidence(**values)


@pytest.mark.parametrize("bad_value", [True, 0, 2_147_483_648])
def test_requires_positive_bounded_delivery_attempt_count(bad_value: object) -> None:
    values = _kwargs()
    values["delivery_attempt_count"] = bad_value
    with pytest.raises(ValueError, match="delivery_attempt_count"):
        build_external_delivery_receipt_evidence(**values)


@pytest.mark.parametrize("bad_value", [True, 0, 2_147_483_648])
def test_requires_positive_bounded_evidence_version(bad_value: object) -> None:
    values = _kwargs()
    values["evidence_version"] = bad_value
    with pytest.raises(ValueError, match="evidence_version"):
        build_external_delivery_receipt_evidence(**values)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("transport_delivered_at", "2026-08-29T01:02:03Z"),
        ("transport_delivered_at", datetime(2026, 8, 29, 1, 2, 3)),
        ("observed_at", datetime(2026, 8, 29, 1, 2, 4)),
    ],
)
def test_requires_timezone_aware_datetime_evidence(field_name: str, bad_value: object) -> None:
    values = _kwargs()
    values[field_name] = bad_value
    with pytest.raises(ValueError, match=field_name):
        build_external_delivery_receipt_evidence(**values)


def test_rejects_receipt_observed_before_reported_delivery() -> None:
    values = _kwargs()
    values["observed_at"] = values["transport_delivered_at"] - timedelta(microseconds=1)
    with pytest.raises(ValueError, match="observed_at"):
        build_external_delivery_receipt_evidence(**values)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("contains_hr_payload", True),
        ("contains_destination", True),
        ("contains_credentials", True),
        ("delivery_outcome_code", "delivered"),
        ("trust_state", "trusted"),
        ("reconciliation_state", "reconciled"),
        ("mutation_authority", "authorized"),
        ("next_action", "Mark delivered."),
    ],
)
def test_fixed_safety_contract_cannot_be_overridden(field_name: str, bad_value: object) -> None:
    values = _kwargs()
    values[field_name] = bad_value
    with pytest.raises(ValueError):
        ExternalDeliveryReceiptEvidence(**values)


def test_evidence_is_structurally_immutable_after_construction() -> None:
    evidence = build_external_delivery_receipt_evidence(**_kwargs())
    with pytest.raises(AttributeError):
        object.__setattr__(evidence, "delivery_attempt_count", 99)


def test_copy_bypass_cannot_create_a_second_canonical_truth() -> None:
    evidence = build_external_delivery_receipt_evidence(**_kwargs())

    replaced = evidence._replace(trust_state="trusted_transport_evidence")
    with pytest.raises(ValueError, match="trust_state"):
        replaced.canonical_json()

    raw_values = list(evidence)
    raw_values[11] = True
    reconstructed = tuple.__new__(ExternalDeliveryReceiptEvidence, tuple(raw_values))
    with pytest.raises(ValueError, match="contains_hr_payload"):
        reconstructed.sha256_digest()
