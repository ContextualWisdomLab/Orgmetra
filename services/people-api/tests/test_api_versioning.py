"""Regression contracts for versioning newly required employing-organization facts."""

from __future__ import annotations

from uuid import UUID

import pytest

from orgmetra_people_api.hire_http import (
    _command_from_payload,
    _looks_like_hire_route,
    _parse_hire_route,
)
from orgmetra_people_api.mutation_http import _command_for_route, _mutation_route

TENANT = UUID("0198a412-8200-7000-8000-000000000001")
PERSON = UUID("0198a412-8200-7000-8000-000000000010")
ORGANIZATION = UUID("0198a412-8200-7000-8000-000000000020")
IDEMPOTENCY_KEY = "api-versioning-key-17"


def _employment_payload(*, status: str, include_employer: bool) -> dict[str, object]:
    """Build one bounded employment payload for the V1/V2 parser contract."""
    payload: dict[str, object] = {
        "person_record_id": str(PERSON),
        "employment_status_code": status,
        "employment_concurrency_code": "exclusive",
        "effective_from": "2026-08-18",
        "decision_reason": "Record the governed employment fact.",
        "confirmation_reference": "human_confirmation:api-versioning",
        "evidence_references": [
            {"evidence_reference": "decision:17", "evidence_version_code": "v1"}
        ],
    }
    if include_employer:
        payload["employing_organization_unit_id"] = str(ORGANIZATION)
    return payload


def _hire_payload(*, status: str, include_employer: bool) -> dict[str, object]:
    """Build one bounded confirmed-hire payload for the V1/V2 parser contract."""
    payload: dict[str, object] = {
        "candidate_profile_id": str(UUID("0198a412-8200-7000-8000-000000000030")),
        "selection_decision_id": str(UUID("0198a412-8200-7000-8000-000000000031")),
        "person_record_id": str(PERSON),
        "person_name_record_id": str(UUID("0198a412-8200-7000-8000-000000000032")),
        "employment_record_id": str(UUID("0198a412-8200-7000-8000-000000000033")),
        "employment_record_version_id": str(UUID("0198a412-8200-7000-8000-000000000034")),
        "candidate_worker_conversion_record_id": str(UUID("0198a412-8200-7000-8000-000000000035")),
        "audit_event_record_id": str(UUID("0198a412-8200-7000-8000-000000000036")),
        "outbox_delivery_record_id": str(UUID("0198a412-8200-7000-8000-000000000037")),
        "effective_from": "2026-08-18",
        "display_name": "Anonymous Worker",
        "employment_status_code": status,
    }
    if include_employer:
        payload["employing_organization_unit_id"] = str(ORGANIZATION)
        payload["employment_employing_organization_record_id"] = str(
            UUID("0198a412-8200-7000-8000-000000000038")
        )
    return payload


def test_employment_v1_preserves_old_payload_and_v2_requires_employer() -> None:
    """Keep terminated V1 parsing while requiring employer facts in V2 active writes."""
    v1_command = _command_for_route(
        "employment-records",
        TENANT,
        _employment_payload(status="terminated", include_employer=False),
        lambda: UUID("0198a412-8200-7000-8000-000000000040"),
        IDEMPOTENCY_KEY,
    )
    assert v1_command.employing_organization_unit_id is None

    v2_command = _command_for_route(
        "employment-records-v2",
        TENANT,
        _employment_payload(status="active", include_employer=True),
        lambda: UUID("0198a412-8200-7000-8000-000000000041"),
        IDEMPOTENCY_KEY,
    )
    assert v2_command.employing_organization_unit_id == ORGANIZATION


def test_versioned_mutation_routes_keep_v1_siblings_unchanged() -> None:
    """Expose only Employment under V2 while retaining the existing V1 siblings."""
    assert _mutation_route("/v1/employment-records") == "employment-records"
    assert _mutation_route("/v2/employment-records") == "employment-records-v2"
    assert _mutation_route("/v2/position-records") is None
    assert _mutation_route("/v2/assignment-records") is None


def test_hire_v1_preserves_old_payload_and_v2_requires_employer() -> None:
    """Keep old terminated hire parsing while requiring employer facts in V2."""
    path = f"/v1/tenants/{TENANT}/candidate-worker-conversions"
    v1_tenant, v1_purpose, v1_version = _parse_hire_route(path, b"purpose=candidate_hire")
    assert (v1_tenant, v1_purpose, v1_version) == (TENANT, "candidate_hire", "v1")
    v1_command = _command_from_payload(
        TENANT,
        _hire_payload(status="terminated", include_employer=False),
        IDEMPOTENCY_KEY,
        api_version="v1",
    )
    assert v1_command.employing_organization_unit_id is None

    v2_path = f"/v2/tenants/{TENANT}/candidate-worker-conversions"
    assert _looks_like_hire_route(v2_path)
    v2_command = _command_from_payload(
        TENANT,
        _hire_payload(status="active", include_employer=True),
        IDEMPOTENCY_KEY,
        api_version="v2",
    )
    assert v2_command.employing_organization_unit_id == ORGANIZATION


def test_active_v1_payload_without_employer_is_rejected_with_migration_guidance() -> None:
    """Do not let the new database invariant become an opaque V1 persistence failure."""
    with pytest.raises(ValueError, match="v2"):
        _command_for_route(
            "employment-records",
            TENANT,
            _employment_payload(status="active", include_employer=False),
            lambda: UUID("0198a412-8200-7000-8000-000000000042"),
            IDEMPOTENCY_KEY,
        )
