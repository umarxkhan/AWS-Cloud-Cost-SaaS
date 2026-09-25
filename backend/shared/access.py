"""Centralized cross-tenant access gate.

Every account-scoped operation resolves the caller's access to a specific
customer account HERE, before any data is read/written:

- tenant admin/member: the account must belong to their own tenant; otherwise
  the operation returns 404 (no existence leak across tenants).
- platform_admin: may access accounts across all tenants (resolved by account
  id via the GSI) and will get 404 if the account does not exist.

The resolved record's `tenant_id` + `aws_account_id` are then used for the
actual DynamoDB operation, guaranteeing scope.
"""
from __future__ import annotations

from . import db
from .errors import not_found


def resolve_access_account(ctx, aws_account_id: str) -> dict:
    """Return the account record the caller is authorized to access."""
    within_tenant = db.get_account(ctx.tenant_id, aws_account_id)
    if within_tenant is not None:
        return within_tenant

    if ctx.is_platform_admin:
        across = db.resolve_account_by_id(aws_account_id)
        if across is not None:
            return across
        raise not_found("Account not found", "ACCOUNT_NOT_FOUND")

    # Same 404 for both "does not exist" and "exists but in another tenant".
    raise not_found("Account not found for your tenant", "ACCOUNT_NOT_FOUND")
