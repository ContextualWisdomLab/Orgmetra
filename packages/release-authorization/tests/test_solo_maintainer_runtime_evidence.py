"""Adversarial runtime regressions for solo-maintainer control evidence."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmetra_release_authorization import ReleaseAuthorizationError
from orgmetra_release_authorization.authorization import _validate_control_snapshot

_CANDIDATE = "a" * 40
_VERIFIED_AT = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)


def _control_snapshot(**overrides: object) -> dict[str, object]:
    """Build one canonical solo-maintainer control snapshot."""
    snapshot: dict[str, object] = {
        "candidate_revision_sha": _CANDIDATE,
        "integrated_default_head_sha": _CANDIDATE,
        "ruleset_evidence_digest_sha256": "2" * 64,
        "required_gate_evidence_digest_sha256": "3" * 64,
        "qualifying_independent_approval_count": 0,
        "last_push_approved": False,
        "required_approving_review_count": 0,
        "require_last_push_approval": False,
        "synthetic_required_reviewers_absent": True,
        "review_threads_resolved": True,
        "all_required_gates_green": True,
        "routine_admin_bypass_disabled": True,
        "verified_at": _VERIFIED_AT,
    }
    snapshot.update(overrides)
    return snapshot


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"qualifying_independent_approval_count": True}, "qualifying independent approval count"),
        ({"qualifying_independent_approval_count": -1}, "qualifying independent approval count"),
        ({"last_push_approved": 1}, "last_push_approved"),
        ({"required_approving_review_count": True}, "required approving review count"),
    ],
)
def test_mutated_runtime_evidence_fails_closed(overrides: dict[str, object], message: str) -> None:
    """Reject malformed values even when a previously validated container is mutated."""
    with pytest.raises(ReleaseAuthorizationError, match=message):
        _validate_control_snapshot(_control_snapshot(**overrides), _CANDIDATE)
