"""Keyverse identity binding and purpose-bound authorization for Orgmetra.

Orgmetra never stores passwords, passkeys, or raw credentials on a person
record. Keyverse authenticates identity and scopes; Orgmetra's trusted service
composition supplies HR policy. The exported value objects validate data but do
not pretend to be unforgeable capabilities against arbitrary same-process code.
"""

from orgmetra_keyverse_adapter.authorization import (
    AuthorizationDecision,
    AuthorizationDeniedError,
    PurposeBoundAccessPolicy,
    PurposeBoundAccessRequest,
    evaluate_purpose_bound_access,
    require_purpose_bound_access,
    validate_authorization_decision,
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
    "validate_authorization_decision",
]
