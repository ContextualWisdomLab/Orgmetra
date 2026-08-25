"""Regression tests for the scheduled Orgmetra PR/gap loop."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "hourly-pr-gap-loop.yml"
SCRIPT = ROOT / "scripts" / "ops" / "gap_baseline_freshness.py"
CENTRAL_SCHEDULER = (
    "ContextualWisdomLab/.github/.github/workflows/"
    "pr-review-merge-scheduler.yml"
)


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gap_baseline_freshness", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reusable_scheduler_is_job_level_and_immutably_pinned() -> None:
    """The scheduled mutation driver must call one pinned reusable workflow job."""
    text = WORKFLOW.read_text(encoding="utf-8")
    scheduler_block = text.split("  scheduler-sweep:\n", 1)[1].split(
        "\n  gap-baseline-freshness:", 1
    )[0]

    assert "\n    steps:" not in scheduler_block
    assert "@main" not in scheduler_block
    assert re.search(
        rf"^    uses: {re.escape(CENTRAL_SCHEDULER)}@[0-9a-f]{{40}}$",
        scheduler_block,
        re.MULTILINE,
    )
    assert "    secrets: inherit" in scheduler_block


def test_live_queue_counts_request_all_pages(monkeypatch) -> None:
    """Open PR/issue counts must not silently truncate at the first 100 rows."""
    module = _load_script()
    calls: list[list[str]] = []

    class Completed:
        returncode = 0
        stderr = ""

        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fake_run(arguments: list[str], **_kwargs: object) -> Completed:
        calls.append(arguments)
        joined = " ".join(arguments)
        if "/pulls?" in joined:
            return Completed(json.dumps([[{"number": 1}], [{"number": 2}]]))
        if "/issues?" in joined:
            return Completed(
                json.dumps([[{"number": 3}], [{"number": 4, "pull_request": {}}]])
            )
        if "/commits?" in joined:
            return Completed(
                json.dumps(
                    [
                        {
                            "commit": {
                                "committer": {"date": "2026-08-25T00:00:00Z"}
                            }
                        }
                    ]
                )
            )
        raise AssertionError(f"unexpected gh invocation: {arguments}")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    state = module._live_state()

    assert state["open_pull_requests"] == 2
    assert state["open_issues"] == 1
    queue_calls = [
        call
        for call in calls
        if "/pulls?" in " ".join(call) or "/issues?" in " ".join(call)
    ]
    assert len(queue_calls) == 2
    for call in queue_calls:
        assert "--paginate" in call
        assert "--slurp" in call


def test_missing_baseline_is_nonfatal_until_dependency_integrates(
    monkeypatch, tmp_path, capsys
) -> None:
    """A pre-#100 scheduled run must report absence without staying permanently red."""
    module = _load_script()
    missing = tmp_path / "product-technical-gap-baseline.md"
    monkeypatch.setattr(module.sys, "argv", ["gap-baseline-freshness", "--baseline", str(missing)])

    assert module.main() == 0
    assert "baseline not present" in capsys.readouterr().out.lower()
