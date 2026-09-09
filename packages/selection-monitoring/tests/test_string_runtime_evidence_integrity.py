"""Regression coverage for string-subclass evidence-boundary integrity."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from orgmetra_selection_monitoring import build_selection_outcome_monitoring_plan


class ForgedReference(str):
    """String subclass that forges namespace and UUID suffix validation."""

    def startswith(self, prefix, *args):  # type: ignore[no-untyped-def]
        """Pretend the hostile value carries every requested namespace."""
        return True

    def split(self, sep=None, maxsplit=-1):  # type: ignore[no-untyped-def]
        """Feed validation a canonical UUIDv4 suffix instead of stored text."""
        return ["evil", "11111111-1111-4111-8111-111111111111"]


class ForgedTenantUUIDText(str):
    """String subclass that forges UUID parsing and canonical-equality checks."""

    def replace(self, old, new, *args):  # type: ignore[no-untyped-def]
        """Feed UUID() canonical text instead of the stored hostile tenant text."""
        canonical = "12345678-1234-4234-8234-123456789abc"
        return canonical.replace(old, new, *args)

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        """Claim canonical equality while retaining the hostile underlying text."""
        if other is None:
            return False
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        """Keep UUID constructor sentinel checks working while defeating canonicality."""
        if other is None:
            return True
        return False


class ForgedGovernanceCode(str):
    """String subclass that can satisfy closed-code comparisons with hostile text."""

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        return False

    def __hash__(self) -> int:
        return hash("quarterly_selection_governance")


class DigestSubclass(str):
    """Semantically valid-looking digest carried by an untrusted runtime subclass."""


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid monitoring-plan input."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "monitoring_plan_reference": "selection_monitoring_plan:10000000-0000-4000-8000-000000000001",
        "job_profile_reference": "job_profile:10000000-0000-4000-8000-000000000002",
        "selection_process_reference": "selection_process:10000000-0000-4000-8000-000000000003",
        "population_snapshot_reference": "population_snapshot:10000000-0000-4000-8000-000000000004",
        "population_snapshot_digest": "a" * 64,
        "outcome_snapshot_reference": "selection_outcome_snapshot:10000000-0000-4000-8000-000000000005",
        "outcome_snapshot_digest": "b" * 64,
        "protected_attribute_policy_reference": "protected_attribute_policy:10000000-0000-4000-8000-000000000006",
        "protected_attribute_policy_digest": "c" * 64,
        "small_sample_policy_reference": "small_sample_policy:10000000-0000-4000-8000-000000000007",
        "small_sample_policy_digest": "d" * 64,
        "statistical_plan_reference": "statistical_plan:10000000-0000-4000-8000-000000000008",
        "statistical_plan_digest": "e" * 64,
        "actor_reference": "actor:10000000-0000-4000-8000-000000000009",
        "reviewer_reference": "actor:10000000-0000-4000-8000-00000000000a",
        "monitoring_start": date(2026, 1, 1),
        "monitoring_end": date(2026, 3, 31),
        "purpose_code": "selection_outcome_monitoring",
        "reason_code": "quarterly_selection_governance",
        "generated_at": datetime(2026, 4, 2, 8, 30, tzinfo=timezone.utc),
    }


def test_rejects_reference_string_subclass_that_can_forge_namespace_validation() -> None:
    """Canonical evidence must not retain text that only pretended to match a namespace."""
    kwargs = valid_kwargs()
    kwargs["monitoring_plan_reference"] = ForgedReference("evil:payload")

    with pytest.raises(ValueError, match="monitoring_plan_reference"):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_rejects_tenant_string_subclass_that_can_forge_uuid_validation() -> None:
    """Authoritative tenant identity must be exact built-in text before UUID parsing."""
    kwargs = valid_kwargs()
    kwargs["tenant_record_id"] = ForgedTenantUUIDText("not-a-tenant-uuid")

    with pytest.raises(ValueError, match="tenant_record_id"):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_rejects_purpose_code_string_subclass_that_can_forge_closed_code_check() -> None:
    """Purpose evidence must be exact built-in text before fixed-code comparison."""
    kwargs = valid_kwargs()
    kwargs["purpose_code"] = ForgedGovernanceCode("attacker_controlled_purpose")

    with pytest.raises(ValueError, match="purpose_code"):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_rejects_reason_code_string_subclass_that_can_forge_closed_code_membership() -> None:
    """Reason evidence must be exact built-in text before allow-list membership."""
    kwargs = valid_kwargs()
    kwargs["reason_code"] = ForgedGovernanceCode("attacker_controlled_reason")

    with pytest.raises(ValueError, match="reason_code"):
        build_selection_outcome_monitoring_plan(**kwargs)


def test_rejects_digest_string_subclass_before_canonical_evidence_binding() -> None:
    """Digest evidence must use the same exact built-in string boundary as other trust text."""
    kwargs = valid_kwargs()
    kwargs["population_snapshot_digest"] = DigestSubclass("a" * 64)

    with pytest.raises(ValueError, match="population_snapshot_digest"):
        build_selection_outcome_monitoring_plan(**kwargs)
