from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmetra_offer_approval import build_offer_approval_packet


def _build(**overrides):
    """Build a valid offer-approval packet, allowing one field to be varied by a regression."""
    values = {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "offer_approval_reference": "offer_approval:22222222-2222-4222-8222-222222222222",
        "candidate_profile_reference": "candidate_profile:33333333-3333-4333-8333-333333333333",
        "requisition_reference": "requisition:44444444-4444-4444-8444-444444444444",
        "job_profile_reference": "job_profile:55555555-5555-4555-8555-555555555555",
        "position_record_reference": None,
        "selection_decision_reference": "selection_decision:66666666-6666-4666-8666-666666666666",
        "selection_decision_digest": "a" * 64,
        "compensation_package_reference": "compensation_package:77777777-7777-4777-8777-777777777777",
        "compensation_package_digest": "b" * 64,
        "offer_terms_reference": "offer_terms:88888888-8888-4888-8888-888888888888",
        "offer_terms_digest": "c" * 64,
        "requester_reference": "actor:99999999-9999-4999-8999-999999999999",
        "approver_reference": "actor:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "purpose_code": "offer_approval_review",
        "reason_code": "selected_candidate_offer_review",
        "generated_at": datetime(2026, 8, 19, 2, 15, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return build_offer_approval_packet(**values)


def test_requester_and_approver_require_authoritative_actor_separation() -> None:
    """Require distinct actor references plus authoritative identity separation before approval."""
    with pytest.raises(ValueError, match="different accountable actor"):
        _build(approver_reference="actor:99999999-9999-4999-8999-999999999999")

    normalized_next_action = _build().next_action.lower()
    assert "requester_reference and approver_reference" in normalized_next_action
    assert "resolved actor identities are distinct" in normalized_next_action


def test_approval_requires_every_reference_to_resolve_in_the_exact_tenant() -> None:
    """Prevent cross-tenant offer evidence mixing behind syntactically valid UUID references."""
    action = _build().next_action
    tenant_clause = "re-resolve every packet reference within tenant_record_id"
    actor_clause = "verify their resolved actor identities are distinct"
    scope_clause = "verify authoritative Job/Position scope"
    approval_clause = "accountable human approval"

    assert tenant_clause in action
    assert action.index(tenant_clause) < action.index(actor_clause)
    assert action.index(actor_clause) < action.index(scope_clause)
    assert action.index(scope_clause) < action.index(approval_clause)
