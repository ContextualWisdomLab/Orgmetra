"""Repository contract for reproducible model-draft package evidence."""

from pathlib import Path


def test_python_support_is_bounded_to_the_exact_hosted_minor() -> None:
    """Public package metadata must not silently claim untested future Python minors."""
    root = Path(__file__).resolve().parents[3]
    pyproject = (root / "packages/job-analysis-model-draft/pyproject.toml").read_text()
    workflow = (root / ".github/workflows/job-analysis-model-draft-quality.yml").read_text()
    assert 'requires-python = ">=3.14,<3.15"' in pyproject
    assert 'python-version: "3.14.7"' in workflow


def test_isolated_install_hash_binds_backend_and_exact_local_wheel() -> None:
    """Build and installed artifact evidence must not depend on ambient runner tooling or unhashed bytes."""
    root = Path(__file__).resolve().parents[3]
    workflow = (root / ".github/workflows/job-analysis-model-draft-quality.yml").read_text()
    requirements = (
        root / "packages/job-analysis-model-draft/build-requirements.txt"
    ).read_text()
    install_backend = (
        "python -m pip install --require-hashes --no-deps --only-binary=:all: "
        "-r packages/job-analysis-model-draft/build-requirements.txt"
    )
    build_wheel = (
        "python -m pip wheel --no-deps --no-build-isolation --wheel-dir "
        "/tmp/orgmetra-job-analysis-model-draft-wheels "
        "/tmp/orgmetra-job-analysis-model-draft-build"
    )
    install_wheel = (
        "python -m pip install --require-hashes --no-deps --target "
        "/tmp/orgmetra-job-analysis-model-draft-installed "
        "-r /tmp/orgmetra-job-analysis-model-draft-wheel.txt"
    )
    assert install_backend in workflow
    assert build_wheel in workflow
    assert 'wheel_sha="$(sha256sum "$wheel" | cut -d\' \' -f1)"' in workflow
    assert install_wheel in workflow
    assert workflow.index(install_backend) < workflow.index(build_wheel)
    assert workflow.index(build_wheel) < workflow.index(install_wheel)
    package_lines = [
        line for line in requirements.splitlines() if line and not line.startswith("#")
    ]
    assert package_lines == [
        "setuptools==84.0.0 "
        "--hash=sha256:51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"
    ]
