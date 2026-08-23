"""Regression coverage for the public identity contract documented by the package."""

from pathlib import Path


def test_readme_does_not_apply_uuidv4_policy_to_tenant_identity() -> None:
    """Keep the tenant operational-UUID contract distinct from leaf UUIDv4 references."""

    readme = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")

    assert (
        "tenant and proposed employment separation to exact opaque canonical "
        "non-sentinel UUIDv4 references"
    ) not in readme
    assert "`tenant_record_id` follows protected Orgmetra core's canonical non-sentinel operational-UUID contract" in readme
    assert "Packet-owned namespaced trust references remain canonical UUIDv4" in readme
