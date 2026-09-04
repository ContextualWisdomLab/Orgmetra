"""Targeted coverage for fail-closed validation branches."""

import pytest

from orgmetra_performance_context_evidence import PerformanceContextEvidencePacket

from test_evidence import values


def test_tenant_uuid_rejects_non_string_and_malformed_text() -> None:
    """Tenant identity covers both exact-runtime and UUID-parse failure boundaries."""
    for invalid in (123, "not-a-uuid"):
        kwargs = values(tenant_record_id=invalid)
        with pytest.raises(ValueError):
            PerformanceContextEvidencePacket(**kwargs)  # type: ignore[arg-type]


def test_operational_reference_rejects_reserved_uuid_sentinel() -> None:
    """Namespaced HRIS references reject canonical but reserved UUID sentinels."""
    kwargs = values(
        employment_record_reference="employment_record:00000000-0000-0000-0000-000000000000"
    )
    with pytest.raises(ValueError):
        PerformanceContextEvidencePacket(**kwargs)  # type: ignore[arg-type]


def test_review_state_rejects_alternative_well_formed_governance_code() -> None:
    """The fixed review-state comparison is exercised independently of code syntax validation."""
    kwargs = values(review_state="review_pending")
    with pytest.raises(ValueError, match="review_state must remain requires_human_review"):
        PerformanceContextEvidencePacket(**kwargs)  # type: ignore[arg-type]
