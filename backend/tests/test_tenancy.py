from shared.tenancy import resolve_tenant_context
from util import body, call


def test_active_user_resolved(seeded):
    ctx = resolve_tenant_context("admin_a")
    assert ctx is not None
    assert ctx.tenant_id == "T_A"
    assert ctx.role == "admin"
    assert ctx.is_active


def test_platform_admin_flag(seeded):
    ctx = resolve_tenant_context("p")
    assert ctx is not None and ctx.is_platform_admin


def test_missing_user_is_none(seeded):
    assert resolve_tenant_context("nobody") is None


def test_disabled_user_is_none(seeded):
    assert resolve_tenant_context("disabled_a") is None


def test_empty_or_none_sub_is_none(seeded):
    assert resolve_tenant_context(None) is None
    assert resolve_tenant_context("") is None


def test_api_401_when_unauthenticated(seeded):
    assert call("GET", "/accounts")["statusCode"] == 401


def test_api_401_for_unknown_subject(seeded):
    assert call("GET", "/accounts", sub="unknown")["statusCode"] == 401


def test_api_401_for_disabled_user(seeded):
    assert call("GET", "/accounts", sub="disabled_a")["statusCode"] == 401


def test_health_is_unauthenticated(seeded):
    resp = call("GET", "/health", sub=None)
    assert resp["statusCode"] == 200
    assert body(resp)["status"] == "ok"
