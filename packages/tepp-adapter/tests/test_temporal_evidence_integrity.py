"""Regression coverage for TEPP temporal-evidence canonicalization integrity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from orgmetra_tepp_adapter import build_tepp_analysis_request_packet


class ForgedDateTime(datetime):
    """Datetime subclass able to forge canonical TEPP/audit evidence."""

    def astimezone(self, tz=None):  # type: ignore[no-untyped-def]
        """Keep the hostile subclass alive across UTC normalization."""
        return self

    def isoformat(self, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
        """Return an instant different from the underlying evidence instant."""
        return "2099-12-31T23:59:59+00:00"


class MutableOffsetTimezone(tzinfo):
    """Timezone provider whose offset can change after packet construction."""

    def __init__(self, offset: timedelta) -> None:
        self.offset = offset

    def utcoffset(self, value: datetime | None) -> timedelta:
        """Return the currently configured offset."""
        return self.offset


class ExplodingOffsetTimezone(tzinfo):
    """Timezone provider that raises while its offset is requested."""

    def utcoffset(self, value: datetime | None) -> timedelta:
        """Raise to verify provider failures become validation errors."""
        raise RuntimeError("offset provider unavailable")


class WrongOffsetTimezone(tzinfo):
    """Timezone provider that returns a non-timedelta offset."""

    def utcoffset(self, value: datetime | None) -> str:  # type: ignore[override]
        """Return an invalid offset type at the trust boundary."""
        return "not-a-timedelta"


def valid_kwargs() -> dict[str, object]:
    """Return one otherwise valid Orgmetra-to-TEPP request packet input."""
    return {
        "tenant_record_id": "11111111-1111-4111-8111-111111111111",
        "validation_study_reference": "validation_study:22222222-2222-4222-8222-222222222222",
        "requested_by_actor_reference": "actor:33333333-3333-4333-8333-333333333333",
        "tepp_workspace_id": "workspace-opaque-8e9f1d",
        "tepp_snapshot_id": "snapshot-opaque-2f6c91",
        "snapshot_digest": "a" * 64,
        "idempotency_key": "orgmetra-tepp-20260821-0001",
        "knowledge_cutoff": datetime(2026, 8, 21, 3, 30, tzinfo=timezone.utc),
        "model_contract_version": "temporal-event-v1",
        "output_profile": "validation-report",
        "generated_at": datetime(2026, 8, 21, 4, 30, tzinfo=timezone.utc),
    }


@pytest.mark.parametrize("field_name", ["knowledge_cutoff", "generated_at"])
def test_rejects_datetime_subclasses_that_can_forge_temporal_evidence(field_name: str) -> None:
    """TEPP request and audit evidence must not invoke caller-overridable datetime methods."""
    kwargs = valid_kwargs()
    kwargs[field_name] = ForgedDateTime(2026, 8, 21, 4, 30, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        build_tepp_analysis_request_packet(**kwargs)


@pytest.mark.parametrize("field_name", ["knowledge_cutoff", "generated_at"])
def test_freezes_mutable_timezone_before_request_and_governance_evidence(field_name: str) -> None:
    """Changing a caller-owned timezone cannot rewrite stored TEPP evidence."""
    provider = MutableOffsetTimezone(timedelta(hours=9))
    kwargs = valid_kwargs()
    kwargs[field_name] = datetime(
        2026,
        8,
        21,
        12 if field_name == "knowledge_cutoff" else 13,
        30,
        1 if field_name == "generated_at" else 0,
        123456 if field_name == "generated_at" else 0,
        tzinfo=provider,
    )
    packet = build_tepp_analysis_request_packet(**kwargs)
    request = packet.canonical_tepp_json()
    evidence = packet.governance_evidence()

    provider.offset = timedelta(hours=10)

    assert packet.knowledge_cutoff == datetime(2026, 8, 21, 3, 30, tzinfo=timezone.utc)
    assert packet.generated_at == datetime(
        2026,
        8,
        21,
        4,
        30,
        1 if field_name == "generated_at" else 0,
        123456 if field_name == "generated_at" else 0,
        tzinfo=timezone.utc,
    )
    assert packet.canonical_tepp_json() == request
    assert packet.governance_evidence() == evidence


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("knowledge_cutoff", datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))),
        ("generated_at", datetime.max.replace(tzinfo=timezone(-timedelta(hours=1)))),
        ("knowledge_cutoff", datetime(2026, 8, 21, 3, 30, tzinfo=ExplodingOffsetTimezone())),
        ("generated_at", datetime(2026, 8, 21, 4, 30, tzinfo=ExplodingOffsetTimezone())),
        ("knowledge_cutoff", datetime(2026, 8, 21, 3, 30, tzinfo=WrongOffsetTimezone())),
        ("generated_at", datetime(2026, 8, 21, 4, 30, tzinfo=WrongOffsetTimezone())),
    ],
)
def test_rejects_unusable_temporal_providers(field_name: str, value: object) -> None:
    """Provider failures, malformed offsets, and UTC arithmetic overflow fail closed."""
    kwargs = valid_kwargs()
    kwargs[field_name] = value

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        build_tepp_analysis_request_packet(**kwargs)


def test_canonical_evidence_rejects_low_level_datetime_reinjection() -> None:
    """Unsafe post-construction mutation cannot invoke forged datetime renderers."""
    packet = build_tepp_analysis_request_packet(**valid_kwargs())
    object.__setattr__(packet, "knowledge_cutoff", ForgedDateTime(2026, 8, 21, 4, 30, tzinfo=timezone.utc))

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        packet.canonical_tepp_json()


def test_generated_at_must_not_precede_knowledge_cutoff() -> None:
    """Reject packets whose generation instant precedes their own knowledge cutoff."""
    kwargs = valid_kwargs()
    kwargs["knowledge_cutoff"] = datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc)
    kwargs["generated_at"] = datetime(2026, 8, 21, 4, 59, 59, 999999, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="generated_at must not precede knowledge_cutoff"):
        build_tepp_analysis_request_packet(**kwargs)


def test_equal_workspace_and_snapshot_identifiers_are_rejected() -> None:
    """Reference manipulation cannot reuse one opaque identifier for two entity types."""
    kwargs = valid_kwargs()
    kwargs["tepp_workspace_id"] = "opaque-duplicated-1f2e3d"
    kwargs["tepp_snapshot_id"] = "opaque-duplicated-1f2e3d"

    with pytest.raises(ValueError, match="must be distinct opaque identifiers"):
        build_tepp_analysis_request_packet(**kwargs)
