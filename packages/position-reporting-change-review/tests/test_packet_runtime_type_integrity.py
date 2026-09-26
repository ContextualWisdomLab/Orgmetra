"""Regression for packet-level validation-hook and attribute substitution."""

import pytest

from orgmetra_position_reporting_change_review import PositionReportingChangeReviewPacket


def test_rejects_packet_runtime_subclass_before_attribute_substitution() -> None:
    """Reject packet polymorphism before trust-bearing attribute resolution can change."""
    def substitute_tenant_attribute(packet_instance: object, attribute_name: str) -> object:
        """Return attacker-controlled tenant evidence."""
        if attribute_name == "tenant_record_id":
            return "not-a-uuid"
        return object.__getattribute__(packet_instance, attribute_name)

    with pytest.raises(TypeError, match="does not support caller-defined subclasses"):
        type(
            "TenantSwapPacket",
            (PositionReportingChangeReviewPacket,),
            {"__getattribute__": substitute_tenant_attribute},
        )


def test_rejects_subclass_that_bypasses_base_post_init() -> None:
    """Reject a class that would suppress the inherited dataclass validation hook."""
    def suppress_post_init(_packet_instance: object) -> None:
        """Suppress all base validation if subclass creation were allowed."""

    with pytest.raises(TypeError, match="does not support caller-defined subclasses"):
        type(
            "PostInitBypassPacket",
            (PositionReportingChangeReviewPacket,),
            {"__post_init__": suppress_post_init},
        )
