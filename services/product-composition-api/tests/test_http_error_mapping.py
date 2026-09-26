from __future__ import annotations

import asyncio
import json

import pytest

from orgmetra_product_composition import (
    CompositionMethodNotAllowedError,
    CompositionMethodNotImplementedError,
    CompositionRequestError,
    CompositionRouteNotFoundError,
    CompositionRouteUnavailableError,
    CompositionRoutingError,
    CompositionTransportError,
    http_response_for_composition_error,
    send_composition_error_response,
)


def _decoded_problem(error: Exception):
    response = http_response_for_composition_error(error)
    return response, json.loads(response.body)


@pytest.mark.parametrize(
    ("error", "status", "code", "title"),
    [
        (CompositionTransportError("raw transport detail"), 400, "invalid_request", "Bad Request"),
        (CompositionRequestError("decoded request detail"), 400, "invalid_request", "Bad Request"),
        (
            CompositionMethodNotImplementedError("capability detail"),
            501,
            "method_not_implemented",
            "Not Implemented",
        ),
        (CompositionRouteNotFoundError("route detail"), 404, "route_not_found", "Not Found"),
        (CompositionRouteUnavailableError("authority detail"), 503, "route_unavailable", "Service Unavailable"),
        (CompositionRoutingError("internal routing detail"), 500, "routing_error", "Internal Server Error"),
    ],
)
def test_about_blank_problem_titles_follow_http_status_phrases_without_disclosure(
    error: Exception,
    status: int,
    code: str,
    title: str,
) -> None:
    response, payload = _decoded_problem(error)

    assert response.status == status
    assert response.headers == (
        (b"content-type", b"application/problem+json"),
        (b"cache-control", b"no-store"),
    )
    assert payload == {
        "code": code,
        "status": status,
        "title": title,
        "type": "about:blank",
    }
    assert "detail" not in payload
    assert str(error) not in response.body.decode("utf-8")


def test_method_not_allowed_carries_canonical_allow_authority() -> None:
    error = CompositionMethodNotAllowedError(
        "method detail",
        allowed_methods=("POST", "GET", "GET"),
    )

    response, payload = _decoded_problem(error)

    assert error.allowed_methods == ("GET", "HEAD", "POST")
    assert response.status == 405
    assert response.headers == (
        (b"content-type", b"application/problem+json"),
        (b"cache-control", b"no-store"),
        (b"allow", b"GET, HEAD, POST"),
    )
    assert payload == {
        "code": "method_not_allowed",
        "status": 405,
        "title": "Method Not Allowed",
        "type": "about:blank",
    }


def test_method_not_allowed_carries_empty_allow_for_temporarily_disabled_resource() -> None:
    error = CompositionMethodNotAllowedError(
        "method detail",
        allowed_methods=(),
    )

    response, payload = _decoded_problem(error)

    assert error.allowed_methods == ()
    assert response.status == 405
    assert response.headers == (
        (b"content-type", b"application/problem+json"),
        (b"cache-control", b"no-store"),
        (b"allow", b""),
    )
    assert payload["code"] == "method_not_allowed"


@pytest.mark.parametrize(
    "allowed_methods",
    [("get",), ("GET\nPOST",), ("GET", object())],
)
def test_method_not_allowed_rejects_noncanonical_allow_authority(
    allowed_methods: tuple[object, ...],
) -> None:
    with pytest.raises(CompositionRoutingError):
        CompositionMethodNotAllowedError(
            "method detail",
            allowed_methods=allowed_methods,
        )


@pytest.mark.parametrize(
    "mutated_methods",
    [
        ("GET",),
        ("POST",),
        ("TRACE",),
        ("GET\r\nx-injected: true",),
    ],
)
def test_http_mapping_rejects_any_mutated_allow_authority(
    mutated_methods: tuple[str, ...],
) -> None:
    error = CompositionMethodNotAllowedError(
        "method detail",
        allowed_methods=("GET",),
    )
    error.allowed_methods = mutated_methods

    with pytest.raises(CompositionRoutingError):
        http_response_for_composition_error(error)


def test_http_mapping_rejects_deleted_allow_authority() -> None:
    error = CompositionMethodNotAllowedError(
        "method detail",
        allowed_methods=("POST",),
    )
    del error.allowed_methods

    with pytest.raises(CompositionRoutingError):
        http_response_for_composition_error(error)


def test_http_mapping_rejects_unissued_method_error_instance() -> None:
    error = CompositionMethodNotAllowedError.__new__(CompositionMethodNotAllowedError)
    RuntimeError.__init__(error, "forged method rejection")
    error.allowed_methods = ("POST",)

    with pytest.raises(CompositionRoutingError):
        http_response_for_composition_error(error)


def test_send_composition_error_response_emits_one_complete_asgi_response() -> None:
    messages: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    asyncio.run(
        send_composition_error_response(
            send,
            CompositionRouteNotFoundError("do not disclose this"),
            request_method="GET",
        )
    )

    assert messages == [
        {
            "type": "http.response.start",
            "status": 404,
            "headers": [
                (b"content-type", b"application/problem+json"),
                (b"cache-control", b"no-store"),
            ],
        },
        {
            "type": "http.response.body",
            "body": b'{"code":"route_not_found","status":404,"title":"Not Found","type":"about:blank"}',
            "more_body": False,
        },
    ]


def test_head_error_response_emits_metadata_without_response_content() -> None:
    messages: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    error = CompositionRouteNotFoundError("do not disclose this")
    mapped = http_response_for_composition_error(error)
    assert mapped.body

    asyncio.run(
        send_composition_error_response(
            send,
            error,
            request_method="HEAD",
        )
    )

    assert messages == [
        {
            "type": "http.response.start",
            "status": 404,
            "headers": [
                (b"content-type", b"application/problem+json"),
                (b"cache-control", b"no-store"),
            ],
        },
        {
            "type": "http.response.body",
            "body": b"",
            "more_body": False,
        },
    ]


def test_malformed_method_error_retains_problem_content() -> None:
    messages: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    asyncio.run(
        send_composition_error_response(
            send,
            CompositionRequestError("invalid method"),
            request_method=None,
        )
    )

    assert messages[1] == {
        "type": "http.response.body",
        "body": b'{"code":"invalid_request","status":400,"title":"Bad Request","type":"about:blank"}',
        "more_body": False,
    }


def test_unknown_exception_is_not_laundered_into_a_composition_http_response() -> None:
    with pytest.raises(TypeError):
        http_response_for_composition_error(RuntimeError("foreign failure"))
