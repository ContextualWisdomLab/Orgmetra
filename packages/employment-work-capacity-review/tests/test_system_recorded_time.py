"""Regression proving system-recorded time is issued by Orgmetra, not the caller."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from orgmetra_employment_work_capacity_review import (
    build_employment_work_capacity_review_packet,
)


def _arguments() -> dict[str, object]:
    """Return one valid review request without any caller-owned recorded time."""
    return {
        "tenant_record_id": "018f47a8-4b1c-7cc2-98b0-0123456789ab",
        "employment_record_reference": "employment_record:018f47a8-4b1c-7cc2-98b0-1123456789ab",
        "current_capacity_ratio": Decimal("1.0000"),
        "proposed_capacity_ratio": Decimal("0.8000"),
        "effective_on": date(2026, 9, 1),
        "employment_terms_evidence_digest": "a" * 64,
        "capacity_policy_evidence_digest": "b" * 64,
        "reviewer_identity_evidence_digest": "c" * 64,
        "requester_actor_reference": f"actor:{uuid4()}",
        "reviewer_actor_reference": f"actor:{uuid4()}",
        "reason_code": "employee_agreed_change",
        "evidence_version": 1,
        "reviewed_at": datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc),
    }


def test_builder_owns_system_recorded_time_and_caller_cannot_inject_it() -> None:
    arguments = _arguments()
    before = datetime.now(timezone.utc)
    packet = build_employment_work_capacity_review_packet(**arguments)  # type: ignore[arg-type]
    after = datetime.now(timezone.utc)
    assert before <= packet.recorded_at <= after

    with pytest.raises(TypeError, match="recorded_at"):
        build_employment_work_capacity_review_packet(  # type: ignore[call-arg,arg-type]
            **arguments,
            recorded_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        )
