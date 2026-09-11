#!/usr/bin/env python3
"""Validate and enumerate Orgmetra PostgreSQL Foundation contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "orgmetra.foundation_postgres_contracts.v1"
REGISTRY_PATH = Path(".github/foundation-postgres-contracts.json")
ROOT_SCRIPT_PATTERN = re.compile(r"tests/test_[a-z0-9_]+_postgres\.sh")
COMPANION_SCRIPT_PATTERN = re.compile(r"tests/test_[a-z0-9_]+\.sh")
CONTRACT_ID_PATTERN = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
REVIEW_REFERENCE_PATTERN = re.compile(r"(?:#[1-9][0-9]*|[A-Za-z0-9_.-]+#[1-9][0-9]*)")


class ContractInventoryError(ValueError):
    """Report a fail-closed PostgreSQL Foundation inventory defect."""


@dataclass(frozen=True, slots=True)
class ScriptBinding:
    """Bind one repository script path to its reviewed SHA-256 digest."""

    script: str
    sha256: str


@dataclass(frozen=True, slots=True)
class ContractBinding:
    """Describe one active PostgreSQL root contract and its companion scripts."""

    contract_id: str
    root: ScriptBinding
    companions: tuple[ScriptBinding, ...]


@dataclass(frozen=True, slots=True)
class ContractExclusion:
    """Describe one reviewed exclusion from active PostgreSQL execution."""

    root: ScriptBinding
    reason: str
    review_reference: str


@dataclass(frozen=True, slots=True)
class ContractInventory:
    """Hold the validated active and excluded PostgreSQL contract inventory."""

    contracts: tuple[ContractBinding, ...]
    exclusions: tuple[ContractExclusion, ...]


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of exact repository file bytes."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    """Reject missing or unknown registry fields so schema drift fails closed."""

    observed = set(value)
    if observed != expected:
        missing = sorted(expected - observed)
        unknown = sorted(observed - expected)
        raise ContractInventoryError(
            f"{context} fields mismatch: missing={missing}, unknown={unknown}"
        )


def _require_string(value: Any, context: str) -> str:
    """Return a non-empty string or reject the registry value."""

    if not isinstance(value, str) or not value.strip():
        raise ContractInventoryError(f"{context} must be a non-empty string")
    return value


def _validate_digest(value: Any, context: str) -> str:
    """Return a lowercase SHA-256 digest or reject the registry value."""

    digest = _require_string(value, context)
    if SHA256_PATTERN.fullmatch(digest) is None:
        raise ContractInventoryError(f"{context} must be a lowercase SHA-256 digest")
    return digest


def _validate_path(
    root: Path,
    value: Any,
    pattern: re.Pattern[str],
    context: str,
) -> str:
    """Return a repository-contained regular script path without symlink indirection."""

    script = _require_string(value, context)
    if pattern.fullmatch(script) is None:
        raise ContractInventoryError(f"{context} has unsupported path: {script}")

    candidate = root
    for component in Path(script).parts:
        candidate = candidate / component
        if candidate.is_symlink():
            raise ContractInventoryError(
                f"{context} must not use filesystem symlinks: {script}"
            )
    if not candidate.is_file():
        raise ContractInventoryError(f"{context} is missing: {script}")

    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise ContractInventoryError(
            f"{context} must resolve inside the repository root: {script}"
        ) from error
    return script


def _validate_binding(
    root: Path,
    raw: Any,
    pattern: re.Pattern[str],
    context: str,
) -> ScriptBinding:
    """Validate one script path and exact-byte digest binding."""

    if not isinstance(raw, dict):
        raise ContractInventoryError(f"{context} must be an object")
    _require_exact_keys(raw, {"script", "sha256"}, context)
    script = _validate_path(root, raw["script"], pattern, f"{context}.script")
    digest = _validate_digest(raw["sha256"], f"{context}.sha256")
    observed = _sha256(root / script)
    if observed != digest:
        raise ContractInventoryError(
            f"{context} digest mismatch for {script}: expected {digest}, observed {observed}"
        )
    return ScriptBinding(script=script, sha256=digest)


def discover_root_scripts(root: Path) -> tuple[str, ...]:
    """Discover every regular root PostgreSQL contract in stable lexical order."""

    tests_dir = root / "tests"
    if not tests_dir.is_dir():
        return ()
    discovered: list[str] = []
    for path in sorted(tests_dir.glob("test_*_postgres.sh")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ContractInventoryError(
                f"discovered PostgreSQL root must not use filesystem symlinks: {relative}"
            )
        if not path.is_file():
            raise ContractInventoryError(
                f"discovered PostgreSQL root is not a regular file: {relative}"
            )
        discovered.append(relative)
    return tuple(discovered)


def load_inventory(
    root: Path,
    registry_path: Path = REGISTRY_PATH,
) -> ContractInventory:
    """Load and fail-closed validate the complete PostgreSQL contract inventory."""

    absolute_registry = root / registry_path
    try:
        raw_document = json.loads(absolute_registry.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContractInventoryError(
            f"PostgreSQL contract registry is not readable JSON: {absolute_registry}: {error}"
        ) from error

    if not isinstance(raw_document, dict):
        raise ContractInventoryError("PostgreSQL contract registry must be an object")
    _require_exact_keys(
        raw_document,
        {"schema_version", "contracts", "exclusions"},
        "registry",
    )
    if raw_document["schema_version"] != SCHEMA_VERSION:
        raise ContractInventoryError(
            f"unsupported PostgreSQL contract registry schema: {raw_document['schema_version']!r}"
        )

    raw_contracts = raw_document["contracts"]
    raw_exclusions = raw_document["exclusions"]
    if not isinstance(raw_contracts, list):
        raise ContractInventoryError("registry.contracts must be an array")
    if not isinstance(raw_exclusions, list):
        raise ContractInventoryError("registry.exclusions must be an array")

    contracts: list[ContractBinding] = []
    exclusions: list[ContractExclusion] = []
    active_ids: set[str] = set()
    active_roots: set[str] = set()
    all_bound_paths: set[str] = set()

    for index, raw_contract in enumerate(raw_contracts):
        context = f"registry.contracts[{index}]"
        if not isinstance(raw_contract, dict):
            raise ContractInventoryError(f"{context} must be an object")
        _require_exact_keys(
            raw_contract,
            {"id", "script", "sha256", "companions"},
            context,
        )
        contract_id = _require_string(raw_contract["id"], f"{context}.id")
        if CONTRACT_ID_PATTERN.fullmatch(contract_id) is None:
            raise ContractInventoryError(f"{context}.id is not lower snake_case: {contract_id}")
        if contract_id in active_ids:
            raise ContractInventoryError(f"duplicate PostgreSQL contract id: {contract_id}")
        active_ids.add(contract_id)

        root_binding = _validate_binding(
            root,
            {"script": raw_contract["script"], "sha256": raw_contract["sha256"]},
            ROOT_SCRIPT_PATTERN,
            context,
        )
        if root_binding.script in active_roots:
            raise ContractInventoryError(
                f"duplicate active PostgreSQL root script: {root_binding.script}"
            )
        active_roots.add(root_binding.script)
        if root_binding.script in all_bound_paths:
            raise ContractInventoryError(
                f"PostgreSQL script is bound more than once: {root_binding.script}"
            )
        all_bound_paths.add(root_binding.script)

        raw_companions = raw_contract["companions"]
        if not isinstance(raw_companions, list):
            raise ContractInventoryError(f"{context}.companions must be an array")
        companions: list[ScriptBinding] = []
        for companion_index, raw_companion in enumerate(raw_companions):
            companion_context = f"{context}.companions[{companion_index}]"
            binding = _validate_binding(
                root,
                raw_companion,
                COMPANION_SCRIPT_PATTERN,
                companion_context,
            )
            if ROOT_SCRIPT_PATTERN.fullmatch(binding.script):
                raise ContractInventoryError(
                    f"{companion_context} must not be a discoverable root contract: "
                    f"{binding.script}"
                )
            if binding.script in all_bound_paths:
                raise ContractInventoryError(
                    f"PostgreSQL script is bound more than once: {binding.script}"
                )
            all_bound_paths.add(binding.script)
            companions.append(binding)

        contracts.append(
            ContractBinding(
                contract_id=contract_id,
                root=root_binding,
                companions=tuple(companions),
            )
        )

    excluded_roots: set[str] = set()
    for index, raw_exclusion in enumerate(raw_exclusions):
        context = f"registry.exclusions[{index}]"
        if not isinstance(raw_exclusion, dict):
            raise ContractInventoryError(f"{context} must be an object")
        _require_exact_keys(
            raw_exclusion,
            {"script", "sha256", "reason", "review_reference"},
            context,
        )
        binding = _validate_binding(
            root,
            {"script": raw_exclusion["script"], "sha256": raw_exclusion["sha256"]},
            ROOT_SCRIPT_PATTERN,
            context,
        )
        if binding.script in all_bound_paths or binding.script in excluded_roots:
            raise ContractInventoryError(
                f"PostgreSQL script is bound more than once: {binding.script}"
            )
        reason = _require_string(raw_exclusion["reason"], f"{context}.reason")
        if len(reason.strip()) < 20:
            raise ContractInventoryError(
                f"{context}.reason must explain the reviewed exclusion"
            )
        review_reference = _require_string(
            raw_exclusion["review_reference"],
            f"{context}.review_reference",
        )
        if REVIEW_REFERENCE_PATTERN.fullmatch(review_reference) is None:
            raise ContractInventoryError(
                f"{context}.review_reference must name a reviewed issue or PR"
            )
        excluded_roots.add(binding.script)
        all_bound_paths.add(binding.script)
        exclusions.append(
            ContractExclusion(
                root=binding,
                reason=reason,
                review_reference=review_reference,
            )
        )

    discovered = set(discover_root_scripts(root))
    declared = active_roots | excluded_roots
    missing = sorted(discovered - declared)
    phantom = sorted(declared - discovered)
    if missing or phantom:
        raise ContractInventoryError(
            "PostgreSQL root contract inventory mismatch: "
            f"unregistered={missing}, not_discovered={phantom}"
        )
    if not discovered:
        raise ContractInventoryError(
            "no PostgreSQL root contracts discovered; Foundation evidence would be vacuous"
        )
    if not contracts:
        raise ContractInventoryError(
            "no active PostgreSQL contracts declared; Foundation evidence would be vacuous"
        )

    return ContractInventory(
        contracts=tuple(sorted(contracts, key=lambda item: item.root.script)),
        exclusions=tuple(sorted(exclusions, key=lambda item: item.root.script)),
    )


def evidence_document(inventory: ContractInventory) -> dict[str, Any]:
    """Build deterministic evidence for the exact validated execution inventory."""

    return {
        "schema_version": SCHEMA_VERSION,
        "active": [
            {
                "id": contract.contract_id,
                "script": contract.root.script,
                "sha256": contract.root.sha256,
                "companions": [
                    {"script": item.script, "sha256": item.sha256}
                    for item in contract.companions
                ],
            }
            for contract in inventory.contracts
        ],
        "excluded": [
            {
                "script": exclusion.root.script,
                "sha256": exclusion.root.sha256,
                "reason": exclusion.reason,
                "review_reference": exclusion.review_reference,
            }
            for exclusion in inventory.exclusions
        ],
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the operator-facing inventory command."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Repository root; defaults to the current directory.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    subparsers.add_parser("list")
    companions = subparsers.add_parser("companions")
    companions.add_argument("script")
    subparsers.add_parser("evidence")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run one validated PostgreSQL Foundation inventory operation."""

    args = _parse_args(sys.argv[1:] if argv is None else argv)
    root = args.root.resolve()
    try:
        inventory = load_inventory(root)
        if args.command == "validate":
            print(
                "PostgreSQL Foundation inventory valid: "
                f"{len(inventory.contracts)} active, {len(inventory.exclusions)} excluded"
            )
            return 0
        if args.command == "list":
            for contract in inventory.contracts:
                print(contract.root.script)
            return 0
        if args.command == "companions":
            matches = [
                contract
                for contract in inventory.contracts
                if contract.root.script == args.script
            ]
            if len(matches) != 1:
                raise ContractInventoryError(
                    f"active PostgreSQL root contract is not registered: {args.script}"
                )
            for companion in matches[0].companions:
                print(companion.script)
            return 0
        if args.command == "evidence":
            print(
                json.dumps(
                    evidence_document(inventory),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        raise ContractInventoryError(f"unsupported command: {args.command}")
    except ContractInventoryError as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
