"""Regression contract for workforce-validation authorized-view issuance."""

from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.registry import ValidityStudyView


TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")


def test_direct_authorized_view_construction_fails_closed() -> None:
    """Require purpose-bound reads, not public construction, to issue study views."""
    with pytest.raises(TypeError, match="issued only by read_validity_study"):
        ValidityStudyView(
            tenant_record_id=TENANT,
            validity_study_id=STUDY,
            fields=(("study_status_code", "study_draft"),),
        )
