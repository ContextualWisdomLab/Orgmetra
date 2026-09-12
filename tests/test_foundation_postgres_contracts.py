"""Tests for fail-closed PostgreSQL Foundation contract inventory discovery."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "scripts"
    / "foundation-postgres-contracts.py"
)
SPEC = importlib.util.spec_from_file_location("foundation_postgres_contracts", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load PostgreSQL contract inventory module: {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FoundationPostgresContractInventoryTests(unittest.TestCase):
    """Exercise discovery, provenance, exclusions, snapshots, and generic companions."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / ".github").mkdir(parents=True)
        (self.root / "tests").mkdir()
        self.alpha = self._write("tests/test_alpha_postgres.sh")
        self.beta = self._write("tests/test_beta_postgres.sh")
        self.companion = self._write("tests/test_beta_schema_hardening.sh")
        self.registry = self._valid_registry()
        self._write_registry(self.registry)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative_path: str, content: str = "#!/usr/bin/env bash\nexit 0\n") -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _binding(self, path: Path) -> dict[str, str]:
        return {
            "script": path.relative_to(self.root).as_posix(),
            "sha256": _digest(path),
        }

    def _valid_registry(self) -> dict[str, object]:
        return {
            "schema_version": MODULE.SCHEMA_VERSION,
            "contracts": [
                {
                    "id": "alpha",
                    **self._binding(self.alpha),
                    "companions": [],
                },
                {
                    "id": "beta",
                    **self._binding(self.beta),
                    "companions": [self._binding(self.companion)],
                },
            ],
            "exclusions": [],
        }

    def _write_registry(self, registry: dict[str, object]) -> None:
        (self.root / MODULE.REGISTRY_PATH).write_text(
            json.dumps(registry, indent=2) + "\n",
            encoding="utf-8",
        )

    def _assert_invalid(self, expected: str) -> None:
        with self.assertRaisesRegex(MODULE.ContractInventoryError, expected):
            MODULE.load_inventory(self.root)

    def test_valid_inventory_discovers_active_roots_and_generic_companion(self) -> None:
        inventory = MODULE.load_inventory(self.root)
        self.assertEqual(
            [item.root.script for item in inventory.contracts],
            ["tests/test_alpha_postgres.sh", "tests/test_beta_postgres.sh"],
        )
        self.assertEqual(
            [item.script for item in inventory.contracts[1].companions],
            ["tests/test_beta_schema_hardening.sh"],
        )
        evidence = MODULE.evidence_document(inventory)
        self.assertEqual(evidence["active"][1]["companions"][0]["script"], self.companion.relative_to(self.root).as_posix())

    def test_unregistered_new_root_contract_fails_closed(self) -> None:
        self._write("tests/test_new_owner_postgres.sh")
        self._assert_invalid("unregistered=.*test_new_owner_postgres")

    def test_missing_registered_script_fails_closed(self) -> None:
        self.beta.unlink()
        self._assert_invalid("is missing: tests/test_beta_postgres")

    def test_stale_digest_fails_closed(self) -> None:
        self.alpha.write_text("#!/usr/bin/env bash\nexit 9\n", encoding="utf-8")
        self._assert_invalid("digest mismatch for tests/test_alpha_postgres")

    def test_duplicate_contract_id_fails_closed(self) -> None:
        contracts = self.registry["contracts"]
        assert isinstance(contracts, list)
        second = contracts[1]
        assert isinstance(second, dict)
        second["id"] = "alpha"
        self._write_registry(self.registry)
        self._assert_invalid("duplicate PostgreSQL contract id: alpha")

    def test_duplicate_root_path_fails_closed(self) -> None:
        contracts = self.registry["contracts"]
        assert isinstance(contracts, list)
        second = contracts[1]
        assert isinstance(second, dict)
        second.update(self._binding(self.alpha))
        self._write_registry(self.registry)
        self._assert_invalid("duplicate active PostgreSQL root script")

    def test_unknown_registry_field_fails_closed(self) -> None:
        self.registry["owner"] = "document_records"
        self._write_registry(self.registry)
        self._assert_invalid("fields mismatch")

    def test_malformed_script_path_fails_closed(self) -> None:
        contracts = self.registry["contracts"]
        assert isinstance(contracts, list)
        first = contracts[0]
        assert isinstance(first, dict)
        first["script"] = "../test_alpha_postgres.sh"
        self._write_registry(self.registry)
        self._assert_invalid("unsupported path")

    def test_symlinked_root_contract_fails_closed(self) -> None:
        alias = self.root / "tests/test_alias_postgres.sh"
        alias.symlink_to(self.alpha.name)
        contracts = self.registry["contracts"]
        assert isinstance(contracts, list)
        contracts.append(
            {
                "id": "alias",
                **self._binding(alias),
                "companions": [],
            }
        )
        self._write_registry(self.registry)
        self._assert_invalid("must not use filesystem symlinks")

    def test_symlinked_companion_fails_closed(self) -> None:
        alias = self.root / "tests/test_beta_alias_hardening.sh"
        alias.symlink_to(self.companion.name)
        contracts = self.registry["contracts"]
        assert isinstance(contracts, list)
        beta = contracts[1]
        assert isinstance(beta, dict)
        beta["companions"] = [self._binding(alias)]
        self._write_registry(self.registry)
        self._assert_invalid("must not use filesystem symlinks")

    def test_discoverable_root_cannot_be_hidden_as_companion(self) -> None:
        contracts = self.registry["contracts"]
        assert isinstance(contracts, list)
        first = contracts[0]
        assert isinstance(first, dict)
        first["companions"] = [self._binding(self.beta)]
        contracts.pop()
        self._write_registry(self.registry)
        self._assert_invalid("must not be a discoverable root contract")

    def test_reviewed_exclusion_can_account_for_discovered_root(self) -> None:
        contracts = self.registry["contracts"]
        assert isinstance(contracts, list)
        contracts.pop(1)
        self.registry["exclusions"] = [
            {
                **self._binding(self.beta),
                "reason": "Temporary isolation while canonical issue repair is reviewed.",
                "review_reference": "Orgmetra#310",
            }
        ]
        self._write_registry(self.registry)
        inventory = MODULE.load_inventory(self.root)
        self.assertEqual([item.root.script for item in inventory.contracts], ["tests/test_alpha_postgres.sh"])
        self.assertEqual([item.root.script for item in inventory.exclusions], ["tests/test_beta_postgres.sh"])

    def test_exclusion_requires_meaningful_reason(self) -> None:
        contracts = self.registry["contracts"]
        assert isinstance(contracts, list)
        contracts.pop(1)
        self.registry["exclusions"] = [
            {
                **self._binding(self.beta),
                "reason": "skip",
                "review_reference": "Orgmetra#310",
            }
        ]
        self._write_registry(self.registry)
        self._assert_invalid("reason must explain")

    def test_exclusion_requires_review_reference(self) -> None:
        contracts = self.registry["contracts"]
        assert isinstance(contracts, list)
        contracts.pop(1)
        self.registry["exclusions"] = [
            {
                **self._binding(self.beta),
                "reason": "Temporary isolation while canonical issue repair is reviewed.",
                "review_reference": "pending",
            }
        ]
        self._write_registry(self.registry)
        self._assert_invalid("review_reference must name")

    def test_all_discovered_contracts_cannot_be_excluded(self) -> None:
        self.registry["contracts"] = []
        self.registry["exclusions"] = [
            {
                **self._binding(self.alpha),
                "reason": "Reviewed temporary exclusion for isolated contract repair.",
                "review_reference": "#310",
            },
            {
                **self._binding(self.beta),
                "reason": "Reviewed temporary exclusion for isolated contract repair.",
                "review_reference": "#310",
            },
        ]
        self._write_registry(self.registry)
        self._assert_invalid("no active PostgreSQL contracts declared")

    def test_zero_discovery_is_non_vacuous_failure(self) -> None:
        self.alpha.unlink()
        self.beta.unlink()
        self.registry["contracts"] = []
        self.registry["exclusions"] = []
        self._write_registry(self.registry)
        self._assert_invalid("no PostgreSQL root contracts discovered")

    def test_execution_snapshot_runs_reviewed_root_and_companion_after_source_mutation(self) -> None:
        marker = self.root / "snapshot-result.txt"
        self.beta.write_text(
            '#!/usr/bin/env bash\nprintf "root-reviewed\\n" > "$ORGMETRA_SNAPSHOT_MARKER"\n',
            encoding="utf-8",
        )
        self.companion.write_text(
            '#!/usr/bin/env bash\nprintf "companion-reviewed\\n" >> "$ORGMETRA_SNAPSHOT_MARKER"\n',
            encoding="utf-8",
        )
        self.registry = self._valid_registry()
        self._write_registry(self.registry)
        inventory = MODULE.load_inventory(self.root)

        with tempfile.TemporaryDirectory() as tempdir:
            snapshot_root = Path(tempdir) / "contracts"
            snapshot = MODULE.materialize_execution_snapshot(
                self.root,
                inventory,
                snapshot_root,
            )
            self.beta.write_text(
                '#!/usr/bin/env bash\nprintf "root-mutated\\n" > "$ORGMETRA_SNAPSHOT_MARKER"\n',
                encoding="utf-8",
            )
            self.companion.write_text(
                '#!/usr/bin/env bash\nprintf "companion-mutated\\n" >> "$ORGMETRA_SNAPSHOT_MARKER"\n',
                encoding="utf-8",
            )

            beta = next(
                item
                for item in snapshot["active"]
                if item["script"] == "tests/test_beta_postgres.sh"
            )
            env = os.environ | {"ORGMETRA_SNAPSHOT_MARKER": str(marker)}
            subprocess.run(
                ["bash", beta["snapshot_script"]],
                cwd=self.root,
                env=env,
                check=True,
            )
            subprocess.run(
                ["bash", beta["companions"][0]["snapshot_script"]],
                cwd=self.root,
                env=env,
                check=True,
            )

        self.assertEqual(
            marker.read_text(encoding="utf-8").splitlines(),
            ["root-reviewed", "companion-reviewed"],
        )

    def test_non_owner_contract_cannot_replace_later_snapshot_entries(self) -> None:
        if shutil.which("sudo") is None:
            self.skipTest("sudo is required to exercise the Foundation non-owner boundary")
        probe = subprocess.run(
            ["sudo", "-n", "-u", "nobody", "true"],
            check=False,
            capture_output=True,
            text=True,
        )
        if probe.returncode != 0:
            self.skipTest("passwordless sudo to nobody is unavailable outside canonical CI")

        marker_fd, marker_name = tempfile.mkstemp(prefix="orgmetra-snapshot-result-", dir="/tmp")
        os.close(marker_fd)
        marker = Path(marker_name)
        marker.chmod(0o666)
        self.alpha.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if chmod u+w \"$ORGMETRA_ATTACK_ROOT\" 2>/dev/null; then exit 41; fi\n"
            "if printf 'root-mutated\\n' > \"$ORGMETRA_ATTACK_ROOT\" 2>/dev/null; then exit 42; fi\n"
            "if mv \"$ORGMETRA_ATTACK_SNAPSHOT_ROOT\" \"${ORGMETRA_ATTACK_SNAPSHOT_ROOT}.moved\" 2>/dev/null; then exit 43; fi\n"
            "if rm -f \"$ORGMETRA_ATTACK_COMPANION\" 2>/dev/null; then exit 44; fi\n",
            encoding="utf-8",
        )
        self.beta.write_text(
            '#!/usr/bin/env bash\nprintf "root-reviewed\\n" > "$ORGMETRA_SNAPSHOT_MARKER"\n',
            encoding="utf-8",
        )
        self.companion.write_text(
            '#!/usr/bin/env bash\nprintf "companion-reviewed\\n" >> "$ORGMETRA_SNAPSHOT_MARKER"\n',
            encoding="utf-8",
        )
        self.registry = self._valid_registry()
        self._write_registry(self.registry)
        inventory = MODULE.load_inventory(self.root)

        try:
            with tempfile.TemporaryDirectory() as tempdir:
                snapshot_parent = Path(tempdir)
                snapshot_root = snapshot_parent / "contracts"
                snapshot = MODULE.materialize_execution_snapshot(
                    self.root,
                    inventory,
                    snapshot_root,
                )
                for path in sorted(snapshot_root.rglob("*")):
                    path.chmod(0o555 if path.is_dir() else 0o444)
                snapshot_root.chmod(0o555)
                snapshot_parent.chmod(0o555)

                alpha = next(item for item in snapshot["active"] if item["id"] == "alpha")
                beta = next(item for item in snapshot["active"] if item["id"] == "beta")
                attack_env = [
                    f"ORGMETRA_ATTACK_ROOT={beta['snapshot_script']}",
                    f"ORGMETRA_ATTACK_COMPANION={beta['companions'][0]['snapshot_script']}",
                    f"ORGMETRA_ATTACK_SNAPSHOT_ROOT={snapshot_root}",
                ]
                subprocess.run(
                    ["sudo", "-n", "-u", "nobody", "env", *attack_env, "bash", alpha["snapshot_script"]],
                    cwd="/",
                    check=True,
                )
                runtime_env = [f"ORGMETRA_SNAPSHOT_MARKER={marker}"]
                subprocess.run(
                    ["sudo", "-n", "-u", "nobody", "env", *runtime_env, "bash", beta["snapshot_script"]],
                    cwd="/",
                    check=True,
                )
                subprocess.run(
                    [
                        "sudo",
                        "-n",
                        "-u",
                        "nobody",
                        "env",
                        *runtime_env,
                        "bash",
                        beta["companions"][0]["snapshot_script"],
                    ],
                    cwd="/",
                    check=True,
                )

                snapshot_parent.chmod(0o700)
                snapshot_root.chmod(0o700)
                for path in sorted(snapshot_root.rglob("*")):
                    path.chmod(0o700 if path.is_dir() else 0o600)

            self.assertEqual(
                marker.read_text(encoding="utf-8").splitlines(),
                ["root-reviewed", "companion-reviewed"],
            )
        finally:
            marker.unlink(missing_ok=True)

    def test_execution_snapshot_rejects_source_drift_after_inventory_validation(self) -> None:
        inventory = MODULE.load_inventory(self.root)
        self.beta.write_text("#!/usr/bin/env bash\nexit 9\n", encoding="utf-8")
        with tempfile.TemporaryDirectory() as tempdir:
            with self.assertRaisesRegex(
                MODULE.ContractInventoryError,
                "changed before execution snapshot",
            ):
                MODULE.materialize_execution_snapshot(
                    self.root,
                    inventory,
                    Path(tempdir) / "contracts",
                )

    def test_snapshot_cli_materializes_private_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            snapshot_root = Path(tempdir) / "contracts"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = MODULE.main(
                    [
                        "--root",
                        str(self.root),
                        "snapshot",
                        "--destination",
                        str(snapshot_root),
                    ]
                )
            self.assertEqual(status, 0)
            document = json.loads(output.getvalue())
            self.assertEqual(document["active"][0]["script"], "tests/test_alpha_postgres.sh")
            self.assertTrue(Path(document["active"][0]["snapshot_script"]).is_file())
            self.assertEqual(snapshot_root.stat().st_mode & 0o777, 0o500)

    def test_workflow_binds_executed_bytes_to_pre_execution_snapshot(self) -> None:
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "foundation-ci.yml"
        ).read_text(encoding="utf-8")
        start = workflow.index("      - name: Run PostgreSQL contracts in isolated containers")
        end = workflow.index("      - name: Prove compatibility toolchain provenance", start)
        execution = workflow[start:end]

        snapshot = 'snapshot --destination "$snapshot_dir"'
        self.assertIn(snapshot, execution)
        self.assertIn('snapshot_by_script["$script"]="$snapshot_script"', execution)
        self.assertIn('verify_snapshot_bytes "$contract"', execution)
        self.assertIn('verify_snapshot_bytes "$companion"', execution)
        self.assertIn('chmod 0555 "$snapshot_parent"', execution)
        self.assertIn('contract_user="orgmetra_pg_contract"', execution)
        self.assertIn('sudo -n -u "$contract_user" true', execution)
        self.assertIn('sudo -n -u "$contract_user" env', execution)
        self.assertNotIn('sudo -n -u nobody', execution)
        self.assertIn('execution_script="$candidate_snapshot_dir/$script"', execution)
        self.assertIn('exec bash "$2"', execution)
        self.assertNotIn('bash "$snapshot_script"', execution)
        self.assertNotIn('DATABASE_URL="$database_url" bash "$contract"', execution)
        self.assertNotIn('DATABASE_URL="$database_url" bash "$companion"', execution)
        self.assertNotIn(
            'foundation-postgres-contracts.py companions "$contract"',
            execution,
        )
        self.assertIn(
            'for bound_script in "${!expected_sha256[@]}"',
            execution,
        )

    def test_cli_list_and_companions_return_validated_paths(self) -> None:
        self.assertEqual(
            MODULE.main(["--root", str(self.root), "list"]),
            0,
        )
        self.assertEqual(
            MODULE.main(
                [
                    "--root",
                    str(self.root),
                    "companions",
                    "tests/test_beta_postgres.sh",
                ]
            ),
            0,
        )

    def test_cli_rejects_unknown_active_root_for_companion_lookup(self) -> None:
        self.assertEqual(
            MODULE.main(
                [
                    "--root",
                    str(self.root),
                    "companions",
                    "tests/test_missing_postgres.sh",
                ]
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()
