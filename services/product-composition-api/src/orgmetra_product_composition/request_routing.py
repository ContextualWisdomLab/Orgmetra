"""Resolve one canonical request against current durable composition authority.

The resolver deliberately separates declared route selection from route availability. A concrete
Path Item declared by the active generation wins before availability is considered, so an
unavailable optional concrete route cannot fall through to a broader available template route.
The function returns only the stable route identifier; owner transport and HTTP response mapping
remain later serving responsibilities.
"""

from __future__ import annotations

import re

from .activation import DeploymentIdentity
from .activation_runtime_integrity import AuthorizedPostgresActivationRegistry
from .admission import CompositionGeneration, CompositionRoute
from .serving_snapshot import RecoveredRouteSnapshot, current_route_ids_for_snapshot

_REQUEST_METHOD = re.compile(r"^[A-Z]{1,16}$")
_REQUEST_PATH = re.compile(r"^/v[0-9]+(?:/[A-Za-z0-9._:-]+)+$")
_TEMPLATE_SEGMENT = re.compile(r"^\{[a-z][a-z0-9_]{0,63}\}$")


class CompositionRoutingError(RuntimeError):
    """Base error for fail-closed product-composition request selection."""


class CompositionRequestError(CompositionRoutingError):
    """Raised when transport input is not in the canonical request-routing profile."""


class CompositionRouteNotFoundError(CompositionRoutingError):
    """Raised when the active generation declares no Path Item for the request path."""


class CompositionMethodNotAllowedError(CompositionRoutingError):
    """Raised when the selected declared Path Item does not admit the request method."""


class CompositionRouteUnavailableError(CompositionRoutingError):
    """Raised when the selected declared route lacks current positive availability evidence."""


def _canonical_request_method(method: object) -> str:
    """Require one exact uppercase HTTP method token without inventing owner operations."""

    if type(method) is not str or _REQUEST_METHOD.fullmatch(method) is None:
        raise CompositionRequestError("request method must be an exact uppercase HTTP token")
    return method


def _canonical_request_path(request_path: object) -> str:
    """Require the decoded canonical product path profile before any durable-state read."""

    if type(request_path) is not str or not request_path or len(request_path) > 2048:
        raise CompositionRequestError("request path must be an exact bounded str")
    if _REQUEST_PATH.fullmatch(request_path) is None:
        raise CompositionRequestError("request path is outside the canonical product path profile")
    if any(segment in {".", ".."} for segment in request_path.split("/")):
        raise CompositionRequestError("request path must not contain dot segments")
    return request_path


def _route_matches_request_path(route: CompositionRoute, request_path: str) -> bool:
    """Match one admitted template against one already-canonical decoded request path."""

    route_segments = route.path_template.strip("/").split("/")
    request_segments = request_path.strip("/").split("/")
    if len(route_segments) != len(request_segments):
        return False
    return all(
        route_segment == request_segment or _TEMPLATE_SEGMENT.fullmatch(route_segment) is not None
        for route_segment, request_segment in zip(route_segments, request_segments, strict=True)
    )


def _selected_path_routes(
    generation: CompositionGeneration,
    request_path: str,
) -> tuple[CompositionRoute, ...]:
    """Select the declared Path Item before availability or operation selection is considered."""

    exact_routes = tuple(
        route for route in generation.routes if route.path_template == request_path
    )
    if exact_routes:
        return exact_routes

    template_routes = tuple(
        route
        for route in generation.routes
        if _route_matches_request_path(route, request_path)
    )
    if template_routes:
        return template_routes
    raise CompositionRouteNotFoundError("active generation declares no route for request path")


def current_route_id_for_request(
    registry: AuthorizedPostgresActivationRegistry,
    deployment: DeploymentIdentity,
    snapshot: RecoveredRouteSnapshot,
    *,
    method: str,
    request_path: str,
) -> str:
    """Return the current stable route ID for one canonical request or fail closed.

    Request syntax is rejected before database use. Durable activation/recovery currentness is
    then linearized by ``current_route_ids_for_snapshot``. Route selection runs over the complete
    declared generation first, applies concrete-before-template precedence, chooses only an
    explicitly declared method, and checks positive route availability last. This ordering
    prevents an unavailable optional concrete Path Item from widening into a template route.
    """

    canonical_method = _canonical_request_method(method)
    canonical_path = _canonical_request_path(request_path)
    available_route_ids = frozenset(
        current_route_ids_for_snapshot(registry, deployment, snapshot)
    )
    generation = snapshot.generation
    path_routes = _selected_path_routes(generation, canonical_path)
    method_routes = tuple(
        route for route in path_routes if canonical_method in route.methods
    )
    if not method_routes:
        raise CompositionMethodNotAllowedError(
            "selected declared Path Item does not admit request method"
        )
    if len(method_routes) != 1:
        raise CompositionRoutingError(
            "active generation exposes ambiguous method authority after admission"
        )

    selected_route = method_routes[0]
    if selected_route.route_id not in available_route_ids:
        raise CompositionRouteUnavailableError(
            "selected declared route lacks current positive availability evidence"
        )
    return selected_route.route_id
