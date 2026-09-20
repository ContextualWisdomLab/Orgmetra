"""Regression for malformed worker numerics that overflow float conversion."""

import pytest

from orgmetra_validity_analysis import ConvergenceDiagnostics


def test_oversized_worker_numeric_is_rejected_as_value_error() -> None:
    """Normalize float-conversion overflow to the package's ValueError contract."""
    oversized_integer = 10**10000

    with pytest.raises(ValueError, match="finite number"):
        ConvergenceDiagnostics(
            converged=True,
            iterations=1,
            objective_value=oversized_integer,
            maximum_gradient=0.1,
        )
