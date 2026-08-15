"""Focused tests for safe framework HTTP exception normalization."""

from __future__ import annotations

import asyncio
import json

from starlette.exceptions import HTTPException
from starlette.requests import Request

from orgmetra_people_api.problems import _http_exception_handler


def test_generic_http_error_preserves_only_safe_headers() -> None:
    """Drop arbitrary framework headers while preserving auth guidance."""

    scope = {
        "type": "http",
        "method": "GET",
        "scheme": "https",
        "path": "/teapot",
        "raw_path": b"/teapot",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 443),
        "root_path": "",
        "http_version": "1.1",
        "state": {},
    }
    response = asyncio.run(
        _http_exception_handler(
            Request(scope),
            HTTPException(
                status_code=418,
                detail="sensitive framework detail",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-Internal-Secret": "do-not-return",
                },
            ),
        )
    )
    document = json.loads(response.body)

    assert response.status_code == 418
    assert document["error_code"] == "http_error"
    assert document["title"] == "HTTP request failed"
    assert "sensitive framework detail" not in response.body.decode("utf-8")
    assert response.headers["www-authenticate"] == "Bearer"
    assert "x-internal-secret" not in response.headers
