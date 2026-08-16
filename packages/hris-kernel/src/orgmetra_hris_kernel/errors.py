"""Operator-readable kernel errors with a required next action."""

from __future__ import annotations


class KernelError(Exception):
    """Base employment-truth error.

    Attributes:
        next_action: The concrete HR or operator step that unblocks the save.
    """

    def __init__(self, message: str, *, next_action: str) -> None:
        """Store the failure and the action that corrects it."""
        super().__init__(message)
        self.next_action = next_action


class IntervalError(KernelError):
    """A half-open interval is empty, reversed, or missing a timezone."""


class IdentityScopeError(KernelError):
    """A historical query named a field that is not an identity key."""


class SingleValuedFactError(KernelError):
    """One identity has two visible versions at the same coordinate."""


class AssignmentPortfolioError(KernelError):
    """Assignment allocations for one employment exceed 1.0000 or are invalid."""


class EmploymentCoverageError(KernelError):
    """An assignment is not covered by the named employment or person."""


class CorrectionError(KernelError):
    """A recorded interval cannot be closed in the requested way."""
