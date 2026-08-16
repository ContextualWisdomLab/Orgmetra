"""Keyverse connector that binds an opaque identity subject to a person.

Orgmetra never stores passwords, passkeys, or raw credentials on a person
record. Use `bind_identity_subject` after Keyverse authenticates the actor,
then continue the HR action that needs that person.
"""

from orgmetra_keyverse_adapter.binding import (
    CredentialRejectedError,
    ExternalIdentityBinding,
    bind_identity_subject,
)

__all__ = [
    "CredentialRejectedError",
    "ExternalIdentityBinding",
    "bind_identity_subject",
]
