"""Regression contract for exact candidate-conversion Employment provenance."""

from __future__ import annotations

import unittest

from orgmetra_people_api.postgres_mutations import _CONVERSION_SQL


class ConversionEmploymentBindingRegressionTests(unittest.TestCase):
    """Keep candidate conversion authority bound to the exact Employment aggregate."""

    def test_conversion_lookup_binds_exact_employment_identity(self) -> None:
        """Reject a Person-only conversion lookup that can authorize a different Employment."""
        self.assertIn("AND conversion.employment_record_id = %s", _CONVERSION_SQL)
        self.assertEqual(_CONVERSION_SQL.count("%s"), 3)


if __name__ == "__main__":  # pragma: no cover - direct local invocation only
    unittest.main()
