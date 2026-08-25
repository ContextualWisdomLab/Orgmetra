#!/usr/bin/env python3
"""Audit the product-technical gap baseline against live repository truth.

This script is the operational regression required by the baseline document's
own execution-loop contract: every loop must refetch live GitHub state and
reject stale buyer copy before acting. It never hard-codes volatile payloads;
every comparison is computed at runtime from the recorded inventory date, the
live default branch, and the live open pull-request/issue queues.

Exit codes:
    0  audit completed; findings are reported in the step summary text
    2  contract violation (unreadable/invalid baseline structure)

The output is plain Markdown so callers can append it directly to
``$GITHUB_STEP_SUMMARY``.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

INVENTORY_DATE_PATTERN = re.compile(
    r"^Inventory date:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE
)


def _run_gh_json(arguments: list[str]) -> list[dict[str, object]]:
    """Return parsed JSON from one ``gh api`` invocation as a list payload."""
    completed = subprocess.run(
        ["gh", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"gh {' '.join(arguments)} failed: {completed.stderr.strip()}")
    return json.loads(completed.stdout)


def _live_state() -> dict[str, object]:
    """Fetch the live open PR/issue queue and newest develop integration."""
    open_pull_requests = _run_gh_json(
        [
            "api",
            "repos/{owner}/{repo}/pulls?state=open&per_page=100".replace(
                "{owner}/{repo}", "ContextualWisdomLab/Orgmetra"
            ),
        ]
    )
    if not isinstance(open_pull_requests, list):
        raise RuntimeError("unexpected pull request payload shape")
    open_issues = _run_gh_json(
        ["api", "repos/ContextualWisdomLab/Orgmetra/issues?state=open&per_page=100"]
    )
    if not isinstance(open_issues, list):
        raise RuntimeError("unexpected issue payload shape")
    # Issues and PRs share the issues endpoint; keep only genuine issues.
    genuine_issues = [item for item in open_issues if "pull_request" not in item]
    commits = _run_gh_json(
        ["api", "repos/ContextualWisdomLab/Orgmetra/commits?sha=develop&per_page=1"]
    )
    newest_commit_date = None
    if isinstance(commits, list) and commits:
        commit_date = commits[0]["commit"]["committer"]["date"]
        newest_commit_date = str(commit_date)
    return {
        "open_pull_requests": len(open_pull_requests),
        "open_issues": len(genuine_issues),
        "newest_develop_commit_date": newest_commit_date,
    }


def main() -> int:
    """Print a Markdown freshness report for the gap baseline snapshot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="docs/product-technical-gap-baseline.md")
    arguments = parser.parse_args()

    baseline_path = Path(arguments.baseline)
    try:
        baseline_text = baseline_path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"gap-baseline freshness: FAIL unreadable baseline: {error}")
        return 2

    match = INVENTORY_DATE_PATTERN.search(baseline_text)
    if match is None:
        print("gap-baseline freshness: FAIL missing 'Inventory date:' header")
        return 2

    inventory_date = datetime.strptime(match.group(1), "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    now = datetime.now(tz=timezone.utc)
    age_days = (now - inventory_date).total_seconds() / 86400

    lines = [
        "## Gap baseline freshness",
        "",
        f"- Baseline file: `{baseline_path.as_posix()}`",
        f"- Inventory date: {inventory_date.date().isoformat()} "
        f"(age {age_days:.1f} days)",
    ]

    try:
        state = _live_state()
    except (RuntimeError, ValueError, KeyError) as error:
        lines.append(f"- Live-state fetch failed (transient?): {error}")
        print("\n".join(lines))
        return 0

    lines.extend(
        [
            f"- Live open pull requests: {state['open_pull_requests']}",
            f"- Live open issues: {state['open_issues']}",
            "- Newest develop integration: "
            f"{state['newest_develop_commit_date']}",
        ]
    )

    newest_integration = state.get("newest_develop_commit_date")
    integrations_after_snapshot = False
    if isinstance(newest_integration, str):
        integration_time = datetime.fromisoformat(
            newest_integration.replace("Z", "+00:00")
        )
        integrations_after_snapshot = integration_time > inventory_date

    if integrations_after_snapshot:
        lines.append(
            "- Result: **refresh candidate** — `develop` integrated commits after "
            "the recorded inventory date. Per the execution loop, refresh the "
            "baseline only when buyer/product-visible truth changed; otherwise "
            "record this audit as observed."
        )
    else:
        lines.append(
            "- Result: current — no develop integration is newer than the "
            "recorded inventory snapshot."
        )

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
