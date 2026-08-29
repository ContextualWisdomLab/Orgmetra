"""Public governed selection-validity analysis handoff and result contracts."""

from .handoff import (
    REVIEWED_FAST_MLSIRM_REVISION,
    ValidationAnalysisHandoff,
    build_validation_analysis_handoff,
)
from .execution import (
    RustExecutionRequest,
    RustRecoveryEvidence,
    UnsupportedExecutionDesign,
    build_rust_recovery_evidence,
)
from .result import ConvergenceDiagnostics, MissingnessSummary, ValidationAnalysisResult

__all__ = [
    "REVIEWED_FAST_MLSIRM_REVISION",
    "ValidationAnalysisHandoff",
    "build_validation_analysis_handoff",
    "RustExecutionRequest",
    "RustRecoveryEvidence",
    "UnsupportedExecutionDesign",
    "build_rust_recovery_evidence",
    "ConvergenceDiagnostics",
    "MissingnessSummary",
    "ValidationAnalysisResult",
]
