"""Client-safe support-reference generation for Orgmetra HTTP responses."""

from __future__ import annotations

from secrets import token_urlsafe


def new_support_reference() -> str:
    """Return a cryptographically random, non-semantic support identifier."""

    return f"err_{token_urlsafe(24)}"
