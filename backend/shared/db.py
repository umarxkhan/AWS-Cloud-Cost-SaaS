"""DynamoDB access layer for the Cloud Cost SaaS.

Table names come from environment variables set by Terraform:
    USERS_TABLE, TENANTS_TABLE, CUSTOMER_ACCOUNTS_TABLE, COST_DATA_TABLE,
    COLLECTION_JOBS_TABLE, QUEUE_URL

customer-accounts schema: PK=tenant_id, SK=account#<aws_account_id>; the GSI
(GSI1) is on `account_id` (=account#<id>) to resolve an account's owning tenant.
An extra `aws_account_id` attribute stores the raw 12-digit id.
cost-data schema: PK=tenant#<tenant_id>#account#<aws_account_id>, SK=YYYY-MM-DD.
"""
from __future__ import annotations

import json
import os
import secrets
from datetime import UTC, datetime
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from .errors import conflict

CUSTOMER_COLLECTOR_ROLE = "CloudCostCollector"


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


_tables: dict = {}


def _table(env_key: str, default: str):
    name = _env(env_key, default)
    if name not in _tables:
        _tables[name] = boto3.resource("dynamodb").Table(name)
    return _tables[name]


def users_table():
    return _table("USERS_TABLE", "saas-prod-users")


def tenants_table():
    return _table("TENANTS_TABLE", "saas-prod-tenants")


def customer_accounts_table():
    return _table("CUSTOMER_ACCOUNTS_TABLE", "saas-prod-customer-accounts")


def cost_data_table():
    return _table("COST_DATA_TABLE", "saas-prod-cost-data")


def collection_jobs_table():
    return _table("COLLECTION_JOBS_TABLE", "saas-prod-collection-jobs")


def _sqs():
    return boto3.client("sqs")


def queue_url() -> str:
    return _env("QUEUE_URL", "")


def cost_data_key(tenant_id: str, account_id: str) -> str:
    """Composite PK for cost-data: tenant#<tenant_id>#account#<account_id>."""
    return f"tenant#{tenant_id}#account#{account_id}"


def customer_account_sk(aws_account_id: str) -> str:
    """Range-key value for customer-accounts."""
    return f"account#{aws_account_id}"


def role_arn_for(aws_account_id: str) -> str:
    return f"arn:aws:iam::{aws_account_id}:role/{CUSTOMER_COLLECTOR_ROLE}"


# --- users -----------------------------------------------------------------
def get_user(sub: str) -> dict | None:
    if not sub:
        return None
    try:
        resp = users_table().get_item(Key={"sub": sub})
    except Exception:
        return None
    return resp.get("Item")


# --- customer accounts ------------------------------------------------------
def create_account(tenant_id: str, aws_account_id: str) -> dict:
    """Idempotency-safe create.

    Raises 409 CONFLICT if the account is already linked to this tenant OR to
    any other tenant. The ExternalId is generated server-side and the role ARN
    is constructed server-side (never accepted from the client).
    """
    account_sk = customer_account_sk(aws_account_id)

    existing_for_tenant = get_account(tenant_id, aws_account_id)
    if existing_for_tenant is not None:
        raise conflict(
            "This AWS account is already linked to your tenant",
            "ACCOUNT_ALREADY_LINKED",
        )

    existing_elsewhere = resolve_account_by_id(aws_account_id)
    if existing_elsewhere is not None:
        raise conflict(
            "This AWS account is already linked to a tenant",
            "ACCOUNT_ALREADY_LINKED_ELSEWHERE",
        )

    now = _utcnow_iso()
    external_id = secrets.token_urlsafe(32)
    item = {
        "tenant_id": tenant_id,
        "account_id": account_sk,
        "aws_account_id": aws_account_id,
        "role_arn": role_arn_for(aws_account_id),
        "external_id": external_id,
        "expected_account_id": aws_account_id,
        "status": "PENDING",
        "created_at": now,
    }
    customer_accounts_table().put_item(Item=item)
    return dict(item)


def get_account(tenant_id: str, aws_account_id: str) -> dict | None:
    try:
        resp = customer_accounts_table().get_item(
            Key={"tenant_id": tenant_id, "account_id": customer_account_sk(aws_account_id)}
        )
    except Exception:
        return None
    return resp.get("Item")


def list_accounts(tenant_id: str) -> list[dict]:
    try:
        resp = customer_accounts_table().query(
            KeyConditionExpression="tenant_id = :t",
            ExpressionAttributeValues={":t": tenant_id},
        )
    except Exception:
        return []
    return resp.get("Items", [])


def resolve_account_by_id(aws_account_id: str) -> dict | None:
    """Find the owning tenant of an account via the GSI (account_id)."""
    try:
        resp = customer_accounts_table().query(
            IndexName="GSI1",
            KeyConditionExpression="account_id = :a",
            ExpressionAttributeValues={":a": customer_account_sk(aws_account_id)},
        )
    except Exception:
        return None
    items = resp.get("Items", [])
    return items[0] if items else None


def update_account_status(
    tenant_id: str,
    aws_account_id: str,
    status: str,
    fail_reason: str | None = None,
    last_validated_at: str | None = None,
) -> None:
    update_expr = ["SET #s = :status"]
    attr_names = {"#s": "status"}
    attr_values = {":status": status}
    if fail_reason is not None:
        update_expr.append("#r = :reason")
        attr_names["#r"] = "fail_reason"
        attr_values[":reason"] = fail_reason
    if last_validated_at is not None:
        update_expr.append("#v = :validated")
        attr_names["#v"] = "last_validated_at"
        attr_values[":validated"] = last_validated_at
    customer_accounts_table().update_item(
        Key={"tenant_id": tenant_id, "account_id": customer_account_sk(aws_account_id)},
        UpdateExpression=", ".join(update_expr),
        ExpressionAttributeNames=attr_names,
        ExpressionAttributeValues=attr_values,
    )


# --- cost data ---------------------------------------------------------------
def query_cost_data(tenant_id: str, aws_account_id: str, start: str, end: str) -> list[dict]:
    try:
        resp = cost_data_table().query(
            KeyConditionExpression="pk = :pk AND sk BETWEEN :s AND :e",
            ExpressionAttributeValues={
                ":pk": cost_data_key(tenant_id, aws_account_id),
                ":s": start,
                ":e": end,
            },
        )
    except Exception:
        return []
    return resp.get("Items", [])


def put_cost_data(
    tenant_id: str,
    aws_account_id: str,
    day: str,
    total_cost: float,
    services: dict,
    currency: str = "USD",
) -> None:
    # DynamoDB numbers must be Decimal, never float.
    services_dec = {str(k): Decimal(str(float(v))) for k, v in (services or {}).items()}
    item = {
        "pk": cost_data_key(tenant_id, aws_account_id),
        "sk": day,
        "tenant_id": tenant_id,
        "aws_account_id": aws_account_id,
        "total_cost": Decimal(str(float(total_cost))),
        "services": services_dec,
        "currency": currency,
        "collected_at": _utcnow_iso(),
    }
    try:
        cost_data_table().put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(pk)",
        )
    except ClientError as exc:
        code = (exc.response or {}).get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            # Duplicate/redelivered message for the same (tenant, account, day):
            # a successful record already exists - idempotently skip, don't overwrite.
            return None
        raise


# --- collection jobs ----------------------------------------------------------
def record_job(tenant_id: str, job_id: str, status: str, error: str | None = None) -> None:
    item = {
        "tenant_id": tenant_id,
        "job_id": job_id,
        "status": status,
        "started_at": _utcnow_iso(),
    }
    if error is not None:
        item["error"] = error
    collection_jobs_table().put_item(Item=item)


# --- SQS ----------------------------------------------------------------------
def send_sqs_message(payload: dict) -> None:
    url = queue_url()
    if not url:
        return
    _sqs().send_message(QueueUrl=url, MessageBody=json.dumps(payload))
