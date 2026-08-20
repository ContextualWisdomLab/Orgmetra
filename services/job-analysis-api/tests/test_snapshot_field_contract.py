"""Fail-closed field-shape regressions for posted job-analysis evidence."""

from __future__ import annotations

from copy import deepcopy
import unittest

from orgmetra_job_analysis_api.snapshot import snapshot_from_document
from fixtures import TENANT, clinical_psychologist_document


class JobAnalysisSnapshotFieldContractTests(unittest.TestCase):
    """Keep runtime parsing aligned with OpenAPI ``additionalProperties: false``."""

    def test_unknown_top_level_field_is_rejected_instead_of_silently_dropped(self) -> None:
        """Do not collapse materially different requests to the same command digest."""
        document = clinical_psychologist_document()
        document["candidate_name"] = "must-not-enter-job-evidence"

        with self.assertRaisesRegex(ValueError, "snapshot document contains unsupported fields"):
            snapshot_from_document(document, tenant_record_id=TENANT)

    def test_unknown_nested_fields_are_rejected_at_every_evidence_boundary(self) -> None:
        """Do not admit covert values beside Task, KSAO, link, FJA, or source contracts."""
        mutations = (
            ("task", lambda document: document["tasks"][0].__setitem__("model_output", "draft")),
            ("task source", lambda document: document["tasks"][0]["source"].__setitem__("raw_excerpt", "value")),
            ("KSAO", lambda document: document["ksao_requirements"][0].__setitem__("candidate_score", 99)),
            ("task-KSAO link", lambda document: document["task_ksao_links"][0].__setitem__("comment", "hidden")),
            ("FJA", lambda document: document["fja_profile"].__setitem__("free_text", "hidden")),
            ("FJA source", lambda document: document["fja_profile"]["source"].__setitem__("credential", "secret")),
        )
        original = clinical_psychologist_document()
        for boundary, mutate in mutations:
            with self.subTest(boundary=boundary):
                document = deepcopy(original)
                mutate(document)
                with self.assertRaisesRegex(ValueError, "contains unsupported fields"):
                    snapshot_from_document(document, tenant_record_id=TENANT)


if __name__ == "__main__":
    unittest.main()
