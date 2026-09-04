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


def test_python_support_is_bounded_to_the_exact_hosted_minor() -> None:
    """Public package metadata must not claim future or older untested Python minors."""
    root = Path(__file__).resolve().parents[3]
    pyproject = (root / "packages/hr-document-retrieval/pyproject.toml").read_text()
    workflow = (root / ".github/workflows/hr-document-retrieval-quality.yml").read_text()
    assert 'requires-python = ">=3.14,<3.15"' in pyproject
    assert 'requires = ["setuptools==84.0.0"]' in pyproject
    assert 'python-version: "3.14.7"' in workflow


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
    assert install_backend in workflow
    package_lines = [
        line for line in requirements.splitlines() if line and not line.startswith("#")
    ]
    assert package_lines == [
        "setuptools==84.0.0 "
        "--hash=sha256:51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"
    ]


def test_isolated_install_hash_binds_the_locally_built_wheel() -> None:
    """Installed package bytes must be bound to the wheel built from the exact checkout."""
    root = Path(__file__).resolve().parents[3]
    workflow = (root / ".github/workflows/hr-document-retrieval-quality.yml").read_text()
    build_wheel = (
        "python -m pip wheel --no-deps --no-build-isolation --wheel-dir "
        "/tmp/orgmetra-hr-document-retrieval-wheels "
        "/tmp/orgmetra-hr-document-retrieval-build"
    )
    hash_wheel = 'wheel_sha="$(sha256sum "$wheel" | cut -d\' \' -f1)"'
    install_wheel = (
        "python -m pip install --require-hashes --no-deps --target "
        "/tmp/orgmetra-hr-document-retrieval-installed "
        "-r /tmp/orgmetra-hr-document-retrieval-wheel.txt"
    )
    assert build_wheel in workflow
    assert hash_wheel in workflow
    assert install_wheel in workflow
    assert workflow.index(build_wheel) < workflow.index(hash_wheel)
    assert workflow.index(hash_wheel) < workflow.index(install_wheel)
    assert "pip install --no-deps --no-build-isolation --target" not in workflow
