"""Regression for runtime-type integrity of HR data-retention review evidence."""

import pytest

from orgmetra_hr_data_retention import HrDataRetentionReviewPacket


def _forged_deletion_authority(_packet: object) -> str:
    """Return the destructive value an attacker would try to inject via inheritance."""
    return "authorized_to_delete"


def test_retention_packet_cannot_be_subclassed_to_forge_derived_authority() -> None:
    """A caller cannot override non-authorizing properties through a packet subclass."""
    with pytest.raises(TypeError, match="final"):
        type(
            "ForgedRetentionReviewPacket",
            (HrDataRetentionReviewPacket,),
            {"disposition_authorization_state": property(_forged_deletion_authority)},
        )
