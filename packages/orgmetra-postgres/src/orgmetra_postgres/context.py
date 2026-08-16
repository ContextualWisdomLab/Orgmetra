"""Purpose-bound authorization context for Orgmetra persistence operations."""

from __future__ import annotations

from dataclasses import dataclass
from string import ascii_lowercase, digits
from uuid import UUID

_ALLOWED_CODE_CHARACTERS = frozenset(ascii_lowercase + digits + "_")


def _normalize_purpose_code(value: str) -> str:
    """Return one bounded lower-case ASCII purpose code or fail closed."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("purpose_code must contain a non-whitespace value")
    if len(normalized) > 64:
        raise ValueError("purpose_code must not exceed 64 characters")
    if not all(character in _ALLOWED_CODE_CHARACTERS for character in normalized):
        raise ValueError(
            "purpose_code must use lower-case ASCII letters, digits, and underscores"
        )
    return normalized


def _normalize_evidence_reference(value: str) -> str:
    """Return one bounded printable-ASCII evidence reference or fail closed."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("evidence_reference must be omitted or contain a value")
    if len(normalized) > 512:
        raise ValueError("evidence_reference must not exceed 512 characters")
    if not normalized.isascii() or any(
        ord(character) < 0x21 or ord(character) > 0x7E for character in normalized
    ):
        raise ValueError(
            "evidence_reference must use printable ASCII characters without whitespace"
        )
    return normalized


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
        """Reject unsafe metadata before a database connection opens."""

        object.__setattr__(
            self,
            "purpose_code",
            _normalize_purpose_code(self.purpose_code),
        )
        if self.evidence_reference is not None:
            object.__setattr__(
                self,
                "evidence_reference",
                _normalize_evidence_reference(self.evidence_reference),
            )
