"""Tests for fail-closed PostgreSQL Foundation contract inventory discovery."""

from __future__ import annotations

import hashlib
import importlib.util
import json
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
    """Exercise discovery, provenance, exclusions, and generic companions."""

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
