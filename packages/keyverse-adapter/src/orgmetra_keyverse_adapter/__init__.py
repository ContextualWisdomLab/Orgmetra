"""Keyverse identity candidates and purpose-bound authorization for Orgmetra.

Orgmetra never stores passwords, passkeys, or raw credentials on a person record.
Raw issuer/subject input may be validated as non-authorizing candidate data, but
it cannot become a durable identity binding until Keyverse publishes immutable,
versioned subject-assertion trust evidence that an Orgmetra ACL can consume.
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
    ExternalIdentityBindingCandidate,
    IdentityBindingTrustUnavailableError,
    bind_identity_subject,
    validate_identity_subject_candidate,
)

__all__ = [
    "AuthorizationDecision",
    "AuthorizationDeniedError",
    "CredentialRejectedError",
    "ExternalIdentityBindingCandidate",
    "IdentityBindingTrustUnavailableError",
    "PurposeBoundAccessPolicy",
    "PurposeBoundAccessRequest",
    "bind_identity_subject",
    "evaluate_purpose_bound_access",
    "require_purpose_bound_access",
    "validate_identity_subject_candidate",
]
