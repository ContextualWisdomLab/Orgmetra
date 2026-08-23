"""Executable contract for the public position-reporting package surface."""

import orgmetra_hris_kernel as kernel


def test_position_reporting_contract_is_exported_from_package_root() -> None:
    """Position-reporting users can import the governed contract from the package root."""
    expected_exports = {
        "PositionReportingHierarchyError",
        "PositionReportingRelationship",
        "PositionReportingSnapshot",
        "build_position_reporting_snapshot",
    }

    assert expected_exports <= set(kernel.__all__)
    for export_name in expected_exports:
        assert getattr(kernel, export_name).__module__ == "orgmetra_hris_kernel.position_reporting"
