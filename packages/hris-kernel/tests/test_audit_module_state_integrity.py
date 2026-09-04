"""Regressions for module-level audit issuance authority storage."""

from orgmetra_hris_kernel import audit as audit_module


def test_audit_issuance_backing_registries_are_not_module_mutation_capabilities() -> None:
    """Importing the audit module must not expose mutable canonical-issuance storage."""
    assert not hasattr(audit_module, "_AUDIT_LIVE_ISSUANCES")
    assert not hasattr(audit_module, "_AUDIT_CREATION_SNAPSHOTS")
