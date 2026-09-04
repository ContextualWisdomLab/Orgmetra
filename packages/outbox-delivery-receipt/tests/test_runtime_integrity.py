from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from uuid import uuid4

import pytest

from orgmetra_outbox_delivery_receipt import (
    ExternalDeliveryReceiptEvidence,
    build_external_delivery_receipt_evidence,
    verify_exact_delivery_attempt,
)


class _FailingTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta:
        raise RuntimeError("hostile timezone provider")

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)


class _NoOffsetTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None


class _ExplosiveEquality:
    def __eq__(self, other: object) -> bool:
        raise RuntimeError("untrusted evidence equality executed")


def _kwargs() -> dict[str, object]:
    return {
        "tenant_record_id": str(uuid4()),
        "outbox_delivery_record_id": str(uuid4()),
        "audit_event_record_id": str(uuid4()),
        "delivery_target_code": "naruon_calendar",
        "delivery_attempt_count": 2,
        "transport_provider_code": "calendar_gateway",
        "transport_receipt_reference": f"transport_receipt:{uuid4()}",
        "transport_receipt_digest": "a" * 64,
        "transport_delivered_at": datetime(2026, 8, 29, 1, 2, 3, tzinfo=timezone.utc),
        "observed_at": datetime(2026, 8, 29, 1, 2, 4, tzinfo=timezone.utc),
        "evidence_version": 1,
    }


def test_timezone_provider_exception_fails_closed_as_value_error() -> None:
    values = _kwargs()
    values["transport_delivered_at"] = datetime(
        2026, 8, 29, 1, 2, 3, tzinfo=_FailingTimezone()
    )

    with pytest.raises(ValueError, match="transport_delivered_at"):
        build_external_delivery_receipt_evidence(**values)


def test_timezone_provider_without_offset_fails_closed() -> None:
    values = _kwargs()
    values["transport_delivered_at"] = datetime(
        2026, 8, 29, 1, 2, 3, tzinfo=_NoOffsetTimezone()
    )

    with pytest.raises(ValueError, match="transport_delivered_at"):
        build_external_delivery_receipt_evidence(**values)


def test_low_level_reconstruction_with_nonfrozen_timestamp_fails_closed() -> None:
    evidence = build_external_delivery_receipt_evidence(**_kwargs())
    raw_values = list(evidence)
    raw_values[8] = datetime(
        2026, 8, 29, 10, 2, 3, tzinfo=timezone(timedelta(hours=9))
    )
    reconstructed = tuple.__new__(ExternalDeliveryReceiptEvidence, tuple(raw_values))

    with pytest.raises(ValueError, match="transport_delivered_at"):
        reconstructed.canonical_json()


def test_exact_attempt_verification_rejects_receipt_subclasses() -> None:
    evidence = build_external_delivery_receipt_evidence(**_kwargs())

    class _ForgedReceipt(ExternalDeliveryReceiptEvidence):
        __slots__ = ()

        def sha256_digest(self) -> str:
            return "f" * 64

    forged = tuple.__new__(_ForgedReceipt, tuple(evidence))

    with pytest.raises(TypeError, match="ExternalDeliveryReceiptEvidence"):
        verify_exact_delivery_attempt(
            forged,
            tenant_record_id=evidence.tenant_record_id,
            outbox_delivery_record_id=evidence.outbox_delivery_record_id,
            audit_event_record_id=evidence.audit_event_record_id,
            delivery_target_code=evidence.delivery_target_code,
            delivery_attempt_count=evidence.delivery_attempt_count,
        )


def test_exact_attempt_verification_validates_evidence_before_scope_comparison() -> None:
    evidence = build_external_delivery_receipt_evidence(**_kwargs())
    raw_values = list(evidence)
    raw_values[0] = _ExplosiveEquality()
    reconstructed = tuple.__new__(ExternalDeliveryReceiptEvidence, tuple(raw_values))

    with pytest.raises(ValueError, match="tenant_record_id"):
        verify_exact_delivery_attempt(
            reconstructed,
            tenant_record_id=evidence.tenant_record_id,
            outbox_delivery_record_id=evidence.outbox_delivery_record_id,
            audit_event_record_id=evidence.audit_event_record_id,
            delivery_target_code=evidence.delivery_target_code,
            delivery_attempt_count=evidence.delivery_attempt_count,
        )
