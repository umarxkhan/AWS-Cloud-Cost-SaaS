"""Account route handlers.

Ownership: every account operation is gated through
`shared.access.resolve_access_account` (tenant isolation). The body of
`link` accepts ONLY `aws_account_id`; role_arn/external_id are generated
server-side and any client-supplied values are ignored.
"""
from __future__ import annotations

from shared import db, tenancy, validation, worker_invoke
from shared.access import resolve_access_account


def _public(record: dict) -> dict:
    """Public projection - never includes external_id or role_arn."""
    return {
        "account_id": record.get("aws_account_id"),
        "status": record.get("status"),
        "created_at": record.get("created_at"),
        "last_validated_at": record.get("last_validated_at"),
        "fail_reason": record.get("fail_reason"),
    }


def link(ctx, path_params: dict, query: dict, body: dict) -> dict:
    tenancy.require_mutation(ctx)  # platform_admin or tenant admin only
    aws_account_id = validation.validate_account_id(body.get("aws_account_id"))
    # create_account is idempotency-safe and raises 409 on duplicate links;
    # it generates external_id and role_arn server-side.
    record = db.create_account(ctx.tenant_id, aws_account_id)
    return {
        "account_id": record["aws_account_id"],
        "status": record["status"],
        # Required once for customer onboarding only:
        "role_arn": record["role_arn"],
        "external_id": record["external_id"],
        "instructions": (
            "Create the cross-account role in your AWS account using the role "
            "ARN and external_id above, then call POST /accounts/{accountId}/validate."
        ),
    }


def list(ctx, path_params: dict, query: dict, body: dict) -> dict:
    tenancy.require_authenticated(ctx)
    accounts = db.list_accounts(ctx.tenant_id)
    return {"accounts": [_public(a) for a in accounts]}


def get(ctx, path_params: dict, query: dict, body: dict) -> dict:
    tenancy.require_authenticated(ctx)
    aws_account_id = validation.validate_account_id(path_params.get("accountId"))
    record = resolve_access_account(ctx, aws_account_id)
    return _public(record)


def validate(ctx, path_params: dict, query: dict, body: dict) -> dict:
    tenancy.require_mutation(ctx)  # platform_admin or tenant admin only
    aws_account_id = validation.validate_account_id(path_params.get("accountId"))
    record = resolve_access_account(ctx, aws_account_id)
    result = worker_invoke.invoke_worker({
        "tenant_id": record["tenant_id"],
        "account_id": record["aws_account_id"],
        "task": "validate",
    })
    return {
        "account_id": record["aws_account_id"],
        "valid": bool(result.get("valid")),
        "status": result.get("status", "UNKNOWN"),
        "found_account_id": result.get("found_account_id"),
    }
