from dataclasses import replace
import json

import pytest

from test_packet import build_valid


def test_packet_carries_explicit_evidence_version() -> None:
    packet = build_valid()
    assert packet.evidence_version == 1
    assert json.loads(packet.canonical_json())["evidence_version"] == 1


def test_evidence_version_changes_canonical_evidence() -> None:
    first = build_valid()
    second = build_valid(evidence_version=2)
    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()


@pytest.mark.parametrize("version", [0, -1, True, "1", 2_147_483_648])
def test_direct_construction_rejects_invalid_evidence_version(version: object) -> None:
    with pytest.raises(ValueError, match="evidence_version"):
        replace(build_valid(), evidence_version=version)
