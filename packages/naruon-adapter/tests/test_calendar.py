"""Regression coverage for the governed Naruon calendar-intent boundary."""

from __future__ import annotations

from dataclasses import replace

import pytest

from orgmetra_naruon_adapter import (
    CalendarIntentContext,
    ContractViolation,
    NARUON_CALENDAR_WRITEBACK_INTENT_PATH,
    NARUON_CONTRACT_SHA,
    build_calendar_intent,
    validate_calendar_intent_response,
)

TENANT_ID = "11111111-1111-4111-8111-111111111111"
PERSON_ID = "22222222-2222-4222-8222-222222222222"


def context(**changes: object) -> CalendarIntentContext:
    """Build one valid calendar-intent context with optional test overrides."""
    base = CalendarIntentContext(
        tenant_record_id=TENANT_ID,
        resource_reference=f"person_record:{PERSON_ID}",
        actor_reference="keyverse_subject:hr-manager-7",
        purpose_code="workforce_scheduling",
        reason_code="manager_confirmed_reminder",
        evidence_version="policy-v3",
        action_kind="performance_review",
        human_confirmed=True,
        target_source_id="caldav-source-7",
    )
    return replace(base, **changes)


def valid_response() -> dict[str, object]:
    """Return one reviewed intent-only Naruon response fixture."""
    return {
        "workspace_id": "workspace-9",
        "target_source_id": "caldav-source-7",
        "protocol": "caldav",
        "writeback_mode": "customer_owned",
        "requires_if_match": False,
        "if_match": None,
        "provenance": {
            "created_by": "naruon-user-4",
            "source_provider": "nextcloud",
            "source_protocol": "caldav",
        },
        "audit_event": "calendar.writeback_intent.created",
        "provider_write_executed": False,
        "status": "intent_ready",
        "runner_request_id": None,
        "provider_status": None,
        "error_code": None,
        "retry_item_uid": None,
    }


def test_builds_confirmed_intent_without_pii_or_provider_execution() -> None:
    """Build only a confirmed PII-minimized intent with provider execution disabled."""
    plan = build_calendar_intent(context())

    assert plan.method == "POST"
    assert plan.path == NARUON_CALENDAR_WRITEBACK_INTENT_PATH
    assert plan.contract_sha == NARUON_CONTRACT_SHA
    assert plan.body == {
        "action": "create",
        "summary": "Complete scheduled performance review",
        "target_source_id": "caldav-source-7",
        "execute_provider": False,
    }
    serialized = repr(plan.body)
    assert TENANT_ID not in serialized
    assert PERSON_ID not in serialized
    assert "hr-manager-7" not in serialized
    assert plan.audit_context["resource_reference"] == f"person_record:{PERSON_ID}"
    assert plan.audit_context["human_confirmed"] is True


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("tenant_record_id", "not-a-uuid"),
        ("resource_reference", "person_record:not-a-uuid"),
        ("resource_reference", f"unknown_record:{PERSON_ID}"),
        ("resource_reference", f"person_record:{PERSON_ID}\nleak"),
        ("actor_reference", "bad\nactor"),
        ("purpose_code", "*"),
        ("reason_code", ""),
        ("evidence_version", "x" * 129),
        ("target_source_id", "bad\x00source"),
    ],
)
def test_rejects_malformed_or_unsafe_context(field: str, bad_value: object) -> None:
    """Reject malformed identifiers, metadata codes, and transport tokens."""
    with pytest.raises(ContractViolation):
        build_calendar_intent(context(**{field: bad_value}))


def test_requires_explicit_human_confirmation() -> None:
    """Reject a calendar intent when accountable human confirmation is false."""
    with pytest.raises(ContractViolation, match="human confirmation"):
        build_calendar_intent(context(human_confirmed=False))


@pytest.mark.parametrize("truthy_non_boolean", [1, "false", "confirmed"])
def test_rejects_truthy_non_boolean_human_confirmation(truthy_non_boolean: object) -> None:
    """Only the bool singleton True can satisfy high-impact confirmation evidence."""
    with pytest.raises(ContractViolation, match="human confirmation"):
        build_calendar_intent(context(human_confirmed=truthy_non_boolean))


def test_rejects_unknown_action_kind() -> None:
    """Reject an action kind that has no reviewed PII-minimized summary contract."""
    with pytest.raises(ContractViolation, match="action kind"):
        build_calendar_intent(context(action_kind="unknown"))


def test_optional_target_source_can_be_omitted() -> None:
    """Allow Naruon to select the target when the caller does not request one."""
    plan = build_calendar_intent(context(target_source_id=None, action_kind="onboarding_task"))
    assert plan.body == {
        "action": "create",
        "summary": "Complete assigned onboarding task",
        "target_source_id": None,
        "execute_provider": False,
    }


def test_validates_intent_only_response_and_retains_correlation_context() -> None:
    """Normalize a reviewed response while preserving Orgmetra audit correlation."""
    plan = build_calendar_intent(context())
    result = validate_calendar_intent_response(plan, valid_response())

    assert result.workspace_id == "workspace-9"
    assert result.target_source_id == "caldav-source-7"
    assert result.source_provider == "nextcloud"
    assert result.provider_write_executed is False
    assert result.audit_context == plan.audit_context


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"unexpected": "field"}, "response keys"),
        ({"workspace_id": ""}, "workspace_id"),
        ({"target_source_id": "other-source"}, "target source"),
        ({"protocol": "webdav"}, "protocol"),
        ({"writeback_mode": "server_owned"}, "writeback mode"),
        ({"requires_if_match": True}, "If-Match"),
        ({"if_match": '\"etag\"'}, "If-Match"),
        ({"audit_event": "calendar.writeback.executed"}, "audit event"),
        ({"provider_write_executed": True}, "provider execution"),
        ({"status": "executed"}, "intent status"),
        ({"runner_request_id": "req-1"}, "execution metadata"),
        ({"provider_status": 201}, "execution metadata"),
        ({"error_code": "ERR"}, "execution metadata"),
        ({"retry_item_uid": "retry-1"}, "execution metadata"),
        ({"provenance": "not-a-mapping"}, "provenance"),
        ({"provenance": {"created_by": "u", "source_provider": "p"}}, "provenance keys"),
        ({"provenance": {"created_by": "u", "source_provider": "p", "source_protocol": "webdav"}}, "provenance protocol"),
        ({"provenance": {"created_by": "", "source_provider": "p", "source_protocol": "caldav"}}, "created_by"),
    ],
)
def test_response_validation_fails_closed_on_contract_drift(
    mutation: dict[str, object], message: str
) -> None:
    """Fail closed for any unreviewed Naruon response shape or semantic drift."""
    plan = build_calendar_intent(context())
    response = valid_response()
    response.update(mutation)
    with pytest.raises(ContractViolation, match=message):
        validate_calendar_intent_response(plan, response)


def test_response_can_return_auto_selected_target_when_request_omits_one() -> None:
    """Accept a reviewed target chosen by Naruon when none was requested."""
    plan = build_calendar_intent(context(target_source_id=None))
    result = validate_calendar_intent_response(plan, valid_response())
    assert result.target_source_id == "caldav-source-7"


def test_rejects_non_string_and_noncanonical_uuid_inputs() -> None:
    """Reject non-string and noncanonical tenant UUID representations."""
    with pytest.raises(ContractViolation, match="tenant_record_id"):
        build_calendar_intent(context(tenant_record_id=123))
    with pytest.raises(ContractViolation, match="tenant_record_id"):
        build_calendar_intent(context(tenant_record_id="AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"))


def test_rejects_non_string_and_unnamespaced_resource_references() -> None:
    """Reject resource references that are non-string or lack a reviewed namespace."""
    with pytest.raises(ContractViolation, match="resource_reference"):
        build_calendar_intent(context(resource_reference=None))
    with pytest.raises(ContractViolation, match="resource_reference"):
        build_calendar_intent(context(resource_reference=PERSON_ID))


def test_rejects_non_string_code_and_token_values() -> None:
    """Reject typed values that cannot satisfy code or opaque-token contracts."""
    with pytest.raises(ContractViolation, match="purpose_code"):
        build_calendar_intent(context(purpose_code=7))
    with pytest.raises(ContractViolation, match="actor_reference"):
        build_calendar_intent(context(actor_reference=7))


def test_rejects_non_mapping_response() -> None:
    """Reject a Naruon response that is not a mapping before field validation."""
    plan = build_calendar_intent(context())
    with pytest.raises(ContractViolation, match="response must be a mapping"):
        validate_calendar_intent_response(plan, [])  # type: ignore[arg-type]
