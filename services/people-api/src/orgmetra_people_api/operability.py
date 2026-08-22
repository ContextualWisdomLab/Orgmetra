"""PII-free liveness and owned-dependency readiness surfaces for People API.

Liveness proves only that the People API process can serve HTTP. Readiness is
stricter: it calls an injected probe for dependencies owned by this service and
returns unavailable until those dependencies can serve work. Identity providers
and other dedicated-writer CWL services are intentionally outside this probe so
the People API never reaches into their private implementation boundaries.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
import json
from typing import Any, Awaitable, Callable, Mapping, Protocol, runtime_checkable

AsgiReceive = Callable[[], Awaitable[dict[str, object]]]
AsgiSend = Callable[[dict[str, object]], Awaitable[None]]
PostgresConnectionFactory = Callable[[], AbstractContextManager[Any]]

_READ_ONLY_SQL = "SET TRANSACTION READ ONLY"
_READINESS_SQL = "SELECT 1"


@runtime_checkable
class ReadinessProbe(Protocol):
    """Check only dependencies whose availability is owned by the People API."""

    def check_ready(self) -> None:
        """Return normally when owned dependencies are ready; otherwise raise."""


@dataclass(frozen=True, slots=True)
class PostgresReadinessProbe:
    """Verify the Orgmetra PostgreSQL dependency without reading HR business data.

    Deployment code supplies the same kind of DB-API connection factory used by
    the People persistence adapters. The probe enters a read-only transaction
    and executes only ``SELECT 1``; it does not set tenant context or touch any
    application table because readiness is infrastructure evidence, not an HR
    data query.
    """

    connection_factory: PostgresConnectionFactory

    def __post_init__(self) -> None:
        """Reject an unusable connection factory before serving readiness traffic."""
        if not callable(self.connection_factory):
            raise TypeError("connection_factory must be callable")

    def check_ready(self) -> None:
        """Raise when PostgreSQL cannot complete the reviewed read-only probe."""
        with self.connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(_READ_ONLY_SQL)
                cursor.execute(_READINESS_SQL)
                row = cursor.fetchone()
        if row != (1,):
            raise RuntimeError("owned PostgreSQL readiness query returned an unexpected result")


@dataclass(frozen=True, slots=True)
class PeopleOperabilityAsgiApp:
    """Expose dependency-light `/health` and `/ready` endpoints for orchestration.

    ``/health`` never invokes dependencies and therefore remains suitable for a
    liveness probe that should not create restart loops during a database outage.
    ``/ready`` invokes the supplied owned-dependency probe and returns HTTP 503
    on any dependency failure. Neither route accepts credentials, reads HR data,
    returns dependency details, or claims that foreign CWL services are healthy.
    """

    readiness_probe: ReadinessProbe

    def __post_init__(self) -> None:
        """Require a concrete readiness contract before the app can be served."""
        if not isinstance(self.readiness_probe, ReadinessProbe):
            raise TypeError("readiness_probe must implement ReadinessProbe")

    async def __call__(self, scope: Mapping[str, object], receive: AsgiReceive, send: AsgiSend) -> None:
        """Serve one PII-free operability request with bounded failure responses."""
        del receive
        if scope.get("type") != "http":
            raise ValueError("PeopleOperabilityAsgiApp accepts only HTTP ASGI scopes")

        if scope.get("method") != "GET":
            await _send_json(
                send,
                status=405,
                payload={
                    "error": "method_not_allowed",
                    "message": "Use GET for People API health and readiness probes.",
                },
                extra_headers=((b"allow", b"GET"),),
            )
            return

        path = scope.get("path")
        if path == "/health":
            await _send_json(send, status=200, payload={"status": "ok"})
            return
        if path == "/ready":
            try:
                self.readiness_probe.check_ready()
            except Exception:  # noqa: BLE001 - readiness must normalize dependency details.
                await _send_json(
                    send,
                    status=503,
                    payload={
                        "error": "not_ready",
                        "message": "Retry after an Orgmetra operator restores the owned People API dependency.",
                    },
                )
                return
            await _send_json(send, status=200, payload={"status": "ready"})
            return

        await _send_json(
            send,
            status=404,
            payload={
                "error": "route_not_found",
                "message": "Use /health for liveness or /ready for owned-dependency readiness.",
            },
        )


async def _send_json(
    send: AsgiSend,
    *,
    status: int,
    payload: Mapping[str, object],
    extra_headers: tuple[tuple[bytes, bytes], ...] = (),
) -> None:
    """Emit deterministic non-cacheable JSON without HR or dependency details."""
    body = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    headers = (
        (b"content-type", b"application/json"),
        (b"cache-control", b"no-store"),
        *extra_headers,
    )
    await send({"type": "http.response.start", "status": status, "headers": list(headers)})
    await send({"type": "http.response.body", "body": body, "more_body": False})
