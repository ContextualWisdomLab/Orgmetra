"""Adversarial contract tests for purpose-bound HR export execution.

The execution boundary is deliberately stricter than the pre-export review packet. It must
freshly re-authorize the exact reviewed scope, materialize only the reviewed fields, append
immutable value-minimized audit evidence before bytes leave Orgmetra, re-check authorization
freshness after protected work, and require a one-time-delivery receipt from the host egress
boundary. Raw HR field values never enter durable execution receipts.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4

import pytest

from orgmetra_hr_data_export import HrDataExportReviewPacket
from orgmetra_hr_data_export.execution import (
    HrDataExportArtifact,
    HrDataExportAuditReceipt,
    HrDataExportEgressReceipt,
    HrDataExportExecutionError,
    HrDataExportExecutionReceipt,
    HrDataExportExecutionVerification,
    execute_reviewed_hr_export,
)

UTC = timezone.utc
TENANT_ID = "11111111-1111-4111-8111-111111111111"
RESOURCE_REFERENCE = "employment_record:22222222-2222-4222-8222-222222222222"
EXPORT_REVIEW_REFERENCE = "export_review:33333333-3333-4333-8333-333333333333"
AUTHORIZATION_REFERENCE = "authorization_decision:44444444-4444-4444-8444-444444444444"
REQUESTER_REFERENCE = "actor:55555555-5555-4555-8555-555555555555"
REVIEWER_REFERENCE = "actor:66666666-6666-4666-8666-666666666666"
EXECUTION_REFERENCE = "export_execution:77777777-7777-4777-8777-777777777777"
EXECUTION_AUTHORIZATION_REFERENCE = (
    "export_authorization:88888888-8888-4888-8888-888888888888"
)
HUMAN_APPROVAL_REFERENCE = "export_approval:99999999-9999-4999-8999-999999999999"
AUDIT_REFERENCE = "audit_event:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
EGRESS_REFERENCE = "one_time_download:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
FIELDS = ("email_address", "employee_number")
BASE_TIME = datetime(2026, 8, 26, 0, 0, tzinfo=UTC)


def make_review() -> HrDataExportReviewPacket:
    """Return one valid value-minimized pre-export review packet."""
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
    requested_fields: tuple[str, ...] = FIELDS,
    authorization_expires_at: datetime | None = None,
    retention_state: str = "retention_permits_export",
    legal_hold_state: str = "no_legal_hold_block",
) -> HrDataExportExecutionVerification:
    """Return an authoritative verification bound to the exact reviewed scope."""
    return HrDataExportExecutionVerification(
        tenant_record_id=review.tenant_record_id,
        export_execution_reference=EXECUTION_REFERENCE,
        export_review_reference=review.export_review_reference,
        export_review_digest=review.sha256_digest(),
        resource_kind=review.resource_kind,
        resource_reference=review.resource_reference,
        requested_fields=requested_fields,
        export_format_code=review.export_format_code,
        destination_kind=review.destination_kind,
        execution_authorization_reference=EXECUTION_AUTHORIZATION_REFERENCE,
        execution_authorization_digest=DIGEST_B,
        authorization_policy_version_code="policy:v2",
        human_approval_reference=HUMAN_APPROVAL_REFERENCE,
        human_approval_digest=DIGEST_C,
        retention_state=retention_state,
        legal_hold_state=legal_hold_state,
        verified_at=BASE_TIME,
        authorization_expires_at=(
            authorization_expires_at
            if authorization_expires_at is not None
            else BASE_TIME + timedelta(minutes=10)
        ),
    )


class SequenceClock:
    """Return exact UTC instants in sequence so TOCTOU boundaries are testable."""

    def __init__(self, *values: datetime) -> None:
        self._values = list(values)
        self.calls = 0

    def __call__(self) -> datetime:
        """Return the next configured instant and count the call."""
        self.calls += 1
        if not self._values:
            raise AssertionError("clock called more often than expected")
        return self._values.pop(0)


class FakeAuthority:
    """Record authority calls and return one preconfigured exact verification."""

    def __init__(self, verification: object, events: list[str]) -> None:
        self.verification = verification
        self.events = events
        self.calls = 0

    def verify_export(
        self,
        *,
        review: HrDataExportReviewPacket,
        review_digest: str,
        requested_at: datetime,
    ) -> object:
        """Return authoritative export scope after recording the protected call."""
        self.calls += 1
        self.events.append("authority")
        assert review_digest == review.sha256_digest()
        assert requested_at.tzinfo is UTC
        return self.verification


class FakeMaterializer:
    """Materialize one bounded payload and expose no durable field values."""

    def __init__(self, artifact: object, events: list[str]) -> None:
        self.artifact = artifact
        self.events = events
        self.calls = 0

    def materialize_export(
        self,
        *,
        verification: HrDataExportExecutionVerification,
    ) -> object:
        """Return the configured artifact for the verified authoritative scope."""
        self.calls += 1
        self.events.append("materialize")
        assert verification.export_execution_reference == EXECUTION_REFERENCE
        return self.artifact


class FakeAudit:
    """Append one pre-delivery immutable audit receipt before egress."""

    def __init__(self, receipt: object, events: list[str]) -> None:
        self.receipt = receipt
        self.events = events
        self.calls = 0

    def append_pre_delivery_audit(
        self,
        *,
        verification: HrDataExportExecutionVerification,
        artifact: HrDataExportArtifact,
        recorded_at: datetime,
    ) -> object:
        """Return the configured immutable audit receipt without raw HR values."""
        self.calls += 1
        self.events.append("audit")
        assert verification.export_execution_reference == EXECUTION_REFERENCE
        assert artifact.sha256_digest == sha256(artifact.content).hexdigest()
        assert recorded_at.tzinfo is UTC
        return self.receipt


class FakeEgress:
    """Publish bytes through one host-owned one-time-download boundary."""

    def __init__(self, receipt: object, events: list[str]) -> None:
        self.receipt = receipt
        self.events = events
        self.calls = 0
        self.last_payload: bytes | None = None

    def publish_one_time_download(
        self,
        *,
        verification: HrDataExportExecutionVerification,
        artifact: HrDataExportArtifact,
        audit_receipt: HrDataExportAuditReceipt,
        published_at: datetime,
    ) -> object:
        """Record the outbound payload and return the host egress receipt."""
        self.calls += 1
        self.events.append("egress")
        self.last_payload = artifact.content
        assert audit_receipt.audit_state == "committed_before_delivery"
        assert published_at.tzinfo is UTC
        return self.receipt


def make_artifact(
    *,
    fields: tuple[str, ...] = FIELDS,
    content: bytes = b'{"email_address":"a@example.test","employee_number":"E-1"}',
    content_type: str = "application/json",
) -> HrDataExportArtifact:
    """Return one exact materialized export artifact."""
    return HrDataExportArtifact(
        field_names=fields,
        content_type=content_type,
        content=content,
    )


def make_audit_receipt(
    verification: HrDataExportExecutionVerification,
    artifact: HrDataExportArtifact,
    *,
    artifact_digest: str | None = None,
    byte_length: int | None = None,
    recorded_at: datetime = BASE_TIME + timedelta(seconds=2),
) -> HrDataExportAuditReceipt:
    """Return one exact pre-delivery audit receipt."""
    return HrDataExportAuditReceipt(
        tenant_record_id=verification.tenant_record_id,
        export_execution_reference=verification.export_execution_reference,
        export_review_digest=verification.export_review_digest,
        execution_authorization_digest=verification.execution_authorization_digest,
        human_approval_digest=verification.human_approval_digest,
        artifact_sha256_digest=(artifact_digest or artifact.sha256_digest),
        artifact_byte_length=(
            byte_length if byte_length is not None else artifact.byte_length
        ),
        audit_event_reference=AUDIT_REFERENCE,
        recorded_at=recorded_at,
    )


def make_egress_receipt(
    verification: HrDataExportExecutionVerification,
    artifact: HrDataExportArtifact,
    audit_receipt: HrDataExportAuditReceipt,
    *,
    artifact_digest: str | None = None,
    byte_length: int | None = None,
    delivered_at: datetime = BASE_TIME + timedelta(seconds=4),
    one_time_use_enforced: bool = True,
) -> HrDataExportEgressReceipt:
    """Return one exact one-time egress receipt bound to pre-delivery audit evidence."""
    return HrDataExportEgressReceipt(
        tenant_record_id=verification.tenant_record_id,
        export_execution_reference=verification.export_execution_reference,
        artifact_sha256_digest=(artifact_digest or artifact.sha256_digest),
        artifact_byte_length=(
            byte_length if byte_length is not None else artifact.byte_length
        ),
        audit_event_reference=audit_receipt.audit_event_reference,
        egress_reference=EGRESS_REFERENCE,
        destination_kind=verification.destination_kind,
        one_time_use_enforced=one_time_use_enforced,
        delivered_at=delivered_at,
    )


def make_ports(
    *,
    review: HrDataExportReviewPacket | None = None,
    clock: SequenceClock | None = None,
) -> tuple[
    HrDataExportReviewPacket,
    HrDataExportExecutionVerification,
    HrDataExportArtifact,
    FakeAuthority,
    FakeMaterializer,
    FakeAudit,
    FakeEgress,
    SequenceClock,
    list[str],
]:
    """Build one coherent success fixture with explicit call-order evidence."""
    governed_review = review or make_review()
    verification = make_verification(governed_review)
    artifact = make_artifact()
    audit_receipt = make_audit_receipt(verification, artifact)
    egress_receipt = make_egress_receipt(verification, artifact, audit_receipt)
    events: list[str] = []
    sequence_clock = clock or SequenceClock(
        BASE_TIME + timedelta(seconds=1),
        BASE_TIME + timedelta(seconds=2),
        BASE_TIME + timedelta(seconds=3),
        BASE_TIME + timedelta(seconds=4),
    )
    return (
        governed_review,
        verification,
        artifact,
        FakeAuthority(verification, events),
        FakeMaterializer(artifact, events),
        FakeAudit(audit_receipt, events),
        FakeEgress(egress_receipt, events),
        sequence_clock,
        events,
    )


def test_success_audits_before_one_time_egress_and_returns_value_free_receipt() -> None:
    """Successful export must audit before egress and return no protected HR field values."""
    review, _, artifact, authority, materializer, audit, egress, clock, events = make_ports()

    receipt = execute_reviewed_hr_export(
        review=review,
        authority=authority,
        materializer=materializer,
        audit_port=audit,
        egress_port=egress,
        now_provider=clock,
    )

    assert events == ["authority", "materialize", "audit", "egress"]
    assert egress.last_payload == artifact.content
    assert receipt.export_state == "export_delivered"
    assert receipt.contains_pii_values is False
    assert receipt.one_time_use_enforced is True
    assert receipt.artifact_sha256_digest == artifact.sha256_digest
    assert receipt.artifact_byte_length == len(artifact.content)
    canonical = receipt.canonical_json()
    assert "a@example.test" not in canonical
    assert "E-1" not in canonical
    assert receipt.sha256_digest() == sha256(canonical.encode("utf-8")).hexdigest()


def test_tampered_review_fails_before_authority() -> None:
    """Post-review field-scope mutation must not reach authoritative resolution."""
    review, _, _, authority, materializer, audit, egress, clock, events = make_ports()
    object.__setattr__(review, "requested_fields", ("salary_amount",))

    with pytest.raises(ValueError):
        execute_reviewed_hr_export(
            review=review,
            authority=authority,
            materializer=materializer,
            audit_port=audit,
            egress_port=egress,
            now_provider=clock,
        )

    assert events == []


def test_wrong_verification_runtime_type_fails_before_materialization() -> None:
    """Caller objects that only look like authority evidence must never reach protected reads."""
    review = make_review()
    events: list[str] = []
    authority = FakeAuthority(object(), events)
    materializer = FakeMaterializer(make_artifact(), events)
    audit = FakeAudit(object(), events)
    egress = FakeEgress(object(), events)

    with pytest.raises(HrDataExportExecutionError, match="verification"):
        execute_reviewed_hr_export(
            review=review,
            authority=authority,
            materializer=materializer,
            audit_port=audit,
            egress_port=egress,
            now_provider=SequenceClock(BASE_TIME + timedelta(seconds=1)),
        )

    assert events == ["authority"]
    assert materializer.calls == audit.calls == egress.calls == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_record_id", "21111111-1111-4111-8111-111111111111"),
        ("export_review_reference", "export_review:00000000-0000-4000-8000-000000000001"),
        ("resource_reference", "employment_record:00000000-0000-4000-8000-000000000002"),
        ("requested_fields", ("email_address",)),
        ("export_format_code", "csv"),
        ("destination_kind", "email_attachment"),
        ("export_review_digest", DIGEST_D),
    ],
)
def test_authority_scope_mismatch_fails_before_materialization(field: str, value: Any) -> None:
    """Every authority field must match the exact reviewed scope before protected data is read."""
    review = make_review()
    verification = make_verification(review)
    object.__setattr__(verification, field, value)
    events: list[str] = []
    authority = FakeAuthority(verification, events)
    materializer = FakeMaterializer(make_artifact(), events)

    with pytest.raises(HrDataExportExecutionError, match="scope"):
        execute_reviewed_hr_export(
            review=review,
            authority=authority,
            materializer=materializer,
            audit_port=FakeAudit(object(), events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(BASE_TIME + timedelta(seconds=1)),
        )

    assert events == ["authority"]
    assert materializer.calls == 0


@pytest.mark.parametrize(
    ("retention_state", "legal_hold_state"),
    [
        ("retention_blocks_export", "no_legal_hold_block"),
        ("retention_permits_export", "legal_hold_blocks_export"),
    ],
)
def test_policy_block_fails_before_materialization(
    retention_state: str,
    legal_hold_state: str,
) -> None:
    """Retention or legal-hold blocks must prevent protected export-field materialization."""
    review = make_review()
    verification = make_verification(
        review,
        retention_state=retention_state,
        legal_hold_state=legal_hold_state,
    )
    events: list[str] = []
    authority = FakeAuthority(verification, events)

    with pytest.raises(HrDataExportExecutionError, match="policy"):
        execute_reviewed_hr_export(
            review=review,
            authority=authority,
            materializer=FakeMaterializer(make_artifact(), events),
            audit_port=FakeAudit(object(), events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(BASE_TIME + timedelta(seconds=1)),
        )

    assert events == ["authority"]


def test_expired_authorization_fails_before_materialization() -> None:
    """An authority decision that is already expired must not unlock HR field reads."""
    review = make_review()
    verification = make_verification(
        review,
        authorization_expires_at=BASE_TIME + timedelta(milliseconds=500),
    )
    events: list[str] = []

    with pytest.raises(HrDataExportExecutionError, match="expired"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(make_artifact(), events),
            audit_port=FakeAudit(object(), events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(BASE_TIME + timedelta(seconds=1)),
        )

    assert events == ["authority"]


@pytest.mark.parametrize(
    "artifact",
    [
        make_artifact(fields=("email_address",)),
        make_artifact(content_type="text/csv"),
        make_artifact(content=b"x" * (10 * 1024 * 1024 + 1)),
    ],
)
def test_artifact_scope_or_size_mismatch_fails_before_audit_and_egress(
    artifact: HrDataExportArtifact,
) -> None:
    """Materialized bytes must exactly match reviewed fields/format and the 10 MiB budget."""
    review = make_review()
    verification = make_verification(review)
    events: list[str] = []
    audit = FakeAudit(object(), events)
    egress = FakeEgress(object(), events)

    with pytest.raises((HrDataExportExecutionError, ValueError)):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(artifact, events),
            audit_port=audit,
            egress_port=egress,
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
            ),
        )

    assert events == ["authority", "materialize"]
    assert audit.calls == egress.calls == 0


def test_authorization_expiring_during_materialization_blocks_audit_and_egress() -> None:
    """Authorization freshness must be rechecked after protected materialization."""
    review = make_review()
    verification = make_verification(
        review,
        authorization_expires_at=BASE_TIME + timedelta(seconds=2),
    )
    events: list[str] = []

    with pytest.raises(HrDataExportExecutionError, match="expired"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(make_artifact(), events),
            audit_port=FakeAudit(object(), events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=3),
            ),
        )

    assert events == ["authority", "materialize"]


def test_mismatched_audit_receipt_blocks_egress() -> None:
    """Pre-delivery audit evidence must bind the exact artifact before bytes can leave."""
    review = make_review()
    verification = make_verification(review)
    artifact = make_artifact()
    events: list[str] = []
    audit_receipt = make_audit_receipt(
        verification,
        artifact,
        artifact_digest=DIGEST_D,
    )
    egress = FakeEgress(object(), events)

    with pytest.raises(HrDataExportExecutionError, match="audit"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(artifact, events),
            audit_port=FakeAudit(audit_receipt, events),
            egress_port=egress,
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
                BASE_TIME + timedelta(seconds=3),
            ),
        )

    assert events == ["authority", "materialize", "audit"]
    assert egress.calls == 0


def test_authorization_expiring_during_audit_blocks_egress() -> None:
    """Audit latency must not let an expired authorization become an outbound transfer."""
    review = make_review()
    verification = make_verification(
        review,
        authorization_expires_at=BASE_TIME + timedelta(seconds=3),
    )
    artifact = make_artifact()
    audit_receipt = make_audit_receipt(verification, artifact)
    events: list[str] = []

    with pytest.raises(HrDataExportExecutionError, match="expired"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(artifact, events),
            audit_port=FakeAudit(audit_receipt, events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
                BASE_TIME + timedelta(seconds=4),
            ),
        )

    assert events == ["authority", "materialize", "audit"]


def test_mismatched_egress_receipt_fails_closed_after_host_delivery() -> None:
    """A lying egress adapter must never produce a successful Orgmetra execution receipt."""
    review = make_review()
    verification = make_verification(review)
    artifact = make_artifact()
    audit_receipt = make_audit_receipt(verification, artifact)
    bad_egress_receipt = make_egress_receipt(
        verification,
        artifact,
        audit_receipt,
        byte_length=artifact.byte_length + 1,
    )
    events: list[str] = []

    with pytest.raises(HrDataExportExecutionError, match="egress"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(artifact, events),
            audit_port=FakeAudit(audit_receipt, events),
            egress_port=FakeEgress(bad_egress_receipt, events),
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
                BASE_TIME + timedelta(seconds=3),
                BASE_TIME + timedelta(seconds=4),
            ),
        )

    assert events == ["authority", "materialize", "audit", "egress"]


def test_direct_execution_receipt_construction_is_forbidden() -> None:
    """Only the governed orchestration path may issue a successful execution receipt."""
    with pytest.raises(TypeError, match="issued"):
        HrDataExportExecutionReceipt(
            tenant_record_id=TENANT_ID,
            export_execution_reference=EXECUTION_REFERENCE,
            export_review_reference=EXPORT_REVIEW_REFERENCE,
            export_review_digest=DIGEST_A,
            execution_authorization_reference=EXECUTION_AUTHORIZATION_REFERENCE,
            execution_authorization_digest=DIGEST_B,
            human_approval_reference=HUMAN_APPROVAL_REFERENCE,
            human_approval_digest=DIGEST_C,
            artifact_sha256_digest=DIGEST_D,
            artifact_byte_length=1,
            audit_event_reference=AUDIT_REFERENCE,
            egress_reference=EGRESS_REFERENCE,
            destination_kind="authenticated_one_time_download",
            one_time_use_enforced=True,
            audited_at=BASE_TIME,
            delivered_at=BASE_TIME,
        )


def test_issued_execution_receipt_detects_post_issuance_tampering() -> None:
    """Changing receipt evidence after issuance must invalidate later canonicalization."""
    review, _, _, authority, materializer, audit, egress, clock, _ = make_ports()
    receipt = execute_reviewed_hr_export(
        review=review,
        authority=authority,
        materializer=materializer,
        audit_port=audit,
        egress_port=egress,
        now_provider=clock,
    )
    object.__setattr__(receipt, "artifact_byte_length", receipt.artifact_byte_length + 1)

    with pytest.raises(HrDataExportExecutionError, match="tampered"):
        receipt.canonical_json()


def test_authority_must_return_exact_verification_type_not_subclass() -> None:
    """Governed verification evidence is final and cannot be subclassed to override behavior."""
    with pytest.raises(TypeError):
        type("ForgedVerification", (HrDataExportExecutionVerification,), {})


def test_artifact_requires_exact_bytes_and_bounded_size() -> None:
    """Artifact construction rejects mutable bytearrays and payloads above the hard budget."""
    with pytest.raises(ValueError, match="bytes"):
        HrDataExportArtifact(
            field_names=FIELDS,
            content_type="application/json",
            content=bytearray(b"{}"),  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="10 MiB"):
        HrDataExportArtifact(
            field_names=FIELDS,
            content_type="application/json",
            content=b"x" * (10 * 1024 * 1024 + 1),
        )


def test_random_uuid4_helpers_remain_opaque_and_nonsemantic() -> None:
    """The test corpus may create opaque UUIDv4 correlations without encoding HR meaning."""
    generated = str(uuid4())
    assert len(generated) == 36
