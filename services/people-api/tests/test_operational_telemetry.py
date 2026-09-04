"""Regression coverage for privacy-safe, low-cardinality People HTTP telemetry."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass, field
import logging
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
    assert classify_people_http_route("/v1/tenants//people/value") is None
    assert classify_people_http_route("/v1/tenants//candidate-worker-conversions") is None
    assert classify_people_http_route("/v1/not-a-people-route") is None
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
    assert normalize_http_method("_OTHER") == "_OTHER"
    assert normalize_http_method(ForgedMethod("BREW")) == "_OTHER"
    assert normalize_http_method(None) == "_OTHER"


def test_rejects_unusable_middleware_dependencies_before_traffic() -> None:
    """Fail fast when the wrapped app, sink, or monotonic clock cannot be called."""
    sink = _RecordingSink()

    with pytest.raises(TypeError, match="app"):
        PeopleHttpTelemetryMiddleware(app=None, sink=sink)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="sink"):
        PeopleHttpTelemetryMiddleware(app=_success_app(), sink=object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="clock"):
        PeopleHttpTelemetryMiddleware(
            app=_success_app(), sink=sink, clock=None  # type: ignore[arg-type]
        )


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


def test_ignores_invalid_and_duplicate_response_start_statuses() -> None:
    """Measure the first valid status without trusting bools or later duplicate starts."""
    sink = _RecordingSink()

    async def unusual_app(scope: Any, receive: Any, send: Any) -> None:
        """Emit an invalid status, then the first valid status, then a duplicate start."""
        del scope, receive
        await send({"type": "http.response.start", "status": True, "headers": []})
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.start", "status": 503, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    app = PeopleHttpTelemetryMiddleware(
        app=unusual_app, sink=sink, clock=_Clock([6.0, 6.2])
    )

    _run(app, _scope())

    assert sink.measurements[0].status_code == 204
    assert sink.measurements[0].error_type is None


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


def test_exporter_failure_never_breaks_people_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Keep telemetry best-effort so exporter outages cannot deny governed HR work."""
    sink = _RecordingSink(fail=True)
    app = PeopleHttpTelemetryMiddleware(
        app=_success_app(), sink=sink, clock=_Clock([5.0, 5.01])
    )

    with caplog.at_level(logging.WARNING, logger="orgmetra_people_api.telemetry"):
        sent = _run(app, _scope())

    assert sent[0]["status"] == 200
    assert sink.measurements == []
    records = [
        record
        for record in caplog.records
        if getattr(record, "telemetry_event", None)
        == "http_server_request_measurement_rejected"
    ]
    assert len(records) == 1
    assert records[0].getMessage() == "People HTTP telemetry measurement was not exported"
    assert "exporter unavailable" not in records[0].getMessage()


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
        ({"error_type": 503}, "error_type"),
        ({"error_type": "database-secret"}, "error_type"),
        ({"status_code": 200, "error_type": "503"}, "error_type"),
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


class _ExplodingClock:
    """Simulate a telemetry clock source that fails on every sample."""

    def __call__(self) -> float:
        """Raise to model an unavailable monotonic clock source."""
        raise RuntimeError("clock source unavailable")


def test_clock_failure_at_request_start_never_blocks_the_wrapped_hr_request() -> None:
    """A failing start-time clock must not propagate into the served HR request."""
    sink = _RecordingSink()
    middleware = PeopleHttpTelemetryMiddleware(
        app=_success_app(),
        sink=sink,
        clock=_ExplodingClock(),
    )

    sent = _run(middleware, _scope())

    starts = [m.get("status") for m in sent if m.get("type") == "http.response.start"]
    assert starts == [200]
    assert sink.measurements == []


def test_clock_failure_at_completion_is_swallowed_without_export() -> None:
    """A failing completion-time clock degrades telemetry instead of the request."""
    sink = _RecordingSink()

    class _HalfBrokenClock:
        """Serve one start sample, then fail for every later sample."""

        def __init__(self) -> None:
            """Arm exactly one successful start-time sample."""
            self._calls = 0

        def __call__(self) -> float:
            """Return the deterministic start sample once, then raise."""
            self._calls += 1
            if self._calls == 1:
                return 10.0
            raise RuntimeError("clock source unavailable")

    middleware = PeopleHttpTelemetryMiddleware(
        app=_success_app(),
        sink=sink,
        clock=_HalfBrokenClock(),
    )

    sent = _run(middleware, _scope())

    starts = [m.get("status") for m in sent if m.get("type") == "http.response.start"]
    assert starts == [200]
    assert sink.measurements == []


def test_telemetry_surface_is_importable_from_package_root() -> None:
    """Deployment adapters must compose telemetry through the public package surface."""
    from orgmetra_people_api import (  # noqa: PLC0415 - import-surface regression
        PeopleHttpRequestMeasurement as ExportedMeasurement,
        PeopleHttpTelemetryMiddleware as ExportedMiddleware,
        classify_people_http_route as ExportedClassifier,
        normalize_http_method as ExportedNormalizer,
    )

    assert ExportedMiddleware is PeopleHttpTelemetryMiddleware
    assert ExportedMeasurement is PeopleHttpRequestMeasurement
    assert ExportedClassifier is classify_people_http_route
    assert ExportedNormalizer is normalize_http_method


def test_clock_failure_at_request_start_logs_degradation_exactly_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """One degraded request must emit exactly one value-free warning record."""
    sink = _RecordingSink()
    middleware = PeopleHttpTelemetryMiddleware(
        app=_success_app(),
        sink=sink,
        clock=_ExplodingClock(),
    )

    with caplog.at_level(logging.WARNING, logger="orgmetra_people_api.telemetry"):
        _run(middleware, _scope())

    degradation_records = [
        record for record in caplog.records
        if getattr(record, "telemetry_event", None)
        == "http_server_request_measurement_rejected"
    ]
    assert len(degradation_records) == 1
