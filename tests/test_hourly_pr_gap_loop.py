"""Regression tests for the scheduled Orgmetra gap-baseline audit."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "hourly-pr-gap-loop.yml"
SCRIPT = ROOT / "scripts" / "ops" / "gap_baseline_freshness.py"
CENTRAL_SCHEDULER = "pr-review-merge-scheduler.yml"
BASELINE = (
    "Inventory date: 2026-08-25 (Asia/Seoul).\n"
    "At this snapshot, 4 pull requests and one non-PR issue are open.\n"
)


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gap_baseline_freshness", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hourly_audit_does_not_create_a_second_pr_writer() -> None:
    """The Orgmetra heartbeat must stay read-only beside the central writer."""
    text = WORKFLOW.read_text(encoding="utf-8")

    assert CENTRAL_SCHEDULER not in text
    assert "contents: write" not in text
    assert "pull-requests: write" not in text
    assert "actions: write" not in text
    assert "id-token: write" not in text
    assert "secrets: inherit" not in text
    assert "permissions:\n  contents: read\n  pull-requests: read\n  issues: read" in text
    assert "ref: ${{ github.event.repository.default_branch }}" in text


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
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["gap-baseline-freshness", "--baseline", str(missing)],
    )

    assert module.main() == 0
    assert "baseline not present" in capsys.readouterr().out.lower()


def test_future_inventory_date_is_nonpassing_without_live_read(
    monkeypatch, tmp_path, capsys
) -> None:
    """A future-dated buyer snapshot cannot be accepted as current repository truth."""
    module = _load_script()
    baseline = tmp_path / "product-technical-gap-baseline.md"
    baseline.write_text(
        BASELINE.replace("2026-08-25", "2999-12-31"), encoding="utf-8"
    )
    live_calls = 0

    def live_state() -> dict[str, object]:
        nonlocal live_calls
        live_calls += 1
        return {
            "open_pull_requests": 4,
            "open_issues": 1,
            "newest_develop_commit_date": "2026-08-25T12:00:00Z",
        }

    monkeypatch.setattr(module, "_live_state", live_state)
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["gap-baseline-freshness", "--baseline", str(baseline)],
    )

    assert module.main() == 2
    assert live_calls == 0
    assert "future inventory date" in capsys.readouterr().out.lower()


def test_same_inventory_day_integration_is_not_newer(
    monkeypatch, tmp_path, capsys
) -> None:
    """A same-Korea-calendar-day commit must not make a date-only snapshot stale."""
    module = _load_script()
    baseline = tmp_path / "product-technical-gap-baseline.md"
    baseline.write_text(BASELINE, encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_live_state",
        lambda: {
            "open_pull_requests": 4,
            "open_issues": 1,
            "newest_develop_commit_date": "2026-08-25T12:00:00Z",
        },
    )
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["gap-baseline-freshness", "--baseline", str(baseline)],
    )

    assert module.main() == 0
    assert "result: current" in capsys.readouterr().out.lower()


def test_next_korea_calendar_day_integration_requires_refresh(
    monkeypatch, tmp_path, capsys
) -> None:
    """UTC timestamps crossing midnight in Korea must stale the prior local date."""
    module = _load_script()
    baseline = tmp_path / "product-technical-gap-baseline.md"
    baseline.write_text(BASELINE, encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_live_state",
        lambda: {
            "open_pull_requests": 4,
            "open_issues": 1,
            "newest_develop_commit_date": "2026-08-25T16:00:00Z",
        },
    )
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["gap-baseline-freshness", "--baseline", str(baseline)],
    )

    assert module.main() == 0
    assert "refresh candidate" in capsys.readouterr().out.lower()


def test_live_state_failure_is_nonpassing(monkeypatch, tmp_path, capsys) -> None:
    """An unavailable live control plane must fail closed instead of silently passing."""
    module = _load_script()
    baseline = tmp_path / "product-technical-gap-baseline.md"
    baseline.write_text(BASELINE, encoding="utf-8")

    def fail_live_state() -> dict[str, object]:
        raise RuntimeError("GitHub API unavailable")

    monkeypatch.setattr(module, "_live_state", fail_live_state)
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["gap-baseline-freshness", "--baseline", str(baseline)],
    )

    assert module.main() == 2
    output = capsys.readouterr().out.lower()
    assert "fail live-state fetch" in output
    assert "github api unavailable" in output


def test_queue_change_is_reported_as_refresh_candidate(
    monkeypatch, tmp_path, capsys
) -> None:
    """A changed live queue makes the point-in-time baseline a refresh candidate."""
    module = _load_script()
    baseline = tmp_path / "product-technical-gap-baseline.md"
    baseline.write_text(BASELINE, encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_live_state",
        lambda: {
            "open_pull_requests": 5,
            "open_issues": 1,
            "newest_develop_commit_date": "2026-08-25T12:00:00Z",
        },
    )
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["gap-baseline-freshness", "--baseline", str(baseline)],
    )

    assert module.main() == 0
    assert "refresh candidate" in capsys.readouterr().out.lower()


def test_empty_develop_commit_payload_fails_closed(monkeypatch) -> None:
    """An empty develop response cannot establish a current integration point."""
    module = _load_script()

    class Completed:
        returncode = 0
        stderr = ""
        stdout = "[]"

    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: Completed())
    try:
        module._live_state()
    except RuntimeError as error:
        assert "empty" in str(error)
    else:
        raise AssertionError("empty develop payload was accepted")


def test_invalid_develop_timestamp_fails_closed(monkeypatch, tmp_path, capsys) -> None:
    """Malformed integration timestamps cannot be reported as a current audit."""
    module = _load_script()
    baseline = tmp_path / "product-technical-gap-baseline.md"
    baseline.write_text(BASELINE, encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_live_state",
        lambda: {
            "open_pull_requests": 4,
            "open_issues": 1,
            "newest_develop_commit_date": "not-a-timestamp",
        },
    )
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["gap-baseline-freshness", "--baseline", str(baseline)],
    )

    assert module.main() == 2
    assert "invalid develop timestamp" in capsys.readouterr().out.lower()
