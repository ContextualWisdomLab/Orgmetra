"""Regression coverage for post-issuance compensation-review evidence integrity."""

from copy import copy
from gc import collect

import pytest

from orgmetra_compensation_change_review import (
    CompensationChangeReviewPacket,
    build_compensation_change_review_packet,
)


def _packet(valid_packet_kwargs: dict[str, object]) -> CompensationChangeReviewPacket:
    """Build one governed packet through the supported public constructor."""
    return build_compensation_change_review_packet(**valid_packet_kwargs)


def test_valid_value_mutation_cannot_rewrite_emitted_evidence(valid_packet_kwargs: dict[str, object]) -> None:
    """Low-level replacement with another valid value cannot emit a second audit truth."""
    packet = _packet(valid_packet_kwargs)
    original = packet.canonical_json()
    object.__setattr__(
        packet,
        "compensation_policy_digest",
        "2" * 64,
    )

    with pytest.raises(ValueError, match="integrity"):
        packet.canonical_json()
    assert '"compensation_policy_digest":"' + ("d" * 64) + '"' in original


def test_shallow_copy_does_not_inherit_process_local_issuance_evidence(valid_packet_kwargs: dict[str, object]) -> None:
    """Unsupported object copies must fail closed rather than inheriting issuance trust."""
    packet = _packet(valid_packet_kwargs)
    copied = copy(packet)

    assert copied is not packet
    with pytest.raises(ValueError, match="integrity"):
        copied.canonical_json()


def test_collected_packet_releases_process_local_issuance_binding(valid_packet_kwargs: dict[str, object]) -> None:
    """Weak cleanup must not leave stale process-local issuance state behind."""
    packet = _packet(valid_packet_kwargs)
    assert packet.canonical_json()
    del packet
    collect()

    replacement = _packet(valid_packet_kwargs)
    assert replacement.canonical_json()
