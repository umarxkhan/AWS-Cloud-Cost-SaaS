# ---------------------------------------------------------------------------
# IAM for the collector pipeline.
# ONLY the worker role holds sts:AssumeRole (cross-account). The enqueue role
# only lists tenants/accounts and sends messages. No Cost Explorer permission
# on the SaaS side (CE lives on the customer-side role).
# ---------------------------------------------------------------------------

# --- collector-enqueue role ------------------------------------------------
resource "aws_iam_role" "enqueue" {
  name = "${var.name_prefix}collector-enqueue"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "enqueue_policy" {
  name = "${var.name_prefix}collector-enqueue"
  role = aws_iam_role.enqueue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:Query", "dynamodb:Scan"]
        Resource = [var.tenants_table_arn, var.customer_accounts_table_arn]
      },
      {
        Effect   = "Allow"
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.queue.arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "*"
      }
    ]
  })
}

# --- collector-worker role (ONLY STS holder) --------------------------------
resource "aws_iam_role" "worker" {
  name = "${var.name_prefix}collector-worker"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "worker_policy" {
  name = "${var.name_prefix}collector-worker"
  role = aws_iam_role.worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Every cross-account assume requires ExternalId at the customer role.
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan",
          "dynamodb:PutItem", "dynamodb:UpdateItem"
        ]
        Resource = [var.customer_accounts_table_arn, var.cost_data_table_arn, var.collection_jobs_table_arn]
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:GetQueueAttributes", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:ChangeMessageVisibility"]
        Resource = aws_sqs_queue.queue.arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "*"
      }
    ]
  })
}