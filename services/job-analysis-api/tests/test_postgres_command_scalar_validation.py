"""Regression coverage for durable Job Analysis command scalars at persistence."""

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
_RESOURCE_REFERENCE = f"job_analysis_snapshot:{ANALYSIS.hex}"


class _TextSubtype(str):
    """Represent caller-defined executable text at the durable write boundary."""


def _never_connect() -> object:
    """Prove malformed command evidence is rejected before database acquisition."""
    raise AssertionError("database acquired before durable command scalar validation")


def _audit_event(
    *,
    actor_reference: str = _ACTOR_REFERENCE,
    purpose_code: str = _PURPOSE_CODE,
) -> AuditOutboxEvent:
    """Build one valid audit event matching the Job Analysis write authority."""
    snapshot = clinical_psychologist_snapshot()
    return AuditOutboxEvent(
        event_id=UUID("0198a412-6000-7000-8000-000000000411"),
        tenant_record_id=TENANT,
        source_service="job_analysis_api",
        event_type="orgmetra.job_architecture.snapshot_recorded",
        resource_reference=_RESOURCE_REFERENCE,
        actor_reference=actor_reference,
        purpose_code=purpose_code,
        reason_code="snapshot_persisted",
        evidence_version_code=snapshot.analysis_version_code,
        result_code="recorded",
        occurred_at=datetime(2026, 8, 18, 5, 1, tzinfo=timezone.utc),
        high_impact=False,
    )


def _persist(
    *,
    idempotency_key: str = IDEMPOTENCY_KEY,
    request_digest: str | None = None,
    actor_reference: str = _ACTOR_REFERENCE,
    purpose_code: str = _PURPOSE_CODE,
) -> None:
    """Invoke the PostgreSQL port with otherwise-valid durable command evidence."""
    snapshot = clinical_psychologist_snapshot()
    digest = request_digest
    if digest is None:
        digest = command_digest(
            snapshot=snapshot,
            position_record_id=None,
            criterion_blueprint_id=None,
        )
    PostgresJobAnalysisPort(_never_connect).persist_snapshot(
        snapshot=snapshot,
        idempotency_key=idempotency_key,
        request_digest=digest,
        actor_reference=actor_reference,
        purpose_code=purpose_code,
        position_record_id=None,
        criterion_blueprint_id=None,
        audit_event=_audit_event(
            actor_reference=actor_reference,
            purpose_code=purpose_code,
        ),
        outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000412"),
        write_command_id=UUID("0198a412-6000-7000-8000-000000000413"),
    )


@pytest.mark.parametrize(
    "idempotency_key",
    [
        _TextSubtype(IDEMPOTENCY_KEY),
        f"{IDEMPOTENCY_KEY}\n",
    ],
)
def test_durable_idempotency_key_fails_closed_before_database(idempotency_key: str) -> None:
    """Persistence must reject executable or control-character Idempotency-Key text."""
    with pytest.raises(ValueError, match="idempotency_key"):
        _persist(idempotency_key=idempotency_key)


@pytest.mark.parametrize(
    "request_digest",
    [
        _TextSubtype("a" * 64),
        "not-a-lowercase-sha256-digest",
    ],
)
def test_durable_request_digest_fails_closed_before_database(request_digest: str) -> None:
    """Persistence must accept only exact lowercase SHA-256 command digests."""
    with pytest.raises(ValueError, match="request_digest"):
        _persist(request_digest=request_digest)


@pytest.mark.parametrize(
    ("field_name", "actor_reference", "purpose_code"),
    [
        ("actor_reference", _TextSubtype(_ACTOR_REFERENCE), _PURPOSE_CODE),
        ("purpose_code", _ACTOR_REFERENCE, _TextSubtype(_PURPOSE_CODE)),
    ],
)
def test_durable_authority_text_fails_closed_before_database(
    field_name: str,
    actor_reference: str,
    purpose_code: str,
) -> None:
    """Actor and purpose authority must be exact immutable text before DB acquisition."""
    with pytest.raises(ValueError, match=field_name):
        _persist(
            actor_reference=actor_reference,
            purpose_code=purpose_code,
        )
