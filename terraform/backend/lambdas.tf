# ---------------------------------------------------------------------------
# backend-api Lambda. Package assembled into backend/build/api/ by
# scripts/package_lambdas.py (sources + backend/shared/ + runtime deps).
# ---------------------------------------------------------------------------

data "archive_file" "api_pkg" {
  type        = "zip"
  source_dir  = "${path.module}/../../../backend/build/api"
  output_path = "${path.module}/../../../backend/build/api.zip"
  excludes    = ["__pycache__", "*.pyc"]
}

resource "aws_lambda_function" "backend_api" {
  function_name = "${var.name_prefix}backend-api"
  role          = aws_iam_role.backend_api.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.api_pkg.output_path
  source_code_hash = filebase64sha256(data.archive_file.api_pkg.output_path)

  environment {
    variables = {
      USERS_TABLE             = var.users_table
      TENANTS_TABLE           = var.tenants_table
      CUSTOMER_ACCOUNTS_TABLE = var.customer_accounts_table
      COST_DATA_TABLE         = var.cost_data_table
      WORKER_FUNCTION         = var.worker_arn
      COGNITO_USER_POOL_ID    = var.user_pool_id
      COGNITO_CLIENT_ID       = var.client_id
      ALLOWED_ORIGIN          = var.frontend_origin
    }
  }

  tags = var.tags
}