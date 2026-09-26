# ---------------------------------------------------------------------------
# API Gateway (REST, AWS_PROXY -> backend-api Lambda) + Cognito authorizer.
#
# Routes:
#   GET   /health                          unauthenticated
#   GET   /accounts                        COGNITO
#   POST  /accounts/link                   COGNITO
#   GET   /accounts/{accountId}            COGNITO
#   POST  /accounts/{accountId}/validate   COGNITO
#   GET   /costs/daily                     COGNITO
#   GET   /costs/monthly                   COGNITO
#   GET   /costs/breakdown                 COGNITO
#
# CACHING: REST API Gateway does not cache responses by default. The API is
# NOT behind CloudFront (CloudFront only serves static frontend files), so
# authenticated responses are never cached at the edge. backend-api must still
# send Cache-Control: no-store on authenticated routes (see backend/api).
# ---------------------------------------------------------------------------

locals {
  backend_invoke = "arn:aws:apigateway:${var.region}:lambda:path/2015-03-31/functions/${aws_lambda_function.backend_api.arn}/invocations"
}

resource "aws_api_gateway_rest_api" "api" {
  name        = "${var.name_prefix}api"
  description = "Cloud Cost Calculator SaaS REST API"
  tags        = var.tags
}

resource "aws_api_gateway_authorizer" "cognito" {
  name          = "cognito_authorizer"
  rest_api_id   = aws_api_gateway_rest_api.api.id
  type          = "COGNITO_USER_POOLS"
  provider_arns = [var.user_pool_arn]
}

# === GET /health (unauthenticated) ==========================================
resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "health"
}

resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "health" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.health.id
  http_method             = aws_api_gateway_method.health_get.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = local.backend_invoke
}

resource "aws_lambda_permission" "allow_api_health" {
  statement_id  = "AllowApiHealth"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = aws_api_gateway_rest_api.api.execution_arn
}

# === /accounts ==============================================================
resource "aws_api_gateway_resource" "accounts" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "accounts"
}

resource "aws_api_gateway_method" "accounts_list" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.accounts.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "accounts_list" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.accounts.id
  http_method             = aws_api_gateway_method.accounts_list.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = local.backend_invoke
}

resource "aws_lambda_permission" "allow_api_accounts_list" {
  statement_id  = "AllowApiAccountsList"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = aws_api_gateway_rest_api.api.execution_arn
}

# /accounts/link (POST)
resource "aws_api_gateway_resource" "accounts_link" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.accounts.id
  path_part   = "link"
}

resource "aws_api_gateway_method" "accounts_link" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.accounts_link.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "accounts_link" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.accounts_link.id
  http_method             = aws_api_gateway_method.accounts_link.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = local.backend_invoke
}

resource "aws_lambda_permission" "allow_api_accounts_link" {
  statement_id  = "AllowApiAccountsLink"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = aws_api_gateway_rest_api.api.execution_arn
}

# /accounts/{accountId} (GET)
resource "aws_api_gateway_resource" "account_item" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.accounts.id
  path_part   = "{accountId}"
}

resource "aws_api_gateway_method" "account_item" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.account_item.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "account_item" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.account_item.id
  http_method             = aws_api_gateway_method.account_item.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = local.backend_invoke
}

resource "aws_lambda_permission" "allow_api_account_item" {
  statement_id  = "AllowApiAccountItem"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = aws_api_gateway_rest_api.api.execution_arn
}

# /accounts/{accountId}/validate (POST)
resource "aws_api_gateway_resource" "account_validate" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.account_item.id
  path_part   = "validate"
}

resource "aws_api_gateway_method" "account_validate" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.account_validate.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "account_validate" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.account_validate.id
  http_method             = aws_api_gateway_method.account_validate.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = local.backend_invoke
}

resource "aws_lambda_permission" "allow_api_account_validate" {
  statement_id  = "AllowApiAccountValidate"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = aws_api_gateway_rest_api.api.execution_arn
}

# === /costs =================================================================
resource "aws_api_gateway_resource" "costs" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "costs"
}

resource "aws_api_gateway_resource" "costs_daily" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.costs.id
  path_part   = "daily"
}

resource "aws_api_gateway_resource" "costs_monthly" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.costs.id
  path_part   = "monthly"
}

resource "aws_api_gateway_resource" "costs_breakdown" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.costs.id
  path_part   = "breakdown"
}

resource "aws_api_gateway_method" "costs_daily" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.costs_daily.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_method" "costs_monthly" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.costs_monthly.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_method" "costs_breakdown" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.costs_breakdown.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "costs_daily" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.costs_daily.id
  http_method             = aws_api_gateway_method.costs_daily.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = local.backend_invoke
}

resource "aws_api_gateway_integration" "costs_monthly" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.costs_monthly.id
  http_method             = aws_api_gateway_method.costs_monthly.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = local.backend_invoke
}

resource "aws_api_gateway_integration" "costs_breakdown" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.costs_breakdown.id
  http_method             = aws_api_gateway_method.costs_breakdown.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = local.backend_invoke
}

resource "aws_lambda_permission" "allow_api_costs_daily" {
  statement_id  = "AllowApiCostsDaily"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = aws_api_gateway_rest_api.api.execution_arn
}

resource "aws_lambda_permission" "allow_api_costs_monthly" {
  statement_id  = "AllowApiCostsMonthly"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = aws_api_gateway_rest_api.api.execution_arn
}

resource "aws_lambda_permission" "allow_api_costs_breakdown" {
  statement_id  = "AllowApiCostsBreakdown"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = aws_api_gateway_rest_api.api.execution_arn
}