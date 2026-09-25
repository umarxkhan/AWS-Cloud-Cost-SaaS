
from shared import worker_invoke
from util import body, call


def _patch_invoke(monkeypatch, returns, called=None):
    calls = []

    def fake(payload):
        calls.append(payload)
        if isinstance(returns, Exception):
            raise returns
        return returns

    monkeypatch.setattr(worker_invoke, "invoke_worker", fake)
    return calls


# --- cross-tenant rejection -------------------------------------------------
def test_tenant_a_cannot_read_tenant_b_account(seeded):
    resp = call("GET", "/accounts/444455556666", sub="admin_a")
    assert resp["statusCode"] == 404


def test_tenant_a_cannot_read_tenant_b_costs(seeded):
    resp = call("GET", "/costs/daily", sub="admin_a",
                query={"accountId": "444455556666", "start": "2026-09-01", "end": "2026-09-05"})
    assert resp["statusCode"] == 404


def test_tenant_a_cannot_validate_tenant_b_account(seeded, monkeypatch):
    calls = _patch_invoke(monkeypatch, {"valid": True, "status": "ACTIVE", "found_account_id": "444455556666"})
    resp = call("POST", "/accounts/444455556666/validate", sub="admin_a")
    assert resp["statusCode"] == 404
    assert calls == []  # worker must NOT be invoked for another tenant's account


# --- platform admin crosses tenants ------------------------------------------
def test_platform_admin_can_read_other_tenant_costs(seeded):
    resp = call("GET", "/costs/daily", sub="p",
                query={"accountId": "444455556666", "start": "2026-09-01", "end": "2026-09-05"})
    assert resp["statusCode"] == 200
    assert body(resp)["entries"][0]["total_cost"] == 99.0


def test_platform_admin_can_validate_other_tenant(seeded, monkeypatch):
    _patch_invoke(monkeypatch, {"valid": True, "status": "ACTIVE", "found_account_id": "444455556666"})
    resp = call("POST", "/accounts/444455556666/validate", sub="p")
    assert resp["statusCode"] == 200
    assert body(resp)["valid"] is True


# --- member read-only ---------------------------------------------------------
def test_member_cannot_link(seeded):
    resp = call("POST", "/accounts/link", sub="member_a", body={"aws_account_id": "999988887777"})
    assert resp["statusCode"] == 403


def test_member_cannot_validate(seeded, monkeypatch):
    calls = _patch_invoke(monkeypatch, {"valid": True, "status": "ACTIVE"})
    resp = call("POST", "/accounts/111122223333/validate", sub="member_a")
    assert resp["statusCode"] == 403
    assert calls == []


def test_member_can_read_own_tenant(seeded):
    assert call("GET", "/accounts", sub="member_a")["statusCode"] == 200
    assert call("GET", "/costs/daily", sub="member_a",
                query={"accountId": "111122223333", "start": "2026-09-01", "end": "2026-09-02"})["statusCode"] == 200


# --- client-supplied tenant_id / role never trusted ---------------------------
def test_client_supplied_tenant_id_is_ignored(seeded):
    evil = {"aws_account_id": "999988887777", "tenant_id": "T_B", "role_arn": "arn:aws:iam::999988887777:role/Evil"}
    resp = call("POST", "/accounts/link", sub="admin_a", body=evil)
    assert resp["statusCode"] == 200
    # The account must be recorded under the CALLER's tenant (T_A), never T_B.
    from shared import db
    assert db.get_account("T_A", "999988887777") is not None
    assert db.get_account("T_B", "999988887777") is None


def test_client_supplied_role_arn_is_ignored(seeded):
    resp = call("POST", "/accounts/link", sub="admin_a",
                body={"aws_account_id": "123123123123", "role_arn": "arn:aws:iam::1:role/Evil", "external_id": "evil"})
    assert resp["statusCode"] == 200
    payload = body(resp)
    assert payload["role_arn"] == "arn:aws:iam::123123123123:role/CloudCostCollector"
    assert payload["external_id"] != "evil"


def test_cross_tenant_validate_payload_uses_owner_tenant(seeded, monkeypatch):
    calls = _patch_invoke(monkeypatch, {"valid": True, "status": "ACTIVE", "found_account_id": "444455556666"})
    call("POST", "/accounts/444455556666/validate", sub="p")
    assert len(calls) == 1
    assert calls[0]["tenant_id"] == "T_B"
    assert calls[0]["account_id"] == "444455556666"
    assert set(calls[0]) == {"tenant_id", "account_id", "task"}  # no sensitive config in payload
