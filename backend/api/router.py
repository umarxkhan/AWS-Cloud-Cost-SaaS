"""API router (skeleton).

AUTHORIZATION PRINCIPLE:
- The backend derives `tenant_id` and role from the Cognito id_token `sub`
  resolved through the `saas-users` DynamoDB table. It MUST NEVER accept a
  client-supplied `tenant_id` for authorization purposes.
- The frontend may supply `accountId` (path/query), but the backend MUST verify
  that the account belongs to the caller's tenant before any access.

Planned routes (final set, enforced in implementation stage):

    GET   /health                              unauthenticated
    POST  /accounts/link                       tenant admin, platform_admin
    GET   /accounts                            any authenticated (scoped)
    GET   /accounts/{accountId}                tenant admin, platform_admin
    POST  /accounts/{accountId}/validate       tenant admin, platform_admin
    GET   /costs/daily?accountId&start&end     any authenticated (scoped)
    GET   /costs/monthly?accountId&month       any authenticated (scoped)
    GET   /costs/breakdown?accountId&date      any authenticated (scoped)

Shared-auth: /health is NONE; everything else requires the Cognito authorizer
and must still re-validate claims + resolve tenant on the backend (never the
edge authorizer alone).
"""
from __future__ import annotations

from typing import Any

ROUTES: dict[tuple[str, str], str] = {
    ("GET", "/health"): "health",
    ("POST", "/accounts/link"): "accounts.link",
    ("GET", "/accounts"): "accounts.list",
    ("POST", "/accounts/{accountId}/validate"): "accounts.validate",
    ("GET", "/costs/daily"): "costs.daily",
    ("GET", "/costs/monthly"): "costs.monthly",
    ("GET", "/costs/breakdown"): "costs.breakdown",
}


def route(event: dict[str, Any]) -> dict[str, Any]:
    # TODO(implementation stage): match method+path, run authorization,
    # dispatch to route handlers under backend/api/routes/.
    raise NotImplementedError("Implemented in stage 3")