"""Public API for the purpose-bound Orgmetra people service."""

from .app import RequiredPurpose, create_app
from .auth import (
    AuthenticationFailed,
    AuthorizationDenied,
    AuthorizedPrincipal,
    IdentityProviderUnavailable,
    TokenAuthorizer,
    ensure_purpose_authorized,
    ensure_scope_authorized,
    extract_bearer_token,
)
from .repository import PeopleRepository

__all__ = [
    "AuthenticationFailed",
    "AuthorizationDenied",
    "AuthorizedPrincipal",
    "IdentityProviderUnavailable",
    "PeopleRepository",
    "RequiredPurpose",
    "TokenAuthorizer",
    "create_app",
    "ensure_purpose_authorized",
    "ensure_scope_authorized",
    "extract_bearer_token",
]
