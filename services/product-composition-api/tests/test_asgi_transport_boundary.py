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


def test_non_http_scope_fails_closed() -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(_scope(type="websocket"))


def test_missing_raw_path_fails_closed_instead_of_trusting_decoded_path() -> None:
    scope = _scope()
    del scope["raw_path"]

    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(scope)


def test_percent_encoded_raw_path_cannot_alias_a_canonical_decoded_path() -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(
            _scope(raw_path=b"/v1/people/%70erson_123")
        )


def test_query_string_is_rejected_before_request_routing() -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(_scope(query_string=b"view=summary"))


def test_raw_and_decoded_path_must_describe_the_same_bytes() -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(
            _scope(raw_path=b"/v1/people/person_999")
        )


def test_nonempty_root_path_is_not_silently_folded_into_route_identity() -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(_scope(root_path="/gateway"))


def test_non_ascii_raw_path_is_outside_the_narrow_transport_profile() -> None:
    with pytest.raises(CompositionTransportError):
        canonical_request_from_asgi_scope(
            _scope(
                path="/v1/people/한글",
                raw_path="/v1/people/한글".encode(),
            )
        )


def test_router_still_owns_canonical_method_and_path_validation() -> None:
    with pytest.raises(CompositionRequestError):
        canonical_request_from_asgi_scope(_scope(method="get"))


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
