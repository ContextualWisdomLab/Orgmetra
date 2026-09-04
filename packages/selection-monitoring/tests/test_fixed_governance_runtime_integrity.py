"""Regression tests for fixed selection-monitoring governance text integrity."""

from dataclasses import replace

import pytest

from test_plan import build_valid


class ForgedFixedGovernanceText(str):
    """String subclass that lies during equality checks but keeps forged JSON text."""

    def __eq__(self, other: object) -> bool:
        """Pretend the forged value equals every governed constant."""
        return True

    def __ne__(self, other: object) -> bool:
        """Pretend the forged value never differs from a governed constant."""
        return False


@pytest.mark.parametrize(
    "field_name",
    ["analysis_scope", "decision_authority", "review_state", "next_action"],
)
def test_rejects_string_subclasses_for_fixed_governance_fields(field_name: str) -> None:
    """Reject canonical evidence whose fixed governance text can bypass comparison."""
    with pytest.raises(ValueError, match=field_name):
        replace(
            build_valid(),
            **{field_name: ForgedFixedGovernanceText("forged_governance_value")},
        )
