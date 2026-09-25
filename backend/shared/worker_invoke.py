"""Synchronous invocation of the collector-worker.

The backend sends ONLY {tenant_id, account_id, task}; it NEVER sends role_arn,
external_id, or expected_account_id (the worker loads its own authoritative
config from DynamoDB). The backend does not have any STS permission.
"""
from __future__ import annotations

import json
import os

import boto3

from .errors import server_error


def invoke_worker(payload: dict) -> dict:
    function = os.environ.get("WORKER_FUNCTION")
    if not function:
        raise server_error("Collector worker is not configured", "WORKER_NOT_CONFIGURED")
    try:
        client = boto3.client("lambda")
        resp = client.invoke(
            FunctionName=function,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
        data = json.loads(resp["Payload"].read())
    except Exception:
        raise server_error("Could not reach collector worker", "WORKER_INVOCATION_FAILED")

    if data.get("statusCode") and int(data["statusCode"]) >= 400:
        raise server_error("Collector worker reported an error", "WORKER_ERROR")
    return data.get("result", data)
