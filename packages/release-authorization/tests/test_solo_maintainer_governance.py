"""Regression tests for live solo-maintainer release-governance evidence."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from orgmetra_release_authorization import ReleaseAuthorizationError
from orgmetra_release_authorization.authorization import _validate_control_snapshot

_CANDIDATE = "a" * 40
_VERIFIED_AT = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)


def _control_snapshot(**overrides: object) -> dict[str, object]:
    """Build exact live repository-policy evidence for one release candidate."""
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


def test_solo_maintainer_policy_can_authorize_without_manufactured_human_approval() -> None:
    """Accept the canonical one-maintainer policy when every technical gate is proven."""
    _validate_control_snapshot(_control_snapshot(), _CANDIDATE)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"required_approving_review_count": 1}, "required approving review count"),
        ({"require_last_push_approval": True}, "last-push approval requirement"),
        ({"synthetic_required_reviewers_absent": False}, "synthetic required reviewers"),
    ],
)
def test_release_policy_rejects_governance_that_cannot_be_satisfied_by_one_maintainer(
    overrides: dict[str, object], message: str
) -> None:
    """Fail closed when live policy reintroduces impossible or synthetic reviewer gates."""
    with pytest.raises(ReleaseAuthorizationError, match=message):
        _validate_control_snapshot(_control_snapshot(**overrides), _CANDIDATE)
