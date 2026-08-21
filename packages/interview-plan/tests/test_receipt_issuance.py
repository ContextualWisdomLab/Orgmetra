"""Regression tests for authoritative structured-interview receipt issuance."""

from datetime import datetime, timezone

import pytest

from orgmetra_interview_plan import StructuredInterviewActivationReceipt


def test_activation_receipt_cannot_be_minted_without_verified_factory_path():
    """Reject valid-looking approval evidence that never crossed the authority boundary."""
    with pytest.raises(TypeError, match="activate_structured_interview_plan"):
        StructuredInterviewActivationReceipt(
            tenant_record_id="10000000-0000-7000-8000-000000000001",
            interview_plan_reference="interview_plan:11111111-1111-4111-8111-111111111111",
            plan_digest="a" * 64,
            approving_actor_reference="actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            authority_evidence_reference=(
                "activation_verification:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
            ),
            authority_evidence_digest="e" * 64,
            approved_at=datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc),
        )
