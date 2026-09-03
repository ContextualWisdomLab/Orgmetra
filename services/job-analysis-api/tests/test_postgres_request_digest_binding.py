"""Regression coverage for semantic request-digest binding at the PostgreSQL boundary."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import JobAnalysisIntegrityError
from fixtures import IDEMPOTENCY_KEY, clinical_psychologist_snapshot
from test_postgres import _audit_event


def test_write_port_rejects_well_formed_digest_for_different_command_before_database() -> None:
    """A syntactically valid digest cannot redefine idempotency semantics at the durable port."""
    snapshot = clinical_psychologist_snapshot()

    def never_connect() -> object:
        raise AssertionError("database acquired before request-digest binding validation")

    with pytest.raises(
        JobAnalysisIntegrityError,
        match="request_digest does not match detached snapshot command",
    ):
        PostgresJobAnalysisPort(never_connect).persist_snapshot(
            snapshot=snapshot,
            idempotency_key=IDEMPOTENCY_KEY,
            request_digest="0" * 64,
            actor_reference="keyverse:actor-ja-1",
            purpose_code="job_analysis_write",
            position_record_id=None,
            criterion_blueprint_id=None,
            audit_event=_audit_event(),
            outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000412"),
            write_command_id=UUID("0198a412-6000-7000-8000-000000000413"),
        )
