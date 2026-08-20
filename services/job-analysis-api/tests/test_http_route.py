"""Executable HTTP transport contracts for job-analysis snapshot persistence."""

from __future__ import annotations

import json
import unittest
from uuid import UUID

from orgmetra_hris_kernel import AuditOutboxEvent, JobAnalysisSnapshot

from orgmetra_job_analysis_api import AuthenticatedPrincipal, AuthenticationFailed
from orgmetra_job_analysis_api.http import JobAnalysisAsgiApp
from orgmetra_job_analysis_api.snapshot import (
    JobAnalysisIdempotencyConflict,
    JobAnalysisIntegrityError,
    JobAnalysisScopeMissing,
)
from fixtures import (
    ANALYSIS,
    CRITERION,
    IDEMPOTENCY_KEY,
    POSITION,
    TENANT,
    clinical_psychologist_document,
    clinical_psychologist_snapshot,
    read_policy,
    write_policy,
)


def _api_principal() -> AuthenticatedPrincipal:
    """Return one actor that can both persist and read snapshots in HTTP tests."""
    return AuthenticatedPrincipal(
        tenant_record_id=TENANT,
        actor_reference="keyverse:actor-ja-1",
        granted_scope_codes=frozenset(
            {"orgmetra.job_architecture.write", "orgmetra.job_architecture.read"}
        ),
    )


class FakeAuthenticator:
    """Return one principal while recording whether authentication ran."""

    def __init__(self, principal: AuthenticatedPrincipal, *, error: Exception | None = None) -> None:
        self.principal = principal
        self.error = error
        self.tokens: list[str] = []

    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        """Authenticate one token without logging it."""
        self.tokens.append(bearer_token)
        if self.error is not None:
            raise self.error
        return self.principal


class FakeWritePort:
    """Return a posted snapshot and capture Idempotency-Key plus scope IDs."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, object]] = []

    def persist_snapshot(
        self,
        *,
        snapshot: JobAnalysisSnapshot,
        idempotency_key: str,
        request_digest: str,
        actor_reference: str,
        purpose_code: str,
        position_record_id: UUID | None,
        criterion_blueprint_id: UUID | None,
        audit_event: AuditOutboxEvent,
        outbox_delivery_record_id: UUID,
        write_command_id: UUID,
    ) -> JobAnalysisSnapshot:
        """Record the write and echo the authorized snapshot."""
        self.calls.append(
            {
                "idempotency_key": idempotency_key,
                "position_record_id": position_record_id,
                "criterion_blueprint_id": criterion_blueprint_id,
                "request_digest": request_digest,
                "audit_event": audit_event,
            }
        )
        if self.error is not None:
            raise self.error
        return snapshot


class FakeReadPort:
    """Return a configured snapshot for HTTP GET tests."""

    def __init__(self, result: JobAnalysisSnapshot | None, *, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[UUID, UUID]] = []

    def read_snapshot(self, *, tenant_record_id: UUID, analysis_record_id: UUID) -> JobAnalysisSnapshot | None:
        """Return deterministic snapshot truth or raise a configured failure."""
        self.calls.append((tenant_record_id, analysis_record_id))
        if self.error is not None:
            raise self.error
        return self.result


class JobAnalysisHttpRouteTests(unittest.IsolatedAsyncioTestCase):
    """Prove write/read HTTP contracts, including payload equality."""

    def _app(
        self,
        *,
        authenticator: object | None = None,
        write_port: object | None = None,
        read_port: object | None = None,
        write_policy_value: object | None = None,
        read_policy_value: object | None = None,
    ) -> JobAnalysisAsgiApp:
        """Build the ASGI app with explicit injected boundaries."""
        return JobAnalysisAsgiApp(
            authenticator=authenticator if authenticator is not None else FakeAuthenticator(_api_principal()),
            write_policy=write_policy() if write_policy_value is None else write_policy_value,
            read_policy=read_policy() if read_policy_value is None else read_policy_value,
            write_port=write_port if write_port is not None else FakeWritePort(),
            read_port=read_port if read_port is not None else FakeReadPort(clinical_psychologist_snapshot()),
        )

    async def _request(
        self,
        app: JobAnalysisAsgiApp,
        *,
        method: str = "POST",
        path: object | None = None,
        query: object = b"",
        headers: object | None = None,
        body: object | None = None,
        chunked: bool = False,
    ) -> tuple[int, dict[bytes, bytes], dict[str, object]]:
        posted = clinical_psychologist_document() if body is None else body
        raw = posted if isinstance(posted, bytes) else json.dumps(posted).encode("utf-8")
        scope = {
            "type": "http",
            "method": method,
            "path": path if path is not None else f"/v1/tenants/{TENANT}/job-analysis-snapshots",
            "query_string": query,
            "headers": headers
            if headers is not None
            else [
                (b"authorization", b"Bearer opaque-token"),
                (b"content-type", b"application/json"),
                (b"idempotency-key", IDEMPOTENCY_KEY.encode("ascii")),
                (b"x-purpose-code", b"job_analysis_write"),
            ],
        }
        messages: list[dict[str, object]] = []
        frames = (
            [
                {"type": "http.request", "body": raw[:20], "more_body": True},
                {"type": "http.request", "body": raw[20:], "more_body": False},
            ]
            if chunked
            else [{"type": "http.request", "body": raw, "more_body": False}]
        )

        async def receive() -> dict[str, object]:
            return frames.pop(0) if frames else {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)
        start, body_message = messages
        return int(start["status"]), dict(start["headers"]), json.loads(bytes(body_message["body"]))

    def test_constructor_rejects_missing_transport_dependencies(self) -> None:
        with self.assertRaisesRegex(TypeError, "authenticator"):
            self._app(authenticator=object())
        with self.assertRaisesRegex(TypeError, "write_policy"):
            self._app(write_policy_value=object())
        with self.assertRaisesRegex(TypeError, "read_policy"):
            self._app(read_policy_value=object())
        with self.assertRaisesRegex(TypeError, "write_port"):
            self._app(write_port=object())
        with self.assertRaisesRegex(TypeError, "read_port"):
            self._app(read_port=object())

    async def test_post_then_get_returns_exact_clinical_psychologist_payload(self) -> None:
        write_port = FakeWritePort()
        read_port = FakeReadPort(clinical_psychologist_snapshot())
        app = self._app(write_port=write_port, read_port=read_port)
        posted = clinical_psychologist_document()
        posted["position_record_id"] = str(POSITION)
        posted["criterion_blueprint_id"] = str(CRITERION)

        status, headers, created = await self._request(app, body=posted, chunked=True)
        self.assertEqual(status, 201)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(created, clinical_psychologist_document())
        self.assertEqual(write_port.calls[0]["idempotency_key"], IDEMPOTENCY_KEY)
        self.assertEqual(write_port.calls[0]["position_record_id"], POSITION)
        self.assertEqual(write_port.calls[0]["criterion_blueprint_id"], CRITERION)

        status, _, fetched = await self._request(
            app,
            method="GET",
            path=f"/v1/tenants/{TENANT}/job-analysis-snapshots/{ANALYSIS}",
            query=b"purpose=job_analysis_read",
            headers=[(b"authorization", b"Bearer opaque-token")],
        )
        self.assertEqual(status, 200)
        self.assertEqual(fetched, clinical_psychologist_document())
        self.assertEqual(fetched, created)

    async def test_wrong_path_and_method_return_transport_errors(self) -> None:
        app = self._app()
        for path in ("/v1/unknown", f"/v2/tenants/{TENANT}/job-analysis-snapshots", 42):
            status, _, payload = await self._request(app, path=path)
            self.assertEqual((status, payload["error"]), (404, "route_not_found"))
        status, headers, payload = await self._request(app, method="DELETE")
        self.assertEqual((status, payload["error"]), (405, "method_not_allowed"))
        self.assertEqual(headers[b"allow"], b"GET, POST")

    async def test_malformed_route_ids_and_post_item_paths_are_invalid(self) -> None:
        app = self._app()
        cases = (
            {"path": "/v1/tenants/not-a-uuid/job-analysis-snapshots"},
            {"path": f"/v1/tenants/{UUID(int=0)}/job-analysis-snapshots"},
            {"method": "GET", "path": f"/v1/tenants/{TENANT}/job-analysis-snapshots/{UUID(int=(1 << 128) - 1)}", "query": b"purpose=job_analysis_read"},
            {"path": f"/v1/tenants/{TENANT}/job-analysis-snapshots/{ANALYSIS}"},
            {"method": "GET", "path": f"/v1/tenants/{TENANT}/job-analysis-snapshots", "query": b"purpose=job_analysis_read"},
        )
        for case in cases:
            with self.subTest(case=case):
                status, _, payload = await self._request(app, **case)
                self.assertEqual((status, payload["error"]), (400, "invalid_request"))

    async def test_authentication_failures_do_not_write(self) -> None:
        write_port = FakeWritePort()
        app = self._app(write_port=write_port)
        header_cases: tuple[object, ...] = (
            [],
            object(),
            [(b"authorization", b"Bearer one"), (b"authorization", b"Bearer two")],
            [(b"x-request-id", b"request-1")],
            [(b"authorization",)],
            [("authorization", "Bearer opaque-token")],
            [(b"authorization", b"Bearer \xff")],
        )
        for headers in header_cases:
            with self.subTest(headers=headers):
                status, _, payload = await self._request(app, headers=headers)
                self.assertEqual((status, payload["error"]), (401, "authentication_required"))
        self.assertEqual(write_port.calls, [])

        app = self._app(authenticator=FakeAuthenticator(_api_principal(), error=AuthenticationFailed("expired")), write_port=write_port)
        status, _, payload = await self._request(app)
        self.assertEqual((status, payload["error"]), (401, "authentication_required"))

    async def test_missing_write_headers_and_bad_body_are_invalid(self) -> None:
        app = self._app()
        status, _, payload = await self._request(
            app,
            headers=[(b"authorization", b"Bearer opaque-token"), (b"x-purpose-code", b"job_analysis_write")],
        )
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        status, _, payload = await self._request(
            app,
            headers=[
                (b"authorization", b"Bearer opaque-token"),
                (b"idempotency-key", IDEMPOTENCY_KEY.encode("ascii")),
            ],
        )
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        status, _, payload = await self._request(
            app,
            headers=[
                (b"authorization", b"Bearer opaque-token"),
                (b"idempotency-key", b""),
                (b"x-purpose-code", b"job_analysis_write"),
            ],
        )
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        status, _, payload = await self._request(
            app,
            headers=[
                (b"authorization", b"Bearer opaque-token"),
                (b"idempotency-key", IDEMPOTENCY_KEY.encode("ascii")),
                (b"x-purpose-code", b"JobAnalysis"),
            ],
        )
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        status, _, payload = await self._request(app, body=b"{")
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        status, _, payload = await self._request(app, body=b"[]")
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        status, _, payload = await self._request(app, body={**clinical_psychologist_document(), "position_record_id": "nope"})
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        status, _, payload = await self._request(app, body={**clinical_psychologist_document(), "position_record_id": 12})
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        status, _, payload = await self._request(
            app,
            body={**clinical_psychologist_document(), "criterion_blueprint_id": str(UUID(int=0))},
        )
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))

    async def test_domain_failures_map_to_stable_status_codes(self) -> None:
        cases = (
            (JobAnalysisScopeMissing("missing job"), 409, "scope_missing"),
            (JobAnalysisIdempotencyConflict("digest"), 409, "idempotency_conflict"),
            (JobAnalysisIntegrityError("drift"), 400, "invalid_request"),
            (ValueError("bad snapshot"), 400, "invalid_request"),
            (RuntimeError("postgres password=do-not-leak"), 500, "internal_error"),
        )
        for error, status_code, error_code in cases:
            with self.subTest(error_code=error_code):
                status, _, payload = await self._request(self._app(write_port=FakeWritePort(error=error)))
                self.assertEqual((status, payload["error"]), (status_code, error_code))
                self.assertNotIn("password", json.dumps(payload))

        status, _, payload = await self._request(
            self._app(read_port=FakeReadPort(None)),
            method="GET",
            path=f"/v1/tenants/{TENANT}/job-analysis-snapshots/{ANALYSIS}",
            query=b"purpose=job_analysis_read",
            headers=[(b"authorization", b"Bearer opaque-token")],
        )
        self.assertEqual((status, payload["error"]), (404, "snapshot_not_found"))

        status, _, payload = await self._request(
            self._app(),
            method="GET",
            path=f"/v1/tenants/{TENANT}/job-analysis-snapshots/{ANALYSIS}",
            query=b"purpose=people_read",
            headers=[(b"authorization", b"Bearer opaque-token")],
        )
        self.assertEqual((status, payload["error"]), (403, "access_denied"))

        for query in (b"\xff", b"bogus", b"purpose=job_analysis_read&purpose=other", "purpose=job_analysis_read", b"fields=tasks"):
            status, _, payload = await self._request(
                self._app(),
                method="GET",
                path=f"/v1/tenants/{TENANT}/job-analysis-snapshots/{ANALYSIS}",
                query=query,
                headers=[(b"authorization", b"Bearer opaque-token")],
            )
            self.assertEqual((status, payload["error"]), (400, "invalid_request"))

        status, _, payload = await self._request(
            self._app(),
            method="GET",
            path=f"/v1/tenants/{TENANT}/job-analysis-snapshots/{ANALYSIS}",
            query=b"purpose=JobAnalysis",
            headers=[(b"authorization", b"Bearer opaque-token")],
        )
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))

    async def test_non_http_scope_is_rejected_as_programming_error(self) -> None:
        app = self._app()

        async def receive() -> dict[str, object]:
            return {"type": "lifespan.startup"}

        async def send(message: dict[str, object]) -> None:
            del message

        with self.assertRaisesRegex(ValueError, "HTTP ASGI scopes"):
            await app({"type": "lifespan"}, receive, send)

    async def test_invalid_body_frames_and_header_bytes_fail_closed(self) -> None:
        app = self._app()

        async def bad_type_receive() -> dict[str, object]:
            return {"type": "http.disconnect"}

        async def bad_body_receive() -> dict[str, object]:
            return {"type": "http.request", "body": "not-bytes", "more_body": False}

        messages: list[dict[str, object]] = []

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": f"/v1/tenants/{TENANT}/job-analysis-snapshots",
            "query_string": b"",
            "headers": [
                (b"authorization", b"Bearer opaque-token"),
                (b"content-type", b"application/json"),
                (b"idempotency-key", IDEMPOTENCY_KEY.encode("ascii")),
                (b"x-purpose-code", b"job_analysis_write"),
            ],
        }
        await app(scope, bad_type_receive, send)
        self.assertEqual(messages[0]["status"], 400)
        messages.clear()
        await app(scope, bad_body_receive, send)
        self.assertEqual(messages[0]["status"], 400)
        status, _, payload = await self._request(
            app,
            headers=[
                (b"authorization", b"Bearer opaque-token"),
                (b"idempotency-key", b"\xff"),
                (b"x-purpose-code", b"job_analysis_write"),
            ],
        )
        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
        status, _, payload = await self._request(
            app,
            headers=[
                (b"authorization", b"Bearer opaque-token"),
                (b"authorization", b"Bearer other"),
                (b"idempotency-key", IDEMPOTENCY_KEY.encode("ascii")),
            ],
        )
        self.assertEqual((status, payload["error"]), (401, "authentication_required"))


if __name__ == "__main__":
    unittest.main()
