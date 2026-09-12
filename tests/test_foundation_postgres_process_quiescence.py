"""Regression contract for isolated PostgreSQL Foundation process ownership."""

from __future__ import annotations

import unittest
from pathlib import Path


class FoundationPostgresProcessQuiescenceTests(unittest.TestCase):
    """Keep one contract from retaining execution after its shell returns."""

    @staticmethod
    def _execution_step() -> str:
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "foundation-ci.yml"
        ).read_text(encoding="utf-8")
        start = workflow.index("      - name: Run PostgreSQL contracts in isolated containers")
        end = workflow.index("      - name: Prove compatibility toolchain provenance", start)
        return workflow[start:end]

    def test_uses_dedicated_ephemeral_contract_identity(self) -> None:
        execution = self._execution_step()

        self.assertIn('contract_user="orgmetra_pg_contract"', execution)
        self.assertIn(
            'sudo -n useradd --system --no-create-home --shell /usr/sbin/nologin "$contract_user"',
            execution,
        )
        self.assertIn('sudo -n -u "$contract_user" true', execution)
        self.assertIn('sudo -n userdel "$contract_user"', execution)
        self.assertNotIn('sudo -n -u nobody', execution)

    def test_fails_closed_when_contract_leaves_background_processes(self) -> None:
        execution = self._execution_step()

        self.assertIn('assert_contract_process_quiescence()', execution)
        self.assertIn('pgrep -u "$contract_user"', execution)
        self.assertIn('PostgreSQL contract leaked background processes', execution)
        self.assertIn('sudo -n pkill -KILL -u "$contract_user"', execution)
        self.assertIn('run_contract_snapshot "$contract" "$database_url"', execution)
        self.assertIn('run_contract_snapshot "$companion" "$database_url"', execution)
        self.assertEqual(execution.count('sudo -n -u "$contract_user" env'), 1)

    def test_uses_fresh_non_shared_runtime_workspace_per_executable(self) -> None:
        execution = self._execution_step()

        self.assertIn('runtime_parent="$(mktemp -d)"', execution)
        self.assertIn('chmod 0711 "$runtime_parent"', execution)
        self.assertIn('contract_runtime="$(mktemp -d "$runtime_parent/run.XXXXXX")"', execution)
        self.assertIn('sudo -n chown "$contract_user" "$contract_runtime"', execution)
        self.assertIn('HOME="$contract_runtime"', execution)
        self.assertIn('TMPDIR="$contract_runtime"', execution)
        self.assertIn('XDG_CACHE_HOME="$contract_runtime/.cache"', execution)
        self.assertIn('XDG_CONFIG_HOME="$contract_runtime/.config"', execution)
        self.assertIn('XDG_STATE_HOME="$contract_runtime/.local/state"', execution)
        self.assertIn('XDG_DATA_HOME="$contract_runtime/.local/share"', execution)
        self.assertIn('XDG_RUNTIME_DIR="$contract_runtime/.runtime"', execution)
        self.assertIn('sudo -n rm -rf -- "$contract_runtime"', execution)
        self.assertIn('sudo -n rm -rf -- "$runtime_parent"', execution)
        self.assertNotIn('HOME=/tmp', execution)

    def test_scrubs_inherited_environment_before_each_executable(self) -> None:
        execution = self._execution_step()

        self.assertIn('sudo -n -u "$contract_user" env -i \\', execution)
        self.assertIn('PATH="$PATH" \\', execution)
        self.assertNotIn('sudo -n -u "$contract_user" env \\', execution)

    def test_executes_against_immutable_exact_candidate_tree(self) -> None:
        execution = self._execution_step()

        self.assertIn('candidate_snapshot_dir="$snapshot_parent/candidate"', execution)
        self.assertIn(
            'git archive --format=tar "$ORGMETRA_EXPECTED_HEAD_SHA" | tar -xf - -C "$candidate_snapshot_dir"',
            execution,
        )
        self.assertIn('chmod -R a-w "$candidate_snapshot_dir"', execution)
        self.assertIn('execution_script="$candidate_snapshot_dir/$script"', execution)
        self.assertIn("cd -- \"$1\" && exec bash \"$2\"", execution)
        self.assertIn('workspace_mode="$(stat -c \'%a\' .)"', execution)
        self.assertIn('chmod 0700 .', execution)
        self.assertIn('chmod "$workspace_mode" .', execution)
        self.assertNotIn('exec bash "$snapshot_script"', execution)


if __name__ == "__main__":
    unittest.main()
