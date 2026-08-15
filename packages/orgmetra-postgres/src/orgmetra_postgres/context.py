"""Purpose-bound authorization context for Orgmetra persistence operations."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PurposeContext:
    """Describe the authenticated purpose attached to one repository operation.

    Authentication and policy evaluation happen in the host service. The
    persistence adapter receives only the already-authorized, immutable context
    needed to bind a transaction to one tenant and record defensible audit
    evidence.
    """

    tenant_reference: UUID
    actor_reference: UUID
    purpose_code: str
    correlation_reference: UUID
    decision_reference: UUID | None = None
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        """Reject empty or unbounded text before a database connection opens."""

        normalized_purpose = self.purpose_code.strip()
        if not normalized_purpose:
            raise ValueError("purpose_code must contain a non-whitespace value")
        if len(normalized_purpose) > 128:
            raise ValueError("purpose_code must not exceed 128 characters")
        object.__setattr__(self, "purpose_code", normalized_purpose)

        if self.evidence_reference is not None:
            normalized_evidence = self.evidence_reference.strip()
            if not normalized_evidence:
                raise ValueError(
                    "evidence_reference must be omitted or contain a value"
                )
            if len(normalized_evidence) > 512:
                raise ValueError(
                    "evidence_reference must not exceed 512 characters"
                )
            object.__setattr__(self, "evidence_reference", normalized_evidence)
