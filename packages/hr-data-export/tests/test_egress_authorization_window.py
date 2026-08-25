"""Regression coverage for authorization expiry across one-time HR export egress."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from orgmetra_hr_data_export import HrDataExportReviewPacket
from orgmetra_hr_data_export.execution import (
    HrDataExportArtifact,
    HrDataExportAuditReceipt,
    HrDataExportEgressReceipt,
    HrDataExportExecutionError,
    HrDataExportExecutionVerification,
    execute_reviewed_hr_export,
)

UTC = timezone.utc
BASE_TIME = datetime(2026, 8, 26, 0, 0, tzinfo=UTC)
TENANT_ID = "11111111-1111-4111-8111-111111111111"
RESOURCE_REFERENCE = "employment_record:22222222-2222-4222-8222-222222222222"
EXPORT_REVIEW_REFERENCE = "export_review:33333333-3333-4333-8333-333333333333"
AUTHORIZATION_REFERENCE = "authorization_decision:44444444-4444-4444-8444-444444444444"
REQUESTER_REFERENCE = "actor:55555555-5555-4555-8555-555555555555"
REVIEWER_REFERENCE = "actor:66666666-6666-4666-8666-666666666666"
EXECUTION_REFERENCE = "export_execution:77777777-7777-4777-8777-777777777777"
EXECUTION_AUTHORIZATION_REFERENCE = "export_authorization:88888888-8888-4888-8888-888888888888"
HUMAN_APPROVAL_REFERENCE = "export_approval:99999999-9999-4999-8999-999999999999"
AUDIT_REFERENCE = "audit_event:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
EGRESS_REFERENCE = "one_time_download:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
FIELDS = ("email_address", "employee_number")


class SequenceClock:
    """Return configured UTC instants in order and fail on unexpected clock reads."""

    def __init__(self, *values: datetime) -> None:
        self._values = list(values)

    def __call__(self) -> datetime:
        """Return the next configured instant."""
        if not self._values:
            raise AssertionError("clock called more often than expected")
        return self._values.pop(0)


class Authority:
    """Return one exact export verification."""

    def __init__(self, verification: HrDataExportExecutionVerification) -> None:
        self.verification = verification

    def verify_export(
        self,
        *,
        review: HrDataExportReviewPacket,
        review_digest: str,
        requested_at: datetime,
    ) -> object:
        """Return the configured verification for the reviewed request."""
        assert review_digest == review.sha256_digest()
        assert requested_at.tzinfo is UTC
        return self.verification


class Materializer:
    """Return one exact bounded export artifact."""

    def __init__(self, artifact: HrDataExportArtifact) -> None:
        self.artifact = artifact

    def materialize_export(self, *, verification: HrDataExportExecutionVerification) -> object:
        """Return exact bytes for the verified execution."""
        assert verification.export_execution_reference == EXECUTION_REFERENCE
        return self.artifact


class AuditPort:
    """Return one pre-delivery immutable audit receipt."""

    def __init__(self, receipt: HrDataExportAuditReceipt) -> None:
        self.receipt = receipt

    def append_pre_delivery_audit(
        self,
        *,
        verification: HrDataExportExecutionVerification,
        artifact: HrDataExportArtifact,
        recorded_at: datetime,
    ) -> object:
        """Return evidence bound to the audited artifact and exact audit instant."""
        assert verification.export_execution_reference == EXECUTION_REFERENCE
        assert artifact.sha256_digest == self.receipt.artifact_sha256_digest
        assert recorded_at == self.receipt.recorded_at
        return self.receipt


class EgressPort:
    """Return one host-owned one-time-delivery receipt and record the side effect."""

    def __init__(self, receipt: HrDataExportEgressReceipt) -> None:
        self.receipt = receipt
        self.calls = 0

    def publish_one_time_download(
        self,
        *,
        verification: HrDataExportExecutionVerification,
        artifact: HrDataExportArtifact,
        audit_receipt: HrDataExportAuditReceipt,
        published_at: datetime,
    ) -> object:
        """Model a completed one-time delivery after the pre-delivery authorization check."""
        self.calls += 1
        assert verification.export_execution_reference == EXECUTION_REFERENCE
        assert artifact.sha256_digest == self.receipt.artifact_sha256_digest
        assert audit_receipt.audit_event_reference == self.receipt.audit_event_reference
        assert published_at <= self.receipt.delivered_at
        return self.receipt


def make_review() -> HrDataExportReviewPacket:
    """Return one valid reviewed export request."""
    return HrDataExportReviewPacket(
        tenant_record_id=TENANT_ID,
        export_review_reference=EXPORT_REVIEW_REFERENCE,
        resource_kind="employment_record",
        resource_reference=RESOURCE_REFERENCE,
        authorization_evidence_reference=AUTHORIZATION_REFERENCE,
        authorization_evidence_digest=DIGEST_A,
        authorization_policy_version_code="policy:v1",
        requester_reference=REQUESTER_REFERENCE,
        reviewer_reference=REVIEWER_REFERENCE,
        purpose_code="hr_data_export_review",
        reason_code="employee_access_request",
        requested_fields=FIELDS,
        export_format_code="json",
        destination_kind="authenticated_one_time_download",
        generated_at=BASE_TIME - timedelta(minutes=5),
    )


def make_verification(
    review: HrDataExportReviewPacket,
    *,
    expires_at: datetime,
) -> HrDataExportExecutionVerification:
    """Return one exact export authorization window for the reviewed scope."""
    return HrDataExportExecutionVerification(
        tenant_record_id=review.tenant_record_id,
        export_execution_reference=EXECUTION_REFERENCE,
        export_review_reference=review.export_review_reference,
        export_review_digest=review.sha256_digest(),
        resource_kind=review.resource_kind,
        resource_reference=review.resource_reference,
        requested_fields=review.requested_fields,
        export_format_code=review.export_format_code,
        destination_kind=review.destination_kind,
        execution_authorization_reference=EXECUTION_AUTHORIZATION_REFERENCE,
        execution_authorization_digest=DIGEST_B,
        authorization_policy_version_code="policy:v2",
        human_approval_reference=HUMAN_APPROVAL_REFERENCE,
        human_approval_digest=DIGEST_C,
        retention_state="retention_permits_export",
        legal_hold_state="no_legal_hold_block",
        verified_at=BASE_TIME,
        authorization_expires_at=expires_at,
    )


def make_ports(
    *,
    delivered_at: datetime,
    expires_at: datetime,
) -> tuple[HrDataExportReviewPacket, Authority, Materializer, AuditPort, EgressPort]:
    """Return one exact export fixture with configurable delivery and authorization times."""
    review = make_review()
    verification = make_verification(review, expires_at=expires_at)
    artifact = HrDataExportArtifact(
        field_names=FIELDS,
        content_type="application/json",
        content=b'{"email_address":"a@example.test","employee_number":"E-1"}',
    )
    audit_receipt = HrDataExportAuditReceipt(
        tenant_record_id=TENANT_ID,
        export_execution_reference=EXECUTION_REFERENCE,
        export_review_digest=verification.export_review_digest,
        execution_authorization_digest=verification.execution_authorization_digest,
        human_approval_digest=verification.human_approval_digest,
        artifact_sha256_digest=artifact.sha256_digest,
        artifact_byte_length=artifact.byte_length,
        audit_event_reference=AUDIT_REFERENCE,
        recorded_at=BASE_TIME + timedelta(seconds=2),
    )
    egress_receipt = HrDataExportEgressReceipt(
        tenant_record_id=TENANT_ID,
        export_execution_reference=EXECUTION_REFERENCE,
        artifact_sha256_digest=artifact.sha256_digest,
        artifact_byte_length=artifact.byte_length,
        audit_event_reference=AUDIT_REFERENCE,
        egress_reference=EGRESS_REFERENCE,
        destination_kind="authenticated_one_time_download",
        one_time_use_enforced=True,
        delivered_at=delivered_at,
    )
    return (
        review,
        Authority(verification),
        Materializer(artifact),
        AuditPort(audit_receipt),
        EgressPort(egress_receipt),
    )


def execute(
    review: HrDataExportReviewPacket,
    authority: Authority,
    materializer: Materializer,
    audit_port: AuditPort,
    egress_port: EgressPort,
    clock: SequenceClock,
) -> Any:
    """Run the public export boundary with one deterministic host clock."""
    return execute_reviewed_hr_export(
        review=review,
        authority=authority,
        materializer=materializer,
        audit_port=audit_port,
        egress_port=egress_port,
        now_provider=clock,
    )


def test_delivery_before_expiry_remains_successful_when_observed_after_expiry() -> None:
    """A completed authorized delivery must not become retryable only because observation is later."""
    expires_at = BASE_TIME + timedelta(seconds=4)
    review, authority, materializer, audit_port, egress_port = make_ports(
        delivered_at=BASE_TIME + timedelta(seconds=3, milliseconds=500),
        expires_at=expires_at,
    )
    receipt = execute(
        review,
        authority,
        materializer,
        audit_port,
        egress_port,
        SequenceClock(
            BASE_TIME + timedelta(seconds=1),
            BASE_TIME + timedelta(seconds=2),
            BASE_TIME + timedelta(seconds=3),
            BASE_TIME + timedelta(seconds=5),
        ),
    )
    assert egress_port.calls == 1
    assert receipt.delivered_at < expires_at
    assert receipt.export_state == "export_delivered"


def test_delivery_at_or_after_expiry_is_rejected_by_receipt_window_binding() -> None:
    """The receipt itself must prove delivery occurred inside the authorized half-open interval."""
    expires_at = BASE_TIME + timedelta(seconds=4)
    review, authority, materializer, audit_port, egress_port = make_ports(
        delivered_at=BASE_TIME + timedelta(seconds=4, milliseconds=500),
        expires_at=expires_at,
    )
    with pytest.raises(HrDataExportExecutionError, match="egress receipt"):
        execute(
            review,
            authority,
            materializer,
            audit_port,
            egress_port,
            SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
                BASE_TIME + timedelta(seconds=3),
                BASE_TIME + timedelta(seconds=5),
            ),
        )
    assert egress_port.calls == 1
