"""Run a bounded exact-revision fast-mlsirm recovery smoke outside Orgmetra."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from uuid import uuid4

from .execution import (
    REVIEWED_FAST_MLSIRM_REVISION,
    RustExecutionRequest,
    build_rust_recovery_evidence,
)

_WORKER_CODE = r'''
import json
import os

import numpy as np
from fast_mlsirm import FitConfig, MLS2PLMConfig, fit, recovery_report, simulate

design_code = os.environ["ORGMETRA_DESIGN_CODE"]
n_persons = int(os.environ["ORGMETRA_PERSONS"])
items_per_dim = int(os.environ["ORGMETRA_ITEMS_PER_DIM"])
cluster_count = int(os.environ["ORGMETRA_CLUSTER_COUNT"])
seed = int(os.environ["ORGMETRA_SEED"])
rust_device = os.environ["ORGMETRA_RUST_DEVICE"]
config = MLS2PLMConfig(
    n_persons=n_persons,
    n_dims=1,
    items_per_dim=items_per_dim,
    latent_dim=1,
    gamma=0.0,
    seed=seed,
)
data = simulate(config)
cluster_id = None
if design_code == "nested_multilevel":
    cluster_id = np.arange(data.Y.shape[0], dtype=np.int64) % cluster_count
result = fit(
    data.Y,
    data.factor_id,
    config=FitConfig(
        model="MLS2PLM",
        estimator="mmle",
        optimizer="adam",
        max_iter=1,
        n_restarts=1,
        backend="rust",
        rust_device=rust_device,
        q_theta=7,
        q_xi=7,
        q_u=7,
    ),
    cluster_id=cluster_id,
)
report = recovery_report(data.truth, result.params)
print(json.dumps({
    "model": result.model,
    "backend": result.backend,
    "rust_device": result.rust_device,
    "status": result.convergence_status,
    "n_iter": result.n_iter,
    "objective": result.objective,
    "n_persons": int(data.Y.shape[0]),
    "n_items": int(data.Y.shape[1]),
    "n_clusters": None if cluster_id is None else int(np.unique(cluster_id).size),
    "recovery_summary": report.summary,
}, sort_keys=True))
'''


def build_parser() -> argparse.ArgumentParser:
    """Build the bounded evidence runner command-line parser."""
    parser = argparse.ArgumentParser(
        description="Run exact-revision fast-mlsirm Rust recovery evidence."
    )
    parser.add_argument("--fast-mlsirm-path", type=Path, required=True)
    parser.add_argument("--handoff-digest", required=True)
    parser.add_argument(
        "--design-code",
        choices=("cross_sectional", "nested_multilevel", "multiple_membership", "longitudinal"),
        default="nested_multilevel",
    )
    parser.add_argument("--rust-device", choices=("cpu", "gpu"), default="cpu")
    parser.add_argument("--persons", type=int, default=48)
    parser.add_argument("--items-per-dim", type=int, default=3)
    parser.add_argument("--clusters", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--worker-count", type=int, default=4)
    return parser


def resolve_revision(repository: Path) -> None:
    """Require a clean external checkout at the exact reviewed Git revision."""
    status = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--ignored",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0:
        raise RuntimeError("fast-mlsirm path is not a readable Git checkout")
    if status.stdout:
        raise RuntimeError("fast-mlsirm checkout must be clean, including ignored files")
    completed = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("fast-mlsirm path is not a readable Git checkout")
    revision = completed.stdout.strip()
    if revision != REVIEWED_FAST_MLSIRM_REVISION:
        raise RuntimeError(
            "fast-mlsirm checkout must equal reviewed revision "
            f"{REVIEWED_FAST_MLSIRM_REVISION}; got {revision or '<missing>'}"
        )


def dataset_digest(
    *, design_code: str, persons: int, items_per_dim: int, clusters: int, seed: int
) -> str:
    """Digest only the synthetic run specification, never generated responses."""
    payload = {
        "clusters": clusters,
        "design_code": design_code,
        "items_per_dim": items_per_dim,
        "persons": persons,
        "seed": seed,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_worker(
    *,
    repository: Path,
    design_code: str,
    rust_device: str,
    persons: int,
    items_per_dim: int,
    clusters: int,
    seed: int,
    worker_count: int,
) -> dict[str, object]:
    """Invoke the external public API in a temporary environment and parse JSON."""
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required to run the pinned fast-mlsirm worker")
    with tempfile.TemporaryDirectory(prefix="orgmetra-fast-mlsirm-run-") as runtime_root:
        runtime_path = Path(runtime_root)
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "TMPDIR": os.environ.get("TMPDIR", ""),
            "ORGMETRA_DESIGN_CODE": design_code,
            "ORGMETRA_PERSONS": str(persons),
            "ORGMETRA_ITEMS_PER_DIM": str(items_per_dim),
            "ORGMETRA_CLUSTER_COUNT": str(clusters),
            "ORGMETRA_SEED": str(seed),
            "ORGMETRA_RUST_DEVICE": rust_device,
            "RAYON_NUM_THREADS": str(worker_count),
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_PROJECT_ENVIRONMENT": str(runtime_path / "venv"),
            "CARGO_TARGET_DIR": str(runtime_path / "cargo-target"),
        }
        completed = subprocess.run(
            [
                uv,
                "run",
                "--frozen",
                "--no-editable",
                "--project",
                str(repository),
                "python",
                "-c",
                _WORKER_CODE,
            ],
            cwd=repository,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"fast-mlsirm worker failed: {detail}")
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("fast-mlsirm worker did not emit one JSON object") from exc
    if not isinstance(output, dict):
        raise RuntimeError("fast-mlsirm worker JSON root must be an object")
    return output


def main(argv: list[str] | None = None) -> int:
    """Verify the clean pinned checkout, run the worker, and print evidence."""
    args = build_parser().parse_args(argv)
    repository = args.fast_mlsirm_path.expanduser().resolve()
    resolve_revision(repository)
    cluster_count = args.clusters if args.design_code == "nested_multilevel" else None
    request = RustExecutionRequest(
        execution_reference=f"validity_execution:{uuid4()}",
        handoff_digest=args.handoff_digest,
        dataset_digest=dataset_digest(
            design_code=args.design_code,
            persons=args.persons,
            items_per_dim=args.items_per_dim,
            clusters=args.clusters,
            seed=args.seed,
        ),
        fast_mlsirm_revision=REVIEWED_FAST_MLSIRM_REVISION,
        design_code=args.design_code,
        sample_size=args.persons,
        item_count=args.items_per_dim,
        seed=args.seed,
        cluster_count=cluster_count,
        occasion_count=2 if args.design_code == "longitudinal" else 1,
        maximum_memberships=2 if args.design_code == "multiple_membership" else 1,
        worker_count=args.worker_count,
        rust_device=args.rust_device,
    )
    request.require_runnable()
    output = run_worker(
        repository=repository,
        design_code=args.design_code,
        rust_device=args.rust_device,
        persons=args.persons,
        items_per_dim=args.items_per_dim,
        clusters=args.clusters,
        seed=args.seed,
        worker_count=args.worker_count,
    )
    resolve_revision(repository)
    evidence = build_rust_recovery_evidence(
        request,
        output,
        completed_at=datetime.now(timezone.utc),
    )
    print(evidence.canonical_json())
    return 0


__all__ = ["build_parser", "dataset_digest", "main", "resolve_revision", "run_worker"]
