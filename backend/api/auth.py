"""Authentication / claim handling.

The API Gateway Cognito authorizer validates the token at the edge and forwards
the validated claims at `requestContext.authorizer.claims`. The backend reads
`sub` from there and resolves authorization from `saas-users` (never the edge
authorizer role, and never anything the client can influence).
"""
from __future__ import annotations

from typing import Any


def extract_claims(event: dict[str, Any] | None) -> dict[str, Any]:
    try:
        authz = ((event or {}).get("requestContext") or {}).get("authorizer") or {}
        claims = authz.get("claims") or {}
        return dict(claims)
    except Exception:
        return {}


def get_sub(event: dict[str, Any] | None) -> str | None:
    claims = extract_claims(event)
    return claims.get("sub") or None
