"""Test the safety contract of the pinned external recovery runner."""

from pathlib import Path
import subprocess
import sys


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE_ROOT / "scripts" / "run_fast_mlsirm_recovery_evidence.py"
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]


def test_runner_help_exposes_pinned_path_and_design_controls() -> None:
    """Keep the evidence command discoverable without starting model execution."""
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--fast-mlsirm-path" in completed.stdout
    assert "--handoff-digest" in completed.stdout
    assert "multiple_membership" in completed.stdout
    assert "longitudinal" in completed.stdout


def test_runner_rejects_an_unpinned_checkout_before_worker_start() -> None:
    """Reject the Orgmetra checkout as a foreign worker before any model code runs."""
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--fast-mlsirm-path",
            str(REPOSITORY_ROOT),
            "--handoff-digest",
            "a" * 64,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert (
        "must be clean" in completed.stderr
        or "must equal reviewed revision" in completed.stderr
    )
