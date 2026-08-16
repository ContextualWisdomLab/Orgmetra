from __future__ import annotations
import json
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
import pytest
from orgmetra_keyverse_auth.authorizer import _select_signing_key
from orgmetra_people_api import AuthenticationFailed, IdentityProviderUnavailable

@pytest.fixture(scope="module")
def public_jwk() -> dict[str, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": "key-1", "alg": "RS256", "use": "sig"})
    return jwk

@pytest.mark.parametrize("key_ops", [["encrypt"], ["sign"], ["verify", "encrypt"]])
def test_explicit_key_ops_must_allow_only_verification(public_jwk, key_ops) -> None:
    jwk = dict(public_jwk)
    jwk["key_ops"] = key_ops
    with pytest.raises(AuthenticationFailed, match="signing key"):
        _select_signing_key({"keys": [jwk]}, key_identifier="key-1", algorithm="RS256")

@pytest.mark.parametrize("key_ops", [[], ["verify", "verify"], ["verify", 1], "verify", ["verify"] * 17])
def test_malformed_key_ops_is_provider_failure(public_jwk, key_ops) -> None:
    jwk = dict(public_jwk)
    jwk["key_ops"] = key_ops
    with pytest.raises(IdentityProviderUnavailable, match="operations"):
        _select_signing_key({"keys": [jwk]}, key_identifier="key-1", algorithm="RS256")

def test_verify_only_key_ops_is_accepted(public_jwk) -> None:
    jwk = dict(public_jwk)
    jwk["key_ops"] = ["verify"]
    selected = _select_signing_key({"keys": [jwk]}, key_identifier="key-1", algorithm="RS256")
    assert selected.algorithm_name == "RS256"

def test_absent_key_ops_remains_accepted_for_compatible_jwk(public_jwk) -> None:
    selected = _select_signing_key({"keys": [dict(public_jwk)]}, key_identifier="key-1", algorithm="RS256")
    assert selected.algorithm_name == "RS256"
