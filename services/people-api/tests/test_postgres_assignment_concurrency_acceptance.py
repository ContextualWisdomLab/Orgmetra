"""Real PostgreSQL interleavings for governed Assignment conflict domains.

The acceptance deliberately drives ``PostgresPeopleMutationPort`` through a
small libpq DB-API boundary instead of mocking cursors.  Each case runs against
an isolated PostgreSQL container and holds the first writer immediately before
COMMIT, so the second writer must cross the production row-lock boundary.  The
wait is observed from ``pg_stat_activity``/``pg_blocking_pids``; sleeps never
establish the correctness ordering.
"""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
import ctypes.util
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from typing import Iterator, Sequence
from uuid import UUID, uuid4

import pytest

from orgmetra_keyverse_adapter import AuthorizationDecision
from orgmetra_people_api.mutations import AssignmentMutationCommand, PeopleMutationIntegrityError
from orgmetra_people_api.postgres_mutations import PostgresPeopleMutationPort

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TENANT = UUID("10000000-0000-7000-8000-000000000001")
_PERSON_ONE = UUID("10000000-0000-7000-8000-000000000101")
_PERSON_TWO = UUID("10000000-0000-7000-8000-000000000102")
_EMPLOYMENT_ONE = UUID("10000000-0000-7000-8000-000000000111")
_EMPLOYMENT_TWO = UUID("10000000-0000-7000-8000-000000000112")
_POSITION_ONE = UUID("10000000-0000-7000-8000-000000000121")
_POSITION_TWO = UUID("10000000-0000-7000-8000-000000000122")
_ASSIGNMENT_EFFECTIVE_FROM = date(2026, 8, 18)
_MIGRATIONS = (
    "database/migrations/0001_foundation_schema.sql",
    "database/migrations/0002_sealed_evidence_digest.sql",
    "database/migrations/0003_audit_outbox_persistence.sql",
    "database/migrations/0004_outbox_delivery_claim.sql",
    "database/migrations/0005_outbox_delivery_finalization.sql",
    "database/migrations/0006_outbox_delivery_dead_letter.sql",
    "database/migrations/0007_outbox_retry_exhaustion.sql",
    "database/migrations/0008_audit_outbox_review_hardening.sql",
    "database/migrations/0009_candidate_worker_conversion_governance.sql",
    "database/migrations/0012_people_mutation_idempotency.sql",
)

_PGRES_COMMAND_OK = 1
_PGRES_TUPLES_OK = 2
_OID_BOOL = 16
_OID_INT8 = 20
_OID_INT2 = 21
_OID_INT4 = 23
_OID_FLOAT4 = 700
_OID_FLOAT8 = 701
_OID_DATE = 1082
_OID_TIMESTAMP = 1114
_OID_TIMESTAMPTZ = 1184
_OID_NUMERIC = 1700
_OID_UUID = 2950
_PARAMETER = re.compile(r"%s")


def _load_libpq() -> ctypes.CDLL:
    """Load the system libpq already required by the repository's psql contracts."""
    candidate = ctypes.util.find_library("pq")
    if candidate is None:
        raise RuntimeError("libpq is required for PostgreSQL Assignment acceptance")
    library = ctypes.CDLL(candidate)
    library.PQconnectdb.argtypes = [ctypes.c_char_p]
    library.PQconnectdb.restype = ctypes.c_void_p
    library.PQstatus.argtypes = [ctypes.c_void_p]
    library.PQstatus.restype = ctypes.c_int
    library.PQerrorMessage.argtypes = [ctypes.c_void_p]
    library.PQerrorMessage.restype = ctypes.c_char_p
    library.PQfinish.argtypes = [ctypes.c_void_p]
    library.PQbackendPID.argtypes = [ctypes.c_void_p]
    library.PQbackendPID.restype = ctypes.c_int
    library.PQexecParams.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
    ]
    library.PQexecParams.restype = ctypes.c_void_p
    library.PQresultStatus.argtypes = [ctypes.c_void_p]
    library.PQresultStatus.restype = ctypes.c_int
    library.PQresultErrorMessage.argtypes = [ctypes.c_void_p]
    library.PQresultErrorMessage.restype = ctypes.c_char_p
    library.PQntuples.argtypes = [ctypes.c_void_p]
    library.PQntuples.restype = ctypes.c_int
    library.PQnfields.argtypes = [ctypes.c_void_p]
    library.PQnfields.restype = ctypes.c_int
    library.PQftype.argtypes = [ctypes.c_void_p, ctypes.c_int]
    library.PQftype.restype = ctypes.c_uint
    library.PQgetisnull.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    library.PQgetisnull.restype = ctypes.c_int
    library.PQgetvalue.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    library.PQgetvalue.restype = ctypes.c_char_p
    library.PQclear.argtypes = [ctypes.c_void_p]
    return library


_LIBPQ = _load_libpq()


def _parameter_text(value: object) -> bytes | None:
    """Serialize the exact scalar parameter types used by People PostgreSQL writes."""
    if value is None:
        return None
    if type(value) is UUID:
        return str(value).encode()
    if type(value) is datetime:
        return value.isoformat().encode()
    if type(value) is date:
        return value.isoformat().encode()
    if type(value) is Decimal:
        return format(value, "f").encode()
    if type(value) is bool:
        return ("true" if value else "false").encode()
    if type(value) in (str, int, float):
        return str(value).encode()
    raise TypeError(f"unsupported libpq acceptance parameter: {type(value).__name__}")


def _decode_field(oid: int, raw: bytes) -> object:
    """Decode PostgreSQL text results into the exact runtime scalars the adapter validates."""
    text = raw.decode()
    if oid == _OID_UUID:
        return UUID(text)
    if oid == _OID_DATE:
        return date.fromisoformat(text)
    if oid in (_OID_TIMESTAMP, _OID_TIMESTAMPTZ):
        return datetime.fromisoformat(text)
    if oid == _OID_NUMERIC:
        return Decimal(text)
    if oid in (_OID_INT2, _OID_INT4, _OID_INT8):
        return int(text)
    if oid in (_OID_FLOAT4, _OID_FLOAT8):
        return float(text)
    if oid == _OID_BOOL:
        return text == "t"
    return text


def _bind_parameters(sql: str, parameters: Sequence[object]) -> tuple[str, list[bytes | None]]:
    """Translate DB-API ``%s`` markers to libpq positional parameters without interpolation."""
    counter = 0

    def replace_marker(_: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        return f"${counter}"

    translated = _PARAMETER.sub(replace_marker, sql)
    if counter != len(parameters):
        raise AssertionError(f"SQL expected {counter} parameters, received {len(parameters)}")
    return translated, [_parameter_text(parameter) for parameter in parameters]


@dataclass(slots=True)
class _CommitBarrier:
    """Hold one real transaction after all adapter writes but before COMMIT."""

    ready: threading.Event
    release: threading.Event

    @classmethod
    def create(cls) -> "_CommitBarrier":
        """Return a fresh one-shot commit barrier."""
        return cls(threading.Event(), threading.Event())


class _LibpqCursor:
    """Minimal DB-API cursor over one libpq connection for production adapter acceptance."""

    def __init__(self, connection: "_LibpqConnection") -> None:
        self._connection = connection
        self._rows: list[tuple[object, ...]] = []
        self._offset = 0

    def __enter__(self) -> "_LibpqCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback

    def execute(self, sql: str, parameters: Sequence[object] | None = None) -> None:
        self._rows = self._connection.execute(sql, () if parameters is None else parameters)
        self._offset = 0

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        rows = self._rows[self._offset : self._offset + size]
        self._offset += len(rows)
        return rows

    def fetchall(self) -> list[tuple[object, ...]]:
        rows = self._rows[self._offset :]
        self._offset = len(self._rows)
        return rows


class _LibpqConnection:
    """One real libpq transaction with psycopg-compatible context semantics."""

    def __init__(
        self,
        database_url: str,
        *,
        application_name: str,
        barrier: _CommitBarrier | None = None,
    ) -> None:
        separator = "&" if "?" in database_url else "?"
        connection_url = f"{database_url}{separator}application_name={application_name}"
        handle = _LIBPQ.PQconnectdb(connection_url.encode())
        if not handle:
            raise RuntimeError("libpq returned a null PostgreSQL connection")
        self._handle = handle
        self._barrier = barrier
        self.closed = False
        if _LIBPQ.PQstatus(handle) != 0:
            message = _LIBPQ.PQerrorMessage(handle).decode().strip()
            _LIBPQ.PQfinish(handle)
            self.closed = True
            raise RuntimeError(f"PostgreSQL connection failed: {message}")
        self.backend_pid = int(_LIBPQ.PQbackendPID(handle))

    def __enter__(self) -> "_LibpqConnection":
        self.execute("BEGIN", ())
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc, traceback
        try:
            if exc_type is None:
                if self._barrier is not None:
                    self._barrier.ready.set()
                    if not self._barrier.release.wait(timeout=30):
                        self.execute("ROLLBACK", ())
                        raise AssertionError("timed out waiting to release the first Assignment transaction")
                self.execute("COMMIT", ())
            else:
                self.execute("ROLLBACK", ())
        finally:
            _LIBPQ.PQfinish(self._handle)
            self.closed = True

    def cursor(self) -> _LibpqCursor:
        return _LibpqCursor(self)

    def execute(self, sql: str, parameters: Sequence[object]) -> list[tuple[object, ...]]:
        translated, encoded = _bind_parameters(sql, parameters)
        values = None
        if encoded:
            values = (ctypes.c_char_p * len(encoded))(
                *[ctypes.c_char_p(value) if value is not None else None for value in encoded]
            )
        result = _LIBPQ.PQexecParams(
            self._handle,
            translated.encode(),
            len(encoded),
            None,
            values,
            None,
            None,
            0,
        )
        if not result:
            message = _LIBPQ.PQerrorMessage(self._handle).decode().strip()
            raise RuntimeError(f"libpq execution failed without a result: {message}")
        try:
            status = _LIBPQ.PQresultStatus(result)
            if status not in (_PGRES_COMMAND_OK, _PGRES_TUPLES_OK):
                message = _LIBPQ.PQresultErrorMessage(result).decode().strip()
                raise RuntimeError(f"PostgreSQL statement failed: {message}\nSQL: {translated}")
            row_count = _LIBPQ.PQntuples(result)
            column_count = _LIBPQ.PQnfields(result)
            column_oids = [_LIBPQ.PQftype(result, column) for column in range(column_count)]
            rows: list[tuple[object, ...]] = []
            for row_index in range(row_count):
                row: list[object] = []
                for column_index, oid in enumerate(column_oids):
                    if _LIBPQ.PQgetisnull(result, row_index, column_index):
                        row.append(None)
                    else:
                        raw = _LIBPQ.PQgetvalue(result, row_index, column_index)
                        row.append(_decode_field(oid, raw))
                rows.append(tuple(row))
            return rows
        finally:
            _LIBPQ.PQclear(result)


class _ConnectionFactory:
    """Capture backend identity and cleanup for one production Assignment writer."""

    def __init__(
        self,
        database_url: str,
        *,
        application_name: str,
        barrier: _CommitBarrier | None = None,
    ) -> None:
        self._database_url = database_url
        self._application_name = application_name
        self._barrier = barrier
        self.connected = threading.Event()
        self.connections: list[_LibpqConnection] = []

    def __call__(self) -> _LibpqConnection:
        connection = _LibpqConnection(
            self._database_url,
            application_name=self._application_name,
            barrier=self._barrier,
        )
        self.connections.append(connection)
        self.connected.set()
        return connection

    @property
    def backend_pid(self) -> int:
        if not self.connections:
            raise AssertionError("writer did not create a PostgreSQL connection")
        return self.connections[-1].backend_pid


@dataclass(slots=True)
class _WriterOutcome:
    result_id: UUID | None = None
    error: BaseException | None = None


def _psql(database_url: str, sql: str) -> str:
    """Execute setup/observation SQL with the repository's existing psql boundary."""
    completed = subprocess.run(
        ["psql", database_url, "-X", "-v", "ON_ERROR_STOP=1", "-Atqc", sql],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _apply_migrations(database_url: str) -> None:
    """Apply the exact migration stack required by the production People mutation path."""
    for migration in _MIGRATIONS:
        subprocess.run(
            ["psql", database_url, "-X", "-v", "ON_ERROR_STOP=1", "-f", migration],
            cwd=_REPO_ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )


@contextmanager
def _isolated_postgres() -> Iterator[str]:
    """Yield one isolated PostgreSQL 16 database using the Foundation image contract."""
    image = os.environ.get("ORGMETRA_POSTGRES_IMAGE")
    if not image:
        raise AssertionError("ORGMETRA_POSTGRES_IMAGE is required for fail-closed PostgreSQL acceptance")
    container_name = f"orgmetra-assignment-concurrency-{uuid4().hex}"
    subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            container_name,
            "--env",
            "POSTGRES_USER=orgmetra",
            "--env",
            "POSTGRES_PASSWORD=orgmetra",
            "--env",
            "POSTGRES_DB=orgmetra",
            "--publish",
            "127.0.0.1::5432",
            image,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    try:
        binding = subprocess.run(
            ["docker", "port", container_name, "5432/tcp"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        port = binding.rsplit(":", 1)[1]
        database_url = f"postgresql://orgmetra:orgmetra@127.0.0.1:{port}/orgmetra"
        for _ in range(60):
            ready = subprocess.run(
                ["psql", database_url, "-X", "-Atqc", "SELECT 1"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.1)
        else:
            logs = subprocess.run(
                ["docker", "logs", container_name],
                capture_output=True,
                text=True,
            ).stdout
            raise AssertionError(f"PostgreSQL acceptance container did not become ready:\n{logs}")
        _apply_migrations(database_url)
        yield database_url
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _conversion_event(*, audit_id: UUID, conversion_id: UUID, evidence_set_id: UUID) -> str:
    """Return one canonical, non-PII conversion event for a repository fixture."""
    return (
        '{"data":{"high_impact":true,"result_code":"worker_created"},'
        '"datacontenttype":"application/json",'
        f'"id":"{audit_id}",'
        '"orgmetraactor":"keyverse_subject:concurrency-fixture",'
        '"orgmetraconfirmation":"confirmation:concurrency-fixture",'
        f'"orgmetraevidence":"decision_evidence_set:{evidence_set_id}",'
        '"orgmetrapurpose":"talent_acquisition",'
        '"orgmetrareason":"candidate_hire_confirmed",'
        f'"orgmetratenant":"{_TENANT}",'
        '"source":"urn:orgmetra:talent_core","specversion":"1.0",'
        f'"subject":"candidate_worker_conversion_record:{conversion_id}",'
        '"time":"2026-08-17T05:01:00Z",'
        '"type":"orgmetra.candidate.worker_converted"}'
    )


def _seed_fixture(database_url: str, *, people: int, positions: int) -> None:
    """Seed right-cleared structural fixtures needed by Assignment acceptance."""
    organization = UUID("10000000-0000-7000-8000-000000000131")
    job = UUID("10000000-0000-7000-8000-000000000141")
    person_ids = (_PERSON_ONE, _PERSON_TWO)[:people]
    employment_ids = (_EMPLOYMENT_ONE, _EMPLOYMENT_TWO)[:people]
    position_ids = (_POSITION_ONE, _POSITION_TWO)[:positions]
    statements = [
        f"INSERT INTO tenant_record (tenant_record_id, tenant_reference) VALUES ('{_TENANT}', 'concurrency_fixture');",
        *[
            "INSERT INTO person_record (tenant_record_id, person_record_id, recorded_from) "
            f"VALUES ('{_TENANT}', '{person_id}', TIMESTAMPTZ '2026-08-17 04:50:00+00');"
            for person_id in person_ids
        ],
        *[
            "INSERT INTO employment_record (tenant_record_id, employment_record_id, person_record_id, recorded_from) "
            f"VALUES ('{_TENANT}', '{employment_id}', '{person_id}', TIMESTAMPTZ '2026-08-17 04:55:00+00');"
            for person_id, employment_id in zip(person_ids, employment_ids, strict=True)
        ],
        *[
            "INSERT INTO employment_record_version "
            "(tenant_record_id, employment_record_version_id, employment_record_id, employment_status_code, "
            "employment_concurrency_code, effective_from, recorded_from) "
            f"VALUES ('{_TENANT}', '10000000-0000-7000-8000-{200 + index:012d}', '{employment_id}', "
            "'active', 'concurrent', DATE '2026-08-17', TIMESTAMPTZ '2026-08-17 04:55:00+00');"
            for index, employment_id in enumerate(employment_ids, start=1)
        ],
        "INSERT INTO organization_unit (tenant_record_id, organization_unit_id, recorded_from) "
        f"VALUES ('{_TENANT}', '{organization}', TIMESTAMPTZ '2026-08-17 04:40:00+00');",
        "INSERT INTO job_profile (tenant_record_id, job_profile_id, recorded_from) "
        f"VALUES ('{_TENANT}', '{job}', TIMESTAMPTZ '2026-08-17 04:40:00+00');",
        *[
            "INSERT INTO position_record "
            "(tenant_record_id, position_record_id, organization_unit_id, job_profile_id, recorded_from) "
            f"VALUES ('{_TENANT}', '{position_id}', '{organization}', '{job}', TIMESTAMPTZ '2026-08-17 04:50:00+00');"
            for position_id in position_ids
        ],
        *[
            "INSERT INTO position_record_version "
            "(tenant_record_id, position_record_version_id, position_record_id, position_status_code, "
            "effective_from, recorded_from) "
            f"VALUES ('{_TENANT}', '10000000-0000-7000-8000-{300 + index:012d}', '{position_id}', "
            "'open', DATE '2026-08-17', TIMESTAMPTZ '2026-08-17 04:50:00+00');"
            for index, position_id in enumerate(position_ids, start=1)
        ],
    ]
    for index, (person_id, employment_id) in enumerate(zip(person_ids, employment_ids, strict=True), start=1):
        candidate_id = UUID(f"10000000-0000-7000-8000-{400 + index:012d}")
        evidence_set_id = UUID(f"10000000-0000-7000-8000-{500 + index:012d}")
        evidence_member_id = UUID(f"10000000-0000-7000-8000-{600 + index:012d}")
        decision_id = UUID(f"10000000-0000-7000-8000-{700 + index:012d}")
        audit_id = UUID(f"10000000-0000-7000-8000-{800 + index:012d}")
        outbox_id = UUID(f"10000000-0000-7000-8000-{900 + index:012d}")
        conversion_id = UUID(f"10000000-0000-7000-8000-{1000 + index:012d}")
        event = _conversion_event(
            audit_id=audit_id,
            conversion_id=conversion_id,
            evidence_set_id=evidence_set_id,
        ).replace("'", "''")
        statements.extend(
            [
                "INSERT INTO candidate_profile "
                "(tenant_record_id, candidate_profile_id, application_status_code, recorded_from) "
                f"VALUES ('{_TENANT}', '{candidate_id}', 'offer', TIMESTAMPTZ '2026-08-17 04:45:00+00');",
                "INSERT INTO decision_evidence_set "
                "(tenant_record_id, decision_evidence_set_id, evidence_set_version_code, digest_algorithm_code, created_at) "
                f"VALUES ('{_TENANT}', '{evidence_set_id}', 'concurrency_fixture_v1', 'sha256', "
                "TIMESTAMPTZ '2026-08-17 04:56:00+00');",
                "INSERT INTO selection_decision_evidence "
                "(tenant_record_id, selection_decision_evidence_id, decision_evidence_set_id, "
                "evidence_reference, evidence_version_code, recorded_at) "
                f"VALUES ('{_TENANT}', '{evidence_member_id}', '{evidence_set_id}', "
                f"'structured_interview:concurrency_{index}', 'rubric_v1', TIMESTAMPTZ '2026-08-17 04:57:00+00');",
                "INSERT INTO selection_decision "
                "(tenant_record_id, selection_decision_id, candidate_profile_id, job_profile_id, "
                "decision_evidence_set_id, actor_reference, purpose_code, decision_code, decision_reason, "
                "confirmation_reference, decided_at, recorded_at) "
                f"VALUES ('{_TENANT}', '{decision_id}', '{candidate_id}', '{job}', '{evidence_set_id}', "
                "'keyverse_subject:concurrency-fixture', 'talent_acquisition', 'hire', "
                "'Right-cleared concurrency acceptance fixture', 'confirmation:concurrency-fixture', "
                "TIMESTAMPTZ '2026-08-17 04:59:00+00', TIMESTAMPTZ '2026-08-17 05:00:00+00');",
                "SELECT record_audit_outbox_event("
                f"'{_TENANT}'::uuid, '{audit_id}'::uuid, '{outbox_id}'::uuid, '{event}', "
                f"encode(digest(convert_to('{event}', 'UTF8'), 'sha256'), 'hex'), 'talent_event_sink');",
                "INSERT INTO candidate_worker_conversion_record "
                "(tenant_record_id, candidate_worker_conversion_record_id, candidate_profile_id, person_record_id, "
                "employment_record_id, selection_decision_id, audit_event_record_id, effective_from, recorded_from) "
                f"VALUES ('{_TENANT}', '{conversion_id}', '{candidate_id}', '{person_id}', '{employment_id}', "
                f"'{decision_id}', '{audit_id}', DATE '2026-08-17', TIMESTAMPTZ '2026-08-17 05:02:00+00');",
            ]
        )
    _psql(database_url, "\n".join(statements))


def _assignment_command(
    *,
    assignment_id: UUID,
    employment_id: UUID,
    person_id: UUID,
    position_id: UUID,
    allocation: Decimal,
    suffix: int,
) -> AssignmentMutationCommand:
    """Build one governed Assignment command with unique atomic-evidence identities."""
    return AssignmentMutationCommand(
        tenant_record_id=_TENANT,
        employment_record_id=employment_id,
        person_record_id=person_id,
        position_record_id=position_id,
        assignment_record_id=assignment_id,
        audit_event_record_id=UUID(f"10000000-0000-7000-8001-{1000 + suffix:012d}"),
        outbox_delivery_record_id=UUID(f"10000000-0000-7000-8001-{2000 + suffix:012d}"),
        allocation_ratio=allocation,
        effective_from=_ASSIGNMENT_EFFECTIVE_FROM,
        confirmation_reference=f"human_confirmation:concurrency-{suffix}",
        evidence_version_code="decision_evidence_set:v1",
        idempotency_key=f"assignment-concurrency-key-{suffix:02d}",
    )


def _authorization(assignment_id: UUID) -> AuthorizationDecision:
    """Bind the exact Assignment target to the purpose-scoped production adapter call."""
    return AuthorizationDecision(
        allowed=True,
        tenant_record_id=_TENANT,
        actor_reference="keyverse_subject:concurrency-operator",
        resource_reference=f"assignment_record:{assignment_id.hex}",
        policy_version_code="people-mutation-v1",
        purpose_code="workforce_admin",
        operation_code="create_record",
        resource_kind="assignment_record",
        requested_fields=frozenset({"assignment_record"}),
        authorized_fields=frozenset({"assignment_record"}),
        reason_code="access_permitted",
        next_action="continue",
    )


def _run_writer(
    *, factory: _ConnectionFactory, command: AssignmentMutationCommand, outcome: _WriterOutcome
) -> None:
    """Execute one production Assignment mutation and retain its terminal result."""
    try:
        result = PostgresPeopleMutationPort(factory).create_assignment(
            command=command,
            authorization=_authorization(command.assignment_record_id),
        )
        outcome.result_id = result.assignment_record_id
    except BaseException as error:
        outcome.error = error


def _assert_database_lock_wait(database_url: str, *, blocked_pid: int, blocker_pid: int) -> None:
    """Prove PostgreSQL itself reports the second backend blocked by the first."""
    for _ in range(300):
        observation = _psql(
            database_url,
            "SELECT concat_ws('|', coalesce(wait_event_type, ''), coalesce(wait_event, ''), "
            f"({blocker_pid} = ANY(pg_blocking_pids({blocked_pid})))::text) "
            f"FROM pg_stat_activity WHERE pid = {blocked_pid};",
        )
        fields = observation.split("|") if observation else []
        if len(fields) == 3 and fields[0] == "Lock" and fields[2] == "true":
            return
        time.sleep(0.01)
    raise AssertionError(
        f"backend {blocked_pid} never exposed a DB-visible lock wait on blocker {blocker_pid}"
    )


def _assert_atomic_assignment_state(
    database_url: str,
    *,
    employment_id: UUID | None = None,
    position_id: UUID | None = None,
) -> None:
    """Require one committed Assignment and no audit/outbox/idempotency residue from rejection."""
    predicate = ""
    if employment_id is not None:
        predicate = f" AND employment_record_id = '{employment_id}'::uuid"
    if position_id is not None:
        predicate = f" AND position_record_id = '{position_id}'::uuid"
    assignment_state = _psql(
        database_url,
        "SELECT concat_ws('|', count(*), coalesce(sum(allocation_ratio), 0)::text) "
        f"FROM assignment_record WHERE tenant_record_id = '{_TENANT}'::uuid{predicate};",
    )
    assert assignment_state == "1|0.7500"
    evidence_state = _psql(
        database_url,
        "SELECT concat_ws('|', "
        "(SELECT count(*) FROM audit_event_record WHERE canonical_event_json::jsonb ->> 'type' = "
        "'orgmetra.people.assignment_created'), "
        "(SELECT count(*) FROM outbox_delivery_record AS outbox JOIN audit_event_record AS audit "
        "ON audit.tenant_record_id = outbox.tenant_record_id "
        "AND audit.audit_event_record_id = outbox.audit_event_record_id "
        "WHERE audit.canonical_event_json::jsonb ->> 'type' = 'orgmetra.people.assignment_created'), "
        "(SELECT count(*) FROM people_mutation_idempotency_record WHERE command_route = 'assignment-records'));",
    )
    assert evidence_state == "1|1|1"


def _assert_connection_cleanup(database_url: str, factories: Sequence[_ConnectionFactory]) -> None:
    """Require client and server connection cleanup after both concurrent writers terminate."""
    assert all(connection.closed for factory in factories for connection in factory.connections)
    active = _psql(
        database_url,
        "SELECT count(*) FROM pg_stat_activity "
        "WHERE application_name LIKE 'orgmetra-assignment-concurrency-writer-%';",
    )
    assert active == "0"


def _exercise_conflict(
    database_url: str,
    *,
    first_command: AssignmentMutationCommand,
    second_command: AssignmentMutationCommand,
    expected_error: str,
    employment_id: UUID | None = None,
    position_id: UUID | None = None,
) -> None:
    """Hold writer A at COMMIT, prove writer B waits, then verify post-commit rejection."""
    barrier = _CommitBarrier.create()
    first_factory = _ConnectionFactory(
        database_url,
        application_name="orgmetra-assignment-concurrency-writer-a",
        barrier=barrier,
    )
    second_factory = _ConnectionFactory(
        database_url,
        application_name="orgmetra-assignment-concurrency-writer-b",
    )
    first_outcome = _WriterOutcome()
    second_outcome = _WriterOutcome()
    first = threading.Thread(
        target=_run_writer,
        kwargs={"factory": first_factory, "command": first_command, "outcome": first_outcome},
        daemon=True,
    )
    second = threading.Thread(
        target=_run_writer,
        kwargs={"factory": second_factory, "command": second_command, "outcome": second_outcome},
        daemon=True,
    )
    first.start()
    assert barrier.ready.wait(timeout=30), "first Assignment writer did not reach its pre-COMMIT barrier"
    assert first_outcome.error is None
    second.start()
    assert second_factory.connected.wait(timeout=30), "second Assignment writer did not connect"
    _assert_database_lock_wait(
        database_url,
        blocked_pid=second_factory.backend_pid,
        blocker_pid=first_factory.backend_pid,
    )
    barrier.release.set()
    first.join(timeout=30)
    second.join(timeout=30)
    assert not first.is_alive() and not second.is_alive()
    assert first_outcome.error is None
    assert first_outcome.result_id == first_command.assignment_record_id
    assert second_outcome.result_id is None
    assert isinstance(second_outcome.error, PeopleMutationIntegrityError)
    assert expected_error in str(second_outcome.error)
    _assert_atomic_assignment_state(
        database_url,
        employment_id=employment_id,
        position_id=position_id,
    )
    _assert_connection_cleanup(database_url, (first_factory, second_factory))


def test_same_employment_different_positions_serializes_on_converted_worker() -> None:
    """A stale Employment portfolio cannot cross the converted-worker conflict boundary."""
    with _isolated_postgres() as database_url:
        _seed_fixture(database_url, people=1, positions=2)
        _exercise_conflict(
            database_url,
            first_command=_assignment_command(
                assignment_id=UUID("10000000-0000-7000-8002-000000000001"),
                employment_id=_EMPLOYMENT_ONE,
                person_id=_PERSON_ONE,
                position_id=_POSITION_ONE,
                allocation=Decimal("0.7500"),
                suffix=1,
            ),
            second_command=_assignment_command(
                assignment_id=UUID("10000000-0000-7000-8002-000000000002"),
                employment_id=_EMPLOYMENT_ONE,
                person_id=_PERSON_ONE,
                position_id=_POSITION_TWO,
                allocation=Decimal("0.5000"),
                suffix=2,
            ),
            expected_error="Visible allocations for one employment exceed 1.0000.",
            employment_id=_EMPLOYMENT_ONE,
        )


def test_different_employments_same_position_serializes_on_position_root() -> None:
    """A stale seat-capacity snapshot cannot cross the Position conflict boundary."""
    with _isolated_postgres() as database_url:
        _seed_fixture(database_url, people=2, positions=1)
        _exercise_conflict(
            database_url,
            first_command=_assignment_command(
                assignment_id=UUID("10000000-0000-7000-8002-000000000003"),
                employment_id=_EMPLOYMENT_ONE,
                person_id=_PERSON_ONE,
                position_id=_POSITION_ONE,
                allocation=Decimal("0.7500"),
                suffix=3,
            ),
            second_command=_assignment_command(
                assignment_id=UUID("10000000-0000-7000-8002-000000000004"),
                employment_id=_EMPLOYMENT_TWO,
                person_id=_PERSON_TWO,
                position_id=_POSITION_ONE,
                allocation=Decimal("0.5000"),
                suffix=4,
            ),
            expected_error="Visible allocations for one position exceed 1.0000.",
            position_id=_POSITION_ONE,
        )
