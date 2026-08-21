"""Build and validate fail-closed Naruon calendar intents for HR workflows.

The adapter is deliberately transport-free. Orgmetra prepares a purpose-bound,
human-confirmed intent using Naruon's published API contract, while the host owns
authentication and HTTP transport. The current contract requests intent creation
only; it never asks Naruon to mutate a customer calendar provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

NARUON_CONTRACT_SHA = "ddd05c5aaf3e170aa2bdc4412647b43b95d5a6b9"
NARUON_CALENDAR_WRITEBACK_INTENT_PATH = "/api/calendar/writeback-intent"

_ACTION_SUMMARIES = MappingProxyType(
    {
        "onboarding_task": "Complete assigned onboarding task",
        "performance_review": "Complete scheduled performance review",
        "policy_acknowledgement": "Review and acknowledge assigned policy",
        "manager_check_in": "Prepare for manager check-in",
    }
)
_RESOURCE_NAMESPACES = frozenset(
    {"person_record", "employment_record", "assignment_record", "position_record"}
)
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_EXPECTED_RESPONSE_KEYS = frozenset(
    {
        "workspace_id",
        "target_source_id",
        "protocol",
        "writeback_mode",
        "requires_if_match",
        "if_match",
        "provenance",
        "audit_event",
        "provider_write_executed",
        "status",
        "runner_request_id",
        "provider_status",
        "error_code",
        "retry_item_uid",
    }
)
_EXPECTED_PROVENANCE_KEYS = frozenset(
    {"created_by", "source_provider", "source_protocol"}
)


class ContractViolation(ValueError):
    """Raised when an input or Naruon response violates the reviewed contract."""


@dataclass(frozen=True, slots=True)
class CalendarIntentContext:
    """Purpose-bound Orgmetra evidence needed before creating a calendar intent."""

    tenant_record_id: str
    resource_reference: str
    actor_reference: str
    purpose_code: str
    reason_code: str
    evidence_version: str
    action_kind: str
    human_confirmed: bool
    target_source_id: str | None = None


@dataclass(frozen=True, slots=True)
class CalendarIntentPlan:
    """Transport-neutral request and correlation evidence for a Naruon intent."""

    method: str
    path: str
    contract_sha: str
    body: Mapping[str, object]
    audit_context: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ValidatedCalendarIntent:
    """Normalized Naruon intent response after fail-closed contract validation."""

    workspace_id: str
    target_source_id: str
    source_provider: str
    provider_write_executed: bool
    audit_context: Mapping[str, object]


def _require_uuid(value: object, label: str) -> str:
    """Return one canonical UUID string or reject malformed/non-canonical input."""
    if type(value) is not str:
        raise ContractViolation(f"{label} must be a canonical UUID")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise ContractViolation(f"{label} must be a canonical UUID") from error
    canonical = str(parsed)
    if value != canonical:
        raise ContractViolation(f"{label} must be a canonical UUID")
    return canonical


def _require_token(value: object, label: str) -> str:
    """Return a bounded printable token suitable for contract metadata."""
    if type(value) is not str or not _TOKEN_PATTERN.fullmatch(value):
        raise ContractViolation(f"{label} must be a bounded opaque token")
    return value


def _require_code(value: object, label: str) -> str:
    """Return a bounded lowercase machine code used for purpose/reason metadata."""
    if type(value) is not str or not _CODE_PATTERN.fullmatch(value):
        raise ContractViolation(f"{label} must be a bounded lowercase code")
    return value


def _require_resource_reference(value: object) -> str:
    """Validate an Orgmetra opaque record reference without dereferencing PII."""
    if type(value) is not str or value.count(":") != 1:
        raise ContractViolation("resource_reference must be a namespaced UUID reference")
    namespace, identifier = value.split(":", 1)
    if namespace not in _RESOURCE_NAMESPACES:
        raise ContractViolation("resource_reference uses an unsupported record namespace")
    return f"{namespace}:{_require_uuid(identifier, 'resource_reference identifier')}"


def _validate_context(context: CalendarIntentContext) -> tuple[str, str | None]:
    """Validate all local authorization/audit evidence before building an intent."""
    if type(context) is not CalendarIntentContext:
        raise ContractViolation("calendar intent context must be the governed context type")
    _require_uuid(context.tenant_record_id, "tenant_record_id")
    _require_resource_reference(context.resource_reference)
    _require_token(context.actor_reference, "actor_reference")
    _require_code(context.purpose_code, "purpose_code")
    _require_code(context.reason_code, "reason_code")
    _require_token(context.evidence_version, "evidence_version")
    action_kind = _require_code(context.action_kind, "action kind")
    if context.human_confirmed is not True:
        raise ContractViolation("calendar intent requires explicit human confirmation")
    summary = _ACTION_SUMMARIES.get(action_kind)
    if summary is None:
        raise ContractViolation("calendar intent action kind is not supported")
    target_source_id = (
        None
        if context.target_source_id is None
        else _require_token(context.target_source_id, "target_source_id")
    )
    return summary, target_source_id


def build_calendar_intent(context: CalendarIntentContext) -> CalendarIntentPlan:
    """Build a confirmed, PII-minimized Naruon calendar intent without provider writes."""
    summary, target_source_id = _validate_context(context)
    body = MappingProxyType(
        {
            "action": "create",
            "summary": summary,
            "target_source_id": target_source_id,
            "execute_provider": False,
        }
    )
    audit_context = MappingProxyType(
        {
            "tenant_record_id": context.tenant_record_id,
            "resource_reference": context.resource_reference,
            "actor_reference": context.actor_reference,
            "purpose_code": context.purpose_code,
            "reason_code": context.reason_code,
            "evidence_version": context.evidence_version,
            "action_kind": context.action_kind,
            "human_confirmed": context.human_confirmed,
            "naruon_contract_sha": NARUON_CONTRACT_SHA,
        }
    )
    return CalendarIntentPlan(
        method="POST",
        path=NARUON_CALENDAR_WRITEBACK_INTENT_PATH,
        contract_sha=NARUON_CONTRACT_SHA,
        body=body,
        audit_context=audit_context,
    )


def _require_exact_keys(
    mapping: Mapping[str, object], expected: frozenset[str], label: str
) -> None:
    """Reject missing or newly introduced fields so contract drift is explicit."""
    observed = frozenset(mapping)
    if observed != expected:
        raise ContractViolation(f"{label} keys do not match the reviewed Naruon contract")


def _require_response_token(response: Mapping[str, object], key: str) -> str:
    """Read one required bounded response token."""
    return _require_token(response.get(key), key)


def validate_calendar_intent_response(
    plan: CalendarIntentPlan, response: Mapping[str, object]
) -> ValidatedCalendarIntent:
    """Validate Naruon's intent-only response and reject provider execution or drift."""
    if not isinstance(response, Mapping):
        raise ContractViolation("calendar intent response must be a mapping")
    _require_exact_keys(response, _EXPECTED_RESPONSE_KEYS, "response")

    workspace_id = _require_response_token(response, "workspace_id")
    target_source_id = _require_response_token(response, "target_source_id")
    requested_target = plan.body.get("target_source_id")
    if requested_target is not None and target_source_id != requested_target:
        raise ContractViolation(
            "calendar intent target source differs from the requested target source"
        )
    if response.get("protocol") != "caldav":
        raise ContractViolation("calendar intent protocol must remain caldav")
    if response.get("writeback_mode") != "customer_owned":
        raise ContractViolation("calendar intent writeback mode must remain customer_owned")
    if response.get("requires_if_match") is not False or response.get("if_match") is not None:
        raise ContractViolation("create intent must not require or carry If-Match")
    if response.get("audit_event") != "calendar.writeback_intent.created":
        raise ContractViolation(
            "calendar intent audit event is not the reviewed intent-only event"
        )
    if response.get("provider_write_executed") is not False:
        raise ContractViolation("calendar intent unexpectedly reports provider execution")
    if response.get("status") != "intent_ready":
        raise ContractViolation("calendar intent status is not intent_ready")

    execution_fields = (
        "runner_request_id",
        "provider_status",
        "error_code",
        "retry_item_uid",
    )
    if any(response.get(field) is not None for field in execution_fields):
        raise ContractViolation("intent-only response must not contain execution metadata")

    provenance = response.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ContractViolation("calendar intent provenance must be a mapping")
    _require_exact_keys(provenance, _EXPECTED_PROVENANCE_KEYS, "provenance")
    created_by = _require_token(provenance.get("created_by"), "created_by")
    source_provider = _require_token(
        provenance.get("source_provider"), "source_provider"
    )
    if provenance.get("source_protocol") != "caldav":
        raise ContractViolation("calendar intent provenance protocol must remain caldav")
    # Validate Naruon's authoritative subject without collapsing it into Keyverse identity.
    del created_by

    return ValidatedCalendarIntent(
        workspace_id=workspace_id,
        target_source_id=target_source_id,
        source_provider=source_provider,
        provider_write_executed=False,
        audit_context=plan.audit_context,
    )
