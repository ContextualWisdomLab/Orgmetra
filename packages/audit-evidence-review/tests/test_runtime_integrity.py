"""Runtime-integrity regressions for the audit-review trust boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID

import pytest

from orgmetra_audit_evidence_review import (
    AuditEvidenceQuery,
    AuditEvidenceReadAuthorization,
    PersistedAuditEvidenceRow,
    read_audit_evidence,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("20000000-0000-7000-8000-000000000002")
EVENT = UUID("11111111-1111-4111-8111-111111111111")
QUERY_REF = "audit_review:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
REQUESTER = "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
START = datetime(2026, 8, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 1, tzinfo=timezone.utc)
RECORDED = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)


def _query() -> AuditEvidenceQuery:
    """Create one valid governed review query."""
    return AuditEvidenceQuery(
        tenant_record_id=TENANT,
        query_reference=QUERY_REF,
        requester_reference=REQUESTER,
        purpose_code="audit_evidence_review",
        recorded_from=START,
        recorded_before=END,
        limit=50,
    )


def _authorization(query: AuditEvidenceQuery) -> AuditEvidenceReadAuthorization:
    """Create one exact-scope permitted authorization decision."""
    return AuditEvidenceReadAuthorization(
        tenant_record_id=query.tenant_record_id,
        query_reference=query.query_reference,
        requester_reference=query.requester_reference,
        purpose_code=query.purpose_code,
        permitted=True,
    )


def _canonical_event() -> str:
    """Create one valid PII-minimized canonical audit envelope."""
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
        "subject": "person:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "time": "2026-08-20T11:59:00Z",
        "type": "orgmetra.people.updated",
    }
    return json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _row() -> PersistedAuditEvidenceRow:
    """Create one valid persisted audit row."""
    canonical = _canonical_event()
    return PersistedAuditEvidenceRow(
        tenant_record_id=TENANT,
        audit_event_record_id=EVENT,
        canonical_event_json=canonical,
        event_envelope_digest=sha256(canonical.encode("utf-8")).hexdigest(),
        recorded_at=RECORDED,
    )


class _Authority:
    """Return one configured authorization object."""

    def __init__(self, decision: AuditEvidenceReadAuthorization) -> None:
        """Store the decision and count calls."""
        self.decision = decision
        self.calls = 0

    def authorize(self, query: AuditEvidenceQuery) -> AuditEvidenceReadAuthorization:
        """Return the configured decision."""
        self.calls += 1
        return self.decision


class _Reader:
    """Return configured persisted rows and count calls."""

    def __init__(self, rows: tuple[PersistedAuditEvidenceRow, ...]) -> None:
        """Store immutable rows."""
        self.rows = rows
        self.calls = 0

    def read_rows(self, query: AuditEvidenceQuery) -> tuple[PersistedAuditEvidenceRow, ...]:
        """Return the configured rows."""
        self.calls += 1
        return self.rows


def test_post_construction_query_mutation_is_revalidated_before_authority_or_store_access() -> None:
    """A caller cannot widen a validated query by rewriting frozen fields after issuance."""
    query = _query()
    object.__setattr__(query, "limit", 1000)
    authority = _Authority(_authorization(_query()))
    reader = _Reader(())

    with pytest.raises(ValueError, match="limit"):
        read_audit_evidence(query=query, authority=authority, reader=reader)

    assert authority.calls == 0
    assert reader.calls == 0


def test_authority_callback_cannot_mutate_the_authoritative_query() -> None:
    """The host callback receives a snapshot, so its object-level mutation cannot widen the read."""
    query = _query()
    captured: list[AuditEvidenceQuery] = []

    class MutatingAuthority:
        """Attempt to rewrite every query field exposed to the authorization callback."""

        def authorize(self, callback_query: AuditEvidenceQuery) -> AuditEvidenceReadAuthorization:
            """Mutate only the callback snapshot and return authorization for the original query."""
            object.__setattr__(callback_query, "tenant_record_id", OTHER_TENANT)
            object.__setattr__(callback_query, "recorded_from", datetime(2026, 1, 1, tzinfo=timezone.utc))
            object.__setattr__(callback_query, "limit", 200)
            return _authorization(query)

    class CapturingReader:
        """Capture the query that reaches the store boundary."""

        def read_rows(self, reader_query: AuditEvidenceQuery) -> tuple[PersistedAuditEvidenceRow, ...]:
            """Return no rows after recording the authoritative query snapshot."""
            captured.append(reader_query)
            return ()

    page = read_audit_evidence(
        query=query,
        authority=MutatingAuthority(),
        reader=CapturingReader(),
    )

    assert page.records == ()
    assert captured[0].tenant_record_id == TENANT
    assert captured[0].recorded_from == START
    assert captured[0].limit == 50


def test_reader_callback_cannot_mutate_the_authoritative_query() -> None:
    """The store callback receives a snapshot, so returned-page checks keep the authorized scope."""
    query = _query()

    class MutatingReader:
        """Attempt to widen the query after the store callback receives it."""

        def read_rows(self, callback_query: AuditEvidenceQuery) -> tuple[PersistedAuditEvidenceRow, ...]:
            """Rewrite callback-only fields before returning one valid row."""
            object.__setattr__(callback_query, "query_reference", "audit_review:cccccccc-cccc-4ccc-8ccc-cccccccccccc")
            object.__setattr__(callback_query, "recorded_from", datetime(2020, 1, 1, tzinfo=timezone.utc))
            object.__setattr__(callback_query, "limit", 0)
            return (_row(),)

    page = read_audit_evidence(
        query=query,
        authority=_Authority(_authorization(query)),
        reader=MutatingReader(),
    )

    assert page.query_reference == QUERY_REF
    assert len(page.records) == 1


def test_post_construction_authorization_mutation_cannot_turn_non_boolean_into_permission() -> None:
    """Authorization output is revalidated rather than trusting a once-valid mutable Python object."""
    query = _query()
    decision = _authorization(query)
    object.__setattr__(decision, "permitted", "yes")
    authority = _Authority(decision)
    reader = _Reader(())

    with pytest.raises(ValueError, match="permitted"):
        read_audit_evidence(query=query, authority=authority, reader=reader)

    assert authority.calls == 1
    assert reader.calls == 0


def test_post_construction_row_mutation_is_reverified_before_evidence_is_returned() -> None:
    """A reader cannot mutate canonical bytes and their digest after row construction to widen evidence."""
    query = _query()
    persisted = _row()
    document = json.loads(persisted.canonical_event_json)
    document["employee_name"] = "should-never-enter-audit-envelope"
    widened = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    object.__setattr__(persisted, "canonical_event_json", widened)
    object.__setattr__(persisted, "event_envelope_digest", sha256(widened.encode("utf-8")).hexdigest())

    with pytest.raises(ValueError, match="governed audit envelope shape"):
        read_audit_evidence(
            query=query,
            authority=_Authority(_authorization(query)),
            reader=_Reader((persisted,)),
        )
