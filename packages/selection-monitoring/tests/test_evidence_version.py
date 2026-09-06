"""Regression coverage for explicit selection-monitoring evidence versioning."""

from dataclasses import replace
import json

import pytest

from orgmetra_selection_monitoring import SelectionOutcomeMonitoringPlan

from test_plan import valid_kwargs


def _plan(evidence_version: int = 1) -> SelectionOutcomeMonitoringPlan:
    """Build one valid monitoring plan while varying only its evidence version."""
    kwargs = valid_kwargs()
    kwargs["evidence_version"] = evidence_version
    return SelectionOutcomeMonitoringPlan(**kwargs)


def test_evidence_version_is_part_of_immutable_monitoring_evidence() -> None:
    """Bind evidence revision identity into canonical JSON and the packet digest."""
    first = _plan(1)
    second = _plan(2)
    assert json.loads(first.canonical_json())["evidence_version"] == 1
    assert first.canonical_json() != second.canonical_json()
    assert first.sha256_digest() != second.sha256_digest()


@pytest.mark.parametrize("evidence_version", [True, False, 0, -1, 2_147_483_648, "1", 1.0])
def test_rejects_noncanonical_evidence_versions(evidence_version: object) -> None:
    """Reject booleans, non-integers, non-positive values, and signed-int32 overflow."""
    with pytest.raises(ValueError, match="evidence_version"):
        _plan(evidence_version)  # type: ignore[arg-type]


def test_replace_cannot_bypass_monitoring_evidence_version_validation() -> None:
    """Revalidate explicit evidence-version bounds when immutable plans are copied."""
    with pytest.raises(ValueError, match="evidence_version"):
        replace(_plan(), evidence_version=0)
