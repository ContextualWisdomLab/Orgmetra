"""Regression contracts for candidate-conversion versus People mutation authority."""

from __future__ import annotations

import inspect
import unittest

from orgmetra_people_api.mutations import PeopleMutationIntegrityError
from orgmetra_people_api.postgres_mutations import (
    PostgresPeopleMutationPort,
    _require_one_person_employment_anchor,
)
from test_people_mutations import PERSON


class ConversionEmploymentBindingRegressionTests(unittest.TestCase):
    """Keep recruiting provenance out of generic Employment and Assignment authority."""

    def test_generic_employment_creation_does_not_require_candidate_conversion(self) -> None:
        """A future Employment cannot depend on a conversion whose FK already needs it."""
        source = inspect.getsource(PostgresPeopleMutationPort.create_employment)
        self.assertNotIn("_CONVERSION_SQL", source)

    def test_generic_assignment_creation_does_not_require_candidate_conversion(self) -> None:
        """Staffing an Employment cannot depend on unrelated historical recruiting provenance."""
        source = inspect.getsource(PostgresPeopleMutationPort.create_assignment)
        self.assertNotIn("_CONVERSION_SQL", source)
        self.assertIn("_ASSIGNMENT_EMPLOYMENT_ANCHOR_SQL", source)

    def test_person_anchor_rejects_non_database_time_evidence(self) -> None:
        """The Person conflict anchor must reject malformed durable time evidence."""
        with self.assertRaisesRegex(PeopleMutationIntegrityError, "anchor identity"):
            _require_one_person_employment_anchor(
                [(PERSON, "2026-09-13T07:00:00+09:00")],
                expected_person_record_id=PERSON,
            )


if __name__ == "__main__":  # pragma: no cover - direct local invocation only
    unittest.main()