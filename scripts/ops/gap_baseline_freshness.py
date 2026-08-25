#!/usr/bin/env python3
"""Audit the product-technical gap baseline against live repository truth.

This script is the operational regression required by the baseline document's
own execution-loop contract: every loop must refetch live GitHub state and
reject stale buyer copy before acting. It never hard-codes volatile payloads;
every comparison is computed at runtime from the recorded inventory date, the
live default branch, and the complete live open pull-request/issue queues.

Exit codes:
    0  audit completed, or the baseline has not integrated yet; findings are reported
    2  contract violation or live-state evidence could not be established

The output is plain Markdown so callers can append it directly to
``$GITHUB_STEP_SUMMARY``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

INVENTORY_DATE_PATTERN = re.compile(
    r"^Inventory date:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE
)
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BASELINE_TIMEZONE = ZoneInfo("Asia/Seoul")


def _run_gh_json(
    arguments: list[str], *, paginate: bool = False
) -> list[dict[str, object]]:
    """Return a list payload from ``gh api``, flattening all pages when asked."""
    command = ["gh", *arguments]
    if paginate:
        command.extend(["--paginate", "--slurp"])
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"gh {' '.join(arguments)} failed: {completed.stderr.strip()}")

    payload = json.loads(completed.stdout)
    if paginate:
        if not isinstance(payload, list):
            raise RuntimeError("unexpected paginated GitHub payload shape")
        flattened: list[dict[str, object]] = []
        for page in payload:
            if not isinstance(page, list) or not all(isinstance(item, dict) for item in page):
                raise RuntimeError("unexpected paginated GitHub page shape")
            flattened.extend(page)
        return flattened

    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise RuntimeError("unexpected GitHub list payload shape")
    return payload


def _live_repository() -> str:
    """Return the repository this workflow actually executes in."""
    repository = os.environ.get("GITHUB_REPOSITORY", "ContextualWisdomLab/Orgmetra")
    if REPOSITORY_PATTERN.fullmatch(repository) is None:
        raise RuntimeError("invalid GITHUB_REPOSITORY shape")
    return repository


def _live_state() -> dict[str, object]:
    """Fetch complete live open PR/issue queues and newest develop integration."""
    repository = _live_repository()
    open_pull_requests = _run_gh_json(
        ["api", f"repos/{repository}/pulls?state=open&per_page=100"],
        paginate=True,
    )
    open_issues = _run_gh_json(
        ["api", f"repos/{repository}/issues?state=open&per_page=100"],
        paginate=True,
    )
    # Issues and PRs share the issues endpoint; keep only genuine issues.
    genuine_issues = [item for item in open_issues if "pull_request" not in item]
    commits = _run_gh_json(
        ["api", f"repos/{repository}/commits?sha=develop&per_page=1"]
    )
    newest_commit_date = None
    if commits:
        commit = commits[0].get("commit")
        if not isinstance(commit, dict):
            raise RuntimeError("unexpected commit payload shape")
        committer = commit.get("committer")
        if not isinstance(committer, dict) or not isinstance(committer.get("date"), str):
            raise RuntimeError("unexpected commit committer payload shape")
        newest_commit_date = committer["date"]
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
    except FileNotFoundError:
        print(
            "gap-baseline freshness: baseline not present on this integrated "
            "branch yet; audit remains non-mutating and will activate when the "
            "baseline owner integrates"
        )
        return 0
    except OSError as error:
        print(f"gap-baseline freshness: FAIL unreadable baseline: {error}")
        return 2

    match = INVENTORY_DATE_PATTERN.search(baseline_text)
    if match is None:
        print("gap-baseline freshness: FAIL missing 'Inventory date:' header")
        return 2

    inventory_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
    now_date = datetime.now(tz=BASELINE_TIMEZONE).date()
    if inventory_date > now_date:
        print(
            "gap-baseline freshness: FAIL future inventory date "
            f"{inventory_date.isoformat()} exceeds current Asia/Seoul date "
            f"{now_date.isoformat()}"
        )
        return 2
    age_days = (now_date - inventory_date).days

    lines = [
        "## Gap baseline freshness",
        "",
        f"- Baseline file: `{baseline_path.as_posix()}`",
        f"- Inventory date: {inventory_date.isoformat()} "
        f"(age {float(age_days):.1f} days)",
    ]

    try:
        state = _live_state()
    except (RuntimeError, ValueError, KeyError) as error:
        lines.append(f"- FAIL live-state fetch: {error}")
        print("\n".join(lines))
        return 2

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
        integrations_after_snapshot = (
            integration_time.astimezone(BASELINE_TIMEZONE).date() > inventory_date
        )

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
