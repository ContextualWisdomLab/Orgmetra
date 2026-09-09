"""Regressions for module-level audit issuance authority storage."""

from orgmetra_hris_kernel import audit as audit_module


def test_audit_issuance_backing_registries_are_not_module_mutation_capabilities() -> None:
    """Importing the audit module must not expose mutable canonical-issuance storage."""
    assert not hasattr(audit_module, "_AUDIT_LIVE_ISSUANCES")
    assert not hasattr(audit_module, "_AUDIT_CREATION_SNAPSHOTS")


def test_audit_module_does_not_export_closure_backed_issuance_mutators() -> None:
    """Consumers must not recover authority dictionaries through exported closure cells."""
    assert not hasattr(audit_module, "_claim_audit_issuance")
    assert not hasattr(audit_module, "_record_audit_creation_snapshot")
    assert not hasattr(audit_module, "_lookup_audit_creation_snapshot")
