"""Test helper: deterministic RS256 JWT minting + JWKS.

The backend (jwt_verify) is pointed at this JWKS via COGNITO_JWKS env so tests
can mint valid tokens and also produce invalid ones (wrong signature, wrong
audience, expired, unknown kid) without any network call.
"""
from __future__ import annotations

import json
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

REGION = "eu-central-1"
USER_POOL_ID = "eu-central-1_testpool"
CLIENT_ID = "test-client"
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"
KID = "test-key-1"

_priv = None
_bad_priv = None


def _private() -> rsa.RSAPrivateKey:
    global _priv
    if _priv is None:
        _priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return _priv


def _bad_key() -> rsa.RSAPrivateKey:
    global _bad_priv
    if _bad_priv is None:
        _bad_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return _bad_priv


def jwks_json() -> str:
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(_private().public_key())
    if isinstance(jwk, str):
        jwk = json.loads(jwk)
    jwk["kid"] = KID
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return json.dumps({"keys": [jwk]})


def mint(
    sub: str | None,
    *,
    key=None,
    kid: str = KID,
    iss: str = ISSUER,
    client_id: str = CLIENT_ID,
    exp: int | None = None,
    token_use: str = "access",
) -> str:
    """Mint a Cognito ACCESS token: client_id-based, no aud required."""
    key = key or _private()
    now = int(time.time())
    claims = {
        "iss": iss,
        "iat": now,
        "exp": exp if exp is not None else now + 3600,
        "token_use": token_use,
        "client_id": client_id,
    }
    if sub is not None:
        claims["sub"] = sub
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


def mint_bad_signature(sub: str) -> str:
    return mint(sub, key=_bad_key(), kid=KID)


def mint_wrong_client_id(sub: str) -> str:
    return mint(sub, client_id="some-other-client")


def mint_wrong_issuer(sub: str) -> str:
    return mint(sub, iss="https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_otherpool")


def mint_expired(sub: str) -> str:
    return mint(sub, exp=int(time.time()) - 100)


def mint_unknown_kid(sub: str) -> str:
    return mint(sub, kid="unknown-kid")


def mint_id_token(sub: str) -> str:
    return mint(sub, token_use="id")


def mint_missing_sub() -> str:
    return mint(None)
