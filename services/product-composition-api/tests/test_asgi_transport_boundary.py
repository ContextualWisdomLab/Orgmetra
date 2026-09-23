from __future__ import annotations

import pytest

import orgmetra_product_composition.asgi_transport as asgi_transport
from orgmetra_product_composition import (
    CanonicalHttpRequest,
    CompositionRequestError,
    CompositionTransportError,
    canonical_request_from_asgi_scope,
    current_route_id_for_asgi_scope,
)


def _scope(**overrides: object) -> dict[str, object]:
    scope: dict[str, object] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.5"},
        "http_version": "1.1",
        "scheme": "https",
        "method": "GET",
        "path": "/v1/people/person_123",
        "raw_path": b"/v1/people/person_123",
        "query_string": b"",
        "root_path": "",
        "headers": (),
        "client": ("127.0.0.1", 12345),
        "server": ("orgmetra.example", 443),
    }
    scope.update(overrides)
    return scope


def test_canonical_http_scope_detaches_exact_method_and_path() -> None:
    request = canonical_request_from_asgi_scope(_scope())

    assert request == CanonicalHttpRequest(
        method="GET",
        path="/v1/people/person_123",
    )
    assert type(request.method) is str
    assert type(request.path) is str


def test_missing_root_path_uses_the_asgi_empty_default() -> None:
    scope = _scope()
    del scope["root_path"]

    assert canonical_request_from_asgi_scope(scope).path == "/v1/people/person_123"


@pytest.mark.parametrize("scope", [object(), {"type": "http"}])
def test_scope_shape_must_preserve_exact_asgi_transport_evidence(scope: object) -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(scope)


@pytest.mark.parametrize("scope_type", [object(), "websocket"])
def test_non_http_scope_fails_closed(scope_type: object) -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(_scope(type=scope_type))


@pytest.mark.parametrize("root_path", [object(), "/gateway"])
def test_root_path_is_exact_and_empty(root_path: object) -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(_scope(root_path=root_path))


def test_missing_raw_path_fails_closed_instead_of_trusting_decoded_path() -> None:
    scope = _scope()
    del scope["raw_path"]

    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(scope)


@pytest.mark.parametrize(
    "raw_path",
    [
        object(),
        b"",
        b"/" + b"a" * 2048,
    ],
)
def test_raw_path_requires_exact_bounded_bytes(raw_path: object) -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(_scope(raw_path=raw_path))


@pytest.mark.parametrize(
    "raw_path",
    [
        b"/v1/people/%70erson_123",
        b"/v1/people/person_123?view=summary",
        b"/v1/people/person_123#fragment",
    ],
)
def test_raw_path_cannot_hide_encoded_query_or_fragment_material(raw_path: bytes) -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(_scope(raw_path=raw_path))


@pytest.mark.parametrize("query_string", [object(), b"view=summary"])
def test_query_string_is_rejected_before_request_routing(query_string: object) -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(_scope(query_string=query_string))


def test_missing_query_string_fails_closed() -> None:
    scope = _scope()
    del scope["query_string"]

    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(scope)


def test_raw_and_decoded_path_must_describe_the_same_bytes() -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(
            _scope(raw_path=b"/v1/people/person_999")
        )


def test_non_ascii_raw_path_is_outside_the_narrow_transport_profile() -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(
            _scope(
                path="/v1/people/한글",
                raw_path="/v1/people/한글".encode(),
            )
        )


@pytest.mark.parametrize(
    "method",
    ["get", "M-SEARCH", "THIS-METHOD-NAME-IS-LONGER"],
)
def test_transport_preserves_valid_http_method_tokens_for_capability_classification(
    method: str,
) -> None:
    request = canonical_request_from_asgi_scope(_scope(method=method))

    assert request.method == method


@pytest.mark.parametrize(
    ("overrides", "expected_error"),
    [
        ({"method": object()}, CompositionRequestError),
        ({"path": "/v1/people/../admin", "raw_path": b"/v1/people/../admin"}, CompositionRequestError),
        ({"path": object(), "raw_path": b"/v1/people/person_123"}, CompositionRequestError),
    ],
)
def test_transport_rejects_malformed_method_or_path_before_request_routing(
    overrides: dict[str, object],
    expected_error: type[Exception],
) -> None:
    with pytest.raises(expected_error):
        canonical_request_from_asgi_scope(_scope(**overrides))


def test_asgi_route_adapter_normalizes_before_calling_request_router(monkeypatch) -> None:
    calls: list[tuple[object, object, object, str, str]] = []

    def fake_router(
        registry: object,
        deployment: object,
        snapshot: object,
        *,
        method: str,
        request_path: str,
    ) -> str:
        calls.append((registry, deployment, snapshot, method, request_path))
        return "people_record"

    monkeypatch.setattr(asgi_transport, "current_route_id_for_request", fake_router)
    registry = object()
    deployment = object()
    snapshot = object()

    assert current_route_id_for_asgi_scope(
        registry,
        deployment,
        snapshot,
        _scope(),
    ) == "people_record"
    assert calls == [
        (
            registry,
            deployment,
            snapshot,
            "GET",
            "/v1/people/person_123",
        )
    ]


def test_asgi_route_adapter_delegates_valid_extension_method_to_capability_boundary(
    monkeypatch,
) -> None:
    calls: list[str] = []

    def fake_router(
        registry: object,
        deployment: object,
        snapshot: object,
        *,
        method: str,
        request_path: str,
    ) -> str:
        calls.append(method)
        return "people_record"

    monkeypatch.setattr(asgi_transport, "current_route_id_for_request", fake_router)

    assert current_route_id_for_asgi_scope(
        object(),
        object(),
        object(),
        _scope(method="M-SEARCH"),
    ) == "people_record"
    assert calls == ["M-SEARCH"]


def test_invalid_transport_never_calls_request_router(monkeypatch) -> None:
    def fake_router(*args: object, **kwargs: object) -> str:
        raise AssertionError("invalid transport must fail before request routing")

    monkeypatch.setattr(asgi_transport, "current_route_id_for_request", fake_router)

    with pytest.raises(CompositionTransportError):
        current_route_id_for_asgi_scope(
            object(),
            object(),
            object(),
            _scope(query_string=b"page=2"),
        )
