"""Cost route handlers.

All cost queries are tenant-isolated: the record is resolved via
`shared.access.resolve_access_account` (which enforces the caller's tenant) and
querying uses that record's tenant_id + aws_account_id for the cost-data PK.
Monthly/breakdown aggregate the approved daily records for the MVP.
"""
from __future__ import annotations

from shared import db, tenancy, validation
from shared.access import resolve_access_account


def _entries(items: list[dict]) -> list[dict]:
    out = []
    for i in sorted(items, key=lambda x: x.get("sk", "")):
        out.append({
            "date": i.get("sk"),
            "total_cost": float(i.get("total_cost", 0.0)),
            "services": i.get("services", {}),
        })
    return out


def daily(ctx, path_params: dict, query: dict, body: dict) -> dict:
    tenancy.require_authenticated(ctx)
    aws_account_id = validation.validate_account_id(query.get("accountId"))
    start, end = validation.validate_date_range(query.get("start"), query.get("end"))
    record = resolve_access_account(ctx, aws_account_id)
    items = db.query_cost_data(record["tenant_id"], record["aws_account_id"], start, end)
    return {
        "account_id": aws_account_id,
        "start": start,
        "end": end,
        "entries": _entries(items),
    }


def monthly(ctx, path_params: dict, query: dict, body: dict) -> dict:
    tenancy.require_authenticated(ctx)
    aws_account_id = validation.validate_account_id(query.get("accountId"))
    month = validation.parse_month(query.get("month"))
    start, end = validation.month_range(month)
    record = resolve_access_account(ctx, aws_account_id)
    items = db.query_cost_data(record["tenant_id"], record["aws_account_id"], start, end)
    total = 0.0
    services: dict = {}
    for i in items:
        total += float(i.get("total_cost", 0.0))
        for svc, amt in (i.get("services") or {}).items():
            services[svc] = round(services.get(svc, 0.0) + float(amt), 4)
    return {
        "account_id": aws_account_id,
        "month": month,
        "total_cost": round(total, 4),
        "services": services,
        "days": len(items),
    }


def breakdown(ctx, path_params: dict, query: dict, body: dict) -> dict:
    tenancy.require_authenticated(ctx)
    aws_account_id = validation.validate_account_id(query.get("accountId"))
    day = validation.parse_date(query.get("date"), "date").isoformat()
    record = resolve_access_account(ctx, aws_account_id)
    items = db.query_cost_data(record["tenant_id"], record["aws_account_id"], day, day)
    item = items[0] if items else None
    if item is None:
        return {"account_id": aws_account_id, "date": day, "total_cost": 0.0, "services": {}}
    return {
        "account_id": aws_account_id,
        "date": day,
        "total_cost": float(item.get("total_cost", 0.0)),
        "services": item.get("services", {}),
    }
