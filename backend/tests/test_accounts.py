from shared import worker_invoke
from util import body, call


def _patch_invoke(monkeypatch, returns):
    calls = []

    def fake(payload):
        calls.append(payload)
        return returns

    monkeypatch.setattr(worker_invoke, "invoke_worker", fake)
    return calls


def test_admin_link_creates_account(seeded):
    resp = call("POST", "/accounts/link", sub="admin_a", body={"aws_account_id": "999988887777"})
    assert resp["statusCode"] == 200
    payload = body(resp)
    assert payload["account_id"] == "999988887777"
    assert payload["role_arn"] == "arn:aws:iam::999988887777:role/CloudCostCollector"
    assert payload["external_id"]  # returned once, for onboarding


def test_link_is_idempotent_conflict_for_same_tenant(seeded):
    call("POST", "/accounts/link", sub="admin_a", body={"aws_account_id": "999988887777"})
    resp = call("POST", "/accounts/link", sub="admin_a", body={"aws_account_id": "999988887777"})
    assert resp["statusCode"] == 409


def test_link_conflict_when_linked_elsewhere(seeded):
    # T_B links the account first; T_A must then get a conflict.
    call("POST", "/accounts/link", sub="admin_b", body={"aws_account_id": "999988887777"})
    resp = call("POST", "/accounts/link", sub="admin_a", body={"aws_account_id": "999988887777"})
    assert resp["statusCode"] == 409


def test_public_list_and_get_do_not_leak_secrets(seeded):
    call("POST", "/accounts/link", sub="admin_a", body={"aws_account_id": "999988887777"})
    listed = body(call("GET", "/accounts", sub="admin_a"))
    for rec in listed["accounts"]:
        assert "external_id" not in rec
        assert "role_arn" not in rec
    got = body(call("GET", "/accounts/999988887777", sub="admin_a"))
    assert "external_id" not in got
    assert "role_arn" not in got


def test_validate_success_updates_and_returns(seeded, monkeypatch):
    _patch_invoke(monkeypatch, {"valid": True, "status": "ACTIVE", "found_account_id": "111122223333"})
    resp = call("POST", "/accounts/111122223333/validate", sub="admin_a")
    assert resp["statusCode"] == 200
    assert body(resp)["valid"] is True
    assert body(resp)["status"] == "ACTIVE"


def test_validate_invalid_account_id(seeded):
    resp = call("POST", "/accounts/123/validate", sub="admin_a")
    assert resp["statusCode"] == 400


def test_link_invalid_account_id(seeded):
    resp = call("POST", "/accounts/link", sub="admin_a", body={"aws_account_id": "abc"})
    assert resp["statusCode"] == 400


def test_missing_body_gives_bad_request(seeded):
    resp = call("POST", "/accounts/link", sub="admin_a", body={})
    assert resp["statusCode"] == 400
