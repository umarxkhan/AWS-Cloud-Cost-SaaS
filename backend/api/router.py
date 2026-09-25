"""API router: route matching + dispatch.

Imports use top-level module names (`shared`, `routes`) to match the Lambda
flat package layout (see scripts/package_lambdas.py). The handler resolves the
Cognito sub -> saas-users -> tenant/role and passes the TenantContext here.
"""
from __future__ import annotations

import re
from collections.abc import Callable

from routes import accounts, costs
from shared.errors import not_found

_STATIC = {
    ("GET", "/health"): "health",
    ("GET", "/accounts"): "accounts.list",
    ("POST", "/accounts/link"): "accounts.link",
    ("GET", "/costs/daily"): "costs.daily",
    ("GET", "/costs/monthly"): "costs.monthly",
    ("GET", "/costs/breakdown"): "costs.breakdown",
}

_DYNAMIC = [
    (r"^/accounts/(?P<accountId>[^/]+)/validate$", "POST", "accounts.validate"),
    (r"^/accounts/(?P<accountId>[^/]+)$", "GET", "accounts.item"),
]

_HANDLERS: dict[str, Callable[..., dict]] = {
    "accounts.link": accounts.link,
    "accounts.list": accounts.list,
    "accounts.item": accounts.get,
    "accounts.validate": accounts.validate,
    "costs.daily": costs.daily,
    "costs.monthly": costs.monthly,
    "costs.breakdown": costs.breakdown,
}


def route(ctx, method: str, path: str, path_params: dict, query: dict, body: dict) -> dict:
    method = (method or "GET").upper()

    match = _STATIC.get((method, path))
    if match == "health":
        return {"status": "ok", "service": "cloud-cost-calculator-saas"}
    if match is not None and match in _HANDLERS:
        params = {}
        return _HANDLERS[match](ctx, params, query or {}, body or {})

    for pattern, dyn_method, name in _DYNAMIC:
        m = re.fullmatch(pattern, path)
        if m and dyn_method == method and name in _HANDLERS:
            params = dict(m.groupdict())
            params.update(path_params or {})
            return _HANDLERS[name](ctx, params, query or {}, body or {})

    raise not_found("Route not found", "ROUTE_NOT_FOUND")
