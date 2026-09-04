"""Regression coverage for inert Job Analysis durable audit occurrence time."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_hris_kernel import AuditOutboxEvent
from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import command_digest
from fixtures import ANALYSIS, IDEMPOTENCY_KEY, TENANT, clinical_psychologist_snapshot

_ACTOR_REFERENCE = "keyverse:actor-ja-1"
_PURPOSE_CODE = "job_analysis_write"


class _ExecutableAuditDatetime(datetime):
    """Trip if durable canonicalization invokes caller-defined datetime behavior."""

    def astimezone(self, tz: object | None = None) -> datetime:
        """Prove exact-type rejection must precede canonical timestamp conversion."""
        del tz
        raise AssertionError(
            "audit datetime astimezone executed before exact-type rejection"
        )


def _never_connect() -> object:
    """Prove invalid audit time is rejected before PostgreSQL acquisition."""
    raise AssertionError("database acquired before audit time runtime validation")


def test_executable_audit_datetime_fails_before_canonicalization_or_database() -> None:
    """A datetime subtype must not execute while durable audit bytes are frozen."""
    snapshot = clinical_psychologist_snapshot()
    audit_event = AuditOutboxEvent(
        event_id=UUID("0198a412-6000-7000-8000-000000000501"),
        tenant_record_id=TENANT,
        source_service="job_analysis_api",
        event_type="orgmetra.job_architecture.snapshot_recorded",
        resource_reference=f"job_analysis_snapshot:{ANALYSIS.hex}",
        actor_reference=_ACTOR_REFERENCE,
        purpose_code=_PURPOSE_CODE,
        reason_code="snapshot_persisted",
        evidence_version_code=snapshot.analysis_version_code,
        result_code="recorded",
        occurred_at=_ExecutableAuditDatetime(
            2026,
            9,
            4,
            5,
            30,
            tzinfo=timezone.utc,
        ),
        high_impact=False,
    )
    port = PostgresJobAnalysisPort(_never_connect)

    with pytest.raises(
        ValueError,
        match=r"audit_event\.occurred_at must be an exact built-in datetime",
    ):
        port.persist_snapshot(
            snapshot=snapshot,
            idempotency_key=IDEMPOTENCY_KEY,
            request_digest=command_digest(
                snapshot=snapshot,
                position_record_id=None,
                criterion_blueprint_id=None,
            ),
            actor_reference=_ACTOR_REFERENCE,
            purpose_code=_PURPOSE_CODE,
            position_record_id=None,
            criterion_blueprint_id=None,
            audit_event=audit_event,
            outbox_delivery_record_id=UUID(
                "0198a412-6000-7000-8000-000000000502"
            ),
            write_command_id=UUID("0198a412-6000-7000-8000-000000000503"),
        )
