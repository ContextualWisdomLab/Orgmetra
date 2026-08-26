"""Adversarial contract tests for purpose-bound HR export execution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

import pytest

import orgmetra_hr_data_export.execution as execution_module
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
EXECUTION_AUTHORIZATION_REFERENCE = "export_authorization:88888888-8888-4888-8888-888888888888"
HUMAN_APPROVAL_REFERENCE = "export_approval:99999999-9999-4999-8999-999999999999"
AUDIT_REFERENCE = "audit_event:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
EGRESS_REFERENCE = "one_time_download:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
FIELDS = ("email_address", "employee_number")
BASE_TIME = datetime(2026, 8, 26, 0, 0, tzinfo=UTC)


def make_review(*, export_format_code: str = "json") -> HrDataExportReviewPacket:
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
        export_format_code=export_format_code,
        destination_kind="authenticated_one_time_download",
        generated_at=BASE_TIME - timedelta(minutes=5),
    )


def verification_kwargs(review: HrDataExportReviewPacket) -> dict[str, Any]:
    """Return exact verification constructor values for one reviewed scope."""
    return {
        "tenant_record_id": review.tenant_record_id,
        "export_execution_reference": EXECUTION_REFERENCE,
        "export_review_reference": review.export_review_reference,
        "export_review_digest": review.sha256_digest(),
        "resource_kind": review.resource_kind,
        "resource_reference": review.resource_reference,
        "requested_fields": review.requested_fields,
        "export_format_code": review.export_format_code,
        "destination_kind": review.destination_kind,
        "execution_authorization_reference": EXECUTION_AUTHORIZATION_REFERENCE,
        "execution_authorization_digest": DIGEST_B,
        "authorization_policy_version_code": "policy:v2",
        "human_approval_reference": HUMAN_APPROVAL_REFERENCE,
        "human_approval_digest": DIGEST_C,
        "retention_state": "retention_permits_export",
        "legal_hold_state": "no_legal_hold_block",
        "verified_at": BASE_TIME,
        "authorization_expires_at": BASE_TIME + timedelta(minutes=10),
    }


def make_verification(
    review: HrDataExportReviewPacket,
    **overrides: Any,
) -> HrDataExportExecutionVerification:
    """Return one authoritative verification with optional controlled overrides."""
    values = verification_kwargs(review)
    values.update(overrides)
    return HrDataExportExecutionVerification(**values)


class SequenceClock:
    """Return exact instants in order so authorization TOCTOU checks are observable."""

    def __init__(self, *values: datetime) -> None:
        self.values = list(values)

    def __call__(self) -> datetime:
        """Return the next configured time or make unexpected extra clock reads fail."""
        if not self.values:
            raise AssertionError("clock called more often than expected")
        return self.values.pop(0)


class FakeAuthority:
    """Return one configured authority result while recording the protected call order."""

    def __init__(self, result: object, events: list[str]) -> None:
        self.result = result
        self.events = events

    def verify_export(
        self,
        *,
        review: HrDataExportReviewPacket,
        review_digest: str,
        requested_at: datetime,
    ) -> object:
        """Return configured evidence after checking the exact review digest and UTC instant."""
        self.events.append("authority")
        assert review_digest == review.sha256_digest()
        assert requested_at.tzinfo is UTC
        return self.result


class MutatingAuthority(FakeAuthority):
    """Attempt to rewrite valid-looking review scope during authoritative verification."""

    def verify_export(
        self,
        *,
        review: HrDataExportReviewPacket,
        review_digest: str,
        requested_at: datetime,
    ) -> object:
        """Mutate after receipt without relying on packet serialization after the mutation."""
        self.events.append("authority")
        assert review_digest
        assert requested_at.tzinfo is UTC
        object.__setattr__(review, "requested_fields", ("employee_number",))
        return self.result


class FakeMaterializer:
    """Return one configured artifact while recording protected field materialization."""

    def __init__(self, result: object, events: list[str]) -> None:
        self.result = result
        self.events = events

    def materialize_export(self, *, verification: HrDataExportExecutionVerification) -> object:
        """Return configured materialization evidence for the exact execution correlation."""
        self.events.append("materialize")
        assert verification.export_execution_reference == EXECUTION_REFERENCE
        return self.result


class FakeAudit:
    """Return one configured pre-delivery audit receipt."""

    def __init__(self, result: object, events: list[str]) -> None:
        self.result = result
        self.events = events

    def append_pre_delivery_audit(
        self,
        *,
        verification: HrDataExportExecutionVerification,
        artifact: HrDataExportArtifact,
        recorded_at: datetime,
    ) -> object:
        """Record audit-before-egress ordering without retaining protected field values."""
        self.events.append("audit")
        assert verification.export_execution_reference == EXECUTION_REFERENCE
        assert artifact.sha256_digest == sha256(artifact.content).hexdigest()
        assert recorded_at.tzinfo is UTC
        return self.result


class FakeEgress:
    """Return one configured one-time-delivery receipt and record the transient bytes seen."""

    def __init__(self, result: object, events: list[str]) -> None:
        self.result = result
        self.events = events
        self.last_payload: bytes | None = None

    def publish_one_time_download(
        self,
        *,
        verification: HrDataExportExecutionVerification,
        artifact: HrDataExportArtifact,
        audit_receipt: HrDataExportAuditReceipt,
        published_at: datetime,
    ) -> object:
        """Record outbound ordering and return configured host delivery evidence."""
        self.events.append("egress")
        self.last_payload = artifact.content
        assert verification.export_execution_reference == EXECUTION_REFERENCE
        assert audit_receipt.audit_state == "committed_before_delivery"
        assert published_at.tzinfo is UTC
        return self.result


def make_artifact(
    *,
    fields: tuple[str, ...] = FIELDS,
    content_type: str = "application/json",
    content: bytes = b'{"email_address":"a@example.test","employee_number":"E-1"}',
) -> HrDataExportArtifact:
    """Return one bounded exact transient export artifact."""
    return HrDataExportArtifact(field_names=fields, content_type=content_type, content=content)


def make_audit_receipt(
    verification: HrDataExportExecutionVerification,
    artifact: HrDataExportArtifact,
    **overrides: Any,
) -> HrDataExportAuditReceipt:
    """Return one pre-delivery audit receipt bound to current artifact evidence."""
    values: dict[str, Any] = {
        "tenant_record_id": verification.tenant_record_id,
        "export_execution_reference": verification.export_execution_reference,
        "export_review_digest": verification.export_review_digest,
        "execution_authorization_digest": verification.execution_authorization_digest,
        "human_approval_digest": verification.human_approval_digest,
        "artifact_sha256_digest": artifact.sha256_digest,
        "artifact_byte_length": artifact.byte_length,
        "audit_event_reference": AUDIT_REFERENCE,
        "recorded_at": BASE_TIME + timedelta(seconds=2),
    }
    values.update(overrides)
    return HrDataExportAuditReceipt(**values)


def make_egress_receipt(
    verification: HrDataExportExecutionVerification,
    artifact: HrDataExportArtifact,
    audit_receipt: HrDataExportAuditReceipt,
    **overrides: Any,
) -> HrDataExportEgressReceipt:
    """Return one exact one-time egress receipt bound to pre-delivery audit evidence."""
    values: dict[str, Any] = {
        "tenant_record_id": verification.tenant_record_id,
        "export_execution_reference": verification.export_execution_reference,
        "artifact_sha256_digest": artifact.sha256_digest,
        "artifact_byte_length": artifact.byte_length,
        "audit_event_reference": audit_receipt.audit_event_reference,
        "egress_reference": EGRESS_REFERENCE,
        "destination_kind": verification.destination_kind,
        "one_time_use_enforced": True,
        "delivered_at": BASE_TIME + timedelta(seconds=4),
    }
    values.update(overrides)
    return HrDataExportEgressReceipt(**values)


def success_ports(
    *,
    export_format_code: str = "json",
    content_type: str | None = None,
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
    """Return one complete exact-scope success fixture."""
    review = make_review(export_format_code=export_format_code)
    verification = make_verification(review)
    artifact = make_artifact(
        content_type=content_type or ("application/json" if export_format_code == "json" else "text/csv")
    )
    audit_receipt = make_audit_receipt(verification, artifact)
    egress_receipt = make_egress_receipt(verification, artifact, audit_receipt)
    events: list[str] = []
    return (
        review,
        verification,
        artifact,
        FakeAuthority(verification, events),
        FakeMaterializer(artifact, events),
        FakeAudit(audit_receipt, events),
        FakeEgress(egress_receipt, events),
        SequenceClock(
            BASE_TIME + timedelta(seconds=1),
            BASE_TIME + timedelta(seconds=2),
            BASE_TIME + timedelta(seconds=3),
            BASE_TIME + timedelta(seconds=4),
        ),
        events,
    )


def execute_fixture(
    review: HrDataExportReviewPacket,
    authority: FakeAuthority,
    materializer: FakeMaterializer,
    audit: FakeAudit,
    egress: FakeEgress,
    clock: SequenceClock,
) -> HrDataExportExecutionReceipt:
    """Execute one fixture through the public governed boundary."""
    return execute_reviewed_hr_export(
        review=review,
        authority=authority,
        materializer=materializer,
        audit_port=audit,
        egress_port=egress,
        now_provider=clock,
    )


@pytest.mark.parametrize(("format_code", "content_type"), [("json", "application/json"), ("csv", "text/csv")])
def test_success_audits_before_egress_and_emits_value_free_receipt(
    format_code: str,
    content_type: str,
) -> None:
    """Both supported formats audit before egress and return only minimized receipt evidence."""
    review, verification, artifact, authority, materializer, audit, egress, clock, events = success_ports(
        export_format_code=format_code,
        content_type=content_type,
    )
    receipt = execute_fixture(review, authority, materializer, audit, egress, clock)

    assert events == ["authority", "materialize", "audit", "egress"]
    assert egress.last_payload == artifact.content
    assert receipt.export_state == "export_delivered"
    assert receipt.contains_pii_values is False
    assert receipt.one_time_use_enforced is True
    assert receipt.artifact_sha256_digest == artifact.sha256_digest
    assert receipt.artifact_byte_length == artifact.byte_length
    canonical = receipt.canonical_json()
    assert "a@example.test" not in canonical and "E-1" not in canonical
    assert receipt.sha256_digest() == sha256(canonical.encode("utf-8")).hexdigest()
    assert repr(verification) == "HrDataExportExecutionVerification(<redacted>)"
    assert repr(artifact) == "HrDataExportArtifact(<redacted>)"
    assert repr(audit.result) == "HrDataExportAuditReceipt(<redacted>)"
    assert repr(egress.result) == "HrDataExportEgressReceipt(<redacted>)"
    assert repr(receipt) == "HrDataExportExecutionReceipt(<redacted>)"


def test_review_runtime_type_and_creation_seal_fail_before_authority() -> None:
    """Only the exact sealed reviewed packet may reach authoritative export verification."""
    review, _, _, authority, materializer, audit, egress, clock, events = success_ports()
    with pytest.raises(TypeError, match="exact governed"):
        execute_reviewed_hr_export(  # type: ignore[arg-type]
            review=object(),
            authority=authority,
            materializer=materializer,
            audit_port=audit,
            egress_port=egress,
            now_provider=clock,
        )
    object.__setattr__(review, "requested_fields", ("employee_number",))
    with pytest.raises(ValueError, match="altered after issuance"):
        execute_fixture(review, authority, materializer, audit, egress, clock)
    assert events == []


def test_review_mutation_during_authority_fails_before_materialization() -> None:
    """The pre-call review snapshot must remain identical across the authority call."""
    review, verification, artifact, _, materializer, audit, egress, clock, events = success_ports()
    authority = MutatingAuthority(verification, events)
    with pytest.raises(ValueError, match="altered after issuance"):
        execute_fixture(review, authority, materializer, audit, egress, clock)
    assert events == ["authority"]


def test_wrong_authority_result_type_fails_before_materialization() -> None:
    """Duck-typed or subclassed authority evidence is not accepted as governed verification."""
    review, _, artifact, _, materializer, audit, egress, clock, events = success_ports()
    with pytest.raises(HrDataExportExecutionError, match="verification"):
        execute_fixture(review, FakeAuthority(object(), events), materializer, audit, egress, clock)
    assert events == ["authority"]
    assert artifact.byte_length > 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_record_id", "21111111-1111-4111-8111-111111111111"),
        ("export_review_reference", "export_review:00000000-0000-4000-8000-000000000001"),
        ("export_review_digest", DIGEST_D),
        ("resource_kind", "person_record"),
        ("resource_reference", "employment_record:00000000-0000-4000-8000-000000000002"),
        ("requested_fields", ("employee_number",)),
        ("export_format_code", "csv"),
        ("destination_kind", "email_attachment"),
    ],
)
def test_authority_scope_mismatch_fails_before_materialization(field: str, value: Any) -> None:
    """Every authoritative scope field must equal the exact reviewed pre-call snapshot."""
    review = make_review()
    verification = make_verification(review)
    object.__setattr__(verification, field, value)
    events: list[str] = []
    materializer = FakeMaterializer(make_artifact(), events)
    with pytest.raises(HrDataExportExecutionError, match="scope"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=materializer,
            audit_port=FakeAudit(object(), events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(BASE_TIME + timedelta(seconds=1)),
        )
    assert events == ["authority"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"retention_state": "retention_blocks_export"}, "policy"),
        ({"legal_hold_state": "legal_hold_blocks_export"}, "policy"),
        ({"authorization_expires_at": BASE_TIME + timedelta(milliseconds=500)}, "expired"),
        ({"verified_at": BASE_TIME + timedelta(seconds=2)}, "not yet valid"),
    ],
)
def test_policy_or_chronology_blocks_before_materialization(
    overrides: dict[str, Any],
    message: str,
) -> None:
    """Policy and current-time failures must block protected field reads."""
    review = make_review()
    verification = make_verification(review, **overrides)
    events: list[str] = []
    with pytest.raises(HrDataExportExecutionError, match=message):
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
    "artifact_result",
    [
        object(),
        make_artifact(fields=("employee_number",)),
        make_artifact(content_type="text/csv"),
    ],
)
def test_invalid_materialization_fails_before_audit_or_egress(artifact_result: object) -> None:
    """Only an exact artifact matching reviewed fields and media type may reach audit."""
    review = make_review()
    verification = make_verification(review)
    events: list[str] = []
    with pytest.raises(HrDataExportExecutionError):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(artifact_result, events),
            audit_port=FakeAudit(object(), events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
            ),
        )
    assert events == ["authority", "materialize"]


def test_authorization_expiring_during_materialization_blocks_audit_and_egress() -> None:
    """Authorization freshness is checked again after protected field materialization."""
    review = make_review()
    verification = make_verification(review, authorization_expires_at=BASE_TIME + timedelta(seconds=2))
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_record_id", "21111111-1111-4111-8111-111111111111"),
        ("export_execution_reference", "export_execution:00000000-0000-4000-8000-000000000001"),
        ("export_review_digest", DIGEST_D),
        ("execution_authorization_digest", DIGEST_D),
        ("human_approval_digest", DIGEST_D),
        ("artifact_sha256_digest", DIGEST_D),
        ("artifact_byte_length", 1),
        ("recorded_at", BASE_TIME + timedelta(seconds=3)),
        ("audit_state", "pending_delivery"),
    ],
)
def test_mismatched_audit_receipt_blocks_egress(field: str, value: Any) -> None:
    """Every pre-delivery audit field must bind the exact artifact and authority evidence."""
    review = make_review()
    verification = make_verification(review)
    artifact = make_artifact()
    receipt = make_audit_receipt(verification, artifact)
    object.__setattr__(receipt, field, value)
    events: list[str] = []
    with pytest.raises(HrDataExportExecutionError, match="audit"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(artifact, events),
            audit_port=FakeAudit(receipt, events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
            ),
        )
    assert events == ["authority", "materialize", "audit"]


def test_wrong_audit_type_and_audit_latency_fail_before_egress() -> None:
    """Untrusted audit objects or authorization expiry during audit never reach outbound egress."""
    review = make_review()
    verification = make_verification(review)
    artifact = make_artifact()
    events: list[str] = []
    with pytest.raises(HrDataExportExecutionError, match="audit port"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(artifact, events),
            audit_port=FakeAudit(object(), events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
            ),
        )
    assert events == ["authority", "materialize", "audit"]

    expiring = make_verification(review, authorization_expires_at=BASE_TIME + timedelta(seconds=3))
    audit_receipt = make_audit_receipt(expiring, artifact)
    events = []
    with pytest.raises(HrDataExportExecutionError, match="expired"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(expiring, events),
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_record_id", "21111111-1111-4111-8111-111111111111"),
        ("export_execution_reference", "export_execution:00000000-0000-4000-8000-000000000001"),
        ("artifact_sha256_digest", DIGEST_D),
        ("artifact_byte_length", 1),
        ("audit_event_reference", "audit_event:00000000-0000-4000-8000-000000000001"),
        ("destination_kind", "email_attachment"),
        ("one_time_use_enforced", False),
        ("delivered_at", BASE_TIME + timedelta(seconds=2)),
        ("delivered_at", BASE_TIME + timedelta(seconds=5)),
    ],
)
def test_mismatched_egress_receipt_cannot_issue_success(field: str, value: Any) -> None:
    """A host egress mismatch cannot produce a successful Orgmetra execution receipt."""
    review = make_review()
    verification = make_verification(review)
    artifact = make_artifact()
    audit_receipt = make_audit_receipt(verification, artifact)
    egress_receipt = make_egress_receipt(verification, artifact, audit_receipt)
    object.__setattr__(egress_receipt, field, value)
    events: list[str] = []
    with pytest.raises(HrDataExportExecutionError, match="egress"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(artifact, events),
            audit_port=FakeAudit(audit_receipt, events),
            egress_port=FakeEgress(egress_receipt, events),
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
                BASE_TIME + timedelta(seconds=3),
                BASE_TIME + timedelta(seconds=4),
            ),
        )
    assert events == ["authority", "materialize", "audit", "egress"]


def test_wrong_egress_type_and_expiry_during_egress_fail_closed() -> None:
    """Invalid egress evidence or expiry during host delivery never issues a success receipt."""
    review = make_review()
    verification = make_verification(review)
    artifact = make_artifact()
    audit_receipt = make_audit_receipt(verification, artifact)
    events: list[str] = []
    with pytest.raises(HrDataExportExecutionError, match="egress port"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(artifact, events),
            audit_port=FakeAudit(audit_receipt, events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
                BASE_TIME + timedelta(seconds=3),
                BASE_TIME + timedelta(seconds=4),
            ),
        )
    assert events == ["authority", "materialize", "audit", "egress"]

    expiring = make_verification(review, authorization_expires_at=BASE_TIME + timedelta(seconds=4))
    expiring_audit = make_audit_receipt(expiring, artifact)
    expiring_egress = make_egress_receipt(expiring, artifact, expiring_audit)
    events = []
    with pytest.raises(HrDataExportExecutionError, match="expired"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(expiring, events),
            materializer=FakeMaterializer(artifact, events),
            audit_port=FakeAudit(expiring_audit, events),
            egress_port=FakeEgress(expiring_egress, events),
            now_provider=SequenceClock(
                BASE_TIME + timedelta(seconds=1),
                BASE_TIME + timedelta(seconds=2),
                BASE_TIME + timedelta(seconds=3),
                BASE_TIME + timedelta(seconds=4),
            ),
        )
    assert events == ["authority", "materialize", "audit", "egress"]


def test_clock_failures_are_stable_and_do_not_reach_authority() -> None:
    """Host clock exceptions and invalid instants fail closed before authority work."""
    review = make_review()
    verification = make_verification(review)
    events: list[str] = []

    def exploding_clock() -> datetime:
        raise RuntimeError("clock backend unavailable")

    with pytest.raises(HrDataExportExecutionError, match="clock failed"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(make_artifact(), events),
            audit_port=FakeAudit(object(), events),
            egress_port=FakeEgress(object(), events),
            now_provider=exploding_clock,
        )
    with pytest.raises(HrDataExportExecutionError, match="invalid time"):
        execute_reviewed_hr_export(
            review=review,
            authority=FakeAuthority(verification, events),
            materializer=FakeMaterializer(make_artifact(), events),
            audit_port=FakeAudit(object(), events),
            egress_port=FakeEgress(object(), events),
            now_provider=SequenceClock(datetime(2026, 8, 26, 0, 0)),
        )
    assert events == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"export_format_code": "xml"},
        {"destination_kind": "email_attachment"},
        {"retention_state": "unknown_retention"},
        {"legal_hold_state": "unknown_hold"},
        {"authorization_expires_at": BASE_TIME},
        {"verified_at": datetime(2026, 8, 26, 0, 0)},
    ],
)
def test_verification_constructor_rejects_invalid_execution_policy(overrides: dict[str, Any]) -> None:
    """Authority evidence constructor rejects unsupported policy, chronology and time shapes."""
    review = make_review()
    with pytest.raises(ValueError):
        make_verification(review, **overrides)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: HrDataExportArtifact(field_names=FIELDS, content_type="text/html", content=b"x"), "media"),
        (lambda: HrDataExportArtifact(field_names=FIELDS, content_type="application/json", content=bytearray(b"x")), "bytes"),
        (lambda: HrDataExportArtifact(field_names=FIELDS, content_type="application/json", content=b"x" * (10 * 1024 * 1024 + 1)), "10 MiB"),
    ],
)
def test_artifact_constructor_rejects_unsafe_media_bytes_or_size(factory: Any, message: str) -> None:
    """Transient artifact construction enforces immutable bytes and the hard memory budget."""
    with pytest.raises(ValueError, match=message):
        factory()


def test_receipt_constructors_reject_invalid_local_states() -> None:
    """Audit and egress receipts reject invalid sizes, states, destination and one-time proof."""
    review = make_review()
    verification = make_verification(review)
    artifact = make_artifact()
    with pytest.raises(ValueError, match="10 MiB"):
        make_audit_receipt(verification, artifact, artifact_byte_length=-1)
    with pytest.raises(ValueError, match="committed_before_delivery"):
        make_audit_receipt(verification, artifact, audit_state="pending_delivery")
    audit_receipt = make_audit_receipt(verification, artifact)
    with pytest.raises(ValueError, match="10 MiB"):
        make_egress_receipt(verification, artifact, audit_receipt, artifact_byte_length=-1)
    with pytest.raises(ValueError, match="destination"):
        make_egress_receipt(verification, artifact, audit_receipt, destination_kind="email_attachment")
    with pytest.raises(ValueError, match="one_time"):
        make_egress_receipt(verification, artifact, audit_receipt, one_time_use_enforced=False)


def test_final_receipt_can_only_be_issued_and_detects_all_post_issuance_rewrites() -> None:
    """The successful receipt has external issuance authority and fails closed after mutation."""
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

    review, _, _, authority, materializer, audit, egress, clock, _ = success_ports()
    receipt = execute_fixture(review, authority, materializer, audit, egress, clock)
    object.__setattr__(receipt, "artifact_byte_length", receipt.artifact_byte_length + 1)
    with pytest.raises(HrDataExportExecutionError, match="tampered"):
        receipt.canonical_json()

    review, _, _, authority, materializer, audit, egress, clock, _ = success_ports()
    receipt = execute_fixture(review, authority, materializer, audit, egress, clock)
    object.__setattr__(receipt, "audited_at", object())
    with pytest.raises(HrDataExportExecutionError, match="invalid or tampered"):
        receipt.canonical_json()

    review, _, _, authority, materializer, audit, egress, clock, _ = success_ports()
    receipt = execute_fixture(review, authority, materializer, audit, egress, clock)
    with execution_module._RECEIPT_SEALS_LOCK:
        execution_module._RECEIPT_SEALS.pop(receipt)
    with pytest.raises(HrDataExportExecutionError, match="tampered"):
        receipt.canonical_json()


@pytest.mark.parametrize(
    "governed_type",
    [
        HrDataExportExecutionVerification,
        HrDataExportArtifact,
        HrDataExportAuditReceipt,
        HrDataExportEgressReceipt,
        HrDataExportExecutionReceipt,
    ],
)
def test_governed_execution_evidence_types_are_final(governed_type: type[object]) -> None:
    """Caller-defined subtypes cannot override trust-bearing behavior at execution boundaries."""
    with pytest.raises(TypeError):
        type("ForgedEvidence", (governed_type,), {})


def test_review_digest_drift_across_authority_fails_before_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review evidence that stops matching its verified snapshot fails closed."""
    review, verification, artifact, _, materializer, audit, egress, clock, events = success_ports()
    original_canonical_json = type(review).canonical_json
    state = {"verified": False}

    class DriftAfterAuthority(FakeAuthority):
        """Flip the drift flag only after authoritative verification returns."""

        def verify_export(
            self,
            *,
            review: HrDataExportReviewPacket,
            review_digest: str,
            requested_at: datetime,
        ) -> object:
            """Record the governed call, then arm post-verification evidence drift."""
            self.events.append("authority")
            assert review_digest == review.sha256_digest()
            assert requested_at.tzinfo is UTC
            state["verified"] = True
            return self.result

    def drifting_canonical_json(self: Any) -> str:
        """Return the verified rendering once, then a divergent rendering afterwards."""
        text = original_canonical_json(self)
        return text + " " if state["verified"] else text

    monkeypatch.setattr(type(review), "canonical_json", drifting_canonical_json)
    with pytest.raises(HrDataExportExecutionError, match="changed across authoritative verification"):
        execute_fixture(
            review,
            DriftAfterAuthority(verification, events),
            materializer,
            audit,
            egress,
            clock,
        )
    assert events == ["authority"]
