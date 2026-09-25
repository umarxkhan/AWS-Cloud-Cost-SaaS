"""DynamoDB access layer (skeleton).

Table names come from environment variables set by Terraform:
    USERS_TABLE, TENANTS_TABLE, CUSTOMER_ACCOUNTS_TABLE, COST_DATA_TABLE,
    COLLECTION_JOBS_TABLE, QUEUE_URL
"""
from __future__ import annotations

import os

import boto3

_users_table = os.environ.get("USERS_TABLE", "saas-prod-users")
_tenants_table = os.environ.get("TENANTS_TABLE", "saas-prod-tenants")
_customer_accounts_table = os.environ.get("CUSTOMER_ACCOUNTS_TABLE", "saas-prod-customer-accounts")
_cost_data_table = os.environ.get("COST_DATA_TABLE", "saas-prod-cost-data")
_collection_jobs_table = os.environ.get("COLLECTION_JOBS_TABLE", "saas-prod-collection-jobs")
_queue_url = os.environ.get("QUEUE_URL", "")

_ddb = boto3.resource("dynamodb")

users_table = _ddb.Table(_users_table)
tenants_table = _ddb.Table(_tenants_table)
customer_accounts_table = _ddb.Table(_customer_accounts_table)
cost_data_table = _ddb.Table(_cost_data_table)
collection_jobs_table = _ddb.Table(_collection_jobs_table)

_sqs = boto3.client("sqs")


def cost_data_key(tenant_id: str, account_id: str) -> str:
    """Composite PK for cost-data: tenant#<tenant_id>#account#<account_id>."""
    return f"tenant#{tenant_id}#account#{account_id}"


# TODO(implementation stage): get_user(sub), create_account(...),
# list_accounts(tenant_id), get_account(tenant_id, account_id),
# write_cost_data(pk, sk, ...), enqueue(tenant_id, account_id, date), ...