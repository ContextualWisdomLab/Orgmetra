import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID

import pytest

from orgmetra_hris_kernel.audit import AuditOutboxEvent

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
EVENT_ID = UUID("00000000-0000-4000-8000-000000000002")
NIL_ID = UUID(int=0)
MAX_ID = UUID(int=(1 << 128) - 1)
OCCURRED_AT = datetime(2026, 8, 17, 1, 30, tzinfo=timezone.utc)


def _event(**overrides):
    """Build one governed event and allow one test to override selected fields."""
    values = {
        "event_id": EVENT_ID,
        "tenant_record_id": TENANT_ID,
        "source_service": "people_core",
        "event_type": "orgmetra.people.assignment.recorded",
        "resource_reference": "assignment_record:01JTESTOPAQUE",
        "actor_reference": "keyverse_subject:01JACTOROPAQUE",
        "purpose_code": "workforce_administration",
        "reason_code": "hire_completion",
        "evidence_version_code": "employment-offer:v3",
        "result_code": "recorded",
        "occurred_at": OCCURRED_AT,
        "high_impact": True,
        "confirmation_reference": "confirmation:01JCONFIRMOPAQUE",
    }
    values.update(overrides)
    return AuditOutboxEvent(**values)


def test_cloud_event_contains_governance_context_without_raw_hr_payload():
    """The audit envelope carries accountability metadata, not shadow HR facts."""
    event = _event()
    envelope = event.to_cloudevent()

    assert envelope == {
        "specversion": "1.0",
        "id": str(EVENT_ID),
        "source": "urn:orgmetra:people_core",
        "type": "orgmetra.people.assignment.recorded",
        "subject": "assignment_record:01JTESTOPAQUE",
        "time": "2026-08-17T01:30:00Z",
        "datacontenttype": "application/json",
        "orgmetratenant": str(TENANT_ID),
        "orgmetraactor": "keyverse_subject:01JACTOROPAQUE",
        "orgmetrapurpose": "workforce_administration",
        "orgmetrareason": "hire_completion",
        "orgmetraevidence": "employment-offer:v3",
        "orgmetraconfirmation": "confirmation:01JCONFIRMOPAQUE",
        "data": {"result_code": "recorded", "high_impact": True},
    }
    assert len(event.content_digest()) == 64
    assert event.content_digest() == event.content_digest()


def test_canonical_json_is_the_exact_persistence_and_digest_byte_contract():
    """Persistence receives one deterministic JSON byte representation, not a re-encoding guess."""
    event = _event()
    canonical = event.canonical_json()

    assert json.loads(canonical) == event.to_cloudevent()
    assert canonical == json.dumps(
        event.to_cloudevent(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    assert sha256(canonical.encode("utf-8")).hexdigest() == event.content_digest()


def test_low_impact_event_may_omit_confirmation_and_normalizes_offset_to_utc():
    """Routine events normalize a non-UTC source timestamp without inventing confirmation."""
    event = _event(
        high_impact=False,
        confirmation_reference=None,
        occurred_at=datetime(
            2026,
            8,
            17,
            10,
            30,
            tzinfo=timezone(timedelta(hours=9)),
        ),
    )

    envelope = event.to_cloudevent()
    assert "orgmetraconfirmation" not in envelope
    assert envelope["time"] == "2026-08-17T01:30:00Z"


def test_high_impact_event_requires_human_confirmation_reference():
    """High-impact employment evidence cannot be emitted without a human confirmation."""
    with pytest.raises(ValueError, match="confirmation_reference"):
        _event(confirmation_reference=None)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("source_service", "People-Core"),
        ("source_service", "people"),
        ("event_type", "people.assignment.recorded"),
        ("event_type", "orgmetra."),
        ("event_type", "orgmetra.People.assignment.recorded"),
        ("resource_reference", "   "),
        ("resource_reference", "person@example.com"),
        ("actor_reference", ""),
        ("actor_reference", "Ada Lovelace"),
        ("purpose_code", " "),
        ("purpose_code", "Workforce Administration"),
        ("reason_code", "\t"),
        ("reason_code", "Hire Completion"),
        ("evidence_version_code", "\n"),
        ("evidence_version_code", "offer version 3"),
        ("result_code", ""),
        ("result_code", "Recorded Result"),
    ],
)
def test_event_rejects_noncanonical_or_blank_contract_fields(field_name, bad_value):
    """Invalid governance identifiers fail closed before reaching persistence."""
    with pytest.raises(ValueError):
        _event(**{field_name: bad_value})


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("event_id", str(EVENT_ID)),
        ("tenant_record_id", str(TENANT_ID)),
        ("occurred_at", "2026-08-17T01:30:00Z"),
        ("high_impact", 1),
        ("source_service", None),
        ("confirmation_reference", 7),
    ],
)
def test_event_rejects_runtime_type_confusion(field_name, bad_value):
    """Public construction fails closed instead of silently coercing contract types."""
    with pytest.raises(ValueError, match="must be"):
        _event(**{field_name: bad_value})


@pytest.mark.parametrize("field_name", ["event_id", "tenant_record_id"])
def test_event_rejects_nil_uuid_identities(field_name):
    """Reserved nil UUIDs cannot become durable event or tenant identities."""
    with pytest.raises(ValueError, match="nil UUID"):
        _event(**{field_name: NIL_ID})


@pytest.mark.parametrize("field_name", ["event_id", "tenant_record_id"])
def test_event_rejects_max_uuid_identities(field_name):
    """RFC 9562 Max UUID sentinels cannot become durable event or tenant identities."""
    with pytest.raises(ValueError, match="max UUID"):
        _event(**{field_name: MAX_ID})


def test_event_rejects_naive_occurrence_time():
    """Audit ordering requires an unambiguous system time."""
    with pytest.raises(ValueError, match="timezone-aware"):
        _event(occurred_at=datetime(2026, 8, 17, 1, 30))


def test_digest_changes_when_governance_context_changes():
    """A reason-code change is detectable by the immutable envelope digest."""
    original = _event().content_digest()
    changed = _event(reason_code="manager_transfer").content_digest()
    assert original != changed


def test_event_rejects_custom_timezone_before_provider_callback():
    """Caller-defined timezone behavior is rejected before any provider hook executes."""
    from datetime import tzinfo

    class ExecutableTimezone(tzinfo):
        """Record any forbidden UTC-offset callback at the audit trust boundary."""

        def __init__(self):
            self.calls = 0

        def utcoffset(self, dt):
            """Expose a tripwire if the boundary executes this provider."""
            del dt
            self.calls += 1
            return timedelta(0)

    provider = ExecutableTimezone()
    with pytest.raises(ValueError, match="datetime.timezone or zoneinfo.ZoneInfo"):
        _event(occurred_at=datetime(2026, 8, 17, 1, 30, tzinfo=provider))

    assert provider.calls == 0


def test_event_rejects_blank_optional_confirmation_reference():
    """An explicitly supplied confirmation identifier must be meaningful."""
    with pytest.raises(ValueError, match="must not be blank"):
        _event(high_impact=False, confirmation_reference="   ")


def test_event_rejects_nonopaque_optional_confirmation_reference():
    """Free-text confirmation data cannot enter an opaque-reference field."""
    with pytest.raises(ValueError, match="opaque reference"):
        _event(high_impact=False, confirmation_reference="approved by Ada")


def test_canonical_event_prevents_actor_replacement_after_construction():
    """Canonical actor evidence is structurally immutable after validation."""
    event = _event()
    original = event.canonical_json()

    with pytest.raises(AttributeError):
        object.__setattr__(event, "actor_reference", "Ada Lovelace")

    assert event.canonical_json() == original


def test_canonical_event_prevents_confirmation_removal_after_construction():
    """A validated high-impact confirmation cannot be removed from the immutable event."""
    event = _event()
    original = event.canonical_json()

    with pytest.raises(AttributeError):
        object.__setattr__(event, "confirmation_reference", None)

    assert event.canonical_json() == original


def test_canonical_event_prevents_identity_replacement_before_stringification():
    """Untrusted replacement identities cannot be installed into the canonical value object."""

    class ExecutableIdentifier:
        """Fail if any rejected replacement is unexpectedly stringified."""

        def __init__(self) -> None:
            self.calls = 0

        def __str__(self) -> str:
            self.calls += 1
            raise AssertionError("untrusted identity stringification executed")

    event = _event()
    replacement = ExecutableIdentifier()

    with pytest.raises(AttributeError):
        object.__setattr__(event, "event_id", replacement)

    assert replacement.calls == 0
    assert event.event_id == EVENT_ID
