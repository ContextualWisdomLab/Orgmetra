"""Append-only candidate-to-worker linkage for identity continuity after hire."""

from dataclasses import dataclass
from uuid import UUID

from .errors import CandidateWorkerRelinkError


@dataclass(frozen=True, slots=True)
class CandidateWorkerLink:
    """Link one candidate profile to the durable person created after hire."""

    candidate_worker_link_id: UUID
    candidate_profile_id: UUID
    person_record_id: UUID


class CandidateWorkerRegistry:
    """Maintain append-only candidate links with idempotent registration."""

    def __init__(self) -> None:
        """Create an empty in-memory registry for domain validation and tests."""

        self._links: dict[UUID, CandidateWorkerLink] = {}

    def register(self, link: CandidateWorkerLink) -> CandidateWorkerLink:
        """Register ``link`` or return the existing equivalent link.

        A candidate can never be relinked to another person. The durable store
        will enforce the same invariant transactionally.
        """

        existing = self._links.get(link.candidate_profile_id)
        if existing is None:
            self._links[link.candidate_profile_id] = link
            return link
        if existing.person_record_id != link.person_record_id:
            raise CandidateWorkerRelinkError(
                "candidate is already linked to a different person"
            )
        return existing

    def get(self, candidate_profile_id: UUID) -> CandidateWorkerLink | None:
        """Return the candidate's durable worker link when one exists."""

        return self._links.get(candidate_profile_id)
