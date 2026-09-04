"""Runtime-type integrity regressions for immutable audit/outbox evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from uuid import UUID

import pytest

from orgmetra_hris_kernel.audit import AuditOutboxEvent


class _ForgedUUID(UUID):
    """Attempt to rewrite an immutable identity during canonical serialization."""

    def __str__(self) -> str:
        """Render an identity different from the underlying UUID value."""
        return "00000000-0000-4000-8000-ffffffffffff"


class _ForgedOccurredAt(datetime):
    """Attempt to rewrite an immutable event timestamp during serialization."""

    def astimezone(self, tz=None):  # noqa: ANN001
        """Preserve hostile runtime behavior through UTC normalization."""
        return self

    def isoformat(self, sep="T", timespec="auto") -> str:  # noqa: ARG002
        """Render a different instant from the underlying timestamp."""
        return "2099-01-01T00:00:00+00:00"


class _OpaqueText(str):
    """Represent valid audit text through an untrusted runtime subclass."""


class _MutableOffset(tzinfo):
    """Expose timezone state that can change after event construction."""

    def __init__(self) -> None:
        """Start with a UTC offset."""
        self.offset = timedelta(0)

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Return the currently configured offset."""
        del value
        return self.offset

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed."""
        del value
        return timedelta(0)


class _TripwireOffset(tzinfo):
    """Fail if post-construction mutation can reintroduce timezone behavior."""

    def __init__(self) -> None:
        self.calls = 0

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Record and reject any callback if mutation unexpectedly succeeds."""
        del value
        self.calls += 1
        raise AssertionError("reintroduced timezone callback executed before rejection")

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed if unexpectedly queried."""
        del value
        return timedelta(0)


class _ExplodingOffset(tzinfo):
    """Raise arbitrary provider behavior while an event instant is resolved."""

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Force the trust boundary to normalize provider failures."""
        del value
        raise RuntimeError("provider details must not escape")

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed if queried."""
        del value
        return timedelta(0)


class _OversizedOffset(tzinfo):
    """Return an extreme offset that cannot be detached from year one."""

    def utcoffset(self, value):  # type: ignore[no-untyped-def]
        """Force UTC detachment outside representable datetime values."""
        del value
        return timedelta(hours=23, minutes=59)

    def dst(self, value):  # type: ignore[no-untyped-def]
        """Keep daylight saving fixed."""
        del value
        return timedelta(0)


def _event(**overrides: object) -> AuditOutboxEvent:
    """Build one valid high-impact audit event with focused overrides."""
    values: dict[str, object] = {
        "event_id": UUID("00000000-0000-4000-8000-000000000002"),
        "tenant_record_id": UUID("00000000-0000-4000-8000-000000000001"),
        "source_service": "people_core",
        "event_type": "orgmetra.people.assignment.recorded",
        "resource_reference": "assignment_record:01JTESTOPAQUE",
        "actor_reference": "keyverse_subject:01JACTOROPAQUE",
        "purpose_code": "workforce_administration",
        "reason_code": "hire_completion",
        "evidence_version_code": "employment-offer:v3",
        "result_code": "recorded",
        "occurred_at": datetime(2026, 8, 21, 5, 20, tzinfo=timezone.utc),
        "high_impact": True,
        "confirmation_reference": "confirmation:01JCONFIRMOPAQUE",
    }
    values.update(overrides)
    return AuditOutboxEvent(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("field_name", ["event_id", "tenant_record_id"])
def test_audit_event_rejects_uuid_subclasses_before_canonicalization(field_name: str) -> None:
    """Caller-controlled UUID rendering cannot alter durable audit identity evidence."""
    forged = _ForgedUUID("00000000-0000-4000-8000-000000000123")
    with pytest.raises(ValueError, match=f"{field_name} must be a UUID"):
        _event(**{field_name: forged})


def test_audit_event_rejects_datetime_subclasses_before_canonicalization() -> None:
    """Caller-controlled timestamp rendering cannot alter durable audit chronology."""
    forged = _ForgedOccurredAt(2026, 8, 21, 5, 20, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="occurred_at must be a datetime"):
        _event(occurred_at=forged)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("source_service", _OpaqueText("people_core")),
        ("event_type", _OpaqueText("orgmetra.people.assignment.recorded")),
        ("resource_reference", _OpaqueText("assignment_record:01JTESTOPAQUE")),
        ("actor_reference", _OpaqueText("keyverse_subject:01JACTOROPAQUE")),
        ("purpose_code", _OpaqueText("workforce_administration")),
        ("reason_code", _OpaqueText("hire_completion")),
        ("evidence_version_code", _OpaqueText("employment-offer:v3")),
        ("result_code", _OpaqueText("recorded")),
        ("confirmation_reference", _OpaqueText("confirmation:01JCONFIRMOPAQUE")),
    ],
)
def test_audit_event_rejects_string_subclasses_before_canonicalization(
    field_name: str, value: str
) -> None:
    """Reject caller-controlled runtime behavior in every audit text field."""
    with pytest.raises(ValueError, match="must be a string"):
        _event(**{field_name: value})


def test_audit_event_detaches_mutable_timezone_state() -> None:
    """Keep canonical audit chronology stable after timezone state mutates."""
    zone = _MutableOffset()
    event = _event(
        high_impact=False,
        confirmation_reference=None,
        occurred_at=datetime(2026, 8, 21, 5, 20, tzinfo=zone),
    )
    first = event.to_cloudevent()

    zone.offset = timedelta(hours=9)

    assert event.occurred_at.tzinfo is timezone.utc
    assert event.to_cloudevent() == first


def test_audit_event_normalizes_timezone_provider_exceptions() -> None:
    """Do not leak arbitrary timezone-provider exceptions from event construction."""
    with pytest.raises(ValueError, match="occurred_at must resolve to a UTC offset"):
        _event(occurred_at=datetime(2026, 8, 21, 5, 20, tzinfo=_ExplodingOffset()))


def test_audit_event_normalizes_offset_overflow_to_value_error() -> None:
    """Fail closed when UTC detachment exceeds representable datetime values."""
    with pytest.raises(ValueError, match="occurred_at must be a representable"):
        _event(occurred_at=datetime(1, 1, 1, 0, 0, tzinfo=_OversizedOffset()))


def test_audit_event_prevents_reintroduced_timezone_behavior_by_structure() -> None:
    """Post-construction mutation fails before caller-controlled timezone callbacks can exist."""
    event = _event()
    tripwire = _TripwireOffset()
    replacement = datetime(2026, 8, 21, 5, 20, tzinfo=tripwire)

    with pytest.raises(AttributeError):
        object.__setattr__(event, "occurred_at", replacement)

    assert event.occurred_at.tzinfo is timezone.utc
    assert tripwire.calls == 0
