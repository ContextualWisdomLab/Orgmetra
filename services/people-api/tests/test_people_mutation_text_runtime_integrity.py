"""Reject caller-controlled text subclasses at authoritative People write boundaries."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from orgmetra_people_api.hire import HireAcceptanceCommand
from orgmetra_people_api.mutations import EmploymentMutationCommand, PositionMutationCommand

TENANT = UUID("0198a412-8000-7000-8000-000000000101")
PERSON = UUID("0198a412-8000-7000-8000-000000000102")
CANDIDATE = UUID("0198a412-8000-7000-8000-000000000103")
SELECTION_DECISION = UUID("0198a412-8000-7000-8000-000000000104")
EMPLOYMENT = UUID("0198a412-8000-7000-8000-000000000105")
EMPLOYMENT_VERSION = UUID("0198a412-8000-7000-8000-000000000106")
ORGANIZATION = UUID("0198a412-8000-7000-8000-000000000107")
JOB = UUID("0198a412-8000-7000-8000-000000000108")
POSITION = UUID("0198a412-8000-7000-8000-000000000109")
POSITION_VERSION = UUID("0198a412-8000-7000-8000-00000000010a")
PERSON_NAME = UUID("0198a412-8000-7000-8000-00000000010b")
CONVERSION = UUID("0198a412-8000-7000-8000-00000000010c")
AUDIT = UUID("0198a412-8000-7000-8000-00000000010d")
OUTBOX = UUID("0198a412-8000-7000-8000-00000000010e")


class _ForgedClosedCode(str):
    """Present unsafe underlying text as the reviewed ``active`` status."""

    def __hash__(self) -> int:
        """Collide with the reviewed status during set lookup."""
        return hash("active")

    def __eq__(self, other: object) -> bool:
        """Claim equality with the reviewed status while retaining unsafe text."""
        return other == "active"

    def __ne__(self, other: object) -> bool:
        """Keep inequality consistent with the forged equality result."""
        return not self.__eq__(other)


class _ForgedConcurrencyCode(str):
    """Present unsafe underlying text as the reviewed ``exclusive`` code."""

    def __hash__(self) -> int:
        """Collide with the reviewed concurrency code during set lookup."""
        return hash("exclusive")

    def __eq__(self, other: object) -> bool:
        """Claim equality with the reviewed concurrency code."""
        return other == "exclusive"

    def __ne__(self, other: object) -> bool:
        """Keep inequality consistent with the forged equality result."""
        return not self.__eq__(other)


class _ForgedIdempotencyKey(str):
    """Hide an unsafe underlying key from length and character validation."""

    def __len__(self) -> int:
        """Pretend the key satisfies the governed length contract."""
        return 20

    def __iter__(self):
        """Yield only visible ASCII while retaining unsafe underlying text."""
        return iter("A" * 20)


class _ForgedDisplayName(str):
    """Hide control-character PII from the mutable Person-name validation path."""

    def encode(self, *args: object, **kwargs: object) -> bytes:
        """Pretend the underlying text encodes as a harmless display name."""
        del args, kwargs
        return b"Alice"

    def strip(self, *args: object, **kwargs: object) -> str:
        """Pretend the underlying text contains usable non-whitespace content."""
        del args, kwargs
        return "Alice"

    def __len__(self) -> int:
        """Pretend the underlying text satisfies the bounded PII length."""
        return 5

    def __iter__(self):
        """Hide the underlying control character from character validation."""
        return iter("Alice")


class _ForgedGovernanceText(str):
    """Present reviewed governance text with caller-defined rendering semantics."""

    def __str__(self) -> str:
        """Render a different value if canonical evidence later formats the field."""
        return "caller_defined_governance_text"


def _employment(**overrides: object) -> EmploymentMutationCommand:
    """Build one otherwise-valid high-impact employment mutation command."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "person_record_id": PERSON,
        "employment_record_id": EMPLOYMENT,
        "employment_record_version_id": EMPLOYMENT_VERSION,
        "audit_event_record_id": AUDIT,
        "outbox_delivery_record_id": OUTBOX,
        "employment_status_code": "active",
        "employment_concurrency_code": "exclusive",
        "effective_from": date(2026, 8, 22),
        "confirmation_reference": "human_confirmation:text-runtime-22",
        "evidence_version_code": "decision_evidence_set:v1",
        "idempotency_key": "people-text-runtime-key-22",
    }
    values.update(overrides)
    return EmploymentMutationCommand(**values)  # type: ignore[arg-type]


def _position(**overrides: object) -> PositionMutationCommand:
    """Build one otherwise-valid position mutation command."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "organization_unit_id": ORGANIZATION,
        "job_profile_id": JOB,
        "position_record_id": POSITION,
        "position_record_version_id": POSITION_VERSION,
        "audit_event_record_id": AUDIT,
        "outbox_delivery_record_id": OUTBOX,
        "position_status_code": "active",
        "effective_from": date(2026, 8, 22),
        "confirmation_reference": "human_confirmation:text-runtime-22",
        "evidence_version_code": "position_evidence:v1",
        "idempotency_key": "position-text-runtime-key-22",
    }
    values.update(overrides)
    return PositionMutationCommand(**values)  # type: ignore[arg-type]


def _hire(**overrides: object) -> HireAcceptanceCommand:
    """Build one otherwise-valid confirmed-hire command."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "candidate_profile_id": CANDIDATE,
        "selection_decision_id": SELECTION_DECISION,
        "person_record_id": PERSON,
        "person_name_record_id": PERSON_NAME,
        "employment_record_id": EMPLOYMENT,
        "employment_record_version_id": EMPLOYMENT_VERSION,
        "candidate_worker_conversion_record_id": CONVERSION,
        "audit_event_record_id": AUDIT,
        "outbox_delivery_record_id": OUTBOX,
        "effective_from": date(2026, 8, 22),
        "display_name": "Alice Example",
        "idempotency_key": "hire-text-runtime-key-22",
        "employment_status_code": "active",
    }
    values.update(overrides)
    return HireAcceptanceCommand(**values)  # type: ignore[arg-type]


def test_rejects_status_string_subclass_that_forges_allow_list_membership() -> None:
    """Canonical employment status text must be the exact value that was reviewed."""
    with pytest.raises(ValueError, match="employment_status_code"):
        _employment(employment_status_code=_ForgedClosedCode("model_decided"))
    with pytest.raises(ValueError, match="position_status_code"):
        _position(position_status_code=_ForgedClosedCode("model_decided"))
    with pytest.raises(ValueError, match="employment_status_code"):
        _hire(employment_status_code=_ForgedClosedCode("model_decided"))


def test_rejects_concurrency_string_subclass_that_forges_allow_list_membership() -> None:
    """Concurrency evidence cannot substitute caller-defined equality semantics."""
    with pytest.raises(ValueError, match="employment_concurrency_code"):
        _employment(employment_concurrency_code=_ForgedConcurrencyCode("shadow_parallel"))


def test_rejects_idempotency_string_subclass_that_forges_scalar_validation() -> None:
    """Idempotency identity must bind the exact validated visible-ASCII text."""
    with pytest.raises(ValueError, match="idempotency_key"):
        _employment(idempotency_key=_ForgedIdempotencyKey("\n"))


def test_rejects_display_name_string_subclass_before_person_pii_persistence() -> None:
    """Necessary Person-name PII cannot hide control text behind overridden methods."""
    with pytest.raises(ValueError, match="display_name"):
        _hire(display_name=_ForgedDisplayName("\n"))


def test_rejects_governance_text_subclasses_before_digest_or_persistence() -> None:
    """Confirmation and evidence text must retain the exact reviewed runtime value."""
    with pytest.raises(ValueError, match="confirmation_reference"):
        _employment(
            confirmation_reference=_ForgedGovernanceText("human_confirmation:text-runtime-22")
        )
    with pytest.raises(ValueError, match="evidence_version_code"):
        _position(evidence_version_code=_ForgedGovernanceText("position_evidence:v1"))
