"""Adversarial runtime-integrity tests for governed offer-approval text evidence."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmetra_offer_approval import OfferApprovalPacket, build_offer_approval_packet


class ForgedGovernanceText(str):
    """Preserve unsafe serialized text while forging reviewed comparisons."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    def __hash__(self) -> int:
        return hash("selected_candidate_offer_review")


class ForgedOperationalUuid(str):
    """Return safe parser input while retaining different tenant audit text."""

    def replace(self, old: str, new: str, count: int = -1) -> str:
        return "11111111111141118111111111111111"

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False


class ForgedReference(str):
    """Return a reviewed UUID suffix while retaining value-bearing reference text."""

    def startswith(self, prefix: str, *args: object) -> bool:
        return True

    def split(self, separator: str | None = None, maxsplit: int = -1) -> list[str]:
        return ["candidate_profile", "10000000-0000-4000-8000-000000000002"]


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise-valid value-free offer approval request."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "offer_approval_reference": "offer_approval:10000000-0000-4000-8000-000000000001",
        "candidate_profile_reference": "candidate_profile:10000000-0000-4000-8000-000000000002",
        "requisition_reference": "requisition:10000000-0000-4000-8000-000000000003",
        "job_profile_reference": "job_profile:10000000-0000-4000-8000-000000000004",
        "position_record_reference": "position_record:10000000-0000-4000-8000-000000000005",
        "selection_decision_reference": "selection_decision:10000000-0000-4000-8000-000000000006",
        "selection_decision_digest": "a" * 64,
        "compensation_package_reference": "compensation_package:10000000-0000-4000-8000-000000000007",
        "compensation_package_digest": "b" * 64,
        "offer_terms_reference": "offer_terms:10000000-0000-4000-8000-000000000008",
        "offer_terms_digest": "c" * 64,
        "requester_reference": "actor:10000000-0000-4000-8000-000000000009",
        "approver_reference": "actor:10000000-0000-4000-8000-00000000000a",
        "purpose_code": "offer_approval_review",
        "reason_code": "selected_candidate_offer_review",
        "generated_at": datetime(2026, 8, 19, 5, 10, tzinfo=timezone.utc),
    }


@pytest.mark.parametrize(
    ("field_name", "forged_text"),
    [
        ("purpose_code", "shadow_offer_review"),
        ("reason_code", "employee_jane_doe"),
        ("decision_authority", "model_decision_allowed"),
        ("review_state", "approved_without_human"),
        ("delivery_state", "authorized_to_send"),
        ("next_action", "send_offer_without_authoritative_resolution"),
    ],
)
def test_rejects_forged_governance_text_before_canonical_evidence(
    field_name: str,
    forged_text: str,
) -> None:
    """Caller-defined string comparison behavior must not forge reviewed evidence."""
    kwargs = valid_kwargs()
    kwargs[field_name] = ForgedGovernanceText(forged_text)

    with pytest.raises(ValueError):
        OfferApprovalPacket(**kwargs)


def test_rejects_forged_tenant_uuid_parser_behavior() -> None:
    """Tenant identity validation must never execute caller-defined string methods."""
    kwargs = valid_kwargs()
    kwargs["tenant_record_id"] = ForgedOperationalUuid("employee_jane_doe")

    with pytest.raises(ValueError):
        build_offer_approval_packet(**kwargs)


def test_rejects_forged_reference_parser_behavior() -> None:
    """Opaque reference validation must bind the exact serialized string value."""
    kwargs = valid_kwargs()
    kwargs["candidate_profile_reference"] = ForgedReference(
        "candidate_profile:employee_jane_doe"
    )

    with pytest.raises(ValueError):
        build_offer_approval_packet(**kwargs)


def test_rejects_post_issuance_runtime_evidence_mutation() -> None:
    """Canonical audit bytes must remain bound to the exact packet that was issued."""
    packet = build_offer_approval_packet(**valid_kwargs())
    issued_digest = packet.sha256_digest()

    object.__setattr__(packet, "offer_terms_digest", "d" * 64)

    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.sha256_digest()
    assert issued_digest != "d" * 64


def test_rejects_attempt_to_reseal_mutated_runtime_evidence() -> None:
    """Calling post-init again must never legitimize altered high-impact evidence."""
    packet = build_offer_approval_packet(**valid_kwargs())
    object.__setattr__(packet, "offer_terms_digest", "d" * 64)

    with pytest.raises(ValueError, match="cannot be reissued"):
        packet.__post_init__()
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()


def test_rejects_runtime_issuance_seal_removal() -> None:
    """Deleting the process-local issuance seal must make canonical export fail closed."""
    packet = build_offer_approval_packet(**valid_kwargs())
    object.__delattr__(packet, "_issuance_seal")

    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()


def test_rejects_reissue_after_seal_deletion_and_evidence_mutation() -> None:
    """Deleting the seal must not make an already-issued packet eligible for reissuance."""
    packet = build_offer_approval_packet(**valid_kwargs())
    object.__delattr__(packet, "_issuance_seal")
    object.__setattr__(packet, "offer_terms_digest", "d" * 64)

    with pytest.raises(ValueError, match="cannot be reissued"):
        packet.__post_init__()
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.canonical_json()
    with pytest.raises(ValueError, match="changed after issuance"):
        packet.sha256_digest()
