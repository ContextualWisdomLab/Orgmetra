"""Media-type regressions for governed job-analysis request bodies."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from orgmetra_job_analysis_api.http import JobAnalysisAsgiApp
from fixtures import IDEMPOTENCY_KEY, TENANT, clinical_psychologist_document, read_policy, write_policy
from test_http_route import FakeAuthenticator, FakeReadPort, FakeWritePort, _api_principal


class JobAnalysisHttpContentTypeTests(unittest.IsolatedAsyncioTestCase):
    """Require JSON media type before reading or persisting a posted document."""

    def _app(self, write_port: FakeWritePort) -> JobAnalysisAsgiApp:
        """Build the public transport boundary with deterministic test ports."""
        return JobAnalysisAsgiApp(
            authenticator=FakeAuthenticator(_api_principal()),
            write_policy=write_policy(),
            read_policy=read_policy(),
            write_port=write_port,
            read_port=FakeReadPort(None),
        )

    async def _post_without_reading_body(
        self,
        *,
        content_type: bytes | None,
    ) -> tuple[int, dict[str, object], FakeWritePort, int]:
        """Post headers while proving an unsupported type is rejected pre-body."""
        write_port = FakeWritePort()
        app = self._app(write_port)
        headers = [
            (b"authorization", b"Bearer opaque-token"),
            (b"idempotency-key", IDEMPOTENCY_KEY.encode("ascii")),
            (b"x-purpose-code", b"job_analysis_write"),
        ]
        if content_type is not None:
            headers.append((b"content-type", content_type))
        scope = {
            "type": "http",
            "method": "POST",
            "path": f"/v1/tenants/{TENANT}/job-analysis-snapshots",
            "query_string": b"",
            "headers": headers,
        }
        messages: list[dict[str, object]] = []
        receive_count = 0

        async def receive() -> dict[str, object]:
            nonlocal receive_count
            receive_count += 1
            raise AssertionError("unsupported media type must fail before body read")

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)
        start, body = messages
        return (
            int(start["status"]),
            json.loads(bytes(body["body"])),
            write_port,
            receive_count,
        )

    async def test_missing_or_non_json_media_type_fails_before_body_read(self) -> None:
        """Do not accept JSON bytes under an absent or misleading media type."""
        for content_type in (None, b"text/plain", b"application/xml", b"\xff"):
            with self.subTest(content_type=content_type):
                status, payload, write_port, receive_count = await self._post_without_reading_body(
                    content_type=content_type
                )
                self.assertEqual((status, payload["error"]), (415, "unsupported_media_type"))
                self.assertEqual(receive_count, 0)
                self.assertEqual(write_port.calls, [])

    async def test_json_media_type_with_charset_is_accepted(self) -> None:
        """Accept a standard JSON media type parameter without weakening the type check."""
        write_port = FakeWritePort()
        app = self._app(write_port)
        raw = json.dumps(clinical_psychologist_document()).encode("utf-8")
        scope = {
            "type": "http",
            "method": "POST",
            "path": f"/v1/tenants/{TENANT}/job-analysis-snapshots",
            "query_string": b"",
            "headers": [
                (b"authorization", b"Bearer opaque-token"),
                (b"idempotency-key", IDEMPOTENCY_KEY.encode("ascii")),
                (b"x-purpose-code", b"job_analysis_write"),
                (b"content-type", b"application/json; charset=utf-8"),
            ],
        }
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": raw, "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(scope, receive, send)
        self.assertEqual(messages[0]["status"], 201)
        self.assertEqual(len(write_port.calls), 1)

    def test_openapi_publishes_the_unsupported_media_type_response(self) -> None:
        """Keep generated clients aligned with the runtime 415 contract."""
        schema = (Path(__file__).resolve().parents[3] / "schemas" / "openapi.yaml").read_text(encoding="utf-8")
        collection = schema.split(
            "  /tenants/{tenant_record_id}/job-analysis-snapshots:", 1
        )[1].split(
            "  /tenants/{tenant_record_id}/job-analysis-snapshots/{analysis_record_id}:",
            1,
        )[0]
        self.assertIn("        '415':\n", collection)
        self.assertIn("$ref: '#/components/responses/UnsupportedMediaType'", collection)


if __name__ == "__main__":
    unittest.main()
