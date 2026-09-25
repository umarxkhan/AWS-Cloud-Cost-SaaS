"""Tenancy + authorization resolution.

The backend derives `tenant_id` and `role` from the Cognito `sub` claim via the
`saas-users` DynamoDB table (the authorization source of truth). The client is
NEVER trusted to supply tenant scope or role.

Typical `saas-users` row:
    sub        = "<cognito sub>"
    tenant_id  = "platform" | "<tenant uuid>"
    role       = "platform_admin" | "admin" | "member"
    status     = "ACTIVE" | "PENDING" | "DISABLED"
    email      = "..."
    created_at = "<iso timestamp>"

Roles:
    platform_admin -> all tenants + the platform tenant (manage + read)
    admin          -> own tenant (manage accounts, validate, read)
    member         -> own tenant (read-only)
"""
from __future__ import annotations

from . import db
from .errors import forbidden, unauthorized

ROLE_PLATFORM_ADMIN = "platform_admin"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"

# Roles allowed to perform tenant mutations (link/validate accounts).
MUTATION_ROLES = {ROLE_PLATFORM_ADMIN, ROLE_ADMIN}


class TenantContext:
    """Resolved tenant + role for an authenticated principal."""

    __slots__ = ("email", "role", "status", "sub", "tenant_id")

    def __init__(self, sub: str, tenant_id: str, role: str, status: str, email: str) -> None:
        self.sub = sub
        self.tenant_id = tenant_id
        self.role = role
        self.status = status
        self.email = email

    @property
    def is_platform_admin(self) -> bool:
        return self.role == ROLE_PLATFORM_ADMIN and self.status == "ACTIVE"

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"


def resolve_tenant_context(sub: str | None) -> TenantContext | None:
    """Resolve a Cognito sub to a TenantContext, or None if unknown/inactive."""
    user = db.get_user(sub) if sub else None
    if not user:
        return None
    status = user.get("status", "ACTIVE")
    if status != "ACTIVE":
        return None
    role = user.get("role") or ROLE_MEMBER
    if role not in {ROLE_PLATFORM_ADMIN, ROLE_ADMIN, ROLE_MEMBER}:
        return None
    return TenantContext(
        sub=user["sub"],
        tenant_id=str(user.get("tenant_id") or ""),
        role=role,
        status=status,
        email=str(user.get("email") or ""),
    )


def require_authenticated(ctx: TenantContext | None) -> TenantContext:
    if ctx is None or not ctx.is_active:
        raise unauthorized("Authentication required", "UNAUTHENTICATED")
    return ctx


def require_roles(ctx: TenantContext | None, allowed: set[str]) -> TenantContext:
    ctx = require_authenticated(ctx)
    if ctx.role not in allowed:
        raise forbidden("Insufficient permissions for this operation", "INSUFFICIENT_PERMISSIONS")
    return ctx


def require_mutation(ctx: TenantContext | None) -> TenantContext:
    """Require platform_admin or tenant admin (members are read-only)."""
    ctx = require_authenticated(ctx)
    if ctx.role not in MUTATION_ROLES:
        raise forbidden("Administrator role required", "INSUFFICIENT_PERMISSIONS")
    return ctx
