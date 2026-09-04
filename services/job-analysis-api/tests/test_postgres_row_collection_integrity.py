"""Regression coverage for inert PostgreSQL fixed-projection row collections."""

from __future__ import annotations

import unittest

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import JobAnalysisIntegrityError
from fixtures import ANALYSIS, TENANT
from test_postgres import (
    FakeConnection,
    FakeCursor,
    _header_row,
    _ksao_rows,
    _link_rows,
    _task_rows,
)


class _ExecutableRowCollection(list[object]):
    """Fail if database collection hooks run before the durable boundary."""

    def __bool__(self) -> bool:
        raise AssertionError("row collection truthiness executed")

    def __len__(self) -> int:
        raise AssertionError("row collection length executed")

    def __getitem__(self, index: object) -> object:
        raise AssertionError("row collection indexing executed")

    def __iter__(self):
        raise AssertionError("row collection iteration executed")


class _CollectionCursor(FakeCursor):
    """Return one executable outer collection at a selected fetch boundary."""

    def __init__(self, script: list[object], *, dangerous_fetch: str) -> None:
        super().__init__(script)
        self.dangerous_fetch = dangerous_fetch
        self.fetchall_count = 0

    def fetchmany(self, size: int) -> object:
        if self.dangerous_fetch == "headers":
            return _ExecutableRowCollection([_header_row()])
        return super().fetchmany(size)

    def fetchall(self) -> object:
        self.fetchall_count += 1
        if self.dangerous_fetch == "tasks" and self.fetchall_count == 1:
            return _ExecutableRowCollection(_task_rows())
        return super().fetchall()


class PostgresRowCollectionIntegrityTests(unittest.TestCase):
    """Require inert collection containers before any row access occurs."""

    @staticmethod
    def _script() -> list[object]:
        return [
            None,
            None,
            [_header_row()],
            _task_rows(),
            _ksao_rows(),
            _link_rows(),
        ]

    def _read(self, *, dangerous_fetch: str) -> None:
        cursor = _CollectionCursor(self._script(), dangerous_fetch=dangerous_fetch)
        port = PostgresJobAnalysisPort(lambda: FakeConnection(cursor))
        port.read_snapshot(tenant_record_id=TENANT, analysis_record_id=ANALYSIS)

    def test_read_rejects_executable_header_collection_before_hooks(self) -> None:
        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "job_analysis_snapshot row collection has invalid shape",
        ):
            self._read(dangerous_fetch="headers")

    def test_read_rejects_executable_child_collection_before_iteration(self) -> None:
        with self.assertRaisesRegex(
            JobAnalysisIntegrityError,
            "job_analysis_task_item row collection has invalid shape",
        ):
            self._read(dangerous_fetch="tasks")


if __name__ == "__main__":
    unittest.main()
