"""Regression coverage for free-form feedback exclusion from review evidence."""

from dataclasses import replace
import json

import pytest

from test_packet import build_valid


def test_packet_explicitly_excludes_free_form_feedback() -> None:
    """Keep free-form human feedback outside the immutable correlation envelope."""
    packet = build_valid()

    assert packet.contains_free_form_feedback is False
    assert json.loads(packet.canonical_json())["contains_free_form_feedback"] is False

    with pytest.raises(ValueError, match="free-form feedback"):
        replace(packet, contains_free_form_feedback=True)
