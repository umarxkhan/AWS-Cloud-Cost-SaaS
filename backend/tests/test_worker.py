import json

import collect.worker as w
import pytest
from shared import db


def _fake_identity(account):
    class _S:
        def get_caller_identity(self):
            return {"Account": account}

    return _S()


def test_validate_marks_active_on_exact_match(seeded, monkeypatch):
    captured = {}

    def fake_assume(cfg):
        captured["cfg"] = cfg
        return {"AccessKeyId": "k", "SecretAccessKey": "s", "SessionToken": "t"}

    monkeypatch.setattr(w, "_assume", fake_assume)
    monkeypatch.setattr(w, "_assumed", lambda creds, svc: _fake_identity("111122223333"))

    result = w.run_validate(db.get_account("T_A", "111122223333"))
    assert result["valid"] is True
    assert result["status"] == "ACTIVE"
    assert captured["cfg"]["role_arn"] == "arn:aws:iam::111122223333:role/CloudCostCollector"
    # Persisted in DynamoDB
    assert db.get_account("T_A", "111122223333")["status"] == "ACTIVE"


def test_validate_refuses_active_on_account_mismatch(seeded, monkeypatch):
    monkeypatch.setattr(w, "_assume", lambda cfg: {"AccessKeyId": "k", "SecretAccessKey": "s", "SessionToken": "t"})
    monkeypatch.setattr(w, "_assumed", lambda creds, svc: _fake_identity("999999999999"))

    result = w.run_validate(db.get_account("T_A", "111122223333"))
    assert result["valid"] is False
    assert result["status"] == "FAILED"
    # MUST NOT be ACTIVE
    assert db.get_account("T_A", "111122223333")["status"] == "FAILED"


def test_worker_uses_db_config_not_client_supplied(seeded, monkeypatch):
    db.create_account("T_A", "222233334444")
    item = db.get_account("T_A", "222233334444")
    item["role_arn"] = "R1"
    item["external_id"] = "E1"
    db.customer_accounts_table().put_item(Item=item)

    captured = {}

    def fake_assume(cfg):
        captured["role"] = cfg["role_arn"]
        captured["ext"] = cfg["external_id"]
        return {"AccessKeyId": "k", "SecretAccessKey": "s", "SessionToken": "t"}

    monkeypatch.setattr(w, "_assume", fake_assume)
    monkeypatch.setattr(w, "_assumed", lambda creds, svc: _fake_identity("222233334444"))

    result = w.run_task({
        "tenant_id": "T_A",
        "account_id": "222233334444",
        "task": "validate",
        "role_arn": "arn:evil",
        "external_id": "evil",
    })
    assert result["valid"] is True
    # The worker assumed the DDB-stored role/external, never the client values.
    assert captured["role"] == "R1"
    assert captured["ext"] == "E1"


def test_run_task_missing_fields(seeded):
    r = w.run_task({"tenant_id": "T_A"})
    assert r["status"] == "ERROR"


def test_run_task_unknown_account_config(seeded):
    r = w.run_task({"tenant_id": "T_A", "account_id": "999900000000"})
    assert r["status"] == "ERROR"


def test_run_task_unknown_task(seeded, monkeypatch):
    monkeypatch.setattr(w, "_assume", lambda cfg: {"AccessKeyId": "k", "SecretAccessKey": "s", "SessionToken": "t"})
    monkeypatch.setattr(w, "_assumed", lambda creds, svc: _fake_identity("111122223333"))
    r = w.run_task({"tenant_id": "T_A", "account_id": "111122223333", "task": "bogus"})
    assert r["status"] == "ERROR"


def test_collect_uses_assumed_ce_credentials_and_daily_granularity(seeded, monkeypatch):
    monkeypatch.setattr(w, "_assume", lambda cfg: {"AccessKeyId": "k", "SecretAccessKey": "s", "SessionToken": "t"})

    captured = {}

    class _CE:
        def __init__(self):
            captured["service"] = "ce"

        def get_cost_and_usage(self, **kwargs):
            captured["kwargs"] = kwargs
            return {
                "ResultsByTime": [{
                    "Groups": [
                        {"Keys": ["AmazonEC2"], "Metrics": {"UnblendedCost": {"Amount": "6.0"}}},
                        {"Keys": ["AmazonS3"], "Metrics": {"UnblendedCost": {"Amount": "4.0"}}},
                    ]
                }]
            }

    monkeypatch.setattr(w, "_assumed", lambda creds, svc: _CE())

    cfg = db.get_account("T_A", "111122223333")
    result = w.run_collect(cfg, "2026-09-03")
    assert result["status"] == "OK"
    assert result["total_cost"] == 10.0
    assert captured["service"] == "ce"
    assert captured["kwargs"]["Granularity"] == "DAILY"
    assert captured["kwargs"]["TimePeriod"] == {"Start": "2026-09-03", "End": "2026-09-03"}
    # Written using the approved cost-data PK/SK
    rows = db.query_cost_data("T_A", "111122223333", "2026-09-03", "2026-09-03")
    assert rows and float(rows[0]["total_cost"]) == 10.0


# --- SQS failure handling (do not acknowledge failed messages) --------------
def test_sqs_handler_success_returns_200(seeded, monkeypatch):
    monkeypatch.setattr(w, "_assume", lambda cfg: {"AccessKeyId": "k", "SecretAccessKey": "s", "SessionToken": "t"})
    monkeypatch.setattr(w, "_assumed", lambda creds, svc: _fake_identity("111122223333"))

    event = {"Records": [{
        "messageId": "m-1",
        "body": json.dumps({"tenant_id": "T_A", "account_id": "111122223333", "task": "validate"}),
    }]}
    resp = w.handler(event)
    assert resp["statusCode"] == 200
    assert resp["body"].startswith("{")


def test_sqs_handler_raises_when_a_record_fails(seeded):
    # collect with a malformed date -> run_task ERROR -> handler must NOT return
    # 200 (which would acknowledge/delete the message).
    event = {"Records": [{
        "messageId": "m-1",
        "body": json.dumps({"tenant_id": "T_A", "account_id": "111122223333", "task": "collect", "date": "garbage"}),
    }]}
    with pytest.raises(RuntimeError):
        w.handler(event)


# --- idempotent cost-data writes ---------------------------------------------
def test_duplicate_cost_data_write_is_idempotent(seeded):
    db.put_cost_data("T_A", "111122223333", "2026-09-04", 5.0, {"S3": 5.0})
    # Duplicate redelivery tries to write a DIFFERENT value for the same day.
    db.put_cost_data("T_A", "111122223333", "2026-09-04", 999.0, {"RDS": 999.0})
    rows = db.query_cost_data("T_A", "111122223333", "2026-09-04", "2026-09-04")
    assert len(rows) == 1
    assert float(rows[0]["total_cost"]) == 5.0  # first successful record preserved


# --- collection date validation ----------------------------------------------
def test_collect_rejects_malformed_date(seeded):
    cfg = db.get_account("T_A", "111122223333")
    r = w.run_collect(cfg, "2026-9-3")  # not zero-padded / not strict YYYY-MM-DD
    assert r["status"] == "ERROR"


def test_collect_accepts_valid_date(seeded, monkeypatch):
    monkeypatch.setattr(w, "_assume", lambda cfg: {"AccessKeyId": "k", "SecretAccessKey": "s", "SessionToken": "t"})

    class _CE:
        def get_cost_and_usage(self, **kwargs):
            return {"ResultsByTime": [{"Groups": [
                {"Keys": ["AmazonS3"], "Metrics": {"UnblendedCost": {"Amount": "7.0"}}}
            ]}]}

    monkeypatch.setattr(w, "_assumed", lambda creds, svc: _CE())
    r = w.run_collect(db.get_account("T_A", "111122223333"), "2026-09-05")
    assert r["status"] == "OK"
    assert r["total_cost"] == 7.0
