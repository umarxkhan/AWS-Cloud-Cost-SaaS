"""collector-worker: SQS consumer; the ONLY STS/cross-account principal.

The worker is AUTHORITATIVE for cross-account configuration: it loads role_arn,
external_id, and expected_account_id from `customer-accounts` itself using the
(tenant_id, account_id) from the message — it never trusts client-supplied role
config. Supports two task types:
    validate  -> AssumeRole (ExternalId) -> GetCallerIdentity -> verify account id
    collect   -> AssumeRole -> Cost Explorer (via customer role) -> write cost-data
"""
from __future__ import annotations

from typing import Any


def handler(event: dict | None = None, context: Any = None) -> dict:
    # TODO(implementation stage): for each SQS record:
    #   tenant_id, account_id, task = payload
    #   config = load from customer-accounts (authoritative)
    #   dispatch validate | collect
    return {"statusCode": 200, "body": "[]"}


def _sts_client():
    raise NotImplementedError("Implemented in stage 3")