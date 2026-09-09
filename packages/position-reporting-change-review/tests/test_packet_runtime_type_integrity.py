"""Regression for packet-level validation-hook and attribute substitution."""

import pytest

from orgmetra_position_reporting_change_review import PositionReportingChangeReviewPacket


def test_rejects_packet_runtime_subclass_before_attribute_substitution() -> None:
    """Reject packet polymorphism before trust-bearing attribute resolution can change."""
    with pytest.raises(TypeError, match="does not support caller-defined subclasses"):

        class TenantSwapPacket(PositionReportingChangeReviewPacket):
            """Try to substitute tenant evidence through attribute dispatch."""

            def __getattribute__(self, name: str) -> object:
                """Return attacker-controlled tenant evidence."""
                if name == "tenant_record_id":
                    return "not-a-uuid"
                return super().__getattribute__(name)


def test_rejects_subclass_that_bypasses_base_post_init() -> None:
    """Reject a class that would suppress the inherited dataclass validation hook."""
    with pytest.raises(TypeError, match="does not support caller-defined subclasses"):

        class PostInitBypassPacket(PositionReportingChangeReviewPacket):
            """Try to replace the base post-init validator with a no-op."""

            def __post_init__(self) -> None:
                """Suppress all base validation if subclass creation were allowed."""
