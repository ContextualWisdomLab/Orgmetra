"""Immutable projections returned by the Orgmetra PostgreSQL adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PersonSnapshot:
    """Represent one tenant-scoped person record visible to the caller."""

    person_record_id: UUID
    display_name: str
    effective_from: date
    effective_to: date | None
    recorded_from: datetime


@dataclass(frozen=True, slots=True)
class CandidateSnapshot:
    """Represent one tenant-scoped candidate profile."""

    candidate_profile_id: UUID
    application_status_code: str
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class CandidateWorkerLink:
    """Represent the immutable identity bridge from candidate to worker."""

    candidate_worker_link_id: UUID
    candidate_profile_id: UUID
    person_record_id: UUID
    linked_at: datetime


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Represent non-content audit evidence for one accepted mutation."""

    audit_event_id: UUID
    action_code: str
    resource_type_code: str
    resource_record_id: UUID
    actor_reference: UUID
    purpose_code: str
    occurred_at: datetime
