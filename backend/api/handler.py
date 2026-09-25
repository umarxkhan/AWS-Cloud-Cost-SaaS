"""Lambda handler entrypoint (skeleton).

Dispatches API Gateway events to router.route(). In the implementation stage
this validates the id_token claims (sub), resolves the tenant via saas-users,
enforces the authorization matrix, and returns the Lambda proxy response.
"""
from __future__ import annotations

from typing import Any


def lambda_handler(event: dict | None = None, context: Any = None) -> dict:
    # TODO(implementation stage): decode/validate Cognito access token,
    # route to the correct handler, apply authorization, build proxy response.
    http_method = (event or {}).get("httpMethod", "GET")
    path = (event or {}).get("path", "/health")

    payload = {
        "service": "cloud-cost-calculator-saas",
        "endpoint": f"{http_method} {path}",
    }
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json_dumps(payload),
    }


def json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj)