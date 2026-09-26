"""Bind ASGI request-target bytes to the narrow product-composition route contract."""

from __future__ import annotations

from dataclasses import dataclass

from .activation import DeploymentIdentity
from .activation_runtime_integrity import AuthorizedPostgresActivationRegistry
from .request_routing import (
    CompositionRequestError,
    _canonical_request_method,
    _canonical_request_path,
    current_route_id_for_request,
)
from .serving_snapshot import RecoveredRouteSnapshot


class CompositionTransportError(CompositionRequestError):
    """Raised when ASGI transport evidence cannot identify one canonical request target."""


@dataclass(frozen=True, slots=True)
class CanonicalHttpRequest:
    """Detached canonical method/path coordinates admitted from one ASGI HTTP scope."""

    method: str
    path: str


def canonical_request_from_asgi_scope(scope: object) -> CanonicalHttpRequest:
    """Detach one exact canonical request from an ASGI HTTP scope or fail closed.

    ``raw_path`` is mandatory even though ASGI permits servers to omit it. Without the original
    bytes this boundary cannot prove that a canonical decoded path was not produced by percent
    decoding or another transport normalization. Query strings and mounted ``root_path`` values are
    outside the current product-route profile rather than being silently discarded or rewritten.
    """

    if type(scope) is not dict:
        raise CompositionTransportError("ASGI scope must be an exact built-in dict")
    if type(scope.get("type")) is not str or scope["type"] != "http":
        raise CompositionTransportError("ASGI scope must describe one HTTP request")

    root_path = scope.get("root_path", "")
    if type(root_path) is not str or root_path != "":
        raise CompositionTransportError("non-empty ASGI root_path is outside the route profile")

    raw_path = scope.get("raw_path")
    if type(raw_path) is not bytes or not raw_path or len(raw_path) > 2048:
        raise CompositionTransportError("ASGI raw_path must be exact bounded request-target bytes")

    query_string = scope.get("query_string")
    if type(query_string) is not bytes or query_string:
        raise CompositionTransportError("query strings are outside the canonical route profile")

    if any(marker in raw_path for marker in (b"%", b"?", b"#")):
        raise CompositionTransportError(
            "raw request path must not contain encoded, query, or fragment material"
        )
    try:
        raw_ascii_path = raw_path.decode("ascii")
    except UnicodeDecodeError as error:
        raise CompositionTransportError(
            "raw request path must use the admitted ASCII route profile"
        ) from error

    canonical_method = _canonical_request_method(scope.get("method"))
    canonical_path = _canonical_request_path(scope.get("path"))
    if raw_ascii_path != canonical_path:
        raise CompositionTransportError(
            "ASGI raw_path and decoded path must identify the same canonical path"
        )
    return CanonicalHttpRequest(method=canonical_method, path=canonical_path)


def current_route_id_for_asgi_scope(
    registry: AuthorizedPostgresActivationRegistry,
    deployment: DeploymentIdentity,
    snapshot: RecoveredRouteSnapshot,
    scope: object,
) -> str:
    """Resolve one ASGI scope only after transport coordinates are canonical and detached."""

    request = canonical_request_from_asgi_scope(scope)
    return current_route_id_for_request(
        registry,
        deployment,
        snapshot,
        method=request.method,
        request_path=request.path,
    )
