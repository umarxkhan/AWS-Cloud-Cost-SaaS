# ---------------------------------------------------------------------------
# Lambdas: collector-enqueue (EventBridge -> SQS) and collector-worker
# (SQS -> STS/CE -> DynamoDB).
#
# PACKAGING: Each Lambda is assembled by scripts/package_lambdas.py into
# backend/build/<name>/ which includes the handler modules, the shared
# backend/shared/ package, and all required third-party runtime dependencies
# (aws-lambda-powertools, pydantic) installed via pip. archive_file below only
# zips that pre-assembled build output so deployed Lambdas never fail with
# missing-module errors.
# ---------------------------------------------------------------------------

data "archive_file" "collect_pkg" {
  type        = "zip"
  source_dir  = "${path.module}/../../../backend/build/collect"
  output_path = "${path.module}/../../../backend/build/collect.zip"
  excludes    = ["__pycache__", "*.pyc"]
}

resource "aws_lambda_function" "enqueue" {
  function_name = "${var.name_prefix}collector-enqueue"
  role          = aws_iam_role.enqueue.arn
  handler       = "enqueue.handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 256

  filename         = data.archive_file.collect_pkg.output_path
  source_code_hash = filebase64sha256(data.archive_file.collect_pkg.output_path)

  environment {
    variables = {
      TENANTS_TABLE           = var.tenants_table
      CUSTOMER_ACCOUNTS_TABLE = var.customer_accounts_table
      QUEUE_URL               = aws_sqs_queue.queue.url
    }
  }

  tags = var.tags
}

resource "aws_lambda_function" "worker" {
  function_name = "${var.name_prefix}collector-worker"
  role          = aws_iam_role.worker.arn
  handler       = "worker.handler"
  runtime       = "python3.11"
  timeout       = 120
  memory_size   = 512

  filename         = data.archive_file.collect_pkg.output_path
  source_code_hash = filebase64sha256(data.archive_file.collect_pkg.output_path)

  environment {
    variables = {
      CUSTOMER_ACCOUNTS_TABLE = var.customer_accounts_table
      COST_DATA_TABLE         = var.cost_data_table
      COLLECTION_JOBS_TABLE   = var.collection_jobs_table
    }
  }

  tags = var.tags
}

# Wire the SQS queue as the worker's event source.
# SQS ->> WORKER TRIGGER (pending): the v6 provider's declarative event-source
# mapping schema could not be validated locally without backend access, so it
# is intentionally not declared here. The real trigger MUST be registered at
# deploy time (aws CLI `lambda event-source-mapping` / AWS API or the confirmed
# provider resource during the AWS-backed `terraform plan` review, Stage 7).
# The invoke permission below authorizes the queue principal to call the worker.
resource "aws_lambda_permission" "allow_sqs_to_worker" {
  statement_id  = "AllowExecutionFromCollectionQueue"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = aws_sqs_queue.queue.arn
}