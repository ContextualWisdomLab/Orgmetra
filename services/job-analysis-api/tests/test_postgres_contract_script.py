"""Static regressions for executable job-analysis PostgreSQL evidence."""

from pathlib import Path


def test_missing_position_failure_requires_the_expected_foreign_key_reason() -> None:
    """Do not accept an unrelated SQL failure as position-scope evidence."""
    contract = (
        Path(__file__).resolve().parents[3]
        / "tests"
        / "test_job_analysis_snapshot_postgres.sh"
    ).read_text(encoding="utf-8")
    assert '"${missing_position_output}" != *"foreign key"*' in contract
    assert '"${missing_position_output}" != *"job_analysis_snapshot_position_tenant_fk"*' in contract
    assert "missing position failed for an unexpected reason" in contract
