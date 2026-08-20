"""Regression contracts for realistic job-analysis evidence fixtures."""

from fixtures import onet_source, sme_source


def test_supervisor_sme_fixture_has_independent_source_provenance() -> None:
    """Do not let local SME evidence masquerade as the O*NET source artifact."""
    onet = onet_source()
    sme = sme_source()

    assert sme.source_uri != onet.source_uri
    assert sme.content_digest_sha256 != onet.content_digest_sha256
