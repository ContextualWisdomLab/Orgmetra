"""Executable contract for purpose-bound immutable audit evidence review."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID

from orgmetra_audit_evidence_review import (
    AuditEvidenceQuery,
    AuditEvidenceReadAuthorization,
    PersistedAuditEvidenceRow,
    read_audit_evidence,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
EVENT = UUID("11111111-1111-4111-8111-111111111111")
QUERY = "audit_review:22222222-2222-4222-8222-222222222222"
REQUESTER = "actor:33333333-3333-4333-8333-333333333333"
FROM = datetime(2026, 8, 1, tzinfo=timezone.utc)
BEFORE = datetime(2026, 9, 1, tzinfo=timezone.utc)
RECORDED = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)


def _canonical_event() -> str:
    """Return one canonical PII-minimized audit envelope from the existing store contract."""
    document = {
        "data": {"high_impact": False, "result_code": "updated"},
        "datacontenttype": "application/json",
        "id": str(EVENT),
        "orgmetraactor": REQUESTER,
        "orgmetraevidence": "v1",
        "orgmetrapurpose": "people_record_update",
        "orgmetrareason": "authorized_change",
        "orgmetratenant": str(TENANT),
        "source": "urn:orgmetra:people_api",
        "specversion": "1.0",
        "subject": "person:44444444-4444-4444-8444-444444444444",
        "time": "2026-08-20T11:59:00Z",
        "type": "orgmetra.people.updated",
    }
    return json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class _Authority:
    """Return exact authorization evidence for the requested audit review."""

    def __init__(self) -> None:
        """Track whether authorization happened before any row read."""
        self.called = False

    def authorize(self, query: AuditEvidenceQuery) -> AuditEvidenceReadAuthorization:
        """Authorize exactly the governed query scope."""
        self.called = True
        return AuditEvidenceReadAuthorization(
            tenant_record_id=query.tenant_record_id,
            query_reference=query.query_reference,
            requester_reference=query.requester_reference,
            purpose_code=query.purpose_code,
            permitted=True,
        )


class _Reader:
    """Expose one persisted audit row only after authorization."""

    def __init__(self, authority: _Authority) -> None:
        """Bind the fake reader to the authority call-order probe."""
        self.authority = authority

    def read_rows(self, query: AuditEvidenceQuery) -> tuple[PersistedAuditEvidenceRow, ...]:
        """Return one digest-verified row and prove authorization preceded the read."""
        assert self.authority.called is True
        canonical = _canonical_event()
        return (
            PersistedAuditEvidenceRow(
                tenant_record_id=query.tenant_record_id,
                audit_event_record_id=EVENT,
                canonical_event_json=canonical,
                event_envelope_digest=sha256(canonical.encode("utf-8")).hexdigest(),
                recorded_at=RECORDED,
            ),
        )


def test_authorized_review_verifies_persisted_evidence_before_returning_it() -> None:
    """Authorized review returns only digest-bound tenant evidence from the requested window."""
    query = AuditEvidenceQuery(
        tenant_record_id=TENANT,
        query_reference=QUERY,
        requester_reference=REQUESTER,
        purpose_code="audit_evidence_review",
        recorded_from=FROM,
        recorded_before=BEFORE,
        limit=50,
    )
    authority = _Authority()
    page = read_audit_evidence(query=query, authority=authority, reader=_Reader(authority))

    assert page.query_reference == QUERY
    assert page.records[0].audit_event_record_id == EVENT
    assert page.records[0].event_envelope_digest == sha256(
        _canonical_event().encode("utf-8")
    ).hexdigest()
