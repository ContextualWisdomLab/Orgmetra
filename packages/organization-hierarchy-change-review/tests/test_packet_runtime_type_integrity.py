"""Regression for packet-level checked-versus-emitted runtime substitution."""

import pytest

from orgmetra_organization_hierarchy_change_review import OrganizationHierarchyChangeReviewPacket


def test_rejects_packet_runtime_subclass_before_trust_field_validation() -> None:
    """Do not let packet polymorphism reach validation or canonical emission."""
    with pytest.raises(TypeError, match="does not support caller-defined subclasses"):

        class TenantSwapPacket(OrganizationHierarchyChangeReviewPacket):
            """Try to change one trust-bearing field across repeated reads."""

            def __getattribute__(self, name: str) -> object:
                """Swap tenant evidence without mutating the inherited frozen slots."""
                if name == "tenant_record_id":
                    return "not-a-uuid"
                return super().__getattribute__(name)


def test_rejects_subclass_that_bypasses_base_post_init() -> None:
    """A subclass must not suppress the base validation hook entirely."""
    with pytest.raises(TypeError, match="does not support caller-defined subclasses"):

        class PostInitBypassPacket(OrganizationHierarchyChangeReviewPacket):
            """Try to replace the inherited post-init validator with a no-op."""

            def __post_init__(self) -> None:
                """Suppress all base validation if subclass creation were permitted."""
