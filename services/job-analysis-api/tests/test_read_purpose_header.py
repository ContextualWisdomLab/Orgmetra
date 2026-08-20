"""Regression contracts for purpose-bound job-analysis reads."""

from __future__ import annotations

import json
import unittest
from uuid import UUID

from orgmetra_hris_kernel import JobAnalysisSnapshot
from orgmetra_job_analysis_api import AuthenticatedPrincipal
from orgmetra_job_analysis_api.http import JobAnalysisAsgiApp

from fixtures import ANALYSIS, TENANT, clinical_psychologist_snapshot, read_policy, write_policy


class _Authenticator:
    async def authenticate(self, bearer_token: str) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(
            tenant_record_id=TENANT,
            actor_reference="keyverse:actor-ja-read-purpose",
            granted_scope_codes=frozenset(
                {"orgmetra.job_architecture.read", "orgmetra.job_architecture.write"}
            ),
        )


class _WritePort:
    def persist_snapshot(self, **kwargs: object) -> JobAnalysisSnapshot:
        snapshot = kwargs["snapshot"]
        assert isinstance(snapshot, JobAnalysisSnapshot)
        return snapshot


class _ReadPort:
    def read_snapshot(
        self,
        *,
        tenant_record_id: UUID,
        analysis_record_id: UUID,
    ) -> JobAnalysisSnapshot | None:
        assert tenant_record_id == TENANT
        assert analysis_record_id == ANALYSIS
        return clinical_psychologist_snapshot()


class ReadPurposeHeaderTests(unittest.IsolatedAsyncioTestCase):
    """Keep read purpose out of URLs and aligned with write-side authorization."""

    async def _get(
        self,
        *,
        headers: list[tuple[bytes, bytes]],
        query_string: bytes = b"",
    ) -> tuple[int, dict[str, object]]:
        app = JobAnalysisAsgiApp(
            authenticator=_Authenticator(),
            write_policy=write_policy(),
            read_policy=read_policy(),
            write_port=_WritePort(),
            read_port=_ReadPort(),
        )
        scope = {
            "type": "http",
            "method": "GET",
            "path": f"/v1/tenants/{TENANT}/job-analysis-snapshots/{ANALYSIS}",
            "query_string": query_string,
            "headers": headers,
        }
        sent: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            sent.append(message)

        await app(scope, receive, send)
        return int(sent[0]["status"]), json.loads(bytes(sent[1]["body"]))

    async def test_get_accepts_purpose_only_from_x_purpose_code_header(self) -> None:
        status, payload = await self._get(
            headers=[
                (b"authorization", b"Bearer opaque-token"),
                (b"x-purpose-code", b"job_analysis_read"),
            ]
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["analysis_record_id"], str(ANALYSIS))

    async def test_query_parameter_cannot_substitute_for_purpose_header(self) -> None:
        status, payload = await self._get(
            headers=[(b"authorization", b"Bearer opaque-token")],
            query_string=b"purpose=job_analysis_read",
        )

        self.assertEqual((status, payload["error"]), (400, "invalid_request"))

    async def test_read_route_rejects_query_parameters_even_with_valid_purpose_header(self) -> None:
        status, payload = await self._get(
            headers=[
                (b"authorization", b"Bearer opaque-token"),
                (b"x-purpose-code", b"job_analysis_read"),
            ],
            query_string=b"purpose=job_analysis_read",
        )

        self.assertEqual((status, payload["error"]), (400, "invalid_request"))
