"""Regression for Psycopg ZoneInfo timestamps crossing the governed read boundary."""

from __future__ import annotations

import unittest
from zoneinfo import ZoneInfo

from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import read_job_analysis_snapshot

from fixtures import ANALYSIS, RECORDED_AT, TENANT, read_policy, read_principal
from test_postgres import (
    FakeConnection,
    FakeCursor,
    _header_row,
    _ksao_rows,
    _link_rows,
    _task_rows,
)


class PostgresReadServiceZoneInfoCompatibilityTests(unittest.TestCase):
    """Keep accepted Psycopg timestamptz evidence valid through customer export."""

    def test_read_accepts_psycopg_zoneinfo_timestamp_through_governed_export(self) -> None:
        """A standard-library ZoneInfo row accepted by the port must remain readable."""
        header = _header_row()
        zoneinfo_recorded_at = RECORDED_AT.astimezone(ZoneInfo("Asia/Seoul"))
        header = header[:6] + (zoneinfo_recorded_at,) + header[7:]
        cursor = FakeCursor(
            [
                None,
                None,
                [header],
                _task_rows(),
                _ksao_rows(),
                _link_rows(),
            ]
        )
        port = PostgresJobAnalysisPort(lambda: FakeConnection(cursor))

        view = read_job_analysis_snapshot(
            principal=read_principal(),
            tenant_record_id=TENANT,
            analysis_record_id=ANALYSIS,
            purpose_code="job_analysis_read",
            policy=read_policy(),
            read_port=port,
        )

        self.assertEqual(
            view.snapshot["recorded_at"],
            RECORDED_AT.isoformat().replace("+00:00", "Z"),
        )


if __name__ == "__main__":
    unittest.main()
