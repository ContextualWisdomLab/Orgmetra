"""Freshness guard around the one-shot release-publication side effect."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
from typing import Callable

from orgmetra_release_authorization import ReleaseAuthorizationReceipt

from .publication import (
    ReleasePublicationError,
    ReleasePublicationIndeterminateError,
    ReleasePublicationPort,
    ReleasePublicationReceipt,
    publish_authorized_release as _publish_authorized_release,
)

_MAX_AUTHORIZATION_AGE = timedelta(seconds=60)


def _authorization_audit_time(receipt: ReleaseAuthorizationReceipt) -> datetime:
    """Read the sealed parent authorization audit time before any publication side effect."""
    try:
        document = json.loads(receipt.canonical_json())
        text = document["audit_recorded_at"]
        if type(text) is not str or not text.endswith("Z"):
            raise ValueError("noncanonical authorization audit time")
        audited_at = datetime.fromisoformat(text[:-1] + "+00:00")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ReleasePublicationError("release authorization audit time is invalid") from exc
    return audited_at


def publish_authorized_release(
    *,
    authorization_receipt: object,
    publication_reference: object,
    publisher: ReleasePublicationPort,
    clock: Callable[[], object],
) -> ReleasePublicationReceipt:
    """Publish once and refuse to bless any release created after authorization expiry."""
    if type(authorization_receipt) is not ReleaseAuthorizationReceipt:
        return _publish_authorized_release(
            authorization_receipt=authorization_receipt,
            publication_reference=publication_reference,
            publisher=publisher,
            clock=clock,
        )
    audit_recorded_at = _authorization_audit_time(authorization_receipt)
    receipt = _publish_authorized_release(
        authorization_receipt=authorization_receipt,
        publication_reference=publication_reference,
        publisher=publisher,
        clock=clock,
    )
    if receipt.published_at - audit_recorded_at > _MAX_AUTHORIZATION_AGE:
        raise ReleasePublicationIndeterminateError(
            "release was published after authorization expiry; do not republish"
        )
    return receipt
