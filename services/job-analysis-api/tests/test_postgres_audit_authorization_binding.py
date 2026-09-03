"""Regression coverage for job-analysis authorization/audit binding at persistence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from typing import TypeVar
from uuid import UUID

import pytest

from orgmetra_hris_kernel import AuditOutboxEvent
from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import JobAnalysisIntegrityError, command_digest
from fixtures import ANALYSIS, IDEMPOTENCY_KEY, OTHER_TENANT, TENANT, clinical_psychologist_snapshot

_ACTOR_REFERENCE = "keyverse:actor-ja-1"
_PURPOSE_CODE = "job_analysis_write"
_RESOURCE_REFERENCE = f"job_analysis_snapshot:{ANALYSIS.hex}"
_AuditEventT = TypeVar("_AuditEventT", bound=AuditOutboxEvent)


class _AuditEventSubtype(AuditOutboxEvent):
    """Trip if persistence consumes caller-defined audit behavior before type rejection."""

    _TRIPWIRE_FIELDS = frozenset(
        {"tenant_record_id", "resource_reference", "actor_reference", "purpose_code"}
    )

    def __getattribute__(self, name: str) -> object:
        """Reject authority-field reads once the adversarial fixture is armed."""
        if name in _AuditEventSubtype._TRIPWIRE_FIELDS:
            try:
                armed = object.__getattribute__(self, "_tripwire_armed")
            except AttributeError:
                armed = False
            if armed:
                raise AssertionError(f"audit subtype authority field consumed before exact-type rejection: {name}")
        return super().__getattribute__(name)

    def canonical_json(self) -> str:
        """Reject canonical serialization if exact-type validation is reordered."""
        raise AssertionError("audit subtype canonical_json consumed before exact-type rejection")

    def content_digest(self) -> str:
        """Reject digest serialization if exact-type validation is reordered."""
        raise AssertionError("audit subtype content_digest consumed before exact-type rejection")


class _ForgedAuthorityText(str):
    """Retain hostile audit text while reporting equality with reviewed evidence."""

    def __new__(cls, value: str, equal_to: str) -> _ForgedAuthorityText:
        """Build valid-looking text whose equality does not describe its stored bytes."""
        instance = super().__new__(cls, value)
        instance._equal_to = equal_to
        return instance

    def __eq__(self, other: object) -> bool:
        """Spoof equality only for the reviewed evidence value."""
        return other == self._equal_to

    def __ne__(self, other: object) -> bool:
        """Keep inequality logically inverse to the forged equality result."""
        return not self.__eq__(other)

    __hash__ = str.__hash__


class _AuditFieldMutatingTimezone(tzinfo):
    """Mutate one exact audit-envelope field from the canonicalization callback surface."""

    def __init__(
        self,
        field_name: str = "actor_reference",
        field_value: object = "keyverse:actor-ja-canonicalization-drift",
    ) -> None:
        """Start inert so AuditOutboxEvent construction itself remains valid."""
        self._audit_event: AuditOutboxEvent | None = None
        self._field_name = field_name
        self._field_value = field_value
        self._armed = False

    def arm(self, audit_event: AuditOutboxEvent) -> None:
        """Enable the mutation only after the exact event constructor has returned."""
        self._audit_event = audit_event
        self._armed = True

    def utcoffset(self, value: datetime | None) -> timedelta:
        """Drift one field when canonicalization asks the timezone for its UTC offset."""
        del value
        if self._armed and self._audit_event is not None:
            object.__setattr__(
                self._audit_event,
                self._field_name,
                self._field_value,
            )
        return timedelta(0)

    def dst(self, value: datetime | None) -> timedelta:
        """Expose a stable zero daylight-saving offset."""
        del value
        return timedelta(0)

    def tzname(self, value: datetime | None) -> str:
        """Return a deterministic test-only timezone name."""
        del value
        return "UTC_TEST"


def _never_connect() -> object:
    """Prove invalid durable evidence is rejected before database acquisition."""
    raise AssertionError("database acquired before job-analysis audit binding validation")


def _audit_event(
    event_class: type[_AuditEventT] = AuditOutboxEvent,
    **overrides: object,
) -> _AuditEventT:
    """Build one shaped audit envelope whose evidence may be adversarially drifted."""
    snapshot = clinical_psychologist_snapshot()
    values: dict[str, object] = {
        "event_id": UUID("0198a412-6000-7000-8000-000000000401"),
        "tenant_record_id": TENANT,
        "source_service": "job_analysis_api",
        "event_type": "orgmetra.job_architecture.snapshot_recorded",
        "resource_reference": _RESOURCE_REFERENCE,
        "actor_reference": _ACTOR_REFERENCE,
        "purpose_code": _PURPOSE_CODE,
        "reason_code": "snapshot_persisted",
        "evidence_version_code": snapshot.analysis_version_code,
        "result_code": "recorded",
        "occurred_at": datetime(2026, 8, 18, 5, 1, tzinfo=timezone.utc),
        "high_impact": False,
    }
    values.update(overrides)
    event = event_class(**values)  # type: ignore[arg-type]
    if type(event) is _AuditEventSubtype:
        object.__setattr__(event, "_tripwire_armed", True)
    return event


def _persist_with_audit(audit_event: AuditOutboxEvent) -> None:
    """Invoke the durable write boundary with one otherwise-valid command."""
    snapshot = clinical_psychologist_snapshot()
    port = PostgresJobAnalysisPort(_never_connect)
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
        outbox_delivery_record_id=UUID("0198a412-6000-7000-8000-000000000402"),
        write_command_id=UUID("0198a412-6000-7000-8000-000000000403"),
    )


@pytest.mark.parametrize(
    "audit_event",
    [
        _audit_event(actor_reference="keyverse:actor-ja-other"),
        _audit_event(purpose_code="job_analysis_read"),
        _audit_event(tenant_record_id=OTHER_TENANT),
        _audit_event(resource_reference="job_analysis_snapshot:0198a412600070008000000000000999"),
    ],
)
def test_job_analysis_audit_authority_drift_fails_before_database(
    audit_event: AuditOutboxEvent,
) -> None:
    """Command authority and durable audit provenance must describe the same write."""
    with pytest.raises(JobAnalysisIntegrityError, match="audit event does not match the job-analysis write authority"):
        _persist_with_audit(audit_event)


@pytest.mark.parametrize(
    ("field_name", "forged_value", "reviewed_value"),
    [
        (
            "resource_reference",
            "job_analysis_snapshot:0198a412600070008000000000000999",
            _RESOURCE_REFERENCE,
        ),
        ("actor_reference", "keyverse:actor-ja-other", _ACTOR_REFERENCE),
        ("purpose_code", "job_analysis_read", _PURPOSE_CODE),
    ],
)
def test_exact_audit_event_rejects_forged_authority_text_before_database(
    field_name: str,
    forged_value: str,
    reviewed_value: str,
) -> None:
    """Exact envelope type must not let subtype-controlled equality authorize durable audit bytes."""
    audit_event = _audit_event(
        **{field_name: _ForgedAuthorityText(forged_value, reviewed_value)}
    )

    with pytest.raises(
        ValueError,
        match=rf"audit_event\.{field_name} must be exact built-in text",
    ):
        _persist_with_audit(audit_event)


@pytest.mark.parametrize(
    "audit_event",
    [
        _audit_event(source_service="people_api"),
        _audit_event(event_type="orgmetra.job_architecture.snapshot_superseded"),
        _audit_event(reason_code="snapshot_corrected"),
        _audit_event(evidence_version_code="unexpected:v1"),
        _audit_event(result_code="updated"),
        _audit_event(confirmation_reference="review:job-analysis-1"),
        _audit_event(high_impact=True, confirmation_reference="review:job-analysis-1"),
    ],
)
def test_job_analysis_audit_semantic_drift_fails_before_database(
    audit_event: AuditOutboxEvent,
) -> None:
    """Durable audit semantics must identify this exact successful snapshot-recording write."""
    with pytest.raises(
        JobAnalysisIntegrityError,
        match="audit event does not match the job-analysis snapshot semantics",
    ):
        _persist_with_audit(audit_event)


@pytest.mark.parametrize(
    ("field_name", "forged_value", "reviewed_value"),
    [
        ("source_service", "people_api", "job_analysis_api"),
        (
            "event_type",
            "orgmetra.job_architecture.snapshot_superseded",
            "orgmetra.job_architecture.snapshot_recorded",
        ),
        ("reason_code", "snapshot_corrected", "snapshot_persisted"),
        ("evidence_version_code", "unexpected:v1", clinical_psychologist_snapshot().analysis_version_code),
        ("result_code", "updated", "recorded"),
    ],
)
def test_exact_audit_event_rejects_forged_semantic_text_before_database(
    field_name: str,
    forged_value: str,
    reviewed_value: str,
) -> None:
    """Runtime text equality must not substitute for durable audit semantic bytes."""
    audit_event = _audit_event(
        **{field_name: _ForgedAuthorityText(forged_value, reviewed_value)}
    )

    with pytest.raises(
        ValueError,
        match=rf"audit_event\.{field_name} must be exact built-in text",
    ):
        _persist_with_audit(audit_event)


def test_canonicalization_callback_cannot_drift_validated_audit_authority() -> None:
    """Canonical bytes must be rechecked after any executable timezone callback."""
    callback_timezone = _AuditFieldMutatingTimezone()
    audit_event = _audit_event(
        occurred_at=datetime(2026, 8, 18, 5, 1, tzinfo=callback_timezone)
    )
    callback_timezone.arm(audit_event)

    with pytest.raises(
        JobAnalysisIntegrityError,
        match="canonical audit evidence does not match validated authority",
    ):
        _persist_with_audit(audit_event)


def test_canonicalization_callback_cannot_drift_validated_audit_semantics() -> None:
    """Frozen canonical bytes must still represent the pre-canonical semantic snapshot."""
    callback_timezone = _AuditFieldMutatingTimezone("result_code", "updated")
    audit_event = _audit_event(
        occurred_at=datetime(2026, 8, 18, 5, 1, tzinfo=callback_timezone)
    )
    callback_timezone.arm(audit_event)

    with pytest.raises(
        JobAnalysisIntegrityError,
        match="canonical audit evidence does not match validated semantics",
    ):
        _persist_with_audit(audit_event)


def test_job_analysis_audit_subtype_fails_before_any_audit_or_database_access() -> None:
    """Exact-type rejection must precede subtype-controlled fields, serialization, and DB I/O."""
    with pytest.raises(TypeError, match="audit_event must be an exact AuditOutboxEvent"):
        _persist_with_audit(_audit_event(_AuditEventSubtype))
