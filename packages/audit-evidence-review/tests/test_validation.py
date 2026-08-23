"""Adversarial validation and authority-boundary regressions for audit review."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from hashlib import sha256
import json
from uuid import UUID

import pytest

from orgmetra_audit_evidence_review import (
    AuditEvidenceQuery,
    AuditEvidenceReadAuthorization,
    AuditEvidenceReviewPage,
    PersistedAuditEvidenceRow,
    read_audit_evidence,
)

TENANT = UUID("10000000-0000-7000-8000-000000000001")
OTHER_TENANT = UUID("20000000-0000-7000-8000-000000000002")
EVENT1 = UUID("11111111-1111-4111-8111-111111111111")
EVENT2 = UUID("22222222-2222-4222-8222-222222222222")
QUERY_REF = "audit_review:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
REQUESTER = "actor:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
START = datetime(2026, 8, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 1, tzinfo=timezone.utc)
RECORDED = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)


def canonical_event(*, tenant: UUID = TENANT, event: UUID = EVENT1) -> str:
    """Build exact canonical JSON matching the existing immutable audit store contract."""
    document = {
        "data": {"high_impact": False, "result_code": "updated"},
        "datacontenttype": "application/json",
        "id": str(event),
        "orgmetraactor": REQUESTER,
        "orgmetraevidence": "v1",
        "orgmetrapurpose": "people_record_update",
        "orgmetrareason": "authorized_change",
        "orgmetratenant": str(tenant),
        "source": "urn:orgmetra:people_api",
        "specversion": "1.0",
        "subject": "person:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "time": "2026-08-20T11:59:00Z",
        "type": "orgmetra.people.updated",
    }
    return json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def row(
    *,
    tenant: UUID = TENANT,
    event: UUID = EVENT1,
    recorded_at: datetime = RECORDED,
    canonical: str | None = None,
    digest: str | None = None,
) -> PersistedAuditEvidenceRow:
    """Build one valid persisted row unless an explicit adversarial value is supplied."""
    text = canonical_event(tenant=tenant, event=event) if canonical is None else canonical
    actual_digest = sha256(text.encode("utf-8")).hexdigest() if digest is None else digest
    return PersistedAuditEvidenceRow(
        tenant_record_id=tenant,
        audit_event_record_id=event,
        canonical_event_json=text,
        event_envelope_digest=actual_digest,
        recorded_at=recorded_at,
    )


def query(**changes: object) -> AuditEvidenceQuery:
    """Build a valid bounded query and permit focused overrides."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "query_reference": QUERY_REF,
        "requester_reference": REQUESTER,
        "purpose_code": "audit_evidence_review",
        "recorded_from": START,
        "recorded_before": END,
        "limit": 100,
    }
    values.update(changes)
    return AuditEvidenceQuery(**values)  # type: ignore[arg-type]


def authorization(q: AuditEvidenceQuery, **changes: object) -> AuditEvidenceReadAuthorization:
    """Build matching authorization evidence and permit focused overrides."""
    values: dict[str, object] = {
        "tenant_record_id": q.tenant_record_id,
        "query_reference": q.query_reference,
        "requester_reference": q.requester_reference,
        "purpose_code": q.purpose_code,
        "permitted": True,
    }
    values.update(changes)
    return AuditEvidenceReadAuthorization(**values)  # type: ignore[arg-type]


class Authority:
    """Configurable fake authority used to prove authorization ordering and scope."""

    def __init__(self, decision: object) -> None:
        """Store the decision and count calls."""
        self.decision = decision
        self.calls = 0

    def authorize(self, q: AuditEvidenceQuery) -> object:
        """Return the configured decision."""
        self.calls += 1
        return self.decision


class Reader:
    """Configurable fake immutable audit-store reader."""

    def __init__(self, rows: object) -> None:
        """Store rows and count calls."""
        self.rows = rows
        self.calls = 0

    def read_rows(self, q: AuditEvidenceQuery) -> object:
        """Return configured rows."""
        self.calls += 1
        return self.rows


class RaisingTimezone(tzinfo):
    """Timezone provider that fails when asked for an offset."""

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        """Raise to prove caller timezone code cannot escape the boundary."""
        raise RuntimeError("boom")

    def dst(self, dt: datetime | None) -> timedelta | None:
        """Return no DST adjustment."""
        return None


class MissingOffsetTimezone(tzinfo):
    """Timezone provider that cannot resolve a concrete offset."""

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        """Return no offset."""
        return None

    def dst(self, dt: datetime | None) -> timedelta | None:
        """Return no DST adjustment."""
        return None


class ForgedStr(str):
    """Hostile string subtype used to prove exact-runtime trust boundaries."""


class ForgedInt(int):
    """Hostile integer subtype used to prove bool/subclass rejection."""


class ForgedUUID(UUID):
    """UUID subtype used to prove authoritative identities require exact runtime UUID."""


class ForgedDateTime(datetime):
    """Datetime subtype used to prove time evidence cannot override behavior."""


def test_query_normalizes_fixed_offset_and_accepts_boundary_limit() -> None:
    """Query stores detached UTC timestamps and the maximum bounded page size."""
    item = query(
        recorded_from=datetime(2026, 8, 1, 9, tzinfo=timezone(timedelta(hours=9))),
        recorded_before=datetime(2026, 10, 30, 9, tzinfo=timezone(timedelta(hours=9))),
        limit=200,
    )
    assert item.recorded_from == datetime(2026, 8, 1, tzinfo=timezone.utc)
    assert item.recorded_before == datetime(2026, 10, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize("bad_uuid", [UUID(int=0), UUID(int=(1 << 128) - 1)])
def test_query_rejects_reserved_tenant_uuid(bad_uuid: UUID) -> None:
    """Reserved UUID sentinels cannot identify a tenant."""
    with pytest.raises(ValueError, match="tenant_record_id"):
        query(tenant_record_id=bad_uuid)


def test_query_rejects_uuid_subtype() -> None:
    """Caller-defined UUID runtime types cannot enter trusted tenant scope."""
    with pytest.raises(ValueError, match="tenant_record_id"):
        query(tenant_record_id=ForgedUUID(str(TENANT)))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("query_reference", "bad"),
        ("query_reference", "audit_review:aaaaaaaa-aaaa-1aaa-8aaa-aaaaaaaaaaaa"),
        ("query_reference", "audit_review:" + "a" * 100),
        ("requester_reference", "reviewer:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        ("requester_reference", ForgedStr(REQUESTER)),
    ],
)
def test_query_rejects_invalid_references(field: str, value: str) -> None:
    """Packet-owned query and requester references are bounded canonical UUIDv4 text."""
    with pytest.raises(ValueError, match=field):
        query(**{field: value})


@pytest.mark.parametrize("purpose", ["other", ForgedStr("audit_evidence_review")])
def test_query_rejects_noncanonical_purpose(purpose: str) -> None:
    """Only exact built-in audit-review purpose text is trusted."""
    with pytest.raises(ValueError, match="purpose_code"):
        query(purpose_code=purpose)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (datetime(2026, 8, 1), "aware"),
        (ForgedDateTime(2026, 8, 1, tzinfo=timezone.utc), "aware"),
        (datetime(2026, 8, 1, tzinfo=RaisingTimezone()), "could not"),
        (datetime(2026, 8, 1, tzinfo=MissingOffsetTimezone()), "concrete"),
    ],
)
def test_query_rejects_untrusted_time(value: datetime, message: str) -> None:
    """System-recorded query bounds reject ambiguous or caller-controlled runtime time."""
    with pytest.raises(ValueError, match=message):
        query(recorded_from=value)


def test_query_normalizes_timestamp_overflow_to_value_error() -> None:
    """Offset arithmetic overflow fails closed with a stable validation error."""
    with pytest.raises(ValueError, match="cannot be normalized"):
        query(recorded_from=datetime.min.replace(tzinfo=timezone(timedelta(hours=14))))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"recorded_before": START}, "later"),
        ({"recorded_before": datetime(2026, 11, 1, tzinfo=timezone.utc)}, "90 days"),
        ({"limit": 0}, "1 through 200"),
        ({"limit": 201}, "1 through 200"),
        ({"limit": True}, "1 through 200"),
        ({"limit": ForgedInt(10)}, "1 through 200"),
    ],
)
def test_query_rejects_unbounded_or_invalid_window(changes: dict[str, object], message: str) -> None:
    """Review requests remain time- and row-bounded."""
    with pytest.raises(ValueError, match=message):
        query(**changes)


def test_authorization_validates_scope_and_boolean() -> None:
    """Authorization evidence uses the same strict scope vocabulary as the query."""
    item = query()
    assert authorization(item).permitted is True
    with pytest.raises(ValueError, match="tenant_record_id"):
        authorization(item, tenant_record_id=UUID(int=0))
    with pytest.raises(ValueError, match="query_reference"):
        authorization(item, query_reference="bad")
    with pytest.raises(ValueError, match="requester_reference"):
        authorization(item, requester_reference="bad")
    with pytest.raises(ValueError, match="purpose_code"):
        authorization(item, purpose_code="other")
    with pytest.raises(ValueError, match="permitted"):
        authorization(item, permitted=1)


def test_row_accepts_canonical_digest_bound_evidence_and_normalizes_recorded_time() -> None:
    """A valid row is reverified and its system-recorded time is detached to UTC."""
    item = row(recorded_at=datetime(2026, 8, 20, 21, tzinfo=timezone(timedelta(hours=9))))
    assert item.recorded_at == RECORDED


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"tenant_record_id": UUID(int=0)}, "tenant_record_id"),
        ({"audit_event_record_id": UUID(int=0)}, "audit_event_record_id"),
        ({"canonical_event_json": 1}, "canonical_event_json must be a string"),
        ({"event_envelope_digest": "x"}, "SHA-256"),
        ({"event_envelope_digest": ForgedStr("0" * 64)}, "SHA-256"),
    ],
)
def test_row_rejects_invalid_primitive_evidence(changes: dict[str, object], message: str) -> None:
    """Persisted row trust primitives are validated before evidence use."""
    values: dict[str, object] = {
        "tenant_record_id": TENANT,
        "audit_event_record_id": EVENT1,
        "canonical_event_json": canonical_event(),
        "event_envelope_digest": sha256(canonical_event().encode()).hexdigest(),
        "recorded_at": RECORDED,
    }
    values.update(changes)
    with pytest.raises(ValueError, match=message):
        PersistedAuditEvidenceRow(**values)  # type: ignore[arg-type]


def test_row_rejects_oversized_canonical_bytes() -> None:
    """Audit review does not accept an unbounded canonical envelope."""
    oversized = "x" * 32769
    with pytest.raises(ValueError, match="32768-byte"):
        PersistedAuditEvidenceRow(
            tenant_record_id=TENANT,
            audit_event_record_id=EVENT1,
            canonical_event_json=oversized,
            event_envelope_digest="0" * 64,
            recorded_at=RECORDED,
        )


def test_row_rejects_digest_mismatch() -> None:
    """Stored digest must bind the exact canonical UTF-8 bytes."""
    with pytest.raises(ValueError, match="digest"):
        row(digest="0" * 64)


@pytest.mark.parametrize(
    ("canonical", "message"),
    [
        ("{", "valid UTF-8 JSON"),
        ("[]", "one JSON object"),
        ('{ "a":1}', "canonical Orgmetra JSON"),
    ],
)
def test_row_rejects_noncanonical_json(canonical: str, message: str) -> None:
    """Persisted bytes must parse to exactly one canonical JSON object."""
    with pytest.raises(ValueError, match=message):
        row(canonical=canonical)


def test_row_rejects_wrong_cloudevent_contract() -> None:
    """Read-time verification preserves the existing CloudEvents envelope version/media type."""
    document = json.loads(canonical_event())
    document["specversion"] = "0.3"
    text = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    with pytest.raises(ValueError, match="CloudEvents"):
        row(canonical=text)
    document["specversion"] = "1.0"
    document["datacontenttype"] = "text/plain"
    text = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    with pytest.raises(ValueError, match="CloudEvents"):
        row(canonical=text)


def test_row_rejects_mismatched_event_and_tenant_bindings() -> None:
    """Canonical event identity and tenant scope must match persisted row columns."""
    with pytest.raises(ValueError, match="event id"):
        row(event=EVENT2, canonical=canonical_event(event=EVENT1))
    with pytest.raises(ValueError, match="event tenant"):
        row(tenant=OTHER_TENANT, canonical=canonical_event(tenant=TENANT))


def test_row_rejects_invalid_recorded_time() -> None:
    """Persisted system-recorded time receives the same fail-closed timestamp validation."""
    with pytest.raises(ValueError, match="aware"):
        row(recorded_at=datetime(2026, 8, 20, 12))


def test_review_page_validates_reference_and_record_collection() -> None:
    """Review output remains immutable and governed by exact runtime record types."""
    item = row()
    assert AuditEvidenceReviewPage(QUERY_REF, (item,)).records == (item,)
    with pytest.raises(ValueError, match="query_reference"):
        AuditEvidenceReviewPage("bad", (item,))
    with pytest.raises(ValueError, match="immutable tuple"):
        AuditEvidenceReviewPage(QUERY_REF, [item])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="exact persisted"):
        AuditEvidenceReviewPage(QUERY_REF, (object(),))  # type: ignore[arg-type]


def test_read_requires_exact_query_and_authorization_types_before_store_access() -> None:
    """Ungoverned query or authority evidence cannot trigger an audit-store read."""
    item = query()
    reader = Reader(())
    with pytest.raises(TypeError, match="exact AuditEvidenceQuery"):
        read_audit_evidence(query=object(), authority=Authority(authorization(item)), reader=reader)  # type: ignore[arg-type]
    assert reader.calls == 0
    with pytest.raises(TypeError, match="authority"):
        read_audit_evidence(query=item, authority=Authority(object()), reader=reader)
    assert reader.calls == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"tenant_record_id": OTHER_TENANT},
        {"query_reference": "audit_review:dddddddd-dddd-4ddd-8ddd-dddddddddddd"},
        {"requester_reference": "actor:eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"},
        {"purpose_code": "audit_evidence_review", "permitted": False},
    ],
)
def test_read_denies_mismatched_or_denied_authorization_before_store_access(changes: dict[str, object]) -> None:
    """Authorization must exactly bind tenant, request, requester, purpose, and permission."""
    item = query()
    decision = authorization(item, **changes)
    reader = Reader(())
    with pytest.raises(PermissionError, match="not authorized"):
        read_audit_evidence(query=item, authority=Authority(decision), reader=reader)
    assert reader.calls == 0


def test_read_requires_tuple_and_limit_bound() -> None:
    """Reader output must be immutable and may not exceed the authorized count."""
    item = query(limit=1)
    auth = Authority(authorization(item))
    with pytest.raises(TypeError, match="immutable tuple"):
        read_audit_evidence(query=item, authority=auth, reader=Reader([]))
    with pytest.raises(ValueError, match="authorized limit"):
        read_audit_evidence(query=item, authority=auth, reader=Reader((row(), row(event=EVENT2))))


def test_read_rejects_ungoverned_cross_tenant_and_out_of_window_rows() -> None:
    """Every returned row is rechecked for runtime type, tenant, and recorded-time scope."""
    item = query()
    auth = Authority(authorization(item))
    with pytest.raises(TypeError, match="ungoverned"):
        read_audit_evidence(query=item, authority=auth, reader=Reader((object(),)))
    with pytest.raises(PermissionError, match="cross-tenant"):
        read_audit_evidence(query=item, authority=auth, reader=Reader((row(tenant=OTHER_TENANT),)))
    with pytest.raises(ValueError, match="outside"):
        read_audit_evidence(
            query=item,
            authority=auth,
            reader=Reader((row(recorded_at=datetime(2026, 9, 1, tzinfo=timezone.utc)),)),
        )


def test_read_requires_strict_recorded_time_id_order() -> None:
    """Stable keyset order prevents duplicate or regressing evidence pages."""
    item = query()
    auth = Authority(authorization(item))
    with pytest.raises(ValueError, match="strict"):
        read_audit_evidence(query=item, authority=auth, reader=Reader((row(event=EVENT2), row(event=EVENT1))))


def test_read_returns_verified_authorized_page() -> None:
    """Authorized evidence reaches the caller only after row and ordering verification."""
    item = query()
    first = row(event=EVENT1)
    second = row(event=EVENT2, recorded_at=RECORDED + timedelta(seconds=1))
    page = read_audit_evidence(
        query=item,
        authority=Authority(authorization(item)),
        reader=Reader((first, second)),
    )
    assert page.query_reference == QUERY_REF
    assert page.records == (first, second)
