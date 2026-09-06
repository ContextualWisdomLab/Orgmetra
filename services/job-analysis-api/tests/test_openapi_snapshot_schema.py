"""OpenAPI regressions for bounded, typed job-analysis snapshot evidence."""

from pathlib import Path


def test_snapshot_arrays_publish_runtime_cardinality_and_item_types() -> None:
    """Keep client schemas aligned with bounded runtime parsing and evidence shapes."""
    schema = (Path(__file__).resolve().parents[3] / "schemas" / "openapi.yaml").read_text(encoding="utf-8")
    command = schema.split("    PersistJobAnalysisSnapshotCommand:", 1)[1].split(
        "    JobAnalysisSnapshotDocument:", 1
    )[0]
    document = schema.split("    JobAnalysisSnapshotDocument:", 1)[1].split(
        "    ErrorResponse:", 1
    )[0]

    for block in (command, document):
        assert "        tasks:\n          type: array\n          minItems: 1\n          maxItems: 500\n          items:\n            $ref: '#/components/schemas/JobAnalysisTaskEvidence'" in block
        assert "        ksao_requirements:\n          type: array\n          minItems: 1\n          maxItems: 500\n          items:\n            $ref: '#/components/schemas/JobAnalysisKSAORequirement'" in block
        assert "        task_ksao_links:\n          type: array\n          minItems: 1\n          maxItems: 5000\n          items:\n            $ref: '#/components/schemas/JobAnalysisTaskKSAOLink'" in block
        assert "        fja_profile:\n          $ref: '#/components/schemas/FunctionalJobAnalysisProfile'" in block

    for component in (
        "    JobAnalysisEvidenceSource:",
        "    JobAnalysisTaskEvidence:",
        "    JobAnalysisKSAORequirement:",
        "    JobAnalysisTaskKSAOLink:",
        "    FunctionalJobAnalysisProfile:",
    ):
        assert component in schema


def test_snapshot_get_publishes_dedicated_not_found_response() -> None:
    """Do not document a missing snapshot as generic invalid-command validation."""
    schema = (Path(__file__).resolve().parents[3] / "schemas" / "openapi.yaml").read_text(encoding="utf-8")
    item_path = "  /tenants/{tenant_record_id}/job-analysis-snapshots/{analysis_record_id}:"
    item_block = schema.split(item_path, 1)[1].split("components:", 1)[0]

    assert "        '404':\n          $ref: '#/components/responses/SnapshotNotFound'" in item_block
    assert "    SnapshotNotFound:" in schema
