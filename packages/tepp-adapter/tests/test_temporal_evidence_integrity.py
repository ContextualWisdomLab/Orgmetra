"""Regression coverage for TEPP temporal-evidence canonicalization integrity."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmetra_tepp_adapter import build_tepp_analysis_request_packet


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical TEPP/audit evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying evidence instant."""
        return "2099-12-31T23:59:59+00:00"


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid Orgmetra-to-TEPP request packet input."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "validation_study_reference": "validation_study:22222222-2222-4222-8222-222222222222",
        "requested_by_actor_reference": "actor:33333333-3333-4333-8333-333333333333",
        "tepp_workspace_id": "workspace-opaque-8e9f1d",
        "tepp_snapshot_id": "snapshot-opaque-2f6c91",
        "snapshot_digest": "a" * 64,
        "idempotency_key": "orgmetra-tepp-20260821-0001",
        "knowledge_cutoff": datetime(2026, 8, 21, 3, 30, tzinfo=timezone.utc),
        "model_contract_version": "temporal-event-v1",
        "output_profile": "validation-report",
        "generated_at": datetime(2026, 8, 21, 4, 30, tzinfo=timezone.utc),
    }


@pytest.mark.parametrize("field_name", ["knowledge_cutoff", "generated_at"])
def test_rejects_datetime_subclasses_that_can_forge_temporal_evidence(field_name: str) -> None:
    """TEPP request and audit evidence must not invoke caller-overridable datetime methods."""
    kwargs = valid_kwargs()
    kwargs[field_name] = ForgedDateTime(2026, 8, 21, 4, 30, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        build_tepp_analysis_request_packet(**kwargs)


def test_generated_at_must_not_precede_knowledge_cutoff() -> None:
    """Reject packets whose generation instant precedes their own knowledge cutoff."""
    kwargs = valid_kwargs()
    kwargs["knowledge_cutoff"] = datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc)
    kwargs["generated_at"] = datetime(2026, 8, 21, 4, 59, 59, 999999, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at must not precede knowledge_cutoff"):
        build_tepp_analysis_request_packet(**kwargs)


def test_equal_workspace_and_snapshot_identifiers_are_rejected() -> None:
    """Reference manipulation cannot reuse one opaque identifier for two entity types."""
    kwargs = valid_kwargs()
    kwargs["tepp_workspace_id"] = "opaque-duplicated-1f2e3d"
    kwargs["tepp_snapshot_id"] = "opaque-duplicated-1f2e3d"

    with pytest.raises(ValueError, match="must be distinct opaque identifiers"):
        build_tepp_analysis_request_packet(**kwargs)
