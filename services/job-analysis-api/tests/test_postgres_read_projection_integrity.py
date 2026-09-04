"""Regression coverage for fixed PostgreSQL read projections and target identity."""

from __future__ import annotations

from collections.abc import Sequence
import unittest
from uuid import UUID

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import JobAnalysisIntegrityError
from fixtures import ANALYSIS, OTHER_TENANT, TENANT
from test_postgres import (
    FakeConnection,
    FakeCursor,
    _header_row,
    _ksao_rows,
    _link_rows,
    _task_rows,
)


class _EqualityForgedUUID(UUID):
    """Model DB-returned UUID evidence that forges equality before validation."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False


class _BrokenSequence(Sequence[object]):
    """Model a DB-API row sequence that fails while values are detached."""

    def __len__(self) -> int:
        return 1

    def __getitem__(self, index: int) -> object:
        raise TypeError("broken row sequence")


class PostgresReadProjectionIntegrityTests(unittest.TestCase):
    """Require every fixed read projection to match its SQL row contract."""

    def _read(self, script: list[object]) -> None:
        cursor = FakeCursor(script)
        port = PostgresJobAnalysisPort(lambda: FakeConnection(cursor))
        port.read_snapshot(tenant_record_id=TENANT, analysis_record_id=ANALYSIS)

    def _valid_script(
        self,
        *,
        headers: object | None = None,
        tasks: object | None = None,
        ksaos: object | None = None,
        links: object | None = None,
    ) -> list[object]:
        return [
            None,
            None,
            [_header_row()] if headers is None else headers,
            _task_rows() if tasks is None else tasks,
            _ksao_rows() if ksaos is None else ksaos,
            _link_rows() if links is None else links,
        ]

    def test_read_rejects_invalid_snapshot_header_shape(self) -> None:
        header = _header_row()
        malformed_rows = (
            object(),
            _BrokenSequence(),
            header[:-1],
            header + ("surplus",),
            (value for value in header),
        )
        for row in malformed_rows:
            with self.subTest(row_type=type(row).__name__):
                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "job_analysis_snapshot row has invalid shape",
                ):
                    self._read(self._valid_script(headers=[row]))

    def test_read_rejects_invalid_task_projection_shape(self) -> None:
        canonical = _task_rows()
        malformed_rows = (
            object(),
            canonical[0][:-1],
            canonical[0] + ("surplus",),
            (value for value in canonical[0]),
        )
        for row in malformed_rows:
            with self.subTest(row_type=type(row).__name__):
                rows = list(canonical)
                rows[0] = row  # type: ignore[assignment]
                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "job_analysis_task_item row has invalid shape",
                ):
                    self._read(self._valid_script(tasks=rows))

    def test_read_rejects_invalid_ksao_projection_shape(self) -> None:
        canonical = _ksao_rows()
        malformed_rows = (
            object(),
            canonical[0][:-1],
            canonical[0] + ("surplus",),
            (value for value in canonical[0]),
        )
        for row in malformed_rows:
            with self.subTest(row_type=type(row).__name__):
                rows = list(canonical)
                rows[0] = row  # type: ignore[assignment]
                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "job_analysis_ksao_item row has invalid shape",
                ):
                    self._read(self._valid_script(ksaos=rows))

    def test_read_rejects_invalid_link_projection_shape(self) -> None:
        canonical = _link_rows()
        malformed_rows = (
            object(),
            canonical[0][:-1],
            canonical[0] + ("surplus",),
            (value for value in canonical[0]),
        )
        for row in malformed_rows:
            with self.subTest(row_type=type(row).__name__):
                rows = list(canonical)
                rows[0] = row  # type: ignore[assignment]
                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "job_analysis_task_ksao_link row has invalid shape",
                ):
                    self._read(self._valid_script(links=rows))

    def test_read_exact_validates_returned_target_identity_before_equality(self) -> None:
        forged_tenant = _EqualityForgedUUID(str(OTHER_TENANT))
        forged_analysis = _EqualityForgedUUID("0198a412-6000-7000-8000-000000000499")
        cases = (
            (
                _header_row(tenant_record_id=forged_tenant),
                "job_analysis_snapshot.tenant_record_id row has invalid identity",
            ),
            (
                _header_row(analysis_record_id=forged_analysis),
                "job_analysis_snapshot.analysis_record_id row has invalid identity",
            ),
        )
        for header, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(JobAnalysisIntegrityError, expected):
                    self._read(self._valid_script(headers=[header]))


if __name__ == "__main__":
    unittest.main()