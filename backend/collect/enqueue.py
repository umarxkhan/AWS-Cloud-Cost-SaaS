"""collector-enqueue: EventBridge schedule -> one SQS message per active account.

Loads active tenants + their active customer-accounts and sends one message per
(tenant_id, account_id) so the worker can process each independently. No STS,
no Cost Explorer, no customer-account access.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from shared import db


def handler(event: dict | None = None, context: Any = None) -> dict:
    try:
        resp = db.tenants_table().scan()
    except Exception:  # noqa: BLE001
        resp = {}
    tenant_ids = [
        t.get("tenant_id")
        for t in resp.get("Items", [])
        if (t.get("status") == "ACTIVE" and t.get("tenant_id"))
    ]
    yesterday = _yesterday()
    count = 0
    for tid in tenant_ids:
        for acc in db.list_accounts(tid):
            if acc.get("status") == "ACTIVE":
                db.send_sqs_message({
                    "tenant_id": tid,
                    "account_id": acc["aws_account_id"],
                    "task": "collect",
                    "date": yesterday,
                })
                count += 1
    return {"statusCode": 200, "body": json.dumps({"enqueued": count})}


def _yesterday() -> str:
    return (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
