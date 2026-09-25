import jwtkit
from util import call, gw


def test_missing_token_returns_401(seeded):
    assert call("GET", "/accounts")["statusCode"] == 401


def test_valid_access_token_without_aud_accepted(seeded):
    # Cognito ACCESS tokens are bound by `client_id`; they carry NO aud claim.
    assert call("GET", "/accounts", sub="admin_a")["statusCode"] == 200


def test_invalid_signature_returns_401(seeded):
    resp = call("GET", "/accounts", token=jwtkit.mint_bad_signature("admin_a"))
    assert resp["statusCode"] == 401


def test_wrong_client_id_returns_401(seeded):
    resp = call("GET", "/accounts", token=jwtkit.mint_wrong_client_id("admin_a"))
    assert resp["statusCode"] == 401


def test_wrong_issuer_returns_401(seeded):
    resp = call("GET", "/accounts", token=jwtkit.mint_wrong_issuer("admin_a"))
    assert resp["statusCode"] == 401


def test_expired_token_returns_401(seeded):
    resp = call("GET", "/accounts", token=jwtkit.mint_expired("admin_a"))
    assert resp["statusCode"] == 401


def test_unknown_kid_returns_401(seeded):
    resp = call("GET", "/accounts", token=jwtkit.mint_unknown_kid("admin_a"))
    assert resp["statusCode"] == 401


def test_id_token_token_use_returns_401(seeded):
    resp = call("GET", "/accounts", token=jwtkit.mint_id_token("admin_a"))
    assert resp["statusCode"] == 401


def test_missing_sub_returns_401(seeded):
    resp = call("GET", "/accounts", token=jwtkit.mint_missing_sub())
    assert resp["statusCode"] == 401


def test_non_bearer_scheme_returns_401(seeded):
    from api.handler import lambda_handler

    event = gw("GET", "/accounts", sub="admin_a")
    event["headers"]["Authorization"] = "Basic abc="
    assert lambda_handler(event)["statusCode"] == 401


def test_valid_token_for_unknown_sub_returns_401(seeded):
    assert call("GET", "/accounts", sub="nobody")["statusCode"] == 401


def test_health_is_public_without_token(seeded):
    assert call("GET", "/health")["statusCode"] == 200


def test_valid_token_for_disabled_user_returns_401(seeded):
    # Valid access token but the saas-users record is disabled -> still rejected.
    assert call("GET", "/accounts", sub="disabled_a")["statusCode"] == 401
