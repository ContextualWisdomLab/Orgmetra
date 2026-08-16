"""Strict HTTP request and response schemas for the Orgmetra people API."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApiModel(BaseModel):
    """Apply fail-closed schema behavior to every public API model."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class HealthResponse(ApiModel):
    """Describe process liveness without exposing dependency details."""

    status: str = Field(pattern=r"^alive$")


class PersonCreateRequest(ApiModel):
    """Request creation of one effective-dated person record."""

    person_record_id: UUID
    display_name: str = Field(min_length=1, max_length=300)
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_effective_period(self) -> PersonCreateRequest:
        """Require a positive half-open effective-time interval."""

        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be later than effective_from")
        return self


class PersonResponse(ApiModel):
    """Return one current person projection visible to the caller."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )

    person_record_id: UUID
    display_name: str
    effective_from: date
    effective_to: date | None
    recorded_from: datetime


class CandidateCreateRequest(ApiModel):
    """Request creation of one candidate profile."""

    candidate_profile_id: UUID
    application_status_code: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9_]+$",
    )


class CandidateResponse(ApiModel):
    """Return one candidate profile visible to the caller."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )

    candidate_profile_id: UUID
    application_status_code: str
    recorded_at: datetime


class CandidateWorkerLinkCreateRequest(ApiModel):
    """Request one immutable candidate-to-worker identity link."""

    person_record_id: UUID
    candidate_worker_link_id: UUID | None = None


class CandidateWorkerLinkResponse(ApiModel):
    """Return one immutable candidate-to-worker identity link."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )

    candidate_worker_link_id: UUID
    candidate_profile_id: UUID
    person_record_id: UUID
    linked_at: datetime


class AuditEventResponse(ApiModel):
    """Return reference-only audit evidence without HR content."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )

    audit_event_id: UUID
    action_code: str
    resource_type_code: str
    resource_record_id: UUID
    actor_reference: UUID
    purpose_code: str
    occurred_at: datetime


class AuditEventListResponse(ApiModel):
    """Return a stable collection envelope for audit evidence."""

    audit_events: tuple[AuditEventResponse, ...]
