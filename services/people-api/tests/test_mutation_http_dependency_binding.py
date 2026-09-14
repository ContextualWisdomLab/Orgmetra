"""Checked-versus-used executable dependency regression for generic People mutation HTTP."""

from __future__ import annotations

import unittest
from uuid import UUID

from orgmetra_keyverse_adapter import PurposeBoundAccessPolicy
from orgmetra_people_api.mutation_http import PeopleMutationAsgiApp
from test_mutation_http_route import (
    EMPLOYMENT,
    IDS,
    PeopleMutationHttpTests,
    RecordingMutationPort,
    SequentialIdFactory,
)

_REPLACEMENT_IDS = [
    UUID("0198a412-8100-7000-8000-000000000090"),
    UUID("0198a412-8100-7000-8000-000000000091"),
    UUID("0198a412-8100-7000-8000-000000000092"),
    UUID("0198a412-8100-7000-8000-000000000093"),
]


class _DependencySwappingAuthenticator:
    """Replace valid app dependencies while authentication is suspended at its boundary."""

    def __init__(
        self,
        *,
        support: PeopleMutationHttpTests,
        replacement_port: RecordingMutationPort,
    ) -> None:
        self.support = support
        self.replacement_port = replacement_port
        self.app: PeopleMutationAsgiApp | None = None

    async def authenticate(self, bearer_token: str):
        """Return the legitimate principal after replacing later-read app capabilities."""
        if self.app is None:
            raise AssertionError("test authenticator was not attached to the app")
        replacement_policy = PurposeBoundAccessPolicy(
            tenant_record_id=self.support.principal.tenant_record_id,
            policy_version_code="replacement-policy-v9",
            resource_kind="employment_record",
            purpose_code="workforce_admin",
            operation_code="create_record",
            required_scope_code="orgmetra.people.write",
            permitted_fields=frozenset({"employment_record"}),
        )
        object.__setattr__(self.app, "employment_policy", replacement_policy)
        object.__setattr__(self.app, "mutation_port", self.replacement_port)
        object.__setattr__(self.app, "id_factory", SequentialIdFactory(_REPLACEMENT_IDS))
        return self.support.principal


class MutationHttpDependencyBindingTests(unittest.IsolatedAsyncioTestCase):
    """Require request-entry capability identity to survive authentication await."""

    async def test_authenticator_cannot_replace_later_mutation_capabilities(self) -> None:
        """A request must use the policy, port and ID factory captured before authentication."""
        support = PeopleMutationHttpTests(
            methodName="test_post_routes_return_opaque_created_identities"
        )
        support.setUp()
        original_port = RecordingMutationPort()
        replacement_port = RecordingMutationPort()
        authenticator = _DependencySwappingAuthenticator(
            support=support,
            replacement_port=replacement_port,
        )
        app = support._app(
            authenticator=authenticator,
            mutation_port=original_port,
        )
        authenticator.app = app

        status, _headers, payload = await support._request(app)

        self.assertEqual(status, 201)
        self.assertEqual(payload, {"employment_record_id": str(EMPLOYMENT)})
        self.assertEqual(len(original_port.employment_calls), 1)
        self.assertEqual(replacement_port.employment_calls, [])
        accepted_command, accepted_authorization = original_port.employment_calls[0]
        self.assertEqual(accepted_command.employment_record_id, IDS[0])
        self.assertEqual(accepted_authorization.policy_version_code, "people-mutation-v1")


if __name__ == "__main__":
    unittest.main()
