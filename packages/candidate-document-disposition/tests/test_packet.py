import json
from datetime import datetime, timezone
from hashlib import sha256

import pytest

from orgmetra_candidate_document_disposition import (
    CandidateDocumentDisposition,
    build_candidate_document_disposition,
)


def _default_kwargs() -> dict:
    return dict(
        tenant_record_id="00000000-0000-4000-a000-000000000001",
        disposition_reference="candidate_document_disposition:00000000-0000-4000-a000-000000000010",
        document_reference="document:00000000-0000-4000-a000-000000000020",
        candidate_reference="candidate_profile:00000000-0000-4000-a000-000000000030",
        hiring_decision_finalized_at=datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc),
        return_eligibility="eligible",
        state="created",
        retention_policy_version="v2026_09",
        retention_policy_digest="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        retention_anchor_event="hiring_decision_finalized",
        retain_until=datetime(2027, 9, 11, 12, 0, 0, tzinfo=timezone.utc),
        legal_hold=False,
        purpose_code="candidate_document_disposition",
        reason_code="non_selected_applicant_return",
        evidence_version=1,
        actor_reference="actor:00000000-0000-4000-a000-000000000040",
    )


def _build(**overrides) -> CandidateDocumentDisposition:
    kwargs = _default_kwargs()
    kwargs.update(overrides)
    return build_candidate_document_disposition(**kwargs)


class TestConstruction:
    def test_default_packet(self):
        p = _build()
        assert isinstance(p, CandidateDocumentDisposition)
        assert p.legal_hold is False
        assert p.state == "created"

    def test_optional_previous_disposition(self):
        p = _build(
            previous_disposition_reference="candidate_document_disposition:00000000-0000-4000-a000-000000000099"
        )
        assert p.previous_disposition_reference is not None
        assert "000000000099" in p.previous_disposition_reference

    def test_optional_claim_window_end(self):
        ts = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
        p = _build(claim_window_end=ts)
        assert p.claim_window_end == ts

    def test_optional_return_dispatched(self):
        ts = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        p = _build(state="return_dispatched", return_dispatched_at=ts)
        assert p.return_dispatched_at == ts

    def test_optional_statutory_retain_until(self):
        ts = datetime(2031, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        p = _build(statutory_retain_until=ts)
        assert p.statutory_retain_until == ts

    def test_optional_retain_until_none(self):
        p = _build(retain_until=None)
        assert p.retain_until is None

    def test_legal_hold_true(self):
        p = _build(legal_hold=True)
        assert p.legal_hold is True

    def test_legal_hold_and_destroyed_raises(self):
        with pytest.raises(ValueError, match="legal hold"):
            _build(legal_hold=True, state="destroyed")

    @pytest.mark.parametrize("reason_code", [
        "talent_pool_consent_withdrawal",
        "confirmed_hire_materialization",
        "statutory_retention_expiry",
        "legal_hold_release",
        "talent_pool_expiry",
    ])
    def test_various_reason_codes(self, reason_code):
        p = _build(reason_code=reason_code)
        assert p.reason_code == reason_code

    def test_talent_pool_consent_withdrawal_reason(self):
        p = _build(reason_code="talent_pool_consent_withdrawal")
        assert p.reason_code == "talent_pool_consent_withdrawal"

    def test_confirmed_hire_materialization_reason(self):
        p = _build(reason_code="confirmed_hire_materialization")
        assert p.reason_code == "confirmed_hire_materialization"

    def test_statutory_retention_expiry_reason(self):
        p = _build(reason_code="statutory_retention_expiry")
        assert p.reason_code == "statutory_retention_expiry"

    def test_legal_hold_release_reason(self):
        p = _build(reason_code="legal_hold_release")
        assert p.reason_code == "legal_hold_release"

    def test_talent_pool_expiry_reason(self):
        p = _build(reason_code="talent_pool_expiry")
        assert p.reason_code == "talent_pool_expiry"

    @pytest.mark.parametrize("code", [
        "eligible",
        "return_exception_voluntary_submission",
        "return_exception_not_requested_by_employer",
        "waived",
    ])
    def test_various_return_eligibility_codes(self, code):
        p = _build(return_eligibility=code)
        assert p.return_eligibility == code

    @pytest.mark.parametrize("state", [
        "created",
        "return_claim_window_open",
        "return_requested",
        "return_request_verified",
        "return_dispatched",
        "return_destroyed",
        "talent_pool_retained",
        "confirmed_hire_transitioned",
        "statutory_retained",
        "statutory_retention_expired_destroyed",
        "legal_hold_suspended",
        "destroyed",
    ])
    def test_various_states(self, state):
        p = _build(state=state)
        assert p.state == state

    @pytest.mark.parametrize("event", [
        "hiring_decision_finalized",
        "confirmed_hire",
        "separation",
        "consent_revoked",
        "talent_pool_expired",
        "statutory_period_start",
    ])
    def test_various_anchor_events(self, event):
        p = _build(retention_anchor_event=event)
        assert p.retention_anchor_event == event

    def test_repr_redacted(self):
        p = _build()
        assert "<redacted>" in repr(p)

    @pytest.mark.parametrize("version", [1, 2_147_483_647])
    def test_evidence_version_boundary(self, version):
        p = _build(evidence_version=version)
        assert p.evidence_version == version

    def test_evidence_version_boundary_low(self):
        p = _build(evidence_version=1)
        assert p.evidence_version == 1

    def test_evidence_version_boundary_high(self):
        p = _build(evidence_version=2_147_483_647)
        assert p.evidence_version == 2_147_483_647

    def test_evidence_version_minimum(self):
        with pytest.raises(ValueError, match="evidence_version"):
            _build(evidence_version=0)

    def test_evidence_version_maximum(self):
        with pytest.raises(ValueError, match="evidence_version"):
            _build(evidence_version=2_147_483_648)

    def test_invalid_tenant_uuid(self):
        with pytest.raises(ValueError, match="tenant_record_id"):
            _build(tenant_record_id="not-a-uuid")

    def test_sentinel_tenant_uuid(self):
        with pytest.raises(ValueError, match="tenant_record_id"):
            _build(tenant_record_id="00000000-0000-0000-0000-000000000000")

    def test_invalid_disposition_reference(self):
        with pytest.raises(ValueError, match="disposition_reference"):
            _build(disposition_reference="bad-ref")

    def test_invalid_document_reference(self):
        with pytest.raises(ValueError, match="document_reference"):
            _build(document_reference="bad-ref")

    def test_invalid_candidate_reference(self):
        with pytest.raises(ValueError, match="candidate_reference"):
            _build(candidate_reference="bad-ref")

    def test_non_uuid4_disposition_reference(self):
        with pytest.raises(ValueError, match="disposition_reference"):
            _build(disposition_reference="candidate_document_disposition:00000000-0000-3000-a000-000000000000")

    def test_unrecognized_retention_anchor_event(self):
        with pytest.raises(ValueError, match="authorized anchor event"):
            _build(retention_anchor_event="unknown_event")

    def test_unrecognized_reason_code(self):
        with pytest.raises(ValueError, match="authorized disposition reason"):
            _build(reason_code="unknown_reason_code")

    def test_invalid_return_eligibility(self):
        with pytest.raises(ValueError, match="return_eligibility"):
            _build(return_eligibility="not-a-valid-code")

    def test_unrecognized_return_eligibility(self):
        with pytest.raises(ValueError, match="authorized disposition return code"):
            _build(return_eligibility="unknown_return_code")

    def test_invalid_state(self):
        with pytest.raises(ValueError, match="state"):
            _build(state="not-a-valid-state")

    def test_unrecognized_state(self):
        with pytest.raises(ValueError, match="authorized disposition state"):
            _build(state="unknown_state")

    def test_invalid_retention_policy_version_code(self):
        with pytest.raises(ValueError, match="retention_policy_version"):
            _build(retention_policy_version="BAD")

    def test_invalid_retention_policy_digest(self):
        with pytest.raises(ValueError, match="retention_policy_digest"):
            _build(retention_policy_digest="xyz")

    def test_invalid_retention_anchor_event(self):
        with pytest.raises(ValueError, match="retention_anchor_event"):
            _build(retention_anchor_event="BAD")

    def test_invalid_purpose_code(self):
        with pytest.raises(ValueError, match="purpose_code"):
            _build(purpose_code="something_else")

    def test_invalid_reason_code(self):
        with pytest.raises(ValueError, match="reason_code"):
            _build(reason_code="BAD")

    def test_invalid_actor_reference(self):
        with pytest.raises(ValueError, match="actor_reference"):
            _build(actor_reference="actor:bad-uuid")

    def test_human_confirmation_false(self):
        kwargs = _default_kwargs()
        with pytest.raises(ValueError, match="human confirmation"):
            CandidateDocumentDisposition(**kwargs, human_confirmation_required=False)

    def test_wrong_review_state(self):
        kwargs = _default_kwargs()
        with pytest.raises(ValueError, match="review_state"):
            CandidateDocumentDisposition(**kwargs, review_state="approved")

    def test_wrong_next_action(self):
        kwargs = _default_kwargs()
        with pytest.raises(ValueError, match="next_action"):
            CandidateDocumentDisposition(**kwargs, next_action="do something else")

    def test_naive_datetime_raises(self):
        with pytest.raises(ValueError, match="timestamp"):
            _build(hiring_decision_finalized_at=datetime(2026, 9, 11, 12, 0, 0))

    def test_naive_retain_until_raises(self):
        with pytest.raises(ValueError, match="timestamp"):
            _build(retain_until=datetime(2026, 9, 11, 12, 0, 0))

    def test_invalid_previous_disposition_reference(self):
        with pytest.raises(ValueError, match="previous_disposition_reference"):
            _build(previous_disposition_reference="bad:ref")


class TestCanonicalJson:
    def test_deterministic(self):
        p1 = _build()
        p2 = _build()
        assert p1.canonical_json() == p2.canonical_json()

    def test_contains_required_fields(self):
        p = _build()
        doc = json.loads(p.canonical_json())
        assert doc["purpose_code"] == "candidate_document_disposition"
        assert doc["state"] == "created"
        assert doc["legal_hold"] is False

    def test_omits_none_optional_fields(self):
        p = _build(previous_disposition_reference=None, claim_window_end=None,
                   return_dispatched_at=None, statutory_retain_until=None)
        doc = json.loads(p.canonical_json())
        assert doc["previous_disposition_reference"] is None
        assert doc["claim_window_end"] is None
        assert doc["return_dispatched_at"] is None
        assert doc["statutory_retain_until"] is None

    def test_includes_set_optional_fields(self):
        ts = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
        p = _build(
            previous_disposition_reference="candidate_document_disposition:00000000-0000-4000-a000-000000000099",
            claim_window_end=ts,
            return_dispatched_at=ts,
            statutory_retain_until=ts,
        )
        doc = json.loads(p.canonical_json())
        assert doc["previous_disposition_reference"] is not None
        assert doc["claim_window_end"] is not None
        assert doc["return_dispatched_at"] is not None
        assert doc["statutory_retain_until"] is not None

    def test_sort_keys(self):
        p = _build()
        doc = json.loads(p.canonical_json())
        keys = list(doc.keys())
        assert keys == sorted(keys)


class TestSha256Digest:
    def test_deterministic(self):
        p = _build()
        assert p.sha256_digest() == p.sha256_digest()

    def test_matches_canonical_json(self):
        p = _build()
        expected = sha256(p.canonical_json().encode("utf-8")).hexdigest()
        assert p.sha256_digest() == expected

    def test_changes_when_field_changes(self):
        p1 = _build(state="created")
        p2 = _build(state="destroyed")
        assert p1.sha256_digest() != p2.sha256_digest()


class TestBuildFunction:
    def test_returns_packet(self):
        p = build_candidate_document_disposition(**_default_kwargs())
        assert isinstance(p, CandidateDocumentDisposition)

    def test_passes_all_fields(self):
        kwargs = _default_kwargs()
        p = build_candidate_document_disposition(**kwargs)
        for k, v in kwargs.items():
            assert getattr(p, k) == v


class TestRegressionInvariants:
    def test_return_claim_window_anchored_to_hiring_decision(self):
        p = _build()
        assert p.hiring_decision_finalized_at is not None
        assert p.claim_window_end is None or p.claim_window_end > p.hiring_decision_finalized_at

    def test_legal_hold_overrides_ordinary_retention(self):
        p = _build(legal_hold=True)
        assert p.legal_hold is True
        assert p.retain_until is not None

    def test_retention_policy_version_is_code(self):
        p = _build(retention_policy_version="v2026_09")
        assert p.retention_policy_version == "v2026_09"
