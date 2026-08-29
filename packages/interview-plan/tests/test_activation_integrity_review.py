"""Regressions for current-head structured-interview activation integrity findings."""

from dataclasses import fields
from datetime import datetime, timedelta, timezone, tzinfo
from threading import Event, Thread
import json

import pytest

import orgmetra_interview_plan.activation as activation_module
from orgmetra_interview_plan import (
    StructuredInterviewActivationVerification,
    activate_structured_interview_plan,
)
from test_activation import (
    APPROVED_AT,
    APPROVER,
    AUTHORITY_EVIDENCE,
    DIGEST_E,
    AllowingAuthority,
    RejectingAuthority,
    plan,
    verification_for,
)

ALTERNATE_AUTHORITY_EVIDENCE = "activation_verification:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ALTERNATE_AUTHORITY_DIGEST = "f" * 64


class MutableOffsetTimezone(tzinfo):
    """UTC-offset provider whose offset can change after initial validation."""

    def __init__(self, offset_hours: int) -> None:
        """Store the mutable offset used by the adversarial approval-time fixture."""
        self.offset_hours = offset_hours

    def utcoffset(self, value):
        """Return the currently configured offset."""
        return timedelta(hours=self.offset_hours)

    def dst(self, value):
        """Return zero daylight-saving offset for deterministic test behavior."""
        return timedelta(0)

    def tzname(self, value):
        """Return a stable diagnostic name for the mutable test timezone."""
        return "MutableOffsetTimezone"


class ApprovalTimeMutatingAuthority:
    """Mutate caller-owned timezone state only after receiving the approval snapshot."""

    def __init__(self, source_timezone: MutableOffsetTimezone) -> None:
        """Keep the caller timezone so authority work can mutate it deterministically."""
        self.source_timezone = source_timezone

    def verify_activation(self, *, plan, approving_actor_reference, approved_at):
        """Require immutable built-in UTC evidence, then mutate the caller timezone."""
        assert approved_at.tzinfo is timezone.utc
        assert approved_at == APPROVED_AT
        self.source_timezone.offset_hours = 2
        return StructuredInterviewActivationVerification(
            tenant_record_id=plan.tenant_record_id,
            interview_plan_reference=plan.interview_plan_reference,
            plan_digest=plan.sha256_digest(),
            approving_actor_reference=approving_actor_reference,
            authority_evidence_reference=AUTHORITY_EVIDENCE,
            authority_evidence_digest=DIGEST_E,
            approved_at=approved_at,
        )


def test_existing_plan_identity_cannot_renew_issuance_seal_after_mutation():
    """Repeated initialization must not legitimize changed bytes on one issued plan identity."""
    candidate_plan = plan()
    object.__setattr__(candidate_plan, "question_count", 3)

    with pytest.raises(ValueError, match="issuance evidence already exists"):
        candidate_plan.__post_init__()
    with pytest.raises(ValueError, match="changed after plan issuance"):
        candidate_plan.canonical_json()
    with pytest.raises(ValueError, match="changed after plan issuance"):
        activate_structured_interview_plan(
            plan=candidate_plan,
            authority=RejectingAuthority(),
            approving_actor_reference=APPROVER,
            approved_at=APPROVED_AT,
        )


def test_activation_freezes_mutable_timezone_before_authority_and_receipt():
    """Authority work cannot make one approved_at value represent two UTC instants."""
    mutable_timezone = MutableOffsetTimezone(1)
    caller_time = datetime(2026, 8, 21, 6, 0, 0, 123456, tzinfo=mutable_timezone)
    candidate_plan = plan()

    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=ApprovalTimeMutatingAuthority(mutable_timezone),
        approving_actor_reference=APPROVER,
        approved_at=caller_time,
    )

    payload = json.loads(receipt.canonical_json())
    assert payload["approved_at"] == "2026-08-21T05:00:00.123456Z"
    assert receipt.approved_at.tzinfo is timezone.utc
    assert receipt.approved_at == APPROVED_AT


def test_verification_mutation_after_validation_cannot_rewrite_receipt(monkeypatch):
    """Receipt construction must use one detached verification snapshot after authority return."""
    candidate_plan = plan()
    verification = verification_for(candidate_plan)
    validation_finished = Event()
    mutation_finished = Event()
    original_validate_digest = activation_module._validate_digest

    def synchronized_validate_digest(value, field_name):
        """Pause after evidence-digest validation so a retained authority alias can mutate."""
        original_validate_digest(value, field_name)
        if field_name == "authority_evidence_digest":
            validation_finished.set()
            assert mutation_finished.wait(timeout=2)

    def mutate_retained_verification():
        """Rewrite valid authority evidence only after the activation boundary validated it."""
        assert validation_finished.wait(timeout=2)
        object.__setattr__(verification, "authority_evidence_reference", ALTERNATE_AUTHORITY_EVIDENCE)
        object.__setattr__(verification, "authority_evidence_digest", ALTERNATE_AUTHORITY_DIGEST)
        mutation_finished.set()

    monkeypatch.setattr(activation_module, "_validate_digest", synchronized_validate_digest)
    mutator = Thread(target=mutate_retained_verification, daemon=True)
    mutator.start()
    receipt = activate_structured_interview_plan(
        plan=candidate_plan,
        authority=AllowingAuthority(verification),
        approving_actor_reference=APPROVER,
        approved_at=APPROVED_AT,
    )
    mutator.join(timeout=2)
    assert not mutator.is_alive()

    payload = json.loads(receipt.canonical_json())
    assert payload["authority_evidence_reference"] == AUTHORITY_EVIDENCE
    assert payload["authority_evidence_digest"] == DIGEST_E


def test_verification_contract_explicitly_binds_reviewed_approval_time():
    """Authority verification must expose the exact approval instant it attests."""
    field_names = {field.name for field in fields(StructuredInterviewActivationVerification)}

    assert "approved_at" in field_names
