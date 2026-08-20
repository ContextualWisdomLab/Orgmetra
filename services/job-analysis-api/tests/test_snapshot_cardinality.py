"""Regression contracts for bounded job-analysis snapshot cardinality."""

import pytest

from fixtures import TENANT, clinical_psychologist_document
from orgmetra_job_analysis_api.snapshot import snapshot_from_document


def test_rejects_oversized_task_collection_before_duplicate_linkage_work() -> None:
    """Bound task parsing explicitly instead of relying only on the HTTP byte ceiling."""
    posted = clinical_psychologist_document()
    posted["tasks"] = posted["tasks"] * 501

    with pytest.raises(ValueError, match="tasks must contain at most 500 items"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_oversized_ksao_collection_before_duplicate_linkage_work() -> None:
    """Bound KSAO parsing explicitly for predictable validation cost."""
    posted = clinical_psychologist_document()
    posted["ksao_requirements"] = posted["ksao_requirements"] * 501

    with pytest.raises(ValueError, match="ksao_requirements must contain at most 500 items"):
        snapshot_from_document(posted, tenant_record_id=TENANT)


def test_rejects_oversized_task_ksao_link_collection_before_link_validation() -> None:
    """Bound relation parsing so dense matrices cannot create unbounded validation work."""
    posted = clinical_psychologist_document()
    posted["task_ksao_links"] = posted["task_ksao_links"] * 834

    with pytest.raises(ValueError, match="task_ksao_links must contain at most 5000 items"):
        snapshot_from_document(posted, tenant_record_id=TENANT)
