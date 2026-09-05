"""Regression contract for the bound PostgreSQL connection capability."""

from __future__ import annotations

from uuid import UUID

from orgmetra_workforce_validation_api.postgres_registry import PostgresValidityStudyReadPort

TENANT = UUID("10000000-0000-7000-8000-000000000001")
STUDY = UUID("00000000-0000-7000-8000-0000000000c1")


class _Cursor:
    """Provide the smallest DB-API cursor needed by an empty registry read."""

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback

    def execute(self, sql: str, params: object = None) -> None:
        del sql, params

    def fetchmany(self, size: int) -> list[object]:
        del size
        return []


class _Connection:
    """Expose one deterministic cursor through the connection context protocol."""

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback

    def cursor(self) -> _Cursor:
        return _Cursor()


class _Factory:
    """Count connection acquisition without performing external I/O."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> _Connection:
        self.calls += 1
        return _Connection()


ORIGINAL_FACTORY = _Factory()
REPLACEMENT_FACTORY = _Factory()


class _SwitchingPort(PostgresValidityStudyReadPort):
    """Present a different dynamic property than the callable stored at construction."""

    @property
    def connection_factory(self) -> _Factory:
        return REPLACEMENT_FACTORY


def test_inherited_read_uses_exact_factory_stored_by_base_constructor() -> None:
    """A subclass property must not replace the already-validated executable dependency."""
    ORIGINAL_FACTORY.calls = 0
    REPLACEMENT_FACTORY.calls = 0
    port = _SwitchingPort(connection_factory=ORIGINAL_FACTORY)

    assert port.read_validity_study(tenant_record_id=TENANT, validity_study_id=STUDY) is None
    assert ORIGINAL_FACTORY.calls == 1
    assert REPLACEMENT_FACTORY.calls == 0
