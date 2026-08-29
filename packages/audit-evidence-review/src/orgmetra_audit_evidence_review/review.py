"""Purpose-bound integrity verification for Orgmetra audit evidence review."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from typing import NoReturn, Protocol
from uuid import UUID

_MAX_UUID_INT = (1 << 128) - 1
_REFERENCE_PATTERN = re.compile(
    r"^(?P<namespace>[a-z][a-z0-9_]*):(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PURPOSE = "audit_evidence_review"
_MAX_WINDOW = timedelta(days=90)
_MAX_LIMIT = 200
_MAX_CANONICAL_BYTES = 32768
_BASE_EVENT_KEYS = frozenset(
    {
        "data",
        "datacontenttype",
        "id",
        "orgmetraactor",
        "orgmetraevidence",
        "orgmetrapurpose",
        "orgmetrareason",
        "orgmetratenant",
        "source",
        "specversion",
        "subject",
        "time",
        "type",
    }
)
_CONFIRMATION_KEY = "orgmetraconfirmation"
_DATA_KEYS = frozenset({"high_impact", "result_code"})
_EVENT_STRING_KEYS = frozenset(
    {
        "datacontenttype",
        "id",
        "orgmetraactor",
        "orgmetraevidence",
        "orgmetrapurpose",
        "orgmetrareason",
        "orgmetratenant",
        "source",
        "specversion",
        "subject",
        "time",
        "type",
    }
)


def _validate_operational_uuid(name: str, value: UUID) -> None:
    """Require a canonical non-sentinel UUID owned by an authoritative Orgmetra boundary."""
    if type(value) is not UUID or value.int in (0, _MAX_UUID_INT):
        raise ValueError(f"{name} must be a non-sentinel UUID.")


def _validate_reference(name: str, value: str, namespace: str) -> None:
    """Require an exact built-in string carrying one packet-owned opaque UUIDv4 reference."""
    if type(value) is not str or len(value) > 96:
        raise ValueError(f"{name} must be a bounded string.")
    match = _REFERENCE_PATTERN.fullmatch(value)
    if match is None or match.group("namespace") != namespace:
        raise ValueError(f"{name} must use the {namespace}: UUIDv4 namespace.")
    parsed = UUID(match.group("uuid"))
    if str(parsed) != match.group("uuid") or parsed.version != 4:
        raise ValueError(f"{name} must use a canonical UUIDv4 suffix.")


def _freeze_timestamp(name: str, value: datetime) -> datetime:
    """Detach a caller-owned timezone provider and return a built-in UTC instant."""
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{name} must be an aware datetime.")
    try:
        offset = value.utcoffset()
    except Exception as error:  # noqa: BLE001 - caller timezone code is untrusted.
        raise ValueError(f"{name} timezone offset could not be resolved.") from error
    if type(offset) is not timedelta:
        raise ValueError(f"{name} must resolve to a concrete UTC offset.")
    try:
        return (value.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} cannot be normalized to UTC.") from error


def _reject_nonfinite_json_number(value: str) -> NoReturn:
    """Reject JSON extensions that encode non-finite numbers instead of valid JSON."""
    raise ValueError(f"non-finite JSON number {value} is not permitted")


@dataclass(frozen=True, slots=True)
class AuditEvidenceQuery:
    """One bounded audit-review request that carries no HR application values."""

    tenant_record_id: UUID
    query_reference: str
    requester_reference: str
    purpose_code: str
    recorded_from: datetime
    recorded_before: datetime
    limit: int = 100

    def __post_init__(self) -> None:
        """Validate scope and freeze the requested system-recorded interval to UTC."""
        _validate_operational_uuid("tenant_record_id", self.tenant_record_id)
        _validate_reference("query_reference", self.query_reference, "audit_review")
        _validate_reference("requester_reference", self.requester_reference, "actor")
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE:
            raise ValueError("purpose_code must be audit_evidence_review.")
        frozen_from = _freeze_timestamp("recorded_from", self.recorded_from)
        frozen_before = _freeze_timestamp("recorded_before", self.recorded_before)
        object.__setattr__(self, "recorded_from", frozen_from)
        object.__setattr__(self, "recorded_before", frozen_before)
        if frozen_before <= frozen_from:
            raise ValueError("recorded_before must be later than recorded_from.")
        if frozen_before - frozen_from > _MAX_WINDOW:
            raise ValueError("audit review window must not exceed 90 days.")
        if type(self.limit) is not int or not 1 <= self.limit <= _MAX_LIMIT:
            raise ValueError("limit must be an integer from 1 through 200.")


@dataclass(frozen=True, slots=True)
class AuditEvidenceReadAuthorization:
    """Authoritative decision proving one requester may read one exact audit query."""

    tenant_record_id: UUID
    query_reference: str
    requester_reference: str
    purpose_code: str
    permitted: bool

    def __post_init__(self) -> None:
        """Validate authorization evidence without granting authority by construction."""
        _validate_operational_uuid("tenant_record_id", self.tenant_record_id)
        _validate_reference("query_reference", self.query_reference, "audit_review")
        _validate_reference("requester_reference", self.requester_reference, "actor")
        if type(self.purpose_code) is not str or self.purpose_code != _PURPOSE:
            raise ValueError("purpose_code must be audit_evidence_review.")
        if type(self.permitted) is not bool:
            raise ValueError("permitted must be a boolean.")


@dataclass(frozen=True, slots=True)
class PersistedAuditEvidenceRow:
    """One immutable audit-store row reverified before review use."""

    tenant_record_id: UUID
    audit_event_record_id: UUID
    canonical_event_json: str
    event_envelope_digest: str
    recorded_at: datetime

    def __post_init__(self) -> None:
        """Verify row identity, exact governed envelope bytes, digest, and recorded time."""
        _validate_operational_uuid("tenant_record_id", self.tenant_record_id)
        _validate_operational_uuid("audit_event_record_id", self.audit_event_record_id)
        if type(self.canonical_event_json) is not str:
            raise ValueError("canonical_event_json must be a string.")
        try:
            canonical_bytes = self.canonical_event_json.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("canonical_event_json must be valid UTF-8 text.") from error
        if len(canonical_bytes) > _MAX_CANONICAL_BYTES:
            raise ValueError("canonical_event_json exceeds the 32768-byte review budget.")
        if type(self.event_envelope_digest) is not str or _DIGEST_PATTERN.fullmatch(
            self.event_envelope_digest
        ) is None:
            raise ValueError("event_envelope_digest must be a lower-case SHA-256 digest.")
        if sha256(canonical_bytes).hexdigest() != self.event_envelope_digest:
            raise ValueError("audit event digest does not match persisted canonical bytes.")
        try:
            document = json.loads(
                self.canonical_event_json,
                parse_constant=_reject_nonfinite_json_number,
            )
        except (ValueError, UnicodeError) as error:
            raise ValueError("canonical_event_json must contain valid UTF-8 JSON.") from error
        if type(document) is not dict:
            raise ValueError("canonical_event_json must contain one JSON object.")
        if (
            json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            != self.canonical_event_json
        ):
            raise ValueError("canonical_event_json is not in canonical Orgmetra JSON form.")
        event_keys = frozenset(document)
        if event_keys not in (_BASE_EVENT_KEYS, _BASE_EVENT_KEYS | {_CONFIRMATION_KEY}):
            raise ValueError("canonical_event_json does not match the governed audit envelope shape.")
        event_data = document.get("data")
        if type(event_data) is not dict or frozenset(event_data) != _DATA_KEYS:
            raise ValueError("canonical_event_json does not match the governed audit data shape.")
        if any(type(document.get(key)) is not str for key in _EVENT_STRING_KEYS):
            raise ValueError("canonical_event_json does not match the governed audit value types.")
        if type(event_data["result_code"]) is not str or type(event_data["high_impact"]) is not bool:
            raise ValueError("canonical_event_json does not match the governed audit value types.")
        if _CONFIRMATION_KEY in document and type(document[_CONFIRMATION_KEY]) is not str:
            raise ValueError("canonical_event_json does not match the governed audit value types.")
        if document.get("specversion") != "1.0" or document.get("datacontenttype") != "application/json":
            raise ValueError("audit event must use the governed CloudEvents 1.0 JSON contract.")
        if document.get("id") != str(self.audit_event_record_id):
            raise ValueError("audit event id does not match the persisted row identity.")
        if document.get("orgmetratenant") != str(self.tenant_record_id):
            raise ValueError("audit event tenant does not match the persisted row scope.")
        object.__setattr__(self, "recorded_at", _freeze_timestamp("recorded_at", self.recorded_at))


@dataclass(frozen=True, slots=True)
class AuditEvidenceReviewPage:
    """Verified evidence returned for one exact authorized review query."""

    query_reference: str
    records: tuple[PersistedAuditEvidenceRow, ...]

    def __post_init__(self) -> None:
        """Keep review output immutable and bound to a canonical query reference."""
        _validate_reference("query_reference", self.query_reference, "audit_review")
        if type(self.records) is not tuple:
            raise ValueError("records must be an immutable tuple.")
        if any(type(row) is not PersistedAuditEvidenceRow for row in self.records):
            raise ValueError("records must contain exact persisted audit evidence rows.")


class AuditEvidenceReadAuthority(Protocol):
    """Host authorization boundary invoked before any audit-store read."""

    def authorize(self, query: AuditEvidenceQuery) -> AuditEvidenceReadAuthorization:
        """Return an exact-scope authorization decision for the review query."""


class AuditEvidenceRowReader(Protocol):
    """Read-only adapter for the existing Orgmetra immutable audit store."""

    def read_rows(self, query: AuditEvidenceQuery) -> tuple[PersistedAuditEvidenceRow, ...]:
        """Return rows already constrained by tenant, time window, order, and limit."""


def _snapshot_query(query: AuditEvidenceQuery) -> AuditEvidenceQuery:
    """Revalidate live query fields and return a detached governed snapshot."""
    return AuditEvidenceQuery(
        tenant_record_id=query.tenant_record_id,
        query_reference=query.query_reference,
        requester_reference=query.requester_reference,
        purpose_code=query.purpose_code,
        recorded_from=query.recorded_from,
        recorded_before=query.recorded_before,
        limit=query.limit,
    )


def _snapshot_authorization(
    authorization: AuditEvidenceReadAuthorization,
) -> AuditEvidenceReadAuthorization:
    """Revalidate authority output so post-construction mutation cannot widen permission."""
    return AuditEvidenceReadAuthorization(
        tenant_record_id=authorization.tenant_record_id,
        query_reference=authorization.query_reference,
        requester_reference=authorization.requester_reference,
        purpose_code=authorization.purpose_code,
        permitted=authorization.permitted,
    )


def _snapshot_row(row: PersistedAuditEvidenceRow) -> PersistedAuditEvidenceRow:
    """Reverify current persisted-row fields and detach evidence from the reader object."""
    return PersistedAuditEvidenceRow(
        tenant_record_id=row.tenant_record_id,
        audit_event_record_id=row.audit_event_record_id,
        canonical_event_json=row.canonical_event_json,
        event_envelope_digest=row.event_envelope_digest,
        recorded_at=row.recorded_at,
    )


def read_audit_evidence(
    *,
    query: AuditEvidenceQuery,
    authority: AuditEvidenceReadAuthority,
    reader: AuditEvidenceRowReader,
) -> AuditEvidenceReviewPage:
    """Authorize first, then verify a bounded ordered page from the immutable audit store."""
    if type(query) is not AuditEvidenceQuery:
        raise TypeError("query must be an exact AuditEvidenceQuery.")
    verified_query = _snapshot_query(query)
    authorization = authority.authorize(_snapshot_query(verified_query))
    if type(authorization) is not AuditEvidenceReadAuthorization:
        raise TypeError("authority must return AuditEvidenceReadAuthorization.")
    verified_authorization = _snapshot_authorization(authorization)
    expected_scope = (
        verified_query.tenant_record_id,
        verified_query.query_reference,
        verified_query.requester_reference,
        verified_query.purpose_code,
    )
    actual_scope = (
        verified_authorization.tenant_record_id,
        verified_authorization.query_reference,
        verified_authorization.requester_reference,
        verified_authorization.purpose_code,
    )
    if actual_scope != expected_scope or not verified_authorization.permitted:
        raise PermissionError("audit evidence review is not authorized for the exact query scope.")

    rows = reader.read_rows(_snapshot_query(verified_query))
    if type(rows) is not tuple:
        raise TypeError("reader must return an immutable tuple.")
    if len(rows) > verified_query.limit:
        raise ValueError("reader returned more audit rows than the authorized limit.")

    previous_key: tuple[datetime, int] | None = None
    verified_rows: list[PersistedAuditEvidenceRow] = []
    for row in rows:
        if type(row) is not PersistedAuditEvidenceRow:
            raise TypeError("reader returned an ungoverned audit evidence row.")
        verified_row = _snapshot_row(row)
        if verified_row.tenant_record_id != verified_query.tenant_record_id:
            raise PermissionError("reader returned cross-tenant audit evidence.")
        if not verified_query.recorded_from <= verified_row.recorded_at < verified_query.recorded_before:
            raise ValueError("reader returned audit evidence outside the authorized time window.")
        key = (verified_row.recorded_at, verified_row.audit_event_record_id.int)
        if previous_key is not None and key <= previous_key:
            raise ValueError("reader must return audit evidence in strict recorded-time/id order.")
        previous_key = key
        verified_rows.append(verified_row)

    return AuditEvidenceReviewPage(
        query_reference=verified_query.query_reference,
        records=tuple(verified_rows),
    )
