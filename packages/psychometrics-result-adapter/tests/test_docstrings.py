"""Beginner-readable public documentation contract for the result-evidence adapter."""

import inspect

import orgmetra_psychometrics_result_adapter as package


def test_public_result_evidence_api_has_docstrings() -> None:
    """Keep the exported class and its public evidence methods documented."""
    envelope_type = package.PsychometricsResultEvidenceEnvelope
    assert inspect.getdoc(package)
    assert inspect.getdoc(envelope_type)
    for method_name in ("canonical_document", "canonical_json", "evidence_digest"):
        assert inspect.getdoc(getattr(envelope_type, method_name))
