"""Focused execution-layer chronology regression for release publication."""

from __future__ import annotations

import json

import pytest

from orgmetra_release_publication import ReleasePublicationError
from orgmetra_release_publication import execution as execution_module


class _CanonicalReceipt:
    """Expose one caller-controlled parent authorization document."""

    def canonical_json(self) -> str:
        """Return a timestamp that is valid ISO text but not canonical Z-form UTC."""
        return json.dumps({"audit_recorded_at": "2026-08-26T08:00:02+00:00"})


def test_execution_guard_rejects_non_z_authorization_audit_time() -> None:
    """Exercise the exact-text/non-Z branch before any publication side effect."""
    with pytest.raises(ReleasePublicationError, match="audit time is invalid"):
        execution_module._authorization_audit_time(_CanonicalReceipt())  # type: ignore[arg-type]
