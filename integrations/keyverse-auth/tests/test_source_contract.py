"""Static contracts for the Keyverse authorization trust boundary."""

from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "orgmetra_keyverse_auth"


def _source_text() -> str:
    """Return all shipped integration source as one audit string."""

    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(PACKAGE_ROOT.glob("*.py"))
    )


def test_authorizer_owns_no_network_or_environment_authority() -> None:
    source = _source_text()

    forbidden_terms = {
        "import requests",
        "import httpx",
        "urllib.request",
        "socket.",
        "os.environ",
        "os.getenv",
        "PyJWKClient",
        "print(",
        "logging.",
    }
    for term in forbidden_terms:
        assert term not in source
    assert "JwksProvider" in source
    assert "IdentityReferenceResolver" in source


def test_only_reviewed_asymmetric_algorithms_are_available() -> None:
    source = (PACKAGE_ROOT / "contracts.py").read_text(encoding="utf-8")

    assert 'frozenset({"RS256", "PS256", "ES256"})' in source
    for forbidden_algorithm in ("HS256", "HS384", "HS512", "none"):
        assert forbidden_algorithm not in source


def test_signature_issuer_audience_and_time_verification_are_explicit() -> None:
    source = (PACKAGE_ROOT / "authorizer.py").read_text(encoding="utf-8")

    required_fragments = {
        '"verify_signature": True',
        '"verify_aud": True',
        '"verify_iss": True',
        '"verify_exp": True',
        '"verify_iat": True',
        '"verify_nbf": True',
        '"require": ["iss", "sub", "aud", "exp", "iat", "jti"]',
        "audience=config.audience",
        "issuer=config.issuer",
    }
    for fragment in required_fragments:
        assert fragment in source
    assert 'options={"verify_signature": False}' not in source


def test_token_claims_are_not_logged_or_persisted() -> None:
    source = _source_text()

    forbidden_fields = {
        "audit_event",
        "token_payload",
        "raw_token",
        "access_token_hash",
        "database_url",
    }
    for field_name in forbidden_fields:
        assert field_name not in source
