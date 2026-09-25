# ---------------------------------------------------------------------------
# Auth: Cognito User Pool + Hosted UI + OAuth Authorization-Code + PKCE.
# Public client (generate_secret=false) => PKCE is enforced.
# NO ALLOW_USER_PASSWORD_AUTH / direct password flows in MVP.
# ---------------------------------------------------------------------------

resource "aws_cognito_user_pool" "pool" {
  name = "${var.name_prefix}user-pool"

  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = true
  }

  # Normal local-user passwords do NOT auto-expire in Cognito. Only
  # admin-created temporary invitation passwords expire (temporary config).

  schema {
    name                = "email"
    attribute_data_type = "String"
    mutable             = true
    required            = true
  }

  # Tenant linkage attribute (server-assigned; authorization source is saas-users).
  schema {
    name                = "tenant_id"
    attribute_data_type = "String"
    mutable             = true
    required            = false
  }

  # Informational `platform-admins` group: the v6 provider does not manage
  # Cognito groups, so this optional group is created OUT-OF-BAND via the
  # Cognito API/console (bootstrap). It is NOT a security control — backend
  # authorization uses `saas-users` (role=platform_admin / tenant_id=platform).

  tags = var.tags
}

resource "aws_cognito_user_pool_domain" "domain" {
  domain       = "${var.domain_prefix}-${replace(var.region, "-", "")}"
  user_pool_id = aws_cognito_user_pool.pool.id
}

resource "aws_cognito_user_pool_client" "client" {
  name            = "${var.name_prefix}web-client"
  user_pool_id    = aws_cognito_user_pool.pool.id
  generate_secret = false # public client -> PKCE required for auth-code flow

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  allowed_oauth_flows_user_pool_client = true
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH"]
  supported_identity_providers         = ["COGNITO"]

  # DEL BLOCKER (before activation): set callback/logout URLs to the real
  # CloudFront origin (https://<distribution>.cloudfront.net) obtained from
  # `terraform output cloudfront_url` after the first apply. localhost URLs are
  # for local development only and must not remain for production.
  callback_urls = ["http://localhost:3000/callback", "https://example-placeholder.auth"]
  logout_urls   = ["http://localhost:3000", "http://localhost:3000/callback"]
}