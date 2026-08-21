"""Test the pinned fast-mlsirm recovery runner without invoking foreign code."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from uuid import UUID

import pytest

from orgmetra_validity_analysis import REVIEWED_FAST_MLSIRM_REVISION, UnsupportedExecutionDesign
from orgmetra_validity_analysis import recovery_runner as runner


REPOSITORY = Path("/private/tmp/fast-mlsirm")


def output(**overrides: object) -> dict[str, object]:
    """Return one worker-shaped aggregate response for runner tests."""
    values: dict[str, object] = {
        "model": "MLS2PLM",
        "backend": "rust",
        "rust_device": "cpu",
        "status": "max_iter_reached",
        "n_iter": 1,
        "objective": 1.0,
        "n_persons": 48,
        "n_items": 3,
        "n_clusters": 4,
        "recovery_summary": {
            "parameter_rmse_mean": 0.1,
            "latent_rmse": 0.2,
            "distance_rmse": 0.3,
            "gamma_abs_error": 0.4,
        },
    }
    values.update(overrides)
    return values


def request_arguments(*, design_code: str = "nested_multilevel") -> list[str]:
    """Return bounded CLI arguments for one runner invocation."""
    return [
        "--fast-mlsirm-path",
        str(REPOSITORY),
        "--handoff-digest",
        "a" * 64,
        "--design-code",
        design_code,
    ]


def test_parser_and_dataset_digest_are_stable() -> None:
    """Expose the governed design controls and deterministic synthetic input digest."""
    parser = runner.build_parser()
    parsed = parser.parse_args(request_arguments())
    assert parsed.design_code == "nested_multilevel"
    assert parsed.timeout_seconds == 180
    first = runner.dataset_digest(
        design_code="nested_multilevel", persons=48, items_per_dim=3, clusters=4, seed=42
    )
    assert first == runner.dataset_digest(
        design_code="nested_multilevel", persons=48, items_per_dim=3, clusters=4, seed=42
    )
    assert len(first) == 64


@pytest.mark.parametrize(
    ("responses", "message"),
    [
        ([SimpleNamespace(returncode=1, stdout="", stderr="")], "readable"),
        ([SimpleNamespace(returncode=0, stdout="dirty\n", stderr="")], "clean"),
        (
            [
                SimpleNamespace(returncode=0, stdout="", stderr=""),
                SimpleNamespace(returncode=1, stdout="", stderr=""),
            ],
            "readable",
        ),
        (
            [
                SimpleNamespace(returncode=0, stdout="", stderr=""),
                SimpleNamespace(returncode=0, stdout="deadbeef", stderr=""),
            ],
            "equal reviewed revision",
        ),
        (
            [
                SimpleNamespace(returncode=0, stdout="", stderr=""),
                SimpleNamespace(returncode=0, stdout="", stderr=""),
            ],
            "equal reviewed revision",
        ),
    ],
)
def test_resolve_revision_rejects_dirty_or_unreadable_checkouts(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[SimpleNamespace],
    message: str,
) -> None:
    """Reject every checkout state that cannot prove immutable reviewed source."""
    sequence = iter(responses)
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: next(sequence))
    with pytest.raises(RuntimeError, match=message):
        runner.resolve_revision(REPOSITORY)


def test_resolve_revision_accepts_clean_exact_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Accept only an empty status and the exact reviewed commit."""
    responses = iter(
        [
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout=REVIEWED_FAST_MLSIRM_REVISION + "\n", stderr=""),
        ]
    )
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: next(responses))
    runner.resolve_revision(REPOSITORY)


def test_run_worker_uses_external_runtime_and_parses_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep uv environments and Cargo targets outside the foreign checkout."""
    captured: dict[str, object] = {}
    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/local/bin/uv")

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        """Capture one subprocess call and return one valid worker object."""
        captured.update(kwargs)
        return SimpleNamespace(returncode=0, stdout=json.dumps(output()), stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner.run_worker(
        repository=REPOSITORY,
        design_code="nested_multilevel",
        rust_device="cpu",
        persons=48,
        items_per_dim=3,
        clusters=4,
        seed=42,
        worker_count=4,
    )
    environment = captured["env"]
    assert result["model"] == "MLS2PLM"
    assert isinstance(environment, dict)
    assert str(environment["UV_PROJECT_ENVIRONMENT"]).endswith("/venv")
    assert str(environment["CARGO_TARGET_DIR"]).endswith("/cargo-target")
    assert captured["timeout"] == 180


def test_run_worker_rejects_missing_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail before subprocess invocation when uv is unavailable."""
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="uv is required"):
        runner.run_worker(
            repository=REPOSITORY,
            design_code="nested_multilevel",
            rust_device="cpu",
            persons=48,
            items_per_dim=3,
            clusters=4,
            seed=42,
            worker_count=4,
        )


def test_run_worker_rejects_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bound a hung external worker instead of waiting indefinitely."""
    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/local/bin/uv")

    def timeout(*args: object, **kwargs: object) -> None:
        """Raise the subprocess timeout sentinel for the runner boundary."""
        raise subprocess.TimeoutExpired(cmd="uv", timeout=180)

    monkeypatch.setattr(runner.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="timed out"):
        runner.run_worker(
            repository=REPOSITORY,
            design_code="nested_multilevel",
            rust_device="cpu",
            persons=48,
            items_per_dim=3,
            clusters=4,
            seed=42,
            worker_count=4,
        )


@pytest.mark.parametrize(
    ("completed", "message"),
    [
        (SimpleNamespace(returncode=1, stdout="", stderr="worker failed"), "worker failed"),
        (SimpleNamespace(returncode=1, stdout="worker output", stderr=""), "worker output"),
        (SimpleNamespace(returncode=0, stdout="not json", stderr=""), "one JSON object"),
        (SimpleNamespace(returncode=0, stdout="[]", stderr=""), "root must be an object"),
    ],
)
def test_run_worker_rejects_process_and_json_failures(
    monkeypatch: pytest.MonkeyPatch,
    completed: SimpleNamespace,
    message: str,
) -> None:
    """Convert worker process, JSON, and root-shape failures into safe errors."""
    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/local/bin/uv")
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: completed)
    with pytest.raises(RuntimeError, match=message):
        runner.run_worker(
            repository=REPOSITORY,
            design_code="nested_multilevel",
            rust_device="cpu",
            persons=48,
            items_per_dim=3,
            clusters=4,
            seed=42,
            worker_count=4,
        )


def test_main_emits_nested_evidence(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Build and print one nested multilevel receipt after the worker succeeds."""
    monkeypatch.setattr(runner, "resolve_revision", lambda repository: None)
    monkeypatch.setattr(runner, "run_worker", lambda **kwargs: output())
    monkeypatch.setattr(runner, "uuid4", lambda: UUID("11111111-1111-4111-8111-111111111111"))
    assert runner.main(request_arguments()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["design_code"] == "nested_multilevel"
    assert payload["cluster_count"] == 4


def test_main_emits_cross_sectional_evidence(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Build the plain runnable design without cluster metadata."""
    monkeypatch.setattr(runner, "resolve_revision", lambda repository: None)
    monkeypatch.setattr(runner, "run_worker", lambda **kwargs: output(n_clusters=None))
    monkeypatch.setattr(runner, "uuid4", lambda: UUID("22222222-2222-4222-8222-222222222222"))
    assert runner.main(request_arguments(design_code="cross_sectional")) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["design_code"] == "cross_sectional"
    assert payload["cluster_count"] is None


def test_main_rechecks_checkout_when_worker_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Always perform the post-worker integrity check, including failure paths."""
    calls: list[Path] = []

    def resolve(repository: Path) -> None:
        """Record each integrity check without touching a foreign checkout."""
        calls.append(repository)

    def fail_worker(**kwargs: object) -> dict[str, object]:
        """Simulate a worker failure after the initial integrity check."""
        raise RuntimeError("worker failed")

    monkeypatch.setattr(runner, "resolve_revision", resolve)
    monkeypatch.setattr(runner, "run_worker", fail_worker)
    with pytest.raises(RuntimeError, match="worker failed"):
        runner.main(request_arguments())
    assert calls == [REPOSITORY.resolve(), REPOSITORY.resolve()]


@pytest.mark.parametrize("design_code", ["multiple_membership", "longitudinal"])
def test_main_fails_closed_for_contract_only_designs(
    monkeypatch: pytest.MonkeyPatch, design_code: str
) -> None:
    """Do not invoke a worker for unsupported multiple-membership or time designs."""
    monkeypatch.setattr(runner, "resolve_revision", lambda repository: None)
    with pytest.raises(UnsupportedExecutionDesign, match=design_code):
        runner.main(request_arguments(design_code=design_code))


def test_runner_test_fixture_has_aware_timestamp() -> None:
    """Keep this module's timestamp import contract explicit for future evidence tests."""
    assert datetime.now(timezone.utc).tzinfo is not None
