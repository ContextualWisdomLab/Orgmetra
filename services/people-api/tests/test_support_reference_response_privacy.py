"""Response-body privacy regressions for People API internal failures."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


_SUPPORT_PATH = Path(__file__).with_name("test_support_reference_correlation.py")
_SPEC = importlib.util.spec_from_file_location("orgmetra_support_reference_fixtures", _SUPPORT_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import machinery invariant
    raise RuntimeError("support-reference regression fixtures could not be loaded")
_SUPPORT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SUPPORT)


class SupportReferenceResponsePrivacyTests(unittest.IsolatedAsyncioTestCase):
    """Keep backend failure details out of every buyer-visible 500 envelope."""

    def setUp(self) -> None:
        self.fixtures = _SUPPORT.SupportReferenceCorrelationTests()
        self.fixtures.setUp()

    async def test_confirmed_hire_persistence_secret_is_absent_from_response(self) -> None:
        app = _SUPPORT.HireAcceptanceAsgiApp(
            authenticator=_SUPPORT.FakeAuthenticator(self.fixtures.principal),
            policy=self.fixtures._hire_policy(),
            mutation_port=_SUPPORT.FailingHirePort(),
        )
        payload = {
            "employing_organization_unit_id": str(_SUPPORT.ORGANIZATION),
            "candidate_profile_id": str(_SUPPORT.CANDIDATE),
            "selection_decision_id": str(_SUPPORT.DECISION),
            "person_record_id": str(_SUPPORT.PERSON),
            "person_name_record_id": "0198a412-9900-7000-8000-000000000021",
            "employment_record_id": str(_SUPPORT.EMPLOYMENT),
            "employment_record_version_id": "0198a412-9900-7000-8000-000000000031",
            "employment_employing_organization_record_id": "0198a412-9900-7000-8000-000000000032",
            "candidate_worker_conversion_record_id": "0198a412-9900-7000-8000-000000000040",
            "audit_event_record_id": str(_SUPPORT.AUDIT_EVENT),
            "outbox_delivery_record_id": "0198a412-9900-7000-8000-000000000051",
            "effective_from": "2026-08-20",
            "display_name": "Ada Lovelace",
            "employment_status_code": "active",
        }
        status, response = await _SUPPORT.invoke(
            app,
            scope={
                "type": "http",
                "method": "POST",
                "path": f"/v1/tenants/{_SUPPORT.TENANT}/candidate-worker-conversions",
                "query_string": b"purpose=candidate_hire",
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"application/json"),
                    (b"idempotency-key", b"response-privacy-hire-99"),
                ],
            },
            body=json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        )

        self.assertEqual(status, 500)
        serialized = json.dumps(response, sort_keys=True)
        self.assertNotIn("must-not-leak", serialized)
        self.assertNotIn("opaque-token", serialized)

    async def test_people_mutation_persistence_secret_is_absent_from_response(self) -> None:
        app = _SUPPORT.PeopleMutationAsgiApp(
            authenticator=_SUPPORT.FakeAuthenticator(self.fixtures.principal),
            employment_policy=self.fixtures._employment_policy(),
            position_policy=self.fixtures._position_policy(),
            assignment_policy=self.fixtures._assignment_policy(),
            mutation_port=_SUPPORT.FailingPeopleMutationPort(),
            id_factory=_SUPPORT.SequentialIdFactory(),
        )
        payload = {
            "employing_organization_unit_id": str(_SUPPORT.ORGANIZATION),
            "person_record_id": str(_SUPPORT.PERSON),
            "employment_status_code": "active",
            "employment_concurrency_code": "exclusive",
            "effective_from": "2026-08-20",
            "decision_reason": "Confirmed hire requires an exclusive employment record.",
            "confirmation_reference": "human_confirmation:review-99",
            "evidence_references": [
                {"evidence_reference": "decision:99", "evidence_version_code": "v1"}
            ],
        }
        status, response = await _SUPPORT.invoke(
            app,
            scope={
                "type": "http",
                "method": "POST",
                "path": "/v1/employment-records",
                "query_string": b"",
                "headers": [
                    (b"authorization", b"Bearer opaque-token"),
                    (b"content-type", b"application/json"),
                    (b"idempotency-key", b"response-privacy-people-99"),
                    (b"x-tenant-reference", str(_SUPPORT.TENANT).encode("ascii")),
                    (b"x-actor-reference", b"keyverse_subject:operator-99"),
                    (b"x-purpose-code", b"workforce_admin"),
                ],
            },
            body=json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        )

        self.assertEqual(status, 500)
        serialized = json.dumps(response, sort_keys=True)
        self.assertNotIn("must-not-leak", serialized)
        self.assertNotIn("opaque-token", serialized)


if __name__ == "__main__":
    unittest.main()
