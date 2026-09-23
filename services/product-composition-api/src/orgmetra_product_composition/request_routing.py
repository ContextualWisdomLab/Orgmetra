"""Resolve one canonical request against current durable composition authority.

The resolver deliberately separates declared route selection from route availability. A concrete
Path Item declared by the active generation wins before availability is considered, so an
unavailable optional concrete route cannot fall through to a broader available template route.
The function returns only the stable route identifier; owner transport and HTTP response mapping
remain later serving responsibilities.
"""

from __future__ import annotations

import re
from threading import RLock
from weakref import WeakKeyDictionary

from .activation import ActivationConflictError, DeploymentIdentity
from .activation_runtime_integrity import AuthorizedPostgresActivationRegistry
from .admission import CompositionGeneration, CompositionRoute, _ALLOWED_METHODS
from .serving_snapshot import RecoveredRouteSnapshot, current_route_ids_for_snapshot

_REQUEST_METHOD = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_REQUEST_PATH = re.compile(r"^/v[0-9]+(?:/[A-Za-z0-9._:-]+)+$")
_TEMPLATE_SEGMENT = re.compile(r"^\{[a-z][a-z0-9_]{0,63}\}$")


class CompositionRoutingError(RuntimeError):
    """Base error for fail-closed product-composition request selection."""


class CompositionRequestError(CompositionRoutingError):
    """Raised when transport input is not in the canonical request-routing profile."""


class CompositionRouteNotFoundError(CompositionRoutingError):
    """Raised when the active generation declares no Path Item for the request path."""


class CompositionMethodNotImplementedError(CompositionRoutingError):
    """Raised when a canonical method is outside the composition server's implemented profile."""


class CompositionMethodNotAllowedError(CompositionRoutingError):
    """Raised with current methods when one selected Path Item rejects the request method."""

    __slots__ = ("allowed_methods", "__weakref__")

    def __init__(self, message: str, *, allowed_methods: tuple[object, ...]) -> None:
        """Issue one canonical Allow authority, including implicit HEAD parity for GET."""

        if type(allowed_methods) is not tuple:
            raise CompositionRoutingError("method rejection requires tuple Allow authority")
        canonical_method_set = {
            _canonical_request_method(method) for method in allowed_methods
        }
        if any(method not in _ALLOWED_METHODS for method in canonical_method_set):
            raise CompositionRoutingError(
                "method rejection Allow authority must use implemented composition methods"
            )
        if "GET" in canonical_method_set:
            canonical_method_set.add("HEAD")
        self.allowed_methods = tuple(sorted(canonical_method_set))
        super().__init__(message)
        _record_method_rejection_authority(self)


class CompositionRouteUnavailableError(CompositionRoutingError):
    """Raised when the selected declared route lacks current positive availability evidence."""


def _build_method_rejection_authority_runtime():
    """Keep construction-time 405 authority outside mutable exception attributes."""

    issued: WeakKeyDictionary[CompositionMethodNotAllowedError, tuple[str, ...]] = (
        WeakKeyDictionary()
    )
    state_lock = RLock()
    missing = object()

    def record(error: CompositionMethodNotAllowedError) -> None:
        """Record the one canonical method set issued with an error instance."""

        with state_lock:
            issued[error] = error.allowed_methods

    def require(error: CompositionMethodNotAllowedError) -> tuple[str, ...]:
        """Return issued authority only while public exception state still matches it."""

        with state_lock:
            canonical = issued.get(error, missing)
            if canonical is missing:
                raise CompositionRoutingError(
                    "method rejection lacks construction-time Allow authority"
                )
            try:
                current = error.allowed_methods
            except AttributeError as exc:
                raise CompositionRoutingError(
                    "method rejection Allow authority is no longer available"
                ) from exc
            if current != canonical:
                raise CompositionRoutingError(
                    "method rejection Allow authority changed after construction"
                )
            return canonical

    return record, require


_record_method_rejection_authority, _require_method_rejection_authority = (
    _build_method_rejection_authority_runtime()
)


def _canonical_request_method(method: object) -> str:
    """Require one exact RFC 9110 HTTP method token without inventing owner operations."""

    if type(method) is not str or _REQUEST_METHOD.fullmatch(method) is None:
        raise CompositionRequestError("request method must be an exact HTTP token")
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


def _route_supports_request_method(route: CompositionRoute, method: str) -> bool:
    """Treat HEAD as the metadata-only counterpart of a declared GET route."""

    return method in route.methods or (method == "HEAD" and "GET" in route.methods)


def _advertised_route_methods(route: CompositionRoute) -> frozenset[str]:
    """Return current HTTP methods exposed by one route, including implicit HEAD for GET."""

    methods = set(route.methods)
    if "GET" in methods:
        methods.add("HEAD")
    return frozenset(methods)


def _current_route_ids(
    registry: AuthorizedPostgresActivationRegistry,
    deployment: DeploymentIdentity,
    snapshot: RecoveredRouteSnapshot,
) -> frozenset[str]:
    """Project superseded durable serving state as route unavailability, not HTTP method truth.

    ``ActivationConflictError`` is the typed #437 signal that the recovery-bound snapshot no longer
    matches current durable activation/recovery state. That is a serviceability failure for this
    request. Authorization/integrity failures deliberately remain unwrapped so they cannot be
    laundered into an ordinary availability response.
    """

    try:
        return frozenset(current_route_ids_for_snapshot(registry, deployment, snapshot))
    except ActivationConflictError as exc:
        raise CompositionRouteUnavailableError(
            "recovered route snapshot no longer has current durable serving authority"
        ) from exc


def current_route_id_for_request(
    registry: AuthorizedPostgresActivationRegistry,
    deployment: DeploymentIdentity,
    snapshot: RecoveredRouteSnapshot,
    *,
    method: str,
    request_path: str,
) -> str:
    """Return the current stable route ID for one canonical request or fail closed.

    Request syntax and server method capability are resolved before declared Path Item selection.
    HEAD shares GET route authority because RFC 9110 defines HEAD as GET without response content;
    owner dispatch remains a later boundary. A selected path crosses ``current_route_ids_for_snapshot``
    when needed either to advertise the resource's current RFC 9110 ``Allow`` authority or to prove
    the requested route is serviceable. Selection runs over the complete declared generation first
    and applies concrete-before-template precedence before availability is considered.
    """

    canonical_method = _canonical_request_method(method)
    canonical_path = _canonical_request_path(request_path)
    if canonical_method not in _ALLOWED_METHODS:
        raise CompositionMethodNotImplementedError(
            "request method is outside the implemented composition HTTP profile"
        )

    generation = snapshot.generation
    path_routes = _selected_path_routes(generation, canonical_path)
    method_routes = tuple(
        route for route in path_routes if _route_supports_request_method(route, canonical_method)
    )
    if not method_routes:
        available_route_ids = _current_route_ids(registry, deployment, snapshot)
        allowed_methods = tuple(
            sorted(
                {
                    method
                    for route in path_routes
                    if route.route_id in available_route_ids
                    for method in _advertised_route_methods(route)
                }
            )
        )
        raise CompositionMethodNotAllowedError(
            "selected declared Path Item does not admit request method",
            allowed_methods=allowed_methods,
        )
    if len(method_routes) != 1:
        raise CompositionRoutingError(
            "active generation exposes ambiguous method authority after admission"
        )

    selected_route = method_routes[0]
    selected_route_id = selected_route.route_id
    available_route_ids = _current_route_ids(registry, deployment, snapshot)
    if selected_route_id not in available_route_ids:
        raise CompositionRouteUnavailableError(
            "selected declared route lacks current positive availability evidence"
        )
    return selected_route_id
