"""Regression contract for candidate-conversion versus People mutation authority."""

from __future__ import annotations

import inspect
import unittest

from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort


class ConversionEmploymentBindingRegressionTests(unittest.TestCase):
    """Keep recruiting provenance out of generic Employment authorization."""

    def test_generic_employment_creation_does_not_require_candidate_conversion(self) -> None:
        """A future Employment cannot depend on a conversion whose FK already needs it."""
        source = inspect.getsource(PostgresPeopleMutationPort.create_employment)
        self.assertNotIn("_CONVERSION_SQL", source)


if __name__ == "__main__":  # pragma: no cover - direct local invocation only
    unittest.main()
