"""Regression coverage for hostile string subclasses at the TEPP evidence boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from orgmetra_tepp_adapter import build_tepp_analysis_request_packet
from orgmetra_tepp_adapter.analysis import _validate_uuid4


class ForgedReference(str):
    """Forge namespace removal while retaining attacker-controlled underlying text."""

    def startswith(self, prefix, *args):  # type: ignore[no-untyped-def]
        return True

    def removeprefix(self, prefix):  # type: ignore[no-untyped-def]
        return "22222222-2222-4222-8222-222222222222"


class ForgedTenantUUIDText(str):
    """Forge UUID parsing/canonical equality while retaining malformed tenant text."""

    def replace(self, old, new, *args):  # type: ignore[no-untyped-def]
        canonical = "11111111-1111-4111-8111-111111111111"
        return canonical.replace(old, new, *args)

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        return other is not None

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        return other is None


class ForgedOpaqueIdentifier(str):
    """Hide a credential-shaped underlying value from the credential detector."""

    def lower(self):  # type: ignore[no-untyped-def]
        return "workspace-safe"


def values() -> dict[str, object]:
    """Return one valid governed TEPP request packet input."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "validation_study_reference": "validation_study:22222222-2222-4222-8222-222222222222",
        "requested_by_actor_reference": "actor:33333333-3333-4333-8333-333333333333",
        "tepp_workspace_id": "workspace-opaque-8e9f1d",
        "tepp_snapshot_id": "snapshot-opaque-2f6c91",
        "snapshot_digest": "a" * 64,
        "idempotency_key": "orgmetra-tepp-20260820-0001",
        "knowledge_cutoff": datetime(2026, 8, 20, 16, 45, 12, 345678, tzinfo=timezone(timedelta(hours=9))),
        "model_contract_version": "temporal-event-v1",
        "output_profile": "validation-report",
        "generated_at": datetime(2026, 8, 20, 7, 50, 1, 123456, tzinfo=timezone.utc),
    }


def test_rejects_reference_string_subclass_that_can_forge_namespace_validation() -> None:
    """Reject subclassed references before namespace helpers can be overridden."""
    kwargs = values()
    kwargs["validation_study_reference"] = ForgedReference("evil-reference")
    with pytest.raises(ValueError, match="validation_study_reference"):
        build_tepp_analysis_request_packet(**kwargs)


def test_rejects_tenant_string_subclass_that_can_forge_uuid_validation() -> None:
    """Reject subclassed authoritative tenant text before UUID canonicalization."""
    kwargs = values()
    kwargs["tenant_record_id"] = ForgedTenantUUIDText("not-a-tenant-uuid")
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_tepp_analysis_request_packet(**kwargs)


def test_uuid4_validator_rejects_string_subclass_before_uuid_parsing() -> None:
    """Keep the shared UUIDv4 validator independently fail-closed for future callers."""
    with pytest.raises(ValueError, match="probe_reference"):
        _validate_uuid4(ForgedTenantUUIDText("22222222-2222-4222-8222-222222222222"), "probe_reference")


def test_rejects_opaque_string_subclass_that_can_hide_credential_shape() -> None:
    """Reject subclassed opaque identifiers before credential-shape inspection."""
    kwargs = values()
    kwargs["tepp_workspace_id"] = ForgedOpaqueIdentifier("sk-secret-workspace")
    with pytest.raises(ValueError, match="tepp_workspace_id"):
        build_tepp_analysis_request_packet(**kwargs)


def test_rejects_idempotency_string_subclass_that_can_hide_credential_shape() -> None:
    """Reject subclassed idempotency keys before credential-shape inspection."""
    kwargs = values()
    kwargs["idempotency_key"] = ForgedOpaqueIdentifier("sk-secret-idempotency-key")
    with pytest.raises(ValueError, match="idempotency_key"):
        build_tepp_analysis_request_packet(**kwargs)
