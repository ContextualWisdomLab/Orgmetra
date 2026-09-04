"""Regression for creation-seal tamper resistance in candidate offer responses."""

from copy import copy, deepcopy
from datetime import datetime, timezone
import pickle

import pytest

from orgmetra_candidate_offer_response.response import build_candidate_offer_response


def _issued_packet():
    """Return one freshly issued governed candidate offer response."""
    return build_candidate_offer_response(
        tenant_record_id="018f6e2a-4f7c-7a1b-9c20-1f3a7d8e5b60",
        offer_response_reference="candidate_offer_response:6ba7b810-9dad-4b11-80b4-00c04fd430c8",
        candidate_profile_reference="candidate_profile:6ba7b811-9dad-4b11-80b4-00c04fd430c8",
        offer_approval_reference="offer_approval:6ba7b812-9dad-4b11-80b4-00c04fd430c8",
        offer_approval_digest="a" * 64,
        offer_terms_reference="offer_terms:6ba7b813-9dad-4b11-80b4-00c04fd430c8",
        offer_terms_digest="b" * 64,
        candidate_actor_reference="candidate:6ba7b814-9dad-4b11-80b4-00c04fd430c8",
        identity_resolution_reference="identity_resolution:6ba7b815-9dad-4b11-80b4-00c04fd430c8",
        identity_resolution_digest="c" * 64,
        response_code="offer_accepted",
        responded_at=datetime(2026, 8, 22, 9, 30, 15, tzinfo=timezone.utc),
        recorded_at=datetime(2026, 8, 22, 9, 30, 16, tzinfo=timezone.utc),
    )


def test_creation_seal_cannot_be_rewritten_with_payload() -> None:
    """A caller must not turn post-issuance rewrites into freshly valid evidence."""
    packet = _issued_packet()

    object.__setattr__(packet, "response_code", "offer_declined")
    forged_live_digest = packet._raw_sha256_digest()  # noqa: SLF001 - adversarial regression
    object.__setattr__(packet, "_creation_evidence_digest", forged_live_digest)

    with pytest.raises(ValueError, match="offer response evidence changed after construction"):
        packet.canonical_json()


@pytest.mark.parametrize(
    "clone_factory",
    [
        copy,
        deepcopy,
        lambda packet: pickle.loads(pickle.dumps(packet)),
    ],
    ids=["copy", "deepcopy", "pickle_round_trip"],
)
def test_cloned_packets_fail_closed_without_issuance_seal(clone_factory) -> None:
    """Copies bypass issuance, so they must fail closed with an explicit error."""
    packet = _issued_packet()
    clone = clone_factory(packet)

    assert isinstance(clone, type(packet))
    with pytest.raises(ValueError, match="candidate offer response evidence has no issuance seal"):
        clone.canonical_json()
