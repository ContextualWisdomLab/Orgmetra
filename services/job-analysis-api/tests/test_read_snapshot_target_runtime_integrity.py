"""Regression contract for inert Job Analysis read-target evidence."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_hris_kernel import JobAnalysisSnapshot
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIntegrityError,
    read_job_analysis_snapshot,
)

from fixtures import (
    ANALYSIS,
    TENANT,
    clinical_psychologist_snapshot,
    read_policy,
    read_principal,
)


class _ExecutableUUID(UUID):
    """Raise if a returned durable identity executes before exact validation."""

    def __eq__(self, other: object) -> bool:
        """Fail if target matching invokes caller-controlled equality."""
        raise AssertionError("returned UUID equality executed")

    def __ne__(self, other: object) -> bool:
        """Fail if target matching invokes caller-controlled inequality."""
        raise AssertionError("returned UUID inequality executed")

    def __str__(self) -> str:
        """Fail if export stringifies caller-controlled identity evidence."""
        raise AssertionError("returned UUID stringification executed")


class _ReadPort:
    """Return one configured exact snapshot from the application read boundary."""

    def __init__(self, snapshot: JobAnalysisSnapshot) -> None:
        self.snapshot = snapshot

    def read_snapshot(
        self,
        *,
        tenant_record_id: UUID,
        analysis_record_id: UUID,
    ) -> JobAnalysisSnapshot:
        """Return the configured snapshot without normalizing its live fields."""
        return self.snapshot


class ReadSnapshotTargetRuntimeIntegrityTests(unittest.TestCase):
    """Reject executable returned target identity before equality or export."""

    def test_returned_target_uuid_subtype_fails_before_runtime_hooks(self) -> None:
        """Treat low-level rewritten tenant/analysis identities as corrupt evidence."""
        cases = (
            ("tenant_record_id", TENANT),
            ("analysis_record_id", ANALYSIS),
        )
        for field_name, authorized_value in cases:
            with self.subTest(field_name=field_name):
                snapshot = clinical_psychologist_snapshot()
                object.__setattr__(
                    snapshot,
                    field_name,
                    _ExecutableUUID(str(authorized_value)),
                )

                with self.assertRaisesRegex(
                    JobAnalysisIntegrityError,
                    "resolved snapshot target identity",
                ):
                    read_job_analysis_snapshot(
                        principal=read_principal(),
                        tenant_record_id=TENANT,
                        analysis_record_id=ANALYSIS,
                        purpose_code="job_analysis_read",
                        policy=read_policy(),
                        read_port=_ReadPort(snapshot),
                    )


if __name__ == "__main__":
    unittest.main()
