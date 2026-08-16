"""Strict offline JWT access-token verification for Keyverse and Orgmetra."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import jwt
from jwt import InvalidTokenError, PyJWK

from orgmetra_people_api import (
    AuthenticationFailed,
    AuthorizationDenied,
    AuthorizedPrincipal,
    IdentityProviderUnavailable,
)

from .contracts import (
    IdentityReferenceResolver,
    JwksProvider,
    KeyverseOidcConfig,
    ResolvedIdentityReferences,
)

_SCOPE_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_.:")


class KeyverseOidcAuthorizer:
    """Verify one JWT access token and resolve its external identities."""

    def __init__(
        self,
        config: KeyverseOidcConfig,
        jwks_provider: JwksProvider,
        identity_resolver: IdentityReferenceResolver,
    ) -> None:
        """Store one strict issuer profile and its two injected dependencies."""

        if not isinstance(jwks_provider, JwksProvider):
            raise TypeError("jwks_provider must implement JwksProvider")
        if not isinstance(identity_resolver, IdentityReferenceResolver):
            raise TypeError("identity_resolver must implement IdentityReferenceResolver")
        self._config = config
        self._jwks_provider = jwks_provider
        self._identity_resolver = identity_resolver

    async def authorize(
        self,
        bearer_token: str,
        required_scope_code: str,
        required_purpose_code: str,
    ) -> AuthorizedPrincipal:
        """Return a principal only when independent scope and purpose grants pass."""

        token = _compact_token(bearer_token)
        required_scope = _scope_code(required_scope_code)
        required_purpose = _purpose_code(required_purpose_code)
        header = _unverified_header(token)
        algorithm = _header_value(header, "alg", 16)
        if algorithm not in self._config.allowed_algorithms:
            raise AuthenticationFailed("token signing algorithm is not allowed")
        token_type = _header_value(header, "typ", 64)
        if token_type.casefold() != self._config.required_token_type.casefold():
            raise AuthenticationFailed("token type is not accepted")
        key_identifier = _header_value(header, "kid", 256)
        key_set = await self._load_key_set()
        signing_key = _select_signing_key(
            key_set,
            key_identifier=key_identifier,
            algorithm=algorithm,
        )
        claims = _decode_claims(
            token,
            signing_key,
            algorithm=algorithm,
            config=self._config,
        )
        subject = _claim_string(claims, "sub", 255)
        tenant_external_id = _claim_string(
            claims,
            self._config.tenant_claim_name,
            255,
        )
        _claim_string(claims, "jti", 255)
        issued_at = _numeric_date(claims, "iat")
        expires_at = _numeric_date(claims, "exp")
        if expires_at <= issued_at:
            raise AuthenticationFailed("token lifetime is invalid")
        if expires_at - issued_at > self._config.maximum_token_lifetime_seconds:
            raise AuthenticationFailed("token lifetime exceeds the allowed maximum")
        scope_codes = _scope_collection(claims)
        if required_scope not in scope_codes:
            raise AuthorizationDenied("required scope is not authorized")
        purpose_codes = _purpose_collection(
            claims,
            self._config.purposes_claim_name,
        )
        if required_purpose not in purpose_codes:
            raise AuthorizationDenied("required purpose is not authorized")
        references = await self._resolve_references(
            subject=subject,
            tenant_external_id=tenant_external_id,
        )
        return AuthorizedPrincipal(
            tenant_reference=references.tenant_reference,
            actor_reference=references.actor_reference,
            allowed_scope_codes=scope_codes,
            allowed_purpose_codes=purpose_codes,
        )

    async def _load_key_set(self) -> Mapping[str, object]:
        """Load one bounded issuer-specific JWK Set from the injected provider."""

        try:
            key_set = await self._jwks_provider.get_jwks(self._config.issuer)
        except IdentityProviderUnavailable:
            raise
        except Exception as error:
            raise IdentityProviderUnavailable(
                "identity signing keys are temporarily unavailable"
            ) from error
        if not isinstance(key_set, Mapping):
            raise IdentityProviderUnavailable("identity signing key set is invalid")
        keys = key_set.get("keys")
        if not isinstance(keys, list) or not keys or len(keys) > 128:
            raise IdentityProviderUnavailable("identity signing key set is invalid")
        if not all(isinstance(key, Mapping) for key in keys):
            raise IdentityProviderUnavailable("identity signing key set is invalid")
        return key_set

    async def _resolve_references(
        self,
        *,
        subject: str,
        tenant_external_id: str,
    ) -> ResolvedIdentityReferences:
        """Resolve verified external identities to opaque Orgmetra references."""

        try:
            references = await self._identity_resolver.resolve(
                issuer=self._config.issuer,
                subject=subject,
                tenant_external_id=tenant_external_id,
            )
        except IdentityProviderUnavailable:
            raise
        except Exception as error:
            raise IdentityProviderUnavailable(
                "identity reference mapping is temporarily unavailable"
            ) from error
        if not isinstance(references, ResolvedIdentityReferences):
            raise IdentityProviderUnavailable("identity reference mapping is invalid")
        return references


def _compact_token(value: str) -> str:
    """Normalize optional edge spaces and validate one compact ASCII JWT."""

    if not isinstance(value, str):
        raise AuthenticationFailed("bearer token is invalid")
    token = value.strip(" ")
    if not token or len(token) > 8_192 or token.count(".") != 2:
        raise AuthenticationFailed("bearer token is invalid")
    if not all(
        character.isascii()
        and (character.isalnum() or character in {"-", "_", "."})
        for character in token
    ):
        raise AuthenticationFailed("bearer token is invalid")
    return token


def _unverified_header(token: str) -> Mapping[str, object]:
    """Decode JOSE routing metadata without granting it verification authority."""

    try:
        header = jwt.get_unverified_header(token)
    except (InvalidTokenError, TypeError, ValueError) as error:
        raise AuthenticationFailed("token header is invalid") from error
    if not isinstance(header, Mapping):
        raise AuthenticationFailed("token header is invalid")
    return header


def _header_value(
    header: Mapping[str, object],
    name: str,
    maximum_length: int,
) -> str:
    """Return one bounded printable JOSE header string."""

    value = header.get(name)
    if not isinstance(value, str):
        raise AuthenticationFailed(f"token {name} header is invalid")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise AuthenticationFailed(f"token {name} header is invalid")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum_length:
        raise AuthenticationFailed(f"token {name} header is invalid")
    if any(ord(character) > 0x7E for character in normalized):
        raise AuthenticationFailed(f"token {name} header is invalid")
    return normalized


def _select_signing_key(
    key_set: Mapping[str, object],
    *,
    key_identifier: str,
    algorithm: str,
) -> PyJWK:
    """Select exactly one signature key without algorithm or key-use ambiguity."""

    raw_keys = key_set["keys"]
    assert isinstance(raw_keys, list)
    matching_keys = [
        key
        for key in raw_keys
        if isinstance(key, Mapping)
        and key.get("kid") == key_identifier
        and key.get("use", "sig") == "sig"
        and key.get("alg", algorithm) == algorithm
    ]
    if not matching_keys:
        raise AuthenticationFailed("token signing key is not accepted")
    if len(matching_keys) != 1:
        raise IdentityProviderUnavailable("identity signing key set is ambiguous")
    _validate_key_operations(matching_keys[0])
    try:
        signing_key = PyJWK.from_dict(dict(matching_keys[0]))
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise IdentityProviderUnavailable("identity signing key is invalid") from error
    if signing_key.algorithm_name != algorithm:
        raise AuthenticationFailed("token signing key algorithm does not match")
    return signing_key


def _validate_key_operations(jwk: Mapping[str, object]) -> None:
    """Accept only a well-formed public verification operation declaration."""

    raw_operations = jwk.get("key_ops")
    if raw_operations is None:
        return
    if (
        not isinstance(raw_operations, Sequence)
        or isinstance(raw_operations, (str, bytes, bytearray))
        or not raw_operations
        or len(raw_operations) > 16
        or not all(isinstance(operation, str) for operation in raw_operations)
    ):
        raise IdentityProviderUnavailable("identity signing key operations are invalid")
    operations = tuple(raw_operations)
    if len(set(operations)) != len(operations):
        raise IdentityProviderUnavailable("identity signing key operations are invalid")
    if set(operations) != {"verify"}:
        raise AuthenticationFailed("token signing key is not accepted")


def _decode_claims(
    token: str,
    signing_key: PyJWK,
    *,
    algorithm: str,
    config: KeyverseOidcConfig,
) -> Mapping[str, object]:
    """Verify cryptographic/registered claims before bounded application parsing."""

    try:
        claims = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=[algorithm],
            audience=config.audience,
            issuer=config.issuer,
            leeway=config.clock_skew_seconds,
            options={
                "require": ["iss", "sub", "aud", "exp", "iat", "jti"],
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_sub": False,
                "verify_jti": False,
            },
        )
    except InvalidTokenError as error:
        raise AuthenticationFailed("token signature or claims are invalid") from error
    if not isinstance(claims, Mapping):
        raise AuthenticationFailed("token claims are invalid")
    return claims


def _claim_string(
    claims: Mapping[str, object],
    name: str,
    maximum_length: int,
) -> str:
    """Return one bounded string claim without allowing stripped controls."""

    value = claims.get(name)
    if not isinstance(value, str):
        raise AuthenticationFailed(f"token {name} claim is invalid")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise AuthenticationFailed(f"token {name} claim is invalid")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum_length:
        raise AuthenticationFailed(f"token {name} claim is invalid")
    return normalized


def _numeric_date(claims: Mapping[str, object], name: str) -> float:
    """Return one finite non-boolean JWT NumericDate value."""

    value = claims.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AuthenticationFailed(f"token {name} claim is invalid")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise AuthenticationFailed(f"token {name} claim is invalid")
    return numeric_value


def _scope_collection(claims: Mapping[str, object]) -> frozenset[str]:
    """Parse one bounded RFC 9068 space-delimited operation-scope claim."""

    raw_scope = claims.get("scope")
    if not isinstance(raw_scope, str) or not raw_scope or len(raw_scope) > 8_192:
        raise AuthenticationFailed("token scope claim is invalid")
    scope_values = raw_scope.split(" ")
    if (
        not scope_values
        or len(scope_values) > 64
        or any(not value for value in scope_values)
    ):
        raise AuthenticationFailed("token scope claim is invalid")
    scopes = tuple(_scope_code(value) for value in scope_values)
    if len(set(scopes)) != len(scopes):
        raise AuthenticationFailed("token scope claim contains duplicates")
    return frozenset(scopes)


def _scope_code(value: object) -> str:
    """Normalize one operation scope using the People API scope vocabulary."""

    if not isinstance(value, str):
        raise AuthenticationFailed("token scope code is invalid")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise AuthenticationFailed("token scope code is invalid")
    normalized = value.strip()
    if not normalized or len(normalized) > 128:
        raise AuthenticationFailed("token scope code is invalid")
    if not all(character in _SCOPE_CHARACTERS for character in normalized):
        raise AuthenticationFailed("token scope code is invalid")
    return normalized


def _purpose_collection(
    claims: Mapping[str, object],
    claim_name: str,
) -> frozenset[str]:
    """Parse one bounded duplicate-free application-purpose collection."""

    raw_purposes = claims.get(claim_name)
    if (
        not isinstance(raw_purposes, Sequence)
        or isinstance(raw_purposes, (str, bytes, bytearray))
        or not raw_purposes
        or len(raw_purposes) > 64
    ):
        raise AuthenticationFailed(f"token {claim_name} claim is invalid")
    purposes = tuple(_purpose_code(value) for value in raw_purposes)
    if len(set(purposes)) != len(purposes):
        raise AuthenticationFailed(f"token {claim_name} claim contains duplicates")
    return frozenset(purposes)


def _purpose_code(value: object) -> str:
    """Normalize one bounded lower-case ASCII HR purpose code."""

    if not isinstance(value, str):
        raise AuthenticationFailed("token purpose code is invalid")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise AuthenticationFailed("token purpose code is invalid")
    normalized = value.strip()
    if not normalized or len(normalized) > 128:
        raise AuthenticationFailed("token purpose code is invalid")
    if not all(
        character.isascii()
        and (character.islower() or character.isdigit() or character == "_")
        for character in normalized
    ):
        raise AuthenticationFailed("token purpose code is invalid")
    return normalized
