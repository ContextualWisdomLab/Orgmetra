"""Keyverse identity binding and purpose-bound authorization for Orgmetra.

Orgmetra never stores passwords, passkeys, or raw credentials on a person
record. Use ``bind_identity_subject`` after Keyverse authenticates the actor,
then evaluate the authenticated subject, tenant, purpose, operation, scope, and
requested field set against an Orgmetra-owned purpose-bound policy before
returning protected HR data.
"""

from orgmetra_keyverse_adapter.authorization import (
    AuthorizationDecision,
    AuthorizationDeniedError,
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    evaluate_purpose_bound_access,
    require_purpose_bound_access,
)
from orgmetra_keyverse_adapter.binding import (
    CredentialRejectedError,
    ExternalIdentityBinding,
    bind_identity_subject,
)

__all__ = [
    "AuthorizationDecision",
    "AuthorizationDeniedError",
    "CredentialRejectedError",
    "ExternalIdentityBinding",
    "PurposeBoundAccessPolicy",
    "PurposeBoundAccessRequest",
    "bind_identity_subject",
    "evaluate_purpose_bound_access",
    "require_purpose_bound_access",
]
