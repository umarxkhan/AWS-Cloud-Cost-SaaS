"""Server-side validation of Cognito access-token JWTs (defense-in-depth).

API Gateway's Cognito authorizer remains the primary edge authorization.
In addition, before resolving the user, we validate the access token's
signature, issuer, expiration, and audience (Cognito client id) so the Lambda
is not solely trusting an edge-forged `requestContext.authorizer.claims`.

Uses PyJWT + cryptography (RSA). The public keys (JWKS) are fetched from the
Cognito user pool and cached. For local/tests, a static JWKS may be provided
via the COGNITO_JWKS env var (JSON) to avoid a network fetch.
"""
from __future__ import annotations

import json
import logging
import os
import time

import jwt
from shared.errors import ApiError, unauthorized

logger = logging.getLogger("cloud-cost-saas")


def _region() -> str:
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "eu-central-1"
    )


def _user_pool_id() -> str:
    return os.environ.get("COGNITO_USER_POOL_ID", "")


def _client_id() -> str:
    return os.environ.get("COGNITO_CLIENT_ID", "")


def issuer() -> str:
    pool = _user_pool_id()
    return f"https://cognito-idp.{_region()}.amazonaws.com/{pool}" if pool else ""


def _jwks_url() -> str:
    return f"{issuer()}/.well-known/jwks.json"


_JWKS_TTL_SECONDS = 900  # 15 minutes; modest, in-process only

_keys_cache: dict = {"keys": {}, "expires_at": 0.0}


def _public_keys(force: bool = False) -> dict:
    """kid -> RSA key. Uses COGNITO_JWKS (tests) or fetches Cognito JWKS.

    The cache is in-process only and is refreshed after a short TTL (or on
    demand via `force` when an unknown kid is encountered) so key rotation is
    honored without introducing any persistent caching.
    """
    now = time.time()
    if not force and _keys_cache["expires_at"] > now:
        return _keys_cache["keys"]

    static = os.environ.get("COGNITO_JWKS")
    if static:
        data = json.loads(static)
    else:
        if not _user_pool_id():
            raise unauthorized("Cognito is not configured", "AUTH_CONFIG_ERROR")
        from urllib.request import urlopen

        with urlopen(_jwks_url(), timeout=5) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))

    keys = {}
    for k in data.get("keys", []):
        try:
            keys[k["kid"]] = jwt.algorithms.RSAAlgorithm.from_jwk(k)
        except Exception:  # noqa: BLE001
            logger.warning("skipping unparseable JWK %s", k.get("kid"))
    _keys_cache["keys"] = keys
    _keys_cache["expires_at"] = now + _JWKS_TTL_SECONDS
    return keys


def verify_access_token(token: str | None) -> dict:
    """Validate a Cognito ACCESS token and return its claims (incl `sub`).

    Cognito access tokens are bound to the app client via the `client_id`
    claim (NOT `aud`), so we verify: RS256 signature, issuer, expiration,
    token_use == "access", a non-empty sub, and client_id == COGNITO_CLIENT_ID.
    """
    if not token:
        raise unauthorized("Missing access token", "UNAUTHORIZED")
    if not _client_id():
        raise unauthorized("Cognito client is not configured", "AUTH_CONFIG_ERROR")
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        key = _public_keys().get(kid)
        if key is None:
            # Unknown kid: the JWKS may have rotated -> refresh once before rejecting.
            key = _public_keys(force=True).get(kid)
        if key is None:
            raise unauthorized("Unknown token signing key", "UNAUTHORIZED")
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=issuer(),
            options={"require": ["exp", "iss"]},
        )
        if claims.get("token_use") != "access":
            raise unauthorized("Unexpected token use", "UNAUTHORIZED")
        if not claims.get("sub"):
            raise unauthorized("Token missing subject", "UNAUTHORIZED")
        if claims.get("client_id") != _client_id():
            raise unauthorized("Unexpected token client", "UNAUTHORIZED")
        return claims
    except jwt.ExpiredSignatureError:
        raise unauthorized("Access token expired", "TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid access token", "UNAUTHORIZED")
    except ApiError:
        raise
    except Exception:  # noqa: BLE001
        logger.exception("JWT verification failed unexpectedly")
        raise unauthorized("Invalid access token", "UNAUTHORIZED")


def extract_bearer(headers: dict | None) -> str | None:
    """Read the Bearer token from the Authorization header."""
    for k, v in (headers or {}).items():
        if k.lower() == "authorization" and v:
            parts = v.split(" ", 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip()
    return None
