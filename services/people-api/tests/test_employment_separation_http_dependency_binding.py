"""Checked-versus-used executable dependency regression for Employment separation HTTP."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.separation_http import EmploymentSeparationAsgiApp
from test_employment_separation_http import (
    AUDIT_EVENT,
    OUTBOX,
    EmploymentSeparationHttpTests,
    RecordingSeparationPort,
)

_REPLACEMENT_AUDIT_EVENT = UUID("0198a412-9000-7000-8000-000000000090")
_REPLACEMENT_OUTBOX = UUID("0198a412-9000-7000-8000-000000000091")


class _DependencySwappingAuthenticator:
    """Replace valid app dependencies while authentication is suspended at its boundary."""

    def __init__(
        self,
        *,
        support: EmploymentSeparationHttpTests,
        replacement_port: RecordingSeparationPort,
    ) -> None:
        self.support = support
        self.replacement_port = replacement_port
        self.app: EmploymentSeparationAsgiApp | None = None

    async def authenticate(self, bearer_token: str):
        """Return the legitimate principal after replacing later-read app capabilities."""
        if bearer_token != "opaque-token":
            raise AssertionError("unexpected bearer token")
        if self.app is None:
            raise AssertionError("test authenticator was not attached to the app")
        replacement_policy = PurposeBoundAccessPolicy(
            tenant_record_id=self.support.principal.tenant_record_id,
            policy_version_code="replacement-separation-v9",
            resource_kind="employment_record",
            purpose_code="workforce_admin",
            operation_code="separate_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"employment_record"}),
        )
        replacement_ids = iter((_REPLACEMENT_AUDIT_EVENT, _REPLACEMENT_OUTBOX))
        object.__setattr__(self.app, "policy", replacement_policy)
        object.__setattr__(self.app, "separation_port", self.replacement_port)
        object.__setattr__(self.app, "id_factory", replacement_ids.__next__)
        return self.support.principal


class EmploymentSeparationHttpDependencyBindingTests(unittest.IsolatedAsyncioTestCase):
    """Require request-entry capability identity to survive authentication await."""

    async def test_authenticator_cannot_replace_later_separation_capabilities(self) -> None:
        """A request must use the policy, port and ID factory captured before authentication."""
        support = EmploymentSeparationHttpTests(
            methodName="test_success_returns_database_owned_terminal_version_and_replay_evidence"
        )
        support.setUp()
        original_port = RecordingSeparationPort()
        replacement_port = RecordingSeparationPort()
        authenticator = _DependencySwappingAuthenticator(
            support=support,
            replacement_port=replacement_port,
        )
        app = support._app(
            authenticator=authenticator,
            separation_port=original_port,
        )
        authenticator.app = app

        status, _headers, _payload = await support._request(app)

        self.assertEqual(status, 200)
        self.assertEqual(len(original_port.calls), 1)
        self.assertEqual(replacement_port.calls, [])
        accepted_command, accepted_authorization = original_port.calls[0]
        self.assertEqual(accepted_command.audit_event_record_id, AUDIT_EVENT)
        self.assertEqual(accepted_command.outbox_delivery_record_id, OUTBOX)
        self.assertEqual(
            accepted_authorization.policy_version_code,
            "employment-separation-v1",
        )


if __name__ == "__main__":
    unittest.main()
