"""Request-edge contracts for the Orgmetra People API."""

from orgmetra_people_api.auth import (
    AuthenticatedPrincipal,
    AuthenticationFailed,
    TokenAuthenticator,
    extract_bearer_token,
)
from orgmetra_people_api.authorization import authorize_resource_fields

__all__ = [
    "AuthenticatedPrincipal",
    "AuthenticationFailed",
    "TokenAuthenticator",
    "authorize_resource_fields",
    "extract_bearer_token",
]
