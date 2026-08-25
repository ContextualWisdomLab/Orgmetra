"""Repository-level guardrails for the dedicated document retrieval quality gate."""

from pathlib import Path


def test_quality_workflow_watches_every_governance_surface() -> None:
    """ADR/doctoring/traceability-only changes must still run the dedicated gate."""
    root = Path(__file__).resolve().parents[3]
    workflow = (root / ".github/workflows/hr-document-retrieval-quality.yml").read_text()
    for expected_path in (
        '"packages/hr-document-retrieval/**"',
        '"docs/adr/0116-purpose-bound-hr-document-retrieval.md"',
        '"docs/doctoring/hr-document-retrieval-references.md"',
        '"docs/traceability/hr-document-retrieval.md"',
    ):
        assert expected_path in workflow


def test_docs_keep_active_pr_truth_distinct_from_protected_main() -> None:
    """The active PR must never be described as already shipped on develop."""
    root = Path(__file__).resolve().parents[3]
    traceability = (root / "docs/traceability/hr-document-retrieval.md").read_text()
    assert "does not contain this executable retrieval boundary" in traceability
    assert "checks, reviews, source code, and PR state do not transfer" in traceability


def test_isolated_install_uses_hash_locked_reviewed_build_backend() -> None:
    """No-build-isolation smoke tests must install an exact reviewed build backend first."""
    root = Path(__file__).resolve().parents[3]
    workflow = (root / ".github/workflows/hr-document-retrieval-quality.yml").read_text()
    requirements = (
        root / "packages/hr-document-retrieval/build-requirements.txt"
    ).read_text()
    install_backend = (
        "python -m pip install --require-hashes --no-deps --only-binary=:all: "
        "-r packages/hr-document-retrieval/build-requirements.txt"
    )
    source_install = (
        "python -m pip install --no-deps --no-build-isolation --target "
        "/tmp/orgmetra-hr-document-retrieval-installed "
        "/tmp/orgmetra-hr-document-retrieval-build"
    )
    assert install_backend in workflow
    assert source_install in workflow
    assert workflow.index(install_backend) < workflow.index(source_install)
    package_lines = [
        line for line in requirements.splitlines() if line and not line.startswith("#")
    ]
    assert package_lines == [
        "setuptools==84.0.0 "
        "--hash=sha256:51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"
    ]
