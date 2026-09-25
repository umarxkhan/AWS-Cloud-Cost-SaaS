# ---------------------------------------------------------------------------
# backend-api IAM: NO STS (explicit deny). Reads auth/tenant/account/cost
# tables, and may synchronously invoke the collector-worker for validation.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "backend_api" {
  name = "${var.name_prefix}backend-api"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "backend_api_policy" {
  name = "${var.name_prefix}backend-api"
  role = aws_iam_role.backend_api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem", "dynamodb:Query",
          "dynamodb:PutItem", "dynamodb:UpdateItem"
        ]
        Resource = [
          var.users_table_arn, var.tenants_table_arn,
          var.customer_accounts_table_arn, var.cost_data_table_arn
        ]
      },
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = var.worker_arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "*"
      },
      {
        # Defense-in-depth: backend-api must NEVER assume cross-account roles.
        Effect   = "Deny"
        Action   = "sts:AssumeRole"
        Resource = "*"
      }
    ]
  })
}