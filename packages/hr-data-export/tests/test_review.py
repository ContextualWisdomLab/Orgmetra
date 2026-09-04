"""Adversarial contract tests for governed HR data export review evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone, tzinfo
from hashlib import sha256
import json

import pytest

from orgmetra_hr_data_export import HrDataExportReviewPacket


TENANT = "0198d2dd-7215-7c44-a8a3-7d4d42b9087e"
EXPORT_REVIEW = "export_review:3f66ab91-2d1d-4a16-a37b-a9a897382692"
RESOURCE = "person_record:431d7f42-720b-4d58-bdab-2af689089a43"
AUTHORIZATION = "authorization_decision:29fde057-7f82-4aaa-a906-e31445b05a0b"
REQUESTER = "actor:30d0887a-acf9-4b33-b19f-71d5015b5c6e"
REVIEWER = "actor:e296fc39-0b2a-48ce-b53a-a7a814cbb0a9"
DIGEST = "7" * 64
FIELDS = ("business_email_address", "display_name")
GENERATED_AT = datetime(2026, 8, 22, 13, 0, tzinfo=timezone(timedelta(hours=9)))


class ForgedStr(str):
    """String subtype whose equality/hash behavior must never cross trust boundaries."""

    def __eq__(self, other: object) -> bool:
        return True

    def __hash__(self) -> int:
        return hash("hr_data_export_review")


class ForgedInt(int):
    """Integer subtype whose ordering must never control evidence validation."""

    def __lt__(self, other: object) -> bool:
        return False

    def __le__(self, other: object) -> bool:
        return False

    def __gt__(self, other: object) -> bool:
        return False

    def __ge__(self, other: object) -> bool:
        return False


class ForgedDateTime(datetime):
    """Datetime subtype must be rejected before caller-defined behavior runs."""


class OffsetlessTimezone(tzinfo):
    """Timezone object that does not identify an actual UTC offset."""

    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None


class ExplodingTimezone(tzinfo):
    """Timezone object whose failure must be normalized by the trust boundary."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        raise RuntimeError("provider detail must not escape")

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)


class MutableTimezone(tzinfo):
    """Timezone whose offset can change after packet construction."""

    def __init__(self) -> None:
        self.hours = 9

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return timedelta(hours=self.hours)

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)


def packet(**overrides: object) -> HrDataExportReviewPacket:
    """Build one minimal valid export-review packet and apply explicit overrides."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "export_review_reference": EXPORT_REVIEW,
        "resource_kind": "person_record",
        "resource_reference": RESOURCE,
        "authorization_evidence_reference": AUTHORIZATION,
        "authorization_evidence_digest": DIGEST,
        "authorization_policy_version_code": "people_export_policy_v1",
        "requester_reference": REQUESTER,
        "reviewer_reference": REVIEWER,
        "purpose_code": "hr_data_export_review",
        "reason_code": "employee_access_request",
        "requested_fields": FIELDS,
        "export_format_code": "json",
        "destination_kind": "authenticated_one_time_download",
        "generated_at": GENERATED_AT,
        "evidence_version": 1,
    }
    values.update(overrides)
    return HrDataExportReviewPacket(**values)  # type: ignore[arg-type]


def test_packet_is_value_minimized_deterministic_and_redacted() -> None:
    """Canonical evidence must contain scope/provenance only, never exported values."""
    result = packet()
    document = json.loads(result.canonical_json())
    assert repr(result) == "HrDataExportReviewPacket(<redacted>)"
    assert document["generated_at"] == "2026-08-22T04:00:00Z"
    assert document["requested_fields"] == list(FIELDS)
    assert document["contains_pii_values"] is False
    assert document["human_review_required"] is True
    assert document["scope_verification_state"] == "requires_authoritative_resolution"
    assert document["export_state"] == "not_authorized_to_export"
    assert "field_values" not in document
    assert result.sha256_digest() == sha256(result.canonical_json().encode("utf-8")).hexdigest()


def test_valid_custom_timezone_is_frozen_to_immutable_utc() -> None:
    """Later timezone-provider mutation must not rewrite recorded audit chronology."""
    zone = MutableTimezone()
    result = packet(generated_at=datetime(2026, 8, 22, 13, 0, tzinfo=zone))
    before = result.canonical_json()
    zone.hours = -7
    assert result.generated_at == datetime(2026, 8, 22, 4, 0, tzinfo=timezone.utc)
    assert result.generated_at.tzinfo is timezone.utc
    assert result.canonical_json() == before


@pytest.mark.parametrize(
    "value",
    [
        None,
        ForgedStr(TENANT),
        "not-a-uuid",
        TENANT.upper(),
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
    ],
)
def test_tenant_identity_rejects_noncanonical_or_executable_text(value: object) -> None:
    """Tenant identity must be canonical non-sentinel built-in UUID text."""
    with pytest.raises(ValueError, match="tenant_record_id"):
        packet(tenant_record_id=value)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("export_review_reference", "wrong:3f66ab91-2d1d-4a16-a37b-a9a897382692"),
        ("export_review_reference", "export_review:not-a-uuid"),
        ("export_review_reference", "export_review:0198d2dd-7215-7c44-a8a3-7d4d42b9087e"),
        ("export_review_reference", ForgedStr(EXPORT_REVIEW)),
        ("resource_reference", "job_profile:431d7f42-720b-4d58-bdab-2af689089a43"),
        ("authorization_evidence_reference", "authorization_decision:not-a-uuid"),
        ("requester_reference", "actor:not-a-uuid"),
        ("reviewer_reference", ForgedStr(REVIEWER)),
    ],
)
def test_opaque_references_are_exact_namespaced_uuid4(field_name: str, value: object) -> None:
    """Correlation references must not carry semantic or caller-defined parser behavior."""
    with pytest.raises(ValueError, match=field_name):
        packet(**{field_name: value})


@pytest.mark.parametrize("resource_kind", ["person", "Person_Record", ForgedStr("person_record")])
def test_resource_kind_requires_descriptive_exact_code(resource_kind: object) -> None:
    """The resource namespace must be explicit lower snake_case built-in text."""
    with pytest.raises(ValueError, match="resource_kind"):
        packet(resource_kind=resource_kind)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("authorization_evidence_digest", "A" * 64),
        ("authorization_evidence_digest", "7" * 63),
        ("authorization_evidence_digest", ForgedStr(DIGEST)),
        ("authorization_policy_version_code", "bad version"),
        ("authorization_policy_version_code", ForgedStr("people_export_policy_v1")),
        ("authorization_policy_version_code", "x" * 129),
    ],
)
def test_authorization_provenance_is_bounded_and_exact(field_name: str, value: object) -> None:
    """Authorization provenance must be immutable correlation, not caller-controlled behavior."""
    with pytest.raises(ValueError, match=field_name):
        packet(**{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("purpose_code", "general_export", "purpose_code"),
        ("purpose_code", ForgedStr("shadow_export"), "purpose_code"),
        ("reason_code", "manager_curiosity", "reason_code"),
        ("reason_code", ForgedStr("employee_access_request"), "reason_code"),
        ("export_format_code", "xlsx", "export_format_code"),
        ("export_format_code", ForgedStr("json"), "export_format_code"),
        ("destination_kind", "email_attachment", "destination_kind"),
        ("destination_kind", ForgedStr("authenticated_one_time_download"), "destination_kind"),
    ],
)
def test_governance_codes_are_closed_and_non_polymorphic(
    field_name: str, value: object, message: str
) -> None:
    """Reviewed export policy constants must not be forged through string subclasses."""
    with pytest.raises(ValueError, match=message):
        packet(**{field_name: value})


def test_requester_and_reviewer_must_be_distinct() -> None:
    """One actor cannot request and independently approve the same HR data egress."""
    with pytest.raises(ValueError, match="reviewer_reference"):
        packet(reviewer_reference=REQUESTER)


@pytest.mark.parametrize(
    "fields",
    [
        [],
        (),
        tuple(f"field_{index:02d}" for index in range(65)),
        ("display_name", "business_email_address"),
        ("display_name", "display_name"),
        ("Display_Name",),
        (ForgedStr("display_name"),),
        ["display_name"],
    ],
)
def test_requested_fields_are_bounded_sorted_unique_exact_tuple(fields: object) -> None:
    """The review must enumerate a small deterministic field subset with no wildcard form."""
    with pytest.raises(ValueError, match="requested_fields"):
        packet(requested_fields=fields)


@pytest.mark.parametrize(
    "generated_at",
    [
        datetime(2026, 8, 22, 4, 0),
        ForgedDateTime(2026, 8, 22, 4, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 22, 4, 0, tzinfo=OffsetlessTimezone()),
        datetime(2026, 8, 22, 4, 0, tzinfo=ExplodingTimezone()),
        datetime(2099, 8, 22, 4, 0, tzinfo=timezone.utc),
    ],
)
def test_generated_at_requires_safe_timezone_aware_builtin_datetime(
    generated_at: datetime,
) -> None:
    """Recorded time must normalize hostile timezone behavior into governed failure."""
    with pytest.raises(ValueError, match="generated_at"):
        packet(generated_at=generated_at)


@pytest.mark.parametrize("version", [True, 0, 2_147_483_648, ForgedInt(1)])
def test_evidence_version_is_bounded_exact_integer(version: object) -> None:
    """Evidence versioning must not accept booleans, subclasses, zero, or overflow."""
    with pytest.raises(ValueError, match="evidence_version"):
        packet(evidence_version=version)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("contains_pii_values", True, "must not contain PII values"),
        ("human_review_required", False, "human review is mandatory"),
        ("scope_verification_state", "verified", "scope_verification_state"),
        ("scope_verification_state", ForgedStr("requires_authoritative_resolution"), "scope_verification_state"),
        ("export_state", "authorized", "export_state"),
        ("export_state", ForgedStr("not_authorized_to_export"), "export_state"),
        ("next_action", "download now", "next_action"),
        ("next_action", ForgedStr("download now"), "next_action"),
    ],
)
def test_direct_construction_cannot_weaken_export_controls(
    field_name: str, value: object, message: str
) -> None:
    """Direct construction must preserve value minimization and fail-closed review state."""
    with pytest.raises(ValueError, match=message):
        packet(**{field_name: value})


def test_packet_subclassing_is_rejected() -> None:
    """A caller cannot subclass the governed packet and override trust behavior."""
    with pytest.raises(TypeError, match="must not be subclassed"):
        type("ForgedPacket", (HrDataExportReviewPacket,), {})


def test_post_construction_tampering_is_revalidated_before_canonicalization() -> None:
    """Low-level mutation cannot serialize a state the constructor would reject."""
    result = packet()
    object.__setattr__(result, "export_state", "authorized")
    with pytest.raises(ValueError, match="export_state"):
        result.canonical_json()
    with pytest.raises(ValueError, match="export_state"):
        result.sha256_digest()


def test_dataclass_replace_preserves_governed_validation() -> None:
    """Common immutable-object replacement cannot silently widen requested fields."""
    with pytest.raises(ValueError, match="requested_fields"):
        replace(packet(), requested_fields=("*",))
