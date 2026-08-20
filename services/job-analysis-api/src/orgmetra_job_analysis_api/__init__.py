"""Governed write and read contracts for persisted job-analysis snapshots."""

from orgmetra_job_analysis_api.auth import (
    AuthenticatedPrincipal,
    AuthenticationFailed,
    TokenAuthenticator,
    extract_bearer_token,
)
from orgmetra_job_analysis_api.authorization import authorize_resource_fields
from orgmetra_job_analysis_api.http import JobAnalysisAsgiApp
from orgmetra_job_analysis_api.postgres import PostgresJobAnalysisPort
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIdempotencyConflict,
    JobAnalysisIntegrityError,
    JobAnalysisReadPort,
    JobAnalysisScopeMissing,
    JobAnalysisSnapshotNotFound,
    JobAnalysisWritePort,
    PersistedJobAnalysisView,
    persist_job_analysis_snapshot,
    read_job_analysis_snapshot,
    snapshot_from_document,
)

__all__ = [
    "AuthenticatedPrincipal",
    "AuthenticationFailed",
    "JobAnalysisAsgiApp",
    "JobAnalysisIdempotencyConflict",
    "JobAnalysisIntegrityError",
    "JobAnalysisReadPort",
    "JobAnalysisScopeMissing",
    "JobAnalysisSnapshotNotFound",
    "JobAnalysisWritePort",
    "PersistedJobAnalysisView",
    "PostgresJobAnalysisPort",
    "TokenAuthenticator",
    "authorize_resource_fields",
    "extract_bearer_token",
    "persist_job_analysis_snapshot",
    "read_job_analysis_snapshot",
    "snapshot_from_document",
]
