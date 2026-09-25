"""collector-worker: SQS consumer / sync-invoke target; the ONLY STS principal.

The worker is AUTHORITATIVE for cross-account configuration: it loads
role_arn, external_id, and expected_account_id from `customer-accounts` itself
(using tenant_id + account_id from the message) — it NEVER trusts client- or
invoker-supplied role/external config.

    validate: AssumeRole(stored role, ExternalId) -> GetCallerIdentity ->
              compare account id -> only mark ACTIVE on exact match.
    collect : AssumeRole -> Cost Explorer using the ASSUMED credentials
              (DAILY granularity) -> write the approved cost-data PK/SK.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from shared import db, validation


def handler(event: dict | None = None, context: Any = None) -> dict:
    event = event or {}
    records = event.get("Records")
    if records:
        results = []
        failed = False
        for rec in records:
            try:
                payload = json.loads(rec.get("body") or "{}")
            except Exception:  # noqa: BLE001
                payload = {}
            result = run_task(payload)
            results.append(result)
            if result.get("status") == "ERROR":
                failed = True
        if failed:
            # Do NOT acknowledge: raise so SQS/Lambda redrive retries the batch
            # and (after max receives) it lands in the DLQ. (A 200 would delete
            # the message. Partial batch failure requires the event-source
            # mapping to enable ReportBatchItemFailures, which is not declared
            # in the current infrastructure, so raising is the safe default.)
            raise RuntimeError(
                "one or more collection messages failed; batch not acknowledged"
            )
        return {"statusCode": 200, "body": json.dumps({"results": results})}
    # Direct synchronous invocation from the backend (validate task).
    return run_task(event)


def run_task(payload: dict) -> dict:
    tenant_id = payload.get("tenant_id")
    account_id = payload.get("account_id")
    task = payload.get("task") or "validate"
    if not tenant_id or not account_id:
        return {"status": "ERROR", "message": "missing tenant_id/account_id"}
    cfg = db.get_account(tenant_id, account_id)
    if cfg is None:
        return {"status": "ERROR", "message": "account configuration not found"}
    if task == "validate":
        return run_validate(cfg)
    if task == "collect":
        return run_collect(cfg, payload.get("date"))
    return {"status": "ERROR", "message": "unknown task"}


def _assume(cfg: dict) -> dict:
    """Assume exactly the stored role with the stored ExternalId."""
    sts = boto3.client("sts")
    resp = sts.assume_role(
        RoleArn=cfg["role_arn"],
        RoleSessionName="saas-cost-collector",
        ExternalId=cfg["external_id"],
    )
    return resp["Credentials"]


def _assumed(creds: dict, service: str):
    return boto3.client(
        service,
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


def run_validate(cfg: dict) -> dict:
    expected = str(cfg.get("expected_account_id") or "")
    try:
        creds = _assume(cfg)
        identity = _assumed(creds, "sts").get_caller_identity()
        found = str(identity.get("Account", ""))
        valid = bool(expected) and found == expected
        status = "ACTIVE" if valid else "FAILED"
        reason = None if valid else "aws account id mismatch"
        db.update_account_status(
            cfg["tenant_id"], cfg["aws_account_id"], status,
            fail_reason=reason, last_validated_at=_now_iso(),
        )
        return {
            "valid": valid,
            "expected_account_id": expected,
            "found_account_id": found,
            "status": status,
        }
    except Exception:  # noqa: BLE001
        db.update_account_status(
            cfg["tenant_id"], cfg["aws_account_id"], "FAILED",
            fail_reason="validation error", last_validated_at=_now_iso(),
        )
        return {
            "valid": False,
            "expected_account_id": expected,
            "found_account_id": "",
            "status": "FAILED",
            "message": "validation failed",
        }


def run_collect(cfg: dict, date: str | None) -> dict:
    day = _normalize_day(date)
    if day is None:
        return {"status": "ERROR", "message": "invalid collection date"}
    try:
        creds = _assume(cfg)
        ce = _assumed(creds, "ce")
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": day, "End": day},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        services: dict = {}
        total = 0.0
        periods = resp.get("ResultsByTime") or []
        if periods:
            for group in periods[0].get("Groups", []):
                keys = group.get("Keys") or []
                if not keys:
                    continue
                svc = str(keys[0])
                amt = float(group.get("Metrics", {}).get("UnblendedCost", {}).get("Amount") or 0)
                services[svc] = round(services.get(svc, 0.0) + amt, 4)
                total += amt
        db.put_cost_data(cfg["tenant_id"], cfg["aws_account_id"], day, round(total, 4), services)
        return {
            "status": "OK",
            "date": day,
            "account_id": cfg["aws_account_id"],
            "total_cost": round(total, 4),
            "services": services,
        }
    except Exception:  # noqa: BLE001
        return {"status": "ERROR", "message": "cost collection failed"}


def _normalize_day(date: str | None) -> str | None:
    """Return a validated YYYY-MM-DD value or None if missing/malformed."""
    if date is None:
        return _yesterday()
    try:
        return validation.parse_date(date, "date").isoformat()
    except Exception:  # noqa: BLE001
        return None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _yesterday() -> str:
    return (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
