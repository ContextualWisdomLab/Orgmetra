"""Persistence port consumed by the Orgmetra people API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_postgres import (
    AuditEvent,
    CandidateSnapshot,
    CandidateWorkerLink,
    PersonSnapshot,
    PurposeContext,
)


@runtime_checkable
class PeopleRepository(Protocol):
    """Describe the persistence operations required by the first HTTP slice."""

    def create_person(
        self,
        context: PurposeContext,
        *,
        person_record_id: UUID,
        display_name: str,
        effective_from: date,
        effective_to: date | None = None,
        recorded_at: datetime | None = None,
    ) -> PersonSnapshot:
        """Create or return an idempotent person record."""

    def get_person(
        self, context: PurposeContext, person_record_id: UUID
    ) -> PersonSnapshot | None:
        """Return one current person record visible to the caller."""

    def create_candidate(
        self,
        context: PurposeContext,
        *,
        candidate_profile_id: UUID,
        application_status_code: str,
    ) -> CandidateSnapshot:
        """Create or return an idempotent candidate profile."""

    def link_candidate_to_worker(
        self,
        context: PurposeContext,
        *,
        candidate_profile_id: UUID,
        person_record_id: UUID,
        candidate_worker_link_id: UUID | None = None,
    ) -> CandidateWorkerLink:
        """Append or return an idempotent candidate-to-worker link."""

    def list_audit_events(
        self, context: PurposeContext, resource_record_id: UUID
    ) -> tuple[AuditEvent, ...]:
        """Return audit events visible for one resource."""
