import os
import sys

import boto3
import pytest
from moto import mock_aws

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.join(_BACKEND, "api"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # backend/tests

os.environ.setdefault("USERS_TABLE", "saas-prod-users")
os.environ.setdefault("TENANTS_TABLE", "saas-prod-tenants")
os.environ.setdefault("CUSTOMER_ACCOUNTS_TABLE", "saas-prod-customer-accounts")
os.environ.setdefault("COST_DATA_TABLE", "saas-prod-cost-data")
os.environ.setdefault("COLLECTION_JOBS_TABLE", "saas-prod-collection-jobs")
os.environ.setdefault("QUEUE_URL", "http://local.test/cost-collection-queue")
os.environ.setdefault("WORKER_FUNCTION", "saas-prod-collector-worker")

import shared.db as _db  # noqa: E402  (needs sys.path set above)


def _create_tables():
    ddb = boto3.resource("dynamodb")
    ddb.create_table(
        TableName="saas-prod-users",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "sub", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "sub", "AttributeType": "S"},
            {"AttributeName": "tenant_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "GSI1",
            "KeySchema": [{"AttributeName": "tenant_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )
    ddb.create_table(
        TableName="saas-prod-tenants",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "tenant_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "tenant_id", "AttributeType": "S"}],
    )
    ddb.create_table(
        TableName="saas-prod-customer-accounts",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "tenant_id", "KeyType": "HASH"},
            {"AttributeName": "account_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "tenant_id", "AttributeType": "S"},
            {"AttributeName": "account_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "GSI1",
            "KeySchema": [{"AttributeName": "account_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )
    ddb.create_table(
        TableName="saas-prod-cost-data",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
    )
    ddb.create_table(
        TableName="saas-prod-collection-jobs",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "tenant_id", "KeyType": "HASH"},
            {"AttributeName": "job_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "tenant_id", "AttributeType": "S"},
            {"AttributeName": "job_id", "AttributeType": "S"},
        ],
    )


def _seed_users():
    users = _db.users_table()
    rows = [
        ("p", "platform_admin", "platform", "ACTIVE"),
        ("admin_a", "admin", "T_A", "ACTIVE"),
        ("member_a", "member", "T_A", "ACTIVE"),
        ("admin_b", "admin", "T_B", "ACTIVE"),
        ("disabled_a", "admin", "T_A", "DISABLED"),
    ]
    for sub, role, tenant, status in rows:
        users.put_item(Item={
            "sub": sub, "tenant_id": tenant, "role": role,
            "status": status, "email": f"{sub}@example.test",
        })
    for tid in ("T_A", "T_B", "platform"):
        _db.tenants_table().put_item(Item={"tenant_id": tid, "status": "ACTIVE"})


@pytest.fixture
def ddb():
    with mock_aws():
        _db._tables.clear()
        _create_tables()
        yield


@pytest.fixture
def seeded(ddb):
    _seed_users()
    rec_a = _db.create_account("T_A", "111122223333")
    rec_b = _db.create_account("T_B", "444455556666")
    _db.put_cost_data("T_A", "111122223333", "2026-09-01", 10.0, {"EC2": 6.0, "S3": 4.0})
    _db.put_cost_data("T_A", "111122223333", "2026-09-02", 20.0, {"EC2": 12.0, "S3": 8.0})
    _db.put_cost_data("T_B", "444455556666", "2026-09-01", 99.0, {"RDS": 99.0})
    return {"A": rec_a, "B": rec_b}
