"""Focused tests for dependency validation and low-level problem helpers."""

from __future__ import annotations

import asyncio
import json
import re
from uuid import uuid4

import pytest
from starlette.requests import Request

from orgmetra_people_api.app import _parse_uuid_header, create_app
from orgmetra_people_api.problems import (
    InvalidRequestMetadata,
    RequestTooLarge,
    _too_large_handler,
)

from conftest import FakeAuthorizer, FakeRepository


def test_app_factory_rejects_missing_repository_port() -> None:
    authorizer = FakeAuthorizer(principal=_principal())

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
        allowed_scope_codes=frozenset({"orgmetra.people.read"}),
        allowed_purpose_codes=frozenset({"people_read"}),
    )


def test_uuid_header_helper_returns_defaults_and_rejects_non_string() -> None:
    default = uuid4()

    assert _parse_uuid_header(None, "X-Test", default=default) == default
    assert _parse_uuid_header(None, "X-Test", default=None) is None
    with pytest.raises(InvalidRequestMetadata, match="X-Test is invalid"):
        _parse_uuid_header(object(), "X-Test", default=None)  # type: ignore[arg-type]


def test_direct_problem_handler_generates_support_when_middleware_is_absent() -> None:
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
    document = json.loads(response.body)

    assert response.status_code == 413
    assert response.media_type == "application/problem+json"
    assert document["error_code"] == "request_body_too_large"
    support_reference = response.headers["x-support-reference"]
    assert re.fullmatch(r"err_[A-Za-z0-9_-]{20,80}", support_reference)
    assert document["support_reference"] == support_reference
    assert "trace_reference" not in document
    assert document["next_action"]
