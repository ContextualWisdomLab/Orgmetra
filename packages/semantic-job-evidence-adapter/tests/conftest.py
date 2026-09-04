"""Shared pytest fixtures for the semantic job evidence adapter contract."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest


SDP_REVISION = "e48aa13c4af7a4875d4b53e6a60b50405c265a2f"


@pytest.fixture
def semantic_values() -> dict[str, object]:
    """Return one fresh valid value-minimized ontology source-evidence fixture."""
    return {
        "tenant_record_id": str(uuid4()),
        "job_analysis_reference": f"job_analysis:{uuid4()}",
        "ontology_request_reference": f"ontology_request:{uuid4()}",
        "requesting_actor_reference": f"actor:{uuid4()}",
        "reviewing_actor_reference": f"actor:{uuid4()}",
        "resolution_use_code": "job_analysis_source_evidence",
        "query_term_digest": "a" * 64,
        "response_evidence_digest": "b" * 64,
        "source_catalog_digest": "c" * 64,
        "semantic_data_portal_revision": SDP_REVISION,
        "api_operation": "POST /ontology/resolve",
        "evidence_version": 1,
        "recorded_at": datetime(2026, 8, 22, 14, 50, 12, 123456, tzinfo=timezone.utc),
    }
