"""Regression coverage for privacy-safe, low-cardinality People HTTP telemetry."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import pytest

from orgmetra_people_api.telemetry import (
    PeopleHttpRequestMeasurement,
    PeopleHttpTelemetryMiddleware,
    classify_people_http_route,
    normalize_http_method,
)


@dataclass
class _RecordingSink:
    """Collect emitted measurements without adding a telemetry dependency."""

    measurements: list[PeopleHttpRequestMeasurement] = field(default_factory=list)
    fail: bool = False

    def record_http_server_request(self, measurement: PeopleHttpRequestMeasurement) -> None:
        """Record one request measurement or simulate an exporter outage."""
        if self.fail:
            raise RuntimeError("exporter unavailable")
        self.measurements.append(measurement)


class _Clock:
    """Return deterministic monotonic samples for middleware tests."""

    def __init__(self, samples: Iterable[float]) -> None:
        """Store a finite sequence of deterministic samples."""
        self._samples = iter(samples)

    def __call__(self) -> float:
        """Return the next deterministic clock sample."""
        return next(self._samples)


def _scope(*, method: object = "GET", path: object = "/v1/employment-records") -> dict[str, object]:
    """Build one minimal HTTP ASGI scope for telemetry tests."""
    return {"type": "http", "method": method, "path": path}


async def _receive() -> dict[str, object]:
    """Return an empty terminal request-body frame."""
    return {"type": "http.request", "body": b"", "more_body": False}


def _run(app: PeopleHttpTelemetryMiddleware, scope: dict[str, object]) -> list[dict[str, object]]:
    """Execute one middleware request and return downstream ASGI messages."""
    sent: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        """Collect one downstream ASGI message."""
        sent.append(message)

    asyncio.run(app(scope, _receive, send))
    return sent


def _success_app(status: int = 200):
    """Build a downstream ASGI app that emits one bounded response."""

    async def app(scope: dict[str, object], receive: Any, send: Any) -> None:
        """Emit one response start and one empty body."""
        del scope, receive
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    return app


def test_classifies_only_known_low_cardinality_people_routes() -> None:
    """Never copy tenant/person identifiers or arbitrary paths into metric labels."""
    tenant = "018f46d3-5d20-7d44-a3c0-7ae917d96534"
    person = "c18e31fd-1ab6-40b8-9ee6-866fed735ee1"

    assert classify_people_http_route(f"/v1/tenants/{tenant}/people/{person}") == (
        "/v1/tenants/{tenant_record_id}/people/{person_record_id}"
    )
    assert classify_people_http_route(f"/v1/tenants/{tenant}/candidate-worker-conversions") == (
        "/v1/tenants/{tenant_record_id}/candidate-worker-conversions"
    )
    assert classify_people_http_route("/v1/employment-records") == "/v1/employment-records"
    assert classify_people_http_route("/v1/position-records") == "/v1/position-records"
    assert classify_people_http_route("/v1/assignment-records") == "/v1/assignment-records"
    assert classify_people_http_route(f"/v1/tenants/{tenant}/secret/{person}") is None
    assert classify_people_http_route("/" + "x" * 300) is None
    assert classify_people_http_route(123) is None


def test_normalizes_unknown_or_runtime_subclass_methods_to_other() -> None:
    """Keep the method label finite and avoid executing caller-controlled equality."""

    class ForgedMethod(str):
        """Represent hostile request text whose equality must never be trusted."""

        def __eq__(self, other: object) -> bool:
            """Pretend to be any known method."""
            return True

        def __hash__(self) -> int:
            """Pretend to hash like GET."""
            return hash("GET")

    assert normalize_http_method("GET") == "GET"
    assert normalize_http_method("POST") == "POST"
    assert normalize_http_method("BREW") == "_OTHER"
    assert normalize_http_method(ForgedMethod("BREW")) == "_OTHER"
    assert normalize_http_method(None) == "_OTHER"


def test_emits_duration_without_identifying_request_values() -> None:
    """Emit only a route template, method, status, duration, and bounded error state."""
    sink = _RecordingSink()
    tenant = "018f46d3-5d20-7d44-a3c0-7ae917d96534"
    person = "c18e31fd-1ab6-40b8-9ee6-866fed735ee1"
    app = PeopleHttpTelemetryMiddleware(
        app=_success_app(), sink=sink, clock=_Clock([10.0, 10.125])
    )

    _run(app, _scope(path=f"/v1/tenants/{tenant}/people/{person}"))

    assert sink.measurements == [
        PeopleHttpRequestMeasurement(
            method="GET",
            route_template="/v1/tenants/{tenant_record_id}/people/{person_record_id}",
            status_code=200,
            duration_seconds=0.125,
            error_type=None,
        )
    ]
    rendered = repr(sink.measurements[0])
    assert tenant not in rendered
    assert person not in rendered


def test_records_server_error_as_low_cardinality_status_error_type() -> None:
    """Represent server failures by bounded HTTP status rather than backend exception text."""
    sink = _RecordingSink()
    app = PeopleHttpTelemetryMiddleware(
        app=_success_app(503), sink=sink, clock=_Clock([4.0, 4.5])
    )

    _run(app, _scope(method="POST", path="/v1/employment-records"))

    assert sink.measurements[0].status_code == 503
    assert sink.measurements[0].error_type == "503"


def test_does_not_mark_client_error_as_server_failure() -> None:
    """Keep a normal 4xx response out of the server-error dimension."""
    sink = _RecordingSink()
    app = PeopleHttpTelemetryMiddleware(
        app=_success_app(403), sink=sink, clock=_Clock([2.0, 2.25])
    )

    _run(app, _scope(method="POST", path="/v1/assignment-records"))

    assert sink.measurements[0].status_code == 403
    assert sink.measurements[0].error_type is None


def test_unknown_route_never_uses_raw_path_as_metric_route() -> None:
    """Omit http.route when the application route template is not known."""
    sink = _RecordingSink()
    raw_path = "/customer/acme/employee/alice@example.com"
    app = PeopleHttpTelemetryMiddleware(
        app=_success_app(404), sink=sink, clock=_Clock([1.0, 1.1])
    )

    _run(app, _scope(path=raw_path))

    measurement = sink.measurements[0]
    assert measurement.route_template is None
    assert raw_path not in repr(measurement)


def test_unhandled_exception_is_measured_then_reraised() -> None:
    """Keep failure observability without turning telemetry into exception handling."""
    sink = _RecordingSink()

    async def failing_app(scope: Any, receive: Any, send: Any) -> None:
        """Raise before an HTTP status is emitted."""
        del scope, receive, send
        raise LookupError("sensitive backend detail")

    app = PeopleHttpTelemetryMiddleware(
        app=failing_app, sink=sink, clock=_Clock([8.0, 8.2])
    )

    with pytest.raises(LookupError, match="sensitive backend detail"):
        _run(app, _scope())

    measurement = sink.measurements[0]
    assert measurement.status_code is None
    assert measurement.error_type == "unhandled_exception"
    assert "LookupError" not in repr(measurement)
    assert "sensitive backend detail" not in repr(measurement)


def test_missing_response_start_is_bounded_operational_error() -> None:
    """Flag a downstream ASGI contract failure without copying arbitrary details."""
    sink = _RecordingSink()

    async def missing_start_app(scope: Any, receive: Any, send: Any) -> None:
        """Return a body without an HTTP response-start frame."""
        del scope, receive
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    app = PeopleHttpTelemetryMiddleware(
        app=missing_start_app, sink=sink, clock=_Clock([3.0, 3.1])
    )

    _run(app, _scope())

    assert sink.measurements[0].status_code is None
    assert sink.measurements[0].error_type == "missing_response_status"


def test_exporter_failure_never_breaks_people_response() -> None:
    """Keep telemetry best-effort so exporter outages cannot deny governed HR work."""
    sink = _RecordingSink(fail=True)
    app = PeopleHttpTelemetryMiddleware(
        app=_success_app(), sink=sink, clock=_Clock([5.0, 5.01])
    )

    sent = _run(app, _scope())

    assert sent[0]["status"] == 200
    assert sink.measurements == []


def test_non_http_scope_passes_through_without_measurement() -> None:
    """Do not attach HTTP metric semantics to lifespan or other ASGI scopes."""
    sink = _RecordingSink()
    called: list[str] = []

    async def lifespan_app(scope: Any, receive: Any, send: Any) -> None:
        """Record that the non-HTTP scope reached the wrapped application."""
        del receive, send
        called.append(str(scope["type"]))

    app = PeopleHttpTelemetryMiddleware(
        app=lifespan_app, sink=sink, clock=_Clock([])
    )
    asyncio.run(app({"type": "lifespan"}, _receive, lambda message: None))

    assert called == ["lifespan"]
    assert sink.measurements == []


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"method": "get"}, "method"),
        ({"route_template": "/raw/customer/123"}, "route_template"),
        ({"status_code": 99}, "status_code"),
        ({"duration_seconds": -0.1}, "duration_seconds"),
        ({"error_type": "database-secret"}, "error_type"),
    ],
)
def test_measurement_rejects_unbounded_or_noncanonical_dimensions(
    kwargs: dict[str, object], message: str
) -> None:
    """Fail closed when direct construction could create unsafe metric dimensions."""
    values: dict[str, object] = {
        "method": "GET",
        "route_template": "/v1/employment-records",
        "status_code": 200,
        "duration_seconds": 0.1,
        "error_type": None,
    }
    values.update(kwargs)

    with pytest.raises((TypeError, ValueError), match=message):
        PeopleHttpRequestMeasurement(**values)  # type: ignore[arg-type]
