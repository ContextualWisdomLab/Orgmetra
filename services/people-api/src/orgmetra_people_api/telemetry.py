"""Privacy-safe, low-cardinality operational telemetry for the People HTTP boundary.

This module deliberately does not depend on an OpenTelemetry SDK or exporter. It
captures one stable request-duration measurement that a deployment adapter can
map to ``http.server.request.duration`` while keeping HR identifiers, raw paths,
query strings, headers, credentials, payload values, and backend exception text
out of metric dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import logging
from time import perf_counter
from typing import Awaitable, Callable, Mapping, Protocol

AsgiReceive = Callable[[], Awaitable[dict[str, object]]]
AsgiSend = Callable[[dict[str, object]], Awaitable[None]]
AsgiApp = Callable[[Mapping[str, object], AsgiReceive, AsgiSend], Awaitable[None]]
Clock = Callable[[], float]

_LOGGER = logging.getLogger(__name__)
_MAX_ROUTE_PATH_CHARACTERS = 256
_KNOWN_HTTP_METHODS = frozenset(
    {
        "CONNECT",
        "DELETE",
        "GET",
        "HEAD",
        "OPTIONS",
        "PATCH",
        "POST",
        "PUT",
        "QUERY",
        "TRACE",
        "_OTHER",
    }
)
_PEOPLE_ROUTE_TEMPLATES = frozenset(
    {
        "/v1/tenants/{tenant_record_id}/people/{person_record_id}",
        "/v1/tenants/{tenant_record_id}/candidate-worker-conversions",
        "/v1/employment-records",
        "/v1/position-records",
        "/v1/assignment-records",
    }
)
_BOUNDED_ERROR_TYPES = frozenset({"unhandled_exception", "missing_response_status"})


class PeopleMetricSink(Protocol):
    """Receive one privacy-minimized HTTP server request measurement."""

    def record_http_server_request(self, measurement: "PeopleHttpRequestMeasurement") -> None:
        """Record one request-duration measurement without changing request outcome."""


@dataclass(frozen=True, slots=True)
class PeopleHttpRequestMeasurement:
    """Represent one bounded HTTP request-duration sample for operational use.

    ``route_template`` is either one application-owned template or ``None``; it
    is never a raw URL path. ``error_type`` is either a bounded middleware state
    or the decimal HTTP 5xx status. These constraints make aggregation useful
    without creating tenant/person/candidate-level metric cardinality.
    """

    method: str
    route_template: str | None
    status_code: int | None
    duration_seconds: float
    error_type: str | None

    def __post_init__(self) -> None:
        """Reject direct construction that could create unsafe metric dimensions."""
        if type(self.method) is not str or self.method not in _KNOWN_HTTP_METHODS:
            raise ValueError("method must be one canonical known HTTP method or _OTHER")
        if self.route_template is not None and (
            type(self.route_template) is not str
            or self.route_template not in _PEOPLE_ROUTE_TEMPLATES
        ):
            raise ValueError("route_template must be one bounded People route template or None")
        if self.status_code is not None and (
            type(self.status_code) is not int or not 100 <= self.status_code <= 599
        ):
            raise ValueError("status_code must be an HTTP status integer or None")
        if (
            type(self.duration_seconds) is not float
            or not isfinite(self.duration_seconds)
            or self.duration_seconds < 0.0
        ):
            raise ValueError("duration_seconds must be one finite non-negative float")
        self._validate_error_type()

    def _validate_error_type(self) -> None:
        """Keep server-error dimensions finite and internally consistent."""
        if self.error_type is None:
            return
        if type(self.error_type) is not str:
            raise ValueError("error_type must be one bounded error code or None")
        if self.error_type in _BOUNDED_ERROR_TYPES:
            return
        if (
            self.status_code is None
            or self.status_code < 500
            or self.error_type != str(self.status_code)
        ):
            raise ValueError("error_type must be a matching HTTP 5xx status or bounded error code")


def normalize_http_method(value: object) -> str:
    """Map a request method to the current finite OpenTelemetry-known method set."""
    if type(value) is str and value in _KNOWN_HTTP_METHODS and value != "_OTHER":
        return value
    return "_OTHER"


def classify_people_http_route(path: object) -> str | None:
    """Return a low-cardinality People route template without exposing raw path data."""
    if type(path) is not str or len(path) > _MAX_ROUTE_PATH_CHARACTERS:
        return None
    parts = path.strip("/").split("/")
    if (
        len(parts) == 5
        and parts[0] == "v1"
        and parts[1] == "tenants"
        and bool(parts[2])
        and parts[3] == "people"
        and bool(parts[4])
    ):
        return "/v1/tenants/{tenant_record_id}/people/{person_record_id}"
    if (
        len(parts) == 4
        and parts[0] == "v1"
        and parts[1] == "tenants"
        and bool(parts[2])
        and parts[3] == "candidate-worker-conversions"
    ):
        return "/v1/tenants/{tenant_record_id}/candidate-worker-conversions"
    if len(parts) == 2 and parts[0] == "v1":
        static_route = f"/v1/{parts[1]}"
        if static_route in _PEOPLE_ROUTE_TEMPLATES:
            return static_route
    return None


@dataclass(frozen=True, slots=True)
class PeopleHttpTelemetryMiddleware:
    """Measure one wrapped People ASGI app without making telemetry authoritative.

    Export is deliberately best-effort: a sink/configuration failure is logged
    with bounded metadata and never changes the wrapped HR request's status or
    exception behavior. Non-HTTP ASGI scopes pass through without HTTP metrics.
    """

    app: AsgiApp
    sink: PeopleMetricSink
    clock: Clock = perf_counter

    def __post_init__(self) -> None:
        """Reject unusable dependency injection before accepting traffic."""
        if not callable(self.app):
            raise TypeError("app must be callable")
        if not callable(getattr(self.sink, "record_http_server_request", None)):
            raise TypeError("sink must implement record_http_server_request")
        if not callable(self.clock):
            raise TypeError("clock must be callable")

    async def __call__(
        self,
        scope: Mapping[str, object],
        receive: AsgiReceive,
        send: AsgiSend,
    ) -> None:
        """Run the wrapped app and emit one privacy-minimized completion measurement."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        started_at: float | None
        try:
            started_at = self.clock()
        except Exception:  # noqa: BLE001 - telemetry must never become HR request authority.
            started_at = None
        status_code: int | None = None

        async def measured_send(message: dict[str, object]) -> None:
            """Capture only the first valid response status before forwarding the frame."""
            nonlocal status_code
            if status_code is None and message.get("type") == "http.response.start":
                candidate = message.get("status")
                if type(candidate) is int and 100 <= candidate <= 599:
                    status_code = candidate
            await send(message)

        try:
            await self.app(scope, receive, measured_send)
        except Exception:
            self._record_completion(
                scope=scope,
                started_at=started_at,
                status_code=status_code,
                error_type="unhandled_exception",
            )
            raise

        error_type: str | None
        if status_code is None:
            error_type = "missing_response_status"
        elif status_code >= 500:
            error_type = str(status_code)
        else:
            error_type = None
        self._record_completion(
            scope=scope,
            started_at=started_at,
            status_code=status_code,
            error_type=error_type,
        )

    def _record_completion(
        self,
        *,
        scope: Mapping[str, object],
        started_at: float | None,
        status_code: int | None,
        error_type: str | None,
    ) -> None:
        """Best-effort emit one bounded measurement without leaking request values."""
        if started_at is None:
            self._warn_measurement_not_exported()
            return
        try:
            duration_seconds = float(self.clock() - started_at)
            measurement = PeopleHttpRequestMeasurement(
                method=normalize_http_method(scope.get("method")),
                route_template=classify_people_http_route(scope.get("path")),
                status_code=status_code,
                duration_seconds=duration_seconds,
                error_type=error_type,
            )
            self.sink.record_http_server_request(measurement)
        except Exception:  # noqa: BLE001 - telemetry must never become HR request authority.
            self._warn_measurement_not_exported()

    def _warn_measurement_not_exported(self) -> None:
        """Log one bounded, value-free telemetry degradation record."""
        _LOGGER.warning(
            "People HTTP telemetry measurement was not exported",
            extra={
                "telemetry_event": "http_server_request_measurement_rejected",
            },
        )
