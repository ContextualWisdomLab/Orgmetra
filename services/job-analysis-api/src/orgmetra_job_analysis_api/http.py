"""Dependency-light ASGI routes for governed job-analysis snapshot persistence.

The transport adapter owns HTTP parsing and stable, non-disclosing responses.
Authentication, purpose-bound authorization, kernel validation, and tenant
isolation remain delegated to the snapshot use cases and persistence port.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from secrets import token_urlsafe
from typing import Awaitable, Callable, Mapping, Sequence
from uuid import UUID

from orgmetra_keyverse_adapter import AuthorizationDeniedError, PurposeBoundAccessPolicy

from orgmetra_job_analysis_api.auth import AuthenticationFailed, TokenAuthenticator, extract_bearer_token
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIdempotencyConflict,
    JobAnalysisIntegrityError,
    JobAnalysisReadPort,
    JobAnalysisScopeMissing,
    JobAnalysisSnapshotNotFound,
    JobAnalysisWritePort,
    persist_job_analysis_snapshot,
    read_job_analysis_snapshot,
)

AsgiReceive = Callable[[], Awaitable[dict[str, object]]]
AsgiSend = Callable[[dict[str, object]], Awaitable[None]]

_ROUTE_PREFIX = ("v1", "tenants")
_PURPOSE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_MAX_UUID_INT = (1 << 128) - 1
_MAX_REQUEST_BODY_BYTES = 1 << 20
_MAX_REQUEST_PATH_CHARACTERS = 256
_MAX_REQUEST_HEADERS = 64
_MAX_REQUEST_HEADER_BYTES = 16384
_ERROR_NEXT_ACTION = {
    "route_not_found": "Use the documented tenant-scoped job-analysis route and retry.",
    "method_not_allowed": "Use POST to persist or GET to read one job-analysis snapshot.",
    "invalid_request": "Correct the referenced identifiers, headers, query, or snapshot document and retry.",
    "authentication_required": "Obtain one valid Keyverse Bearer credential and retry.",
    "unsupported_media_type": "Set Content-Type to application/json and retry without changing the evidence bytes.",
    "access_denied": "Request the exact tenant, purpose, resource, and least-privilege scope required for this operation.",
    "snapshot_not_found": "Verify the tenant and snapshot references, then retry the exact target.",
    "scope_missing": "Resolve the required Job, Position, or criterion parent in the same tenant before retrying.",
    "idempotency_conflict": "Reuse the original snapshot bytes or submit the changed command under a new Idempotency-Key.",
    "internal_error": "Retry later or contact an Orgmetra operator with the support_reference; never include the bearer token.",
}


class _InvalidHttpRequest(ValueError):
    """Indicate malformed request input that must fail before persistence."""


class _UnsupportedMediaType(ValueError):
    """Indicate a POST body whose media type is absent or not JSON."""


@dataclass(frozen=True, slots=True)
class JobAnalysisAsgiApp:
    """Expose governed snapshot write and read through versioned ASGI routes.

    Supported routes::

        POST /v1/tenants/{tenant_record_id}/job-analysis-snapshots
        GET  /v1/tenants/{tenant_record_id}/job-analysis-snapshots/{analysis_record_id}

    POST requires ``Authorization``, ``Content-Type: application/json``,
    ``Idempotency-Key``, and ``X-Purpose-Code``. The request body is the
    snapshot document. GET requires ``Authorization`` and ``X-Purpose-Code``;
    purpose never travels in the URL or query string. Successful responses are
    never cached as shared evidence.
    """

    authenticator: TokenAuthenticator
    write_policy: PurposeBoundAccessPolicy
    read_policy: PurposeBoundAccessPolicy
    write_port: JobAnalysisWritePort
    read_port: JobAnalysisReadPort

    def __post_init__(self) -> None:
        """Reject incomplete dependency injection before serving protected data."""
        if not isinstance(self.authenticator, TokenAuthenticator):
            raise TypeError("authenticator must implement TokenAuthenticator")
        if not isinstance(self.write_policy, PurposeBoundAccessPolicy):
            raise TypeError("write_policy must be a PurposeBoundAccessPolicy")
        if not isinstance(self.read_policy, PurposeBoundAccessPolicy):
            raise TypeError("read_policy must be a PurposeBoundAccessPolicy")
        if not isinstance(self.write_port, JobAnalysisWritePort):
            raise TypeError("write_port must implement JobAnalysisWritePort")
        if not isinstance(self.read_port, JobAnalysisReadPort):
            raise TypeError("read_port must implement JobAnalysisReadPort")

    async def __call__(self, scope: Mapping[str, object], receive: AsgiReceive, send: AsgiSend) -> None:
        """Serve one HTTP request without exposing bearer tokens or internal errors."""
        if scope.get("type") != "http":
            raise ValueError("JobAnalysisAsgiApp accepts only HTTP ASGI scopes")

        method = scope.get("method")
        path = scope.get("path")
        if not isinstance(path, str) or not _looks_like_snapshot_route(path):
            await _send_json(
                send,
                status=404,
                payload={
                    "error": "route_not_found",
                    "message": "Use /v1/tenants/{tenant_record_id}/job-analysis-snapshots.",
                },
            )
            return
        if method not in {"GET", "POST"}:
            await _send_json(
                send,
                status=405,
                payload={
                    "error": "method_not_allowed",
                    "message": "Use POST to persist or GET to read one job-analysis snapshot.",
                },
                extra_headers=((b"allow", b"GET, POST"),),
            )
            return

        parts = path.strip("/").split("/")
        try:
            tenant_record_id = UUID(parts[2])
            analysis_record_id = UUID(parts[4]) if len(parts) == 5 else None
        except (ValueError, IndexError):
            await _send_invalid_request(send)
            return
        if tenant_record_id.int in (0, _MAX_UUID_INT):
            await _send_invalid_request(send)
            return
        if analysis_record_id is not None and analysis_record_id.int in (0, _MAX_UUID_INT):
            await _send_invalid_request(send)
            return
        if method == "POST" and analysis_record_id is not None:
            await _send_invalid_request(send)
            return
        if method == "GET" and analysis_record_id is None:
            await _send_invalid_request(send)
            return

        try:
            bearer_token = extract_bearer_token(_authorization_header(scope))
            principal = await self.authenticator.authenticate(bearer_token)
        except AuthenticationFailed:
            await _send_json(
                send,
                status=401,
                payload={
                    "error": "authentication_required",
                    "message": "Provide one valid Bearer credential and retry.",
                },
                extra_headers=((b"www-authenticate", b"Bearer"),),
            )
            return
        except Exception:  # noqa: BLE001 - identity backend failures must remain client-safe.
            await _send_json(
                send,
                status=500,
                payload={
                    "error": "internal_error",
                    "message": "Retry later or contact an Orgmetra operator with non-secret request metadata; never include the bearer token.",
                },
            )
            return

        try:
            headers = _typed_headers(scope)
            purpose_code = _required_header(headers, b"x-purpose-code")
            if _PURPOSE_PATTERN.fullmatch(purpose_code) is None:
                raise _InvalidHttpRequest("purpose must be a lower snake_case code")

            if method == "POST":
                idempotency_key = _required_header(headers, b"idempotency-key")
                _require_json_content_type(headers)
                document = await _read_json_object(receive)
                position_record_id = _optional_uuid(document.pop("position_record_id", None))
                criterion_blueprint_id = _optional_uuid(document.pop("criterion_blueprint_id", None))
                view = persist_job_analysis_snapshot(
                    principal=principal,
                    tenant_record_id=tenant_record_id,
                    document=document,
                    idempotency_key=idempotency_key,
                    purpose_code=purpose_code,
                    position_record_id=position_record_id,
                    criterion_blueprint_id=criterion_blueprint_id,
                    policy=self.write_policy,
                    write_port=self.write_port,
                )
                await _send_json(
                    send,
                    status=201,
                    payload=view.snapshot,
                    extra_headers=(
                        (
                            b"location",
                            f"/v1/tenants/{tenant_record_id}/job-analysis-snapshots/{view.snapshot['analysis_record_id']}".encode("ascii"),
                        ),
                    ),
                )
                return

            raw_query = scope.get("query_string", b"")
            if not isinstance(raw_query, bytes) or raw_query:
                raise _InvalidHttpRequest("job-analysis reads do not accept query parameters")
            view = read_job_analysis_snapshot(
                principal=principal,
                tenant_record_id=tenant_record_id,
                analysis_record_id=analysis_record_id,
                purpose_code=purpose_code,
                policy=self.read_policy,
                read_port=self.read_port,
            )
        except _UnsupportedMediaType:
            await _send_json(
                send,
                status=415,
                payload={
                    "error": "unsupported_media_type",
                    "message": "Send the snapshot document as application/json and retry.",
                },
            )
            return
        except _InvalidHttpRequest:
            await _send_invalid_request(send)
            return
        except AuthorizationDeniedError:
            await _send_json(
                send,
                status=403,
                payload={
                    "error": "access_denied",
                    "message": "Request a purpose and scope authorized for this exact job-analysis snapshot.",
                },
            )
            return
        except JobAnalysisSnapshotNotFound:
            await _send_json(
                send,
                status=404,
                payload={
                    "error": "snapshot_not_found",
                    "message": "Verify the snapshot reference and tenant, then retry.",
                },
            )
            return
        except JobAnalysisScopeMissing:
            await _send_json(
                send,
                status=409,
                payload={
                    "error": "scope_missing",
                    "message": "Bind the snapshot to an existing job, and to a present position or criterion when those identifiers are supplied.",
                },
            )
            return
        except JobAnalysisIdempotencyConflict:
            await _send_json(
                send,
                status=409,
                payload={
                    "error": "idempotency_conflict",
                    "message": "Reuse the same snapshot payload or retry with a new Idempotency-Key.",
                },
            )
            return
        except (JobAnalysisIntegrityError, ValueError, TypeError):
            await _send_json(
                send,
                status=400,
                payload={
                    "error": "invalid_request",
                    "message": "Correct the snapshot document, tenant, and required write headers, then retry.",
                },
            )
            return
        except Exception:  # noqa: BLE001 - HTTP boundary must fail closed without leaking backend details.
            await _send_json(
                send,
                status=500,
                payload={
                    "error": "internal_error",
                    "message": "Retry later or contact an Orgmetra operator with non-secret request metadata; never include the bearer token.",
                },
            )
            return

        await _send_json(send, status=200, payload=view.snapshot)


def _looks_like_snapshot_route(path: str) -> bool:
    """Recognize only one bounded collection or item snapshot route."""
    if len(path) > _MAX_REQUEST_PATH_CHARACTERS:
        return False
    parts = path.strip("/").split("/")
    if len(parts) not in {4, 5}:
        return False
    return tuple(parts[:2]) == _ROUTE_PREFIX and parts[3] == "job-analysis-snapshots"


def _optional_uuid(value: object) -> UUID | None:
    """Parse an optional posted UUID or reject a malformed identifier."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise _InvalidHttpRequest("optional scope IDs must be UUID strings")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise _InvalidHttpRequest("optional scope IDs must be UUID strings") from error
    if parsed.int in (0, _MAX_UUID_INT):
        raise _InvalidHttpRequest("optional scope IDs must be operational UUIDs")
    return parsed


def _typed_headers(scope: Mapping[str, object]) -> dict[bytes, bytes]:
    """Return one bounded set of lower-cased singleton request headers."""
    raw_headers = scope.get("headers", ())
    if not isinstance(raw_headers, Sequence) or len(raw_headers) > _MAX_REQUEST_HEADERS:
        raise AuthenticationFailed("request headers are invalid")
    headers: dict[bytes, bytes] = {}
    total_header_bytes = 0
    for header in raw_headers:
        if not isinstance(header, Sequence) or len(header) != 2:
            raise AuthenticationFailed("request headers are invalid")
        name, value = header
        if not isinstance(name, bytes) or not isinstance(value, bytes):
            raise AuthenticationFailed("request headers are invalid")
        total_header_bytes += len(name) + len(value)
        if total_header_bytes > _MAX_REQUEST_HEADER_BYTES:
            raise AuthenticationFailed("request headers exceed the accepted size")
        key = name.lower()
        if key in headers:
            raise AuthenticationFailed("duplicate request header")
        headers[key] = value
    return headers


def _authorization_header(scope: Mapping[str, object]) -> str | None:
    """Return one ASCII Authorization header, rejecting duplicates and bad bytes."""
    headers = _typed_headers(scope)
    value = headers.get(b"authorization")
    if value is None:
        raise AuthenticationFailed("exactly one authorization header is required")
    try:
        return value.decode("ascii")
    except UnicodeDecodeError as error:
        raise AuthenticationFailed("authorization header must be ASCII") from error


def _required_header(headers: Mapping[bytes, bytes], name: bytes) -> str:
    """Return one required printable ASCII header used by governed requests."""
    value = headers.get(name)
    if value is None:
        raise _InvalidHttpRequest(f"{name.decode('ascii')} header is required")
    try:
        text = value.decode("ascii")
    except UnicodeDecodeError as error:
        raise _InvalidHttpRequest(f"{name.decode('ascii')} header must be ASCII") from error
    if not text:
        raise _InvalidHttpRequest(f"{name.decode('ascii')} header must not be blank")
    return text


def _require_json_content_type(headers: Mapping[bytes, bytes]) -> None:
    """Require an ASCII application/json media type before reading POST bytes."""
    value = headers.get(b"content-type")
    if value is None:
        raise _UnsupportedMediaType("content-type header is required")
    try:
        media_type = value.decode("ascii").split(";", 1)[0].strip().lower()
    except UnicodeDecodeError as error:
        raise _UnsupportedMediaType("content-type header must be ASCII") from error
    if media_type != "application/json":
        raise _UnsupportedMediaType("content-type must be application/json")


def _object_without_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Build one JSON object while rejecting ambiguous repeated member names."""
    value: dict[str, object] = {}
    for member_name, member_value in pairs:
        if member_name in value:
            raise _InvalidHttpRequest("request body contains a duplicate JSON member")
        value[member_name] = member_value
    return value


async def _read_json_object(receive: AsgiReceive) -> dict[str, object]:
    """Read one bounded, unambiguous JSON object body from chunked ASGI frames."""
    chunks: list[bytes] = []
    total_bytes = 0
    more_body = True
    while more_body:
        message = await receive()
        if message.get("type") != "http.request":
            raise _InvalidHttpRequest("request body frame is invalid")
        body = message.get("body", b"")
        if not isinstance(body, bytes):
            raise _InvalidHttpRequest("request body must be bytes")
        total_bytes += len(body)
        if total_bytes > _MAX_REQUEST_BODY_BYTES:
            raise _InvalidHttpRequest("request body exceeds the accepted size")
        chunks.append(body)
        more_body = bool(message.get("more_body"))
    raw = b"".join(chunks)
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_object_without_duplicate_members,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _InvalidHttpRequest("request body must be JSON") from error
    if not isinstance(payload, dict):
        raise _InvalidHttpRequest("request body must be a JSON object")
    return payload


async def _send_invalid_request(send: AsgiSend) -> None:
    """Emit the stable invalid-request response used by transport validation."""
    await _send_json(
        send,
        status=400,
        payload={
            "error": "invalid_request",
            "message": "Correct the tenant/snapshot IDs, purpose, Idempotency-Key, and snapshot document, then retry.",
        },
    )


def _governed_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Add the customer-safe error envelope while preserving the legacy alias."""
    response_payload = dict(payload)
    error_code = response_payload.get("error")
    if isinstance(error_code, str):
        response_payload.update(
            {
                "error_code": error_code,
                "next_action": _ERROR_NEXT_ACTION[error_code],
                "support_reference": f"err_{token_urlsafe(18)}",
            }
        )
    return response_payload


async def _send_json(
    send: AsgiSend,
    *,
    status: int,
    payload: Mapping[str, object],
    extra_headers: tuple[tuple[bytes, bytes], ...] = (),
) -> None:
    """Emit deterministic JSON with governed, non-cacheable error metadata."""
    body = json.dumps(
        _governed_payload(payload),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    headers = (
        (b"content-type", b"application/json"),
        (b"cache-control", b"no-store"),
        (b"vary", b"Authorization"),
        *extra_headers,
    )
    await send({"type": "http.response.start", "status": status, "headers": list(headers)})
    await send({"type": "http.response.body", "body": body, "more_body": False})
