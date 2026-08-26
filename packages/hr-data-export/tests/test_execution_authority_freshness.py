"""Regression for authority expiry before protected HR export materialization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from orgmetra_hr_data_export import HrDataExportReviewPacket
from orgmetra_hr_data_export.execution import (
    HrDataExportArtifact,
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
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
FIELDS = ("email_address", "employee_number")


def test_expiry_during_authority_blocks_protected_materialization() -> None:
    """A slow authority call must not let expired scope reach protected HR field reads."""
    review = HrDataExportReviewPacket(
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
    verification = HrDataExportExecutionVerification(
        tenant_record_id=TENANT_ID,
        export_execution_reference=EXECUTION_REFERENCE,
        export_review_reference=EXPORT_REVIEW_REFERENCE,
        export_review_digest=review.sha256_digest(),
        resource_kind="employment_record",
        resource_reference=RESOURCE_REFERENCE,
        requested_fields=FIELDS,
        export_format_code="json",
        destination_kind="authenticated_one_time_download",
        execution_authorization_reference=EXECUTION_AUTHORIZATION_REFERENCE,
        execution_authorization_digest=DIGEST_B,
        authorization_policy_version_code="policy:v2",
        human_approval_reference=HUMAN_APPROVAL_REFERENCE,
        human_approval_digest=DIGEST_C,
        retention_state="retention_permits_export",
        legal_hold_state="no_legal_hold_block",
        verified_at=BASE_TIME,
        authorization_expires_at=BASE_TIME + timedelta(seconds=2),
    )
    artifact = HrDataExportArtifact(
        field_names=FIELDS,
        content_type="application/json",
        content=b'{"email_address":"a@example.test","employee_number":"E-1"}',
    )
    events: list[str] = []

    class Authority:
        def verify_export(self, **_: object) -> object:
            events.append("authority")
            return verification

    class Materializer:
        def materialize_export(self, **_: object) -> object:
            events.append("materialize")
            return artifact

    instants = iter((BASE_TIME + timedelta(seconds=1), BASE_TIME + timedelta(seconds=3)))

    def clock() -> datetime:
        return next(instants)

    with pytest.raises(HrDataExportExecutionError, match="expired"):
        execute_reviewed_hr_export(
            review=review,
            authority=Authority(),
            materializer=Materializer(),
            audit_port=object(),
            egress_port=object(),
            now_provider=clock,
        )

    assert events == ["authority"]
    assert sha256(artifact.content).hexdigest() == artifact.sha256_digest
