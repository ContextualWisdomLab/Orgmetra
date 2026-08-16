"""Persistence port consumed by the Orgmetra people API."""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable
from uuid import UUID

from orgmetra_postgres import (
    AuditEvent,
    CandidateSnapshot,
    CandidateWorkerLink,
    EmploymentSnapshot,
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
    ) -> PersonSnapshot:
        """Create or return a person record with repository-owned knowledge time."""

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

    def get_candidate(
        self, context: PurposeContext, candidate_profile_id: UUID
    ) -> CandidateSnapshot | None:
        """Return one current candidate profile visible to the caller."""

    def create_employment(
        self,
        context: PurposeContext,
        *,
        employment_record_id: UUID,
        person_record_id: UUID,
        employment_status_code: str,
        effective_from: date,
        effective_to: date | None = None,
    ) -> EmploymentSnapshot | None:
        """Create or return one employment relationship, or None if the person is hidden."""

    def get_employment(
        self, context: PurposeContext, employment_record_id: UUID
    ) -> EmploymentSnapshot | None:
        """Return one current employment record visible to the caller."""

    def link_candidate_to_worker(
        self,
        context: PurposeContext,
        *,
        candidate_profile_id: UUID,
        person_record_id: UUID,
        candidate_worker_link_id: UUID | None = None,
    ) -> CandidateWorkerLink:
        """Append or return an idempotent candidate-to-worker link."""

    def get_candidate_worker_link(
        self, context: PurposeContext, candidate_profile_id: UUID
    ) -> CandidateWorkerLink | None:
        """Return the hire link visible for one candidate."""

    def list_audit_events(
        self, context: PurposeContext, resource_record_id: UUID
    ) -> tuple[AuditEvent, ...]:
        """Return audit events visible for one resource."""
