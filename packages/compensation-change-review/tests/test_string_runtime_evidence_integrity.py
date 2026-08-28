"""Regression coverage for string-subclass evidence-boundary integrity."""

from __future__ import annotations

from dataclasses import replace

import pytest

from orgmetra_compensation_change_review import build_compensation_change_review_packet


class ForgedReference(str):
    """String subclass that forges namespace and UUID suffix validation."""

    def startswith(self, prefix, *args):  # type: ignore[no-untyped-def]
        return True

    def split(self, sep=None, maxsplit=-1):  # type: ignore[no-untyped-def]
        return ["evil", "22222222-2222-4222-8222-222222222222"]


class ForgedTenantUUIDText(str):
    """String subclass that forges UUID parsing and canonical-equality checks."""

    def replace(self, old, new, *args):  # type: ignore[no-untyped-def]
        canonical = "11111111-1111-4111-8111-111111111111"
        return canonical.replace(old, new, *args)

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        return other is not None

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        return other is None


class ForgedGovernanceText(str):
    """String subclass that forges fixed equality and allow-list membership."""

    def __eq__(self, other):  # type: ignore[no-untyped-def]
        return True

    def __ne__(self, other):  # type: ignore[no-untyped-def]
        return False

    def __hash__(self) -> int:
        return hash("annual_compensation_review")


def test_rejects_reference_string_subclass_that_can_forge_namespace_validation(
    valid_packet_kwargs: dict[str, object],
) -> None:
    kwargs = valid_packet_kwargs.copy()
    kwargs["compensation_review_reference"] = ForgedReference("evil:payload")
    with pytest.raises(ValueError, match="compensation_review_reference"):
        build_compensation_change_review_packet(**kwargs)


def test_rejects_tenant_string_subclass_that_can_forge_uuid_validation(
    valid_packet_kwargs: dict[str, object],
) -> None:
    kwargs = valid_packet_kwargs.copy()
    kwargs["tenant_record_id"] = ForgedTenantUUIDText("not-a-tenant-uuid")
    with pytest.raises(ValueError, match="tenant_record_id"):
        build_compensation_change_review_packet(**kwargs)


def test_rejects_forged_purpose_and_reason_codes(valid_packet_kwargs: dict[str, object]) -> None:
    purpose_kwargs = valid_packet_kwargs.copy()
    purpose_kwargs["purpose_code"] = ForgedGovernanceText("attacker_controlled_purpose")
    with pytest.raises(ValueError, match="purpose_code"):
        build_compensation_change_review_packet(**purpose_kwargs)

    reason_kwargs = valid_packet_kwargs.copy()
    reason_kwargs["reason_code"] = ForgedGovernanceText("attacker_controlled_reason")
    with pytest.raises(ValueError, match="reason_code"):
        build_compensation_change_review_packet(**reason_kwargs)


def test_rejects_digest_string_subclass_before_pattern_match(valid_packet_kwargs: dict[str, object]) -> None:
    """Digest evidence must not retain caller-defined string behavior."""
    kwargs = valid_packet_kwargs.copy()
    kwargs["compensation_policy_digest"] = ForgedGovernanceText("a" * 64)
    with pytest.raises(ValueError, match="compensation_policy_digest"):
        build_compensation_change_review_packet(**kwargs)


@pytest.mark.parametrize(
    "field_name",
    (
        "decision_authority",
        "review_state",
        "scope_verification_state",
        "mutation_state",
        "external_execution_state",
        "next_action",
    ),
)
def test_rejects_forged_direct_construction_constant_text(
    field_name: str,
    valid_packet_kwargs: dict[str, object],
) -> None:
    packet = build_compensation_change_review_packet(**valid_packet_kwargs)
    with pytest.raises(ValueError, match=field_name):
        replace(packet, **{field_name: ForgedGovernanceText("attacker_controlled_text")})
