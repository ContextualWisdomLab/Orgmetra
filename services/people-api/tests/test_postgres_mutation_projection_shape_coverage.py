"""Hosted-coverage regressions for fixed People PostgreSQL projection widths."""

from __future__ import annotations

import pytest

import orgmetra_people_api.postgres_mutations as postgres_mutations
from orgmetra_people_api.mutations import PeopleMutationIntegrityError


@pytest.mark.parametrize(
    ("helper_name", "error_message"),
    [
        ("_employment_version_from_row", "employment version row has an invalid shape"),
        ("_position_version_from_row", "position version row has an invalid shape"),
        ("_assignment_from_row", "assignment row has an invalid shape"),
    ],
)
def test_fixed_projection_helpers_reject_wrong_width(
    helper_name: str,
    error_message: str,
) -> None:
    """Cover each fail-closed width guard reported missing by exact-head Foundation CI."""
    helper = getattr(postgres_mutations, helper_name)

    with pytest.raises(PeopleMutationIntegrityError, match=error_message):
        helper(postgres_mutations.UUID("10000000-0000-7000-8000-000000000001"), ())
