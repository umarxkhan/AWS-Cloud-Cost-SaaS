from util import body, call


def test_daily_own_tenant(seeded):
    resp = call("GET", "/costs/daily", sub="admin_a",
                query={"accountId": "111122223333", "start": "2026-09-01", "end": "2026-09-05"})
    assert resp["statusCode"] == 200
    entries = body(resp)["entries"]
    assert [e["date"] for e in entries] == ["2026-09-01", "2026-09-02"]


def test_daily_cross_tenant_rejected(seeded):
    resp = call("GET", "/costs/daily", sub="admin_a",
                query={"accountId": "444455556666", "start": "2026-09-01", "end": "2026-09-05"})
    assert resp["statusCode"] == 404


def test_monthly_aggregates_daily_records(seeded):
    resp = call("GET", "/costs/monthly", sub="member_a",
                query={"accountId": "111122223333", "month": "2026-09"})
    assert resp["statusCode"] == 200
    assert body(resp)["total_cost"] == 30.0
    assert body(resp)["services"]["EC2"] == 18.0
    assert body(resp)["days"] == 2


def test_breakdown_own_tenant(seeded):
    resp = call("GET", "/costs/breakdown", sub="admin_a",
                query={"accountId": "111122223333", "date": "2026-09-02"})
    assert resp["statusCode"] == 200
    assert body(resp)["total_cost"] == 20.0
    assert body(resp)["services"]["S3"] == 8.0


def test_breakdown_cross_tenant_rejected(seeded):
    resp = call("GET", "/costs/breakdown", sub="admin_a",
                query={"accountId": "444455556666", "date": "2026-09-01"})
    assert resp["statusCode"] == 404


def test_missing_date_params_rejected(seeded):
    assert call("GET", "/costs/daily", sub="admin_a", query={"accountId": "111122223333"})["statusCode"] == 400


def test_start_after_end_rejected(seeded):
    resp = call("GET", "/costs/daily", sub="admin_a",
                query={"accountId": "111122223333", "start": "2026-09-09", "end": "2026-09-01"})
    assert resp["statusCode"] == 400


def test_oversized_range_rejected(seeded):
    resp = call("GET", "/costs/daily", sub="admin_a",
                query={"accountId": "111122223333", "start": "2026-01-01", "end": "2026-06-01"})
    assert resp["statusCode"] == 400


def test_invalid_month_rejected(seeded):
    resp = call("GET", "/costs/monthly", sub="admin_a",
                query={"accountId": "111122223333", "month": "2026-13"})
    assert resp["statusCode"] == 400


def test_tenant_a_cannot_read_tenant_b_cost_totals(seeded):
    resp = call("GET", "/costs/monthly", sub="admin_a",
                query={"accountId": "444455556666", "month": "2026-09"})
    assert resp["statusCode"] == 404
