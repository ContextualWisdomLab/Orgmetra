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


if __name__ == "__main__":
    unittest.main()
