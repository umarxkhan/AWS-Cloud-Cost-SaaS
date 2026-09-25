"""collector-enqueue: EventBridge schedule -> one SQS message per (tenant, account).

Does NOT touch customer accounts. Loads active tenants + their active
customer-accounts and sends a message per account_id so the worker can process
each independently. No STS, no Cost Explorer.
"""
from __future__ import annotations

from typing import Any


def handler(event: dict | None = None, context: Any = None) -> dict:
    # TODO(implementation stage): query saas-tenants (ACTIVE) -> their
    # customer-accounts (ACTIVE) -> sqs.send_message(QUEUE_URL).
    return {"statusCode": 200, "body": "[]"}