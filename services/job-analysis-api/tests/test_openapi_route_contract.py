"""OpenAPI regressions for the executable job-analysis tenant route."""

from pathlib import Path


def test_openapi_matches_the_path_tenant_and_authenticated_actor_authority() -> None:
    """Do not publish a global route or duplicate tenant/actor header authority."""
    schema = (Path(__file__).resolve().parents[3] / "schemas" / "openapi.yaml").read_text(encoding="utf-8")
    collection_path = "  /tenants/{tenant_record_id}/job-analysis-snapshots:"
    item_path = "  /tenants/{tenant_record_id}/job-analysis-snapshots/{analysis_record_id}:"
    assert collection_path in schema
    assert item_path in schema
    assert "  /job-analysis-snapshots:" not in schema
    assert "  /job-analysis-snapshots/{analysis_record_id}:" not in schema

    collection_block = schema.split(collection_path, 1)[1].split(item_path, 1)[0]
    assert "        - name: tenant_record_id\n" in collection_block
    assert "          in: path\n" in collection_block
    assert "#/components/parameters/TenantReference" not in collection_block
    assert "#/components/parameters/ActorReference" not in collection_block

    item_block = schema.split(item_path, 1)[1].split("components:", 1)[0]
    assert "        - name: tenant_record_id\n" in item_block
    assert "        - name: analysis_record_id\n" in item_block
