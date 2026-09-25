"""Lambda handler entrypoint.

Reads the Cognito-authorizer claims (sub), resolves the user from `saas-users`,
dispatches to the router, and builds the Lambda-proxy response. Internal
exception details are logged but NEVER serialized into the response.
"""
from __future__ import annotations

import json
import logging
import os
from decimal import Decimal
from typing import Any

import router
from jwt_verify import extract_bearer, verify_access_token
from shared import tenancy
from shared.errors import ApiError, server_error

logger = logging.getLogger("cloud-cost-saas")
logger.setLevel(logging.INFO)

_HEALTH_PATH = "/health"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def lambda_handler(event: dict | None = None, context: Any = None) -> dict:
    event = event or {}
    method = (event.get("httpMethod") or "GET").upper()
    path = event.get("path") or _HEALTH_PATH
    path_params = event.get("pathParameters") or {}
    query = event.get("queryStringParameters") or {}
    body = _parse_body(event)

    status = 200
    try:
        # /health is unauthenticated; everything else must present a valid
        # Cognito access token (verified server-side) and resolve an active user.
        ctx = None
        if path != _HEALTH_PATH:
            token = extract_bearer(event.get("headers"))
            claims = verify_access_token(token)
            sub = claims.get("sub")
            ctx = tenancy.resolve_tenant_context(sub)

        payload = router.route(ctx, method, path, path_params, query, body)
    except ApiError as err:
        if err.status_code >= 500:
            logger.exception("api error: %s", err.message)
        status = err.status_code
        payload = err.to_dict()
    except Exception as err:
        logger.exception("unhandled error: %s", err)
        status = 500
        payload = server_error().to_dict()

    headers = {"Content-Type": "application/json", "Cache-Control": "no-store"}
    origin = os.environ.get("ALLOWED_ORIGIN", "").strip()
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
    return {"statusCode": status, "headers": headers, "body": json.dumps(payload, default=_json_default)}


def _parse_body(event: dict) -> dict:
    raw = event.get("body")
    if not raw:
        return {}
    if event.get("isBase64Encoded"):
        try:
            import base64

            raw = base64.b64decode(raw).decode("utf-8")
        except Exception:  # noqa: BLE001
            return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:  # noqa: BLE001
        return {}
