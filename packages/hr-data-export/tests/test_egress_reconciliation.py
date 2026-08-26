"""Regression tests for ambiguous one-time HR export delivery outcomes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from orgmetra_hr_data_export import HrDataExportReviewPacket
from orgmetra_hr_data_export.execution import (
    HrDataExportArtifact,
    HrDataExportAuditReceipt,
    HrDataExportDeliveryIndeterminateError,
    HrDataExportEgressReceipt,
    HrDataExportExecutionReceipt,
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


def _review() -> HrDataExportReviewPacket:
    """Build one valid reviewed export scope without retaining HR values."""
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


def _verification(review: HrDataExportReviewPacket) -> HrDataExportExecutionVerification:
    """Build current export-specific authority evidence for the reviewed scope."""
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
        authorization_expires_at=BASE_TIME + timedelta(minutes=10),
    )


class _Clock:
    """Return deterministic request, authorization, audit, publish and observation instants."""

    def __init__(self) -> None:
        """Seed the exact five clock readings used by one successful execution attempt."""
        self.values = iter(
            [
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
                BASE_TIME + timedelta(seconds=3),
                BASE_TIME + timedelta(seconds=4),
            ]
        )

    def __call__(self) -> datetime:
        """Return the next deterministic UTC instant."""
        return next(self.values)


class _ClockFailsAfterPublish(_Clock):
    """Model clock loss after the outbound side effect may already have occurred."""

    def __init__(self) -> None:
        """Track reads so only the post-publication observation fails."""
        super().__init__()
        self.calls = 0

    def __call__(self) -> datetime:
        """Raise on the fifth read, which is the first read after publication."""
        self.calls += 1
        if self.calls == 5:
            raise RuntimeError("clock unavailable after publication")
        return super().__call__()


class _Authority:
    """Return one exact current export verification."""

    def __init__(self, verification: HrDataExportExecutionVerification) -> None:
        """Store the governed verification returned by the fake authority."""
        self.verification = verification

    def verify_export(self, **_: object) -> object:
        """Return the configured current authority evidence."""
        return self.verification


class _Materializer:
    """Return one bounded transient export artifact."""

    def __init__(self, artifact: HrDataExportArtifact) -> None:
        """Store the protected artifact returned by the fake materializer."""
        self.artifact = artifact

    def materialize_export(self, **_: object) -> object:
        """Return the configured artifact without creating durable HR-value evidence."""
        return self.artifact


class _Audit:
    """Return one immutable pre-delivery audit receipt."""

    def __init__(self, receipt: HrDataExportAuditReceipt) -> None:
        """Store the value-minimized audit receipt returned by the fake audit port."""
        self.receipt = receipt

    def append_pre_delivery_audit(self, **_: object) -> object:
        """Return the configured audit-before-egress evidence."""
        return self.receipt


class _AmbiguousEgress:
    """Model delivery that succeeds externally but returns an unusable first receipt."""

    def __init__(self, reconciled_receipt: object) -> None:
        """Store authoritative reconciliation output and initialize side-effect counters."""
        self.reconciled_receipt = reconciled_receipt
        self.publish_calls = 0
        self.reconcile_calls = 0

    def publish_one_time_download(self, **_: object) -> object:
        """Record exactly one external publish while returning unusable immediate evidence."""
        self.publish_calls += 1
        return object()

    def reconcile_one_time_download(self, **_: object) -> object:
        """Look up existing delivery evidence without causing another publication."""
        self.reconcile_calls += 1
        return self.reconciled_receipt


class _PublishRaisesAfterSideEffect(_AmbiguousEgress):
    """Model a transport exception after the host may already have completed delivery."""

    def publish_one_time_download(self, **_: object) -> object:
        """Record the single possible side effect, then lose the immediate response."""
        self.publish_calls += 1
        raise TimeoutError("delivery response lost after side effect")


def _execution_inputs() -> tuple[
    HrDataExportReviewPacket,
    HrDataExportExecutionVerification,
    HrDataExportArtifact,
    HrDataExportAuditReceipt,
    HrDataExportEgressReceipt,
]:
    """Build one internally consistent reviewed, authorized, audited export fixture."""
    review = _review()
    verification = _verification(review)
    artifact = HrDataExportArtifact(
        field_names=FIELDS,
        content_type="application/json",
        content=b'{"email_address":"a@example.test","employee_number":"E-1"}',
    )
    audit_receipt = HrDataExportAuditReceipt(
        tenant_record_id=TENANT_ID,
        export_execution_reference=EXECUTION_REFERENCE,
        export_review_digest=verification.export_review_digest,
        execution_authorization_digest=DIGEST_B,
        human_approval_digest=DIGEST_C,
        artifact_sha256_digest=artifact.sha256_digest,
        artifact_byte_length=artifact.byte_length,
        audit_event_reference=AUDIT_REFERENCE,
        recorded_at=BASE_TIME + timedelta(seconds=2),
    )
    reconciled = HrDataExportEgressReceipt(
        tenant_record_id=TENANT_ID,
        export_execution_reference=EXECUTION_REFERENCE,
        artifact_sha256_digest=sha256(artifact.content).hexdigest(),
        artifact_byte_length=artifact.byte_length,
        audit_event_reference=AUDIT_REFERENCE,
        egress_reference=EGRESS_REFERENCE,
        destination_kind="authenticated_one_time_download",
        one_time_use_enforced=True,
        delivered_at=BASE_TIME + timedelta(seconds=4),
    )
    return review, verification, artifact, audit_receipt, reconciled


def _execute(egress: object, clock: object) -> HrDataExportExecutionReceipt:
    """Execute one fixture through the public governed export boundary."""
    review, verification, artifact, audit_receipt, _ = _execution_inputs()
    return execute_reviewed_hr_export(
        review=review,
        authority=_Authority(verification),
        materializer=_Materializer(artifact),
        audit_port=_Audit(audit_receipt),
        egress_port=egress,  # type: ignore[arg-type]
        now_provider=clock,  # type: ignore[arg-type]
    )


def test_invalid_post_side_effect_receipt_reconciles_without_republishing() -> None:
    """Malformed immediate evidence is reconciled by correlation without a second publish."""
    *_, reconciled = _execution_inputs()
    egress = _AmbiguousEgress(reconciled)

    receipt = _execute(egress, _Clock())

    assert isinstance(receipt, HrDataExportExecutionReceipt)
    assert receipt.egress_reference == EGRESS_REFERENCE
    assert egress.publish_calls == 1
    assert egress.reconcile_calls == 1


def test_publish_exception_reconciles_existing_delivery_without_republishing() -> None:
    """A lost publish response reconciles the existing execution instead of retrying egress."""
    *_, reconciled = _execution_inputs()
    egress = _PublishRaisesAfterSideEffect(reconciled)

    receipt = _execute(egress, _Clock())

    assert receipt.egress_reference == EGRESS_REFERENCE
    assert egress.publish_calls == 1
    assert egress.reconcile_calls == 1


def test_unreconciled_delivery_is_explicitly_nonretryable() -> None:
    """Absent authoritative reconciliation fails as indeterminate and never republishes."""
    egress = _AmbiguousEgress(object())

    with pytest.raises(HrDataExportDeliveryIndeterminateError, match="do not republish automatically"):
        _execute(egress, _Clock())

    assert egress.publish_calls == 1
    assert egress.reconcile_calls == 1


def test_clock_loss_after_publish_is_indeterminate_not_retryable() -> None:
    """Clock failure after the side effect cannot be misreported as a safe retry opportunity."""
    *_, reconciled = _execution_inputs()
    egress = _AmbiguousEgress(reconciled)

    with pytest.raises(HrDataExportDeliveryIndeterminateError, match="do not republish automatically"):
        _execute(egress, _ClockFailsAfterPublish())

    assert egress.publish_calls == 1
    assert egress.reconcile_calls == 0
