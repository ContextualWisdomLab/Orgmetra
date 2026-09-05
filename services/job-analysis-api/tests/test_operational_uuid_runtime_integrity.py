"""Runtime-integrity contracts for operational UUID evidence boundaries."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_hris_kernel import JobAnalysisSnapshot

from orgmetra_job_analysis_api.snapshot import (
    read_job_analysis_snapshot,
    validate_operational_uuid,
)
from fixtures import (
    ANALYSIS,
    JOB,
    TENANT,
    clinical_psychologist_snapshot,
    read_policy,
    read_principal,
)


class _SpoofedHexUUID(UUID):
    """Expose a reviewed resource hex while retaining another UUID value."""

    @property
    def hex(self) -> str:
        """Return the authorized analysis identifier instead of stored identity."""
        return ANALYSIS.hex


class _RecordingReadPort:
    """Record protected-read calls so validation ordering is observable."""

    def __init__(self, result: JobAnalysisSnapshot) -> None:
        self.result = result
        self.calls: list[tuple[UUID, UUID]] = []

    def read_snapshot(
        self,
        *,
        tenant_record_id: UUID,
        analysis_record_id: UUID,
    ) -> JobAnalysisSnapshot:
        """Return deterministic evidence after recording the requested identity."""
        self.calls.append((tenant_record_id, analysis_record_id))
        return self.result


class OperationalUUIDRuntimeIntegrityTests(unittest.TestCase):
    """Require one detached exact UUID snapshot before authority or persistence use."""

    def test_uuid_subclass_cannot_spoof_authorized_resource_before_read_port(self) -> None:
        """Reject a UUID subtype whose public hex disagrees with its stored identity."""
        spoofed = _SpoofedHexUUID(str(JOB))
        port = _RecordingReadPort(clinical_psychologist_snapshot())

        with self.assertRaises(ValueError):
            read_job_analysis_snapshot(
                principal=read_principal(),
                tenant_record_id=TENANT,
                analysis_record_id=spoofed,
                purpose_code="job_analysis_read",
                policy=read_policy(),
                read_port=port,
            )

        self.assertEqual(port.calls, [])

    def test_validated_uuid_is_detached_from_caller_owned_alias(self) -> None:
        """Mutation of the caller UUID after validation cannot rewrite accepted evidence."""
        caller_owned = UUID(str(ANALYSIS))

        accepted = validate_operational_uuid("analysis_record_id", caller_owned)
        object.__setattr__(caller_owned, "int", JOB.int)

        self.assertIs(type(accepted), UUID)
        self.assertIsNot(accepted, caller_owned)
        self.assertEqual(accepted, ANALYSIS)


if __name__ == "__main__":
    unittest.main()
