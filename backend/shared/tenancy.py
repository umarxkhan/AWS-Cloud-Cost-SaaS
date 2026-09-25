"""Tenancy + authorization resolution (skeleton).

The backend derives `tenant_id` and `role` from the Cognito `sub` claim via the
`saas-users` DynamoDB table — this is the authorization source of truth. The
client MUST never be trusted to supply tenant scope.

Typical `saas-users` row:
    sub        = "<cognito sub>"
    tenant_id  = "platform" | "<tenant uuid>"
    role       = "platform_admin" | "admin" | "member"
    status     = "ACTIVE" | "PENDING" | "DISABLED"
    email      = "..."
    created_at = "<iso timestamp>"

Authorization levels:
    platform_admin -> all tenants + the platform tenant
    admin          -> own tenant (manage accounts, validate, costs)
    member         -> own tenant (read-only costs)

Implemented in the implementation stage.
"""
from __future__ import annotations

from typing import Any


class TenantContext:
    """Resolved tenant + role for an authenticated principal."""

    __slots__ = ("sub", "tenant_id", "role", "status", "email")

    def __init__(self, sub: str, tenant_id: str, role: str, status: str, email: str) -> None:
        self.sub = sub
        self.tenant_id = tenant_id
        self.role = role
        self.status = status
        self.email = email

    @property
    def is_platform_admin(self) -> bool:
        return self.role == "platform_admin" and self.status == "ACTIVE"

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"


# TODO(implementation stage): resolve_tenant_context(sub) -> TenantContext | None
# 1. GetItem saas-users where PK = sub.
# 2. If missing/inactive -> None (401/403).
# 3. Return TenantContext.
def resolve_tenant_context(sub: str) -> "TenantContext | None":
    raise NotImplementedError("Implemented in stage 3")