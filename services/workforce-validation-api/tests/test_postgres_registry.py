"""PostgreSQL adapter contract for the workforce-validation registry owner."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from orgmetra_workforce_validation_api.postgres_registry import PostgresValidityStudyReadPort
from orgmetra_workforce_validation_api.registry import ValidityStudyIntegrityError, ValidityStudyRecord

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")
CRITERION = UUID("00000000-0000-7000-8000-0000000000b1")
RECORDED_FROM = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _row(
    *,
    tenant_record_id: UUID = TENANT,
    validity_study_id: UUID = STUDY,
    study_status_code: str = "active",
) -> tuple[object, ...]:
    return (
        tenant_record_id,
        validity_study_id,
        CRITERION,
        study_status_code,
        RECORDED_FROM,
        None,
    )


class _Cursor:
    """Record exact DB-API calls and return a bounded row set."""

    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, object]] = []
        self.fetch_size: int | None = None

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback

    def execute(self, sql: str, params: object = None) -> None:
        self.calls.append((sql, params))

    def fetchmany(self, size: int) -> list[object]:
        self.fetch_size = size
        return self.rows[:size]


class _Connection:
    """Provide one deterministic cursor through a context-manager connection."""

    def __init__(self, cursor: _Cursor) -> None:
        self.cursor_instance = cursor

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback

    def cursor(self) -> _Cursor:
        return self.cursor_instance


class _Factory:
    """Expose whether executable connection acquisition was reached."""

    def __init__(self, rows: list[object], callback=None) -> None:
        self.cursor = _Cursor(rows)
        self.callback = callback
        self.calls = 0

    def __call__(self) -> _Connection:
        self.calls += 1
        if self.callback is not None:
            self.callback()
        return _Connection(self.cursor)


def test_constructor_rejects_non_callable_factory() -> None:
    with pytest.raises(TypeError, match="connection_factory must be callable"):
        PostgresValidityStudyReadPort(connection_factory=object())  # type: ignore[arg-type]


def test_connection_factory_cannot_be_replaced_after_port_validation() -> None:
    original_factory = _Factory([])
    replacement_factory = _Factory([])
    port = PostgresValidityStudyReadPort(connection_factory=original_factory)

    with pytest.raises(AttributeError):
        object.__setattr__(port, "connection_factory", replacement_factory)

    assert port.connection_factory is original_factory
    assert port.read_validity_study(tenant_record_id=TENANT, validity_study_id=STUDY) is None
    assert original_factory.calls == 1
    assert replacement_factory.calls == 0


def test_invalid_target_is_rejected_before_connection_acquisition() -> None:
    factory = _Factory([])
    port = PostgresValidityStudyReadPort(connection_factory=factory)

    with pytest.raises(ValueError, match="tenant_record_id must be an exact operational UUID"):
        port.read_validity_study(tenant_record_id="not-a-uuid", validity_study_id=STUDY)  # type: ignore[arg-type]

    assert factory.calls == 0


def test_empty_read_is_tenant_bound_read_only_and_schema_qualified() -> None:
    factory = _Factory([])
    port = PostgresValidityStudyReadPort(connection_factory=factory)

    assert port.read_validity_study(tenant_record_id=TENANT, validity_study_id=STUDY) is None

    assert factory.cursor.fetch_size == 2
    assert len(factory.cursor.calls) == 3
    read_only_sql, read_only_params = factory.cursor.calls[0]
    tenant_sql, tenant_params = factory.cursor.calls[1]
    registry_sql, registry_params = factory.cursor.calls[2]
    assert read_only_sql == "SET TRANSACTION READ ONLY"
    assert read_only_params is None
    assert tenant_sql == "SELECT pg_catalog.set_config('orgmetra.tenant_record_id', %s, true)"
    assert tenant_params == (str(TENANT),)
    assert "FROM workforce_validation.validity_study" in registry_sql
    assert "public.validity_study" not in registry_sql
    assert registry_params == (TENANT, STUDY)


def test_multiple_rows_fail_closed() -> None:
    port = PostgresValidityStudyReadPort(connection_factory=_Factory([_row(), _row()]))

    with pytest.raises(ValidityStudyIntegrityError, match="multiple current validity-study rows"):
        port.read_validity_study(tenant_record_id=TENANT, validity_study_id=STUDY)


@pytest.mark.parametrize(
    "row",
    [
        list(_row()),
        _row()[:-1],
    ],
)
def test_noncanonical_row_container_fails_closed(row: object) -> None:
    port = PostgresValidityStudyReadPort(connection_factory=_Factory([row]))

    with pytest.raises(ValidityStudyIntegrityError, match="non-canonical validity-study row"):
        port.read_validity_study(tenant_record_id=TENANT, validity_study_id=STUDY)


def test_invalid_row_scalar_is_reported_as_persistence_integrity_failure() -> None:
    port = PostgresValidityStudyReadPort(
        connection_factory=_Factory([_row(study_status_code="NOT_CANONICAL")])
    )

    with pytest.raises(ValidityStudyIntegrityError, match="invalid validity-study row"):
        port.read_validity_study(tenant_record_id=TENANT, validity_study_id=STUDY)


@pytest.mark.parametrize(
    "row",
    [
        _row(tenant_record_id=UUID("10000000-0000-7000-8000-000000000002")),
        _row(validity_study_id=UUID("00000000-0000-7000-8000-0000000000c2")),
    ],
)
def test_foreign_row_target_fails_closed(row: tuple[object, ...]) -> None:
    port = PostgresValidityStudyReadPort(connection_factory=_Factory([row]))

    with pytest.raises(ValidityStudyIntegrityError, match="another target"):
        port.read_validity_study(tenant_record_id=TENANT, validity_study_id=STUDY)


def test_valid_row_reconstructs_owner_record() -> None:
    port = PostgresValidityStudyReadPort(connection_factory=_Factory([_row()]))

    record = port.read_validity_study(tenant_record_id=TENANT, validity_study_id=STUDY)

    assert type(record) is ValidityStudyRecord
    assert record.tenant_record_id == TENANT
    assert record.validity_study_id == STUDY
    assert record.criterion_blueprint_id == CRITERION
    assert record.study_status_code == "active"
    assert record.recorded_from == RECORDED_FROM
    assert record.recorded_to is None


def test_connection_callback_cannot_switch_snapshotted_target() -> None:
    tenant = UUID("10000000-0000-7000-8000-000000000001")
    study = UUID("00000000-0000-7000-8000-0000000000c1")
    original_tenant_int = tenant.int
    original_study_int = study.int
    other_tenant = UUID("10000000-0000-7000-8000-000000000002")
    other_study = UUID("00000000-0000-7000-8000-0000000000c2")

    def mutate_retained_inputs() -> None:
        object.__setattr__(tenant, "int", other_tenant.int)
        object.__setattr__(study, "int", other_study.int)

    factory = _Factory(
        [
            _row(
                tenant_record_id=UUID(int=original_tenant_int),
                validity_study_id=UUID(int=original_study_int),
            )
        ],
        callback=mutate_retained_inputs,
    )
    port = PostgresValidityStudyReadPort(connection_factory=factory)

    record = port.read_validity_study(tenant_record_id=tenant, validity_study_id=study)

    _, tenant_params = factory.cursor.calls[1]
    _, registry_params = factory.cursor.calls[2]
    assert tenant_params == (str(UUID(int=original_tenant_int)),)
    assert registry_params == (UUID(int=original_tenant_int), UUID(int=original_study_int))
    assert record is not None
    assert record.tenant_record_id == UUID(int=original_tenant_int)
    assert record.validity_study_id == UUID(int=original_study_int)
