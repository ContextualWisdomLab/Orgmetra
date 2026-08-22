"""Regression for runtime-type integrity of HR data-retention review evidence."""

import pytest

from orgmetra_hr_data_retention import HrDataRetentionReviewPacket


def test_retention_packet_cannot_be_subclassed_to_forge_derived_authority() -> None:
    """A caller cannot override non-authorizing properties through a packet subclass."""
    with pytest.raises(TypeError, match="final"):

        class ForgedRetentionReviewPacket(HrDataRetentionReviewPacket):
            """Attempt to turn a review packet into forged deletion authority."""

            @property
            def disposition_authorization_state(self) -> str:
                """Forge a destructive state if subclassing were permitted."""
                return "authorized_to_delete"
