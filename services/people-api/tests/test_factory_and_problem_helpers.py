"""Focused tests for dependency validation and low-level problem helpers."""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from starlette.requests import Request

from orgmetra_people_api.app import (
    _parse_evidence_header,
    _parse_uuid_header,
    create_app,
)
from orgmetra_people_api.problems import (
    RequestTooLarge,
    _too_large_handler,
)

from conftest import FakeAuthorizer, FakeRepository


def test_app_factory_rejects_missing_repository_port() -> None:
    authorizer = FakeAuthorizer(
        principal=_principal(),
    )

    with pytest.raises(TypeError, match="PeopleRepository"):
        create_app(object(), authorizer)  # type: ignore[arg-type]


def test_app_factory_rejects_missing_authorizer_port() -> None:
    with pytest.raises(TypeError, match="TokenAuthorizer"):
        create_app(FakeRepository(), object())  # type: ignore[arg-type]


def _principal():
    """Create a principal without importing test-only behavior into production."""

    from orgmetra_people_api import AuthorizedPrincipal

    return AuthorizedPrincipal(
        tenant_reference=uuid4(),
        actor_reference=uuid4(),
        allowed_purpose_codes=frozenset({"people_read"}),
    )


def test_uuid_header_helper_returns_defaults_and_rejects_non_string() -> None:
    default = uuid4()

    assert _parse_uuid_header(None, "X-Test", default=default) == default
    assert _parse_uuid_header(None, "X-Test", default=None) is None
    with pytest.raises(Exception, match="metadata"):
        _parse_uuid_header(object(), "X-Test", default=None)  # type: ignore[arg-type]


def test_evidence_header_helper_accepts_none_and_rejects_controls() -> None:
    assert _parse_evidence_header(None) is None
    assert _parse_evidence_header(" evidence://record/1 ") == "evidence://record/1"
    with pytest.raises(Exception, match="metadata"):
        _parse_evidence_header("evidence://record/1\x7f")


def test_direct_problem_handler_generates_trace_when_middleware_is_absent() -> None:
    scope = {
        "type": "http",
        "method": "POST",
        "scheme": "https",
        "path": "/direct",
        "raw_path": b"/direct",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 443),
        "root_path": "",
        "http_version": "1.1",
    }
    response = asyncio.run(_too_large_handler(Request(scope), RequestTooLarge()))
    document = response.body.decode("utf-8")

    assert response.status_code == 413
    assert response.media_type == "application/problem+json"
    assert "request_body_too_large" in document
    assert UUID(response.headers.get("x-request-id", str(uuid4())))
