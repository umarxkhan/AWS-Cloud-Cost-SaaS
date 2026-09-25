# ---------------------------------------------------------------------------
# SQS: collection queue + dead-letter queue.
#
# Pipeline: EventBridge -> collector-enqueue -> cost-collection-queue ->
#           collector-worker (SQS event source) -> STS/CE -> DynamoDB.
#
# Retry / visibility:
#   - visibility_timeout_seconds (300) is >= the worker timeout (120s) so
#     in-flight messages are not redelivered while the worker is still
#     processing.
#   - redrive_policy moves failed messages to the existing DLQ after
#     maxReceiveCount attempts (maxReceiveCount is an integer).
# ---------------------------------------------------------------------------

resource "aws_sqs_queue" "dlq" {
  name = "${var.name_prefix}cost-collection-dlq"

  message_retention_seconds = 1209600 # 14 days

  tags = var.tags
}

resource "aws_sqs_queue" "queue" {
  name = "${var.name_prefix}cost-collection-queue"

  message_retention_seconds  = 345600 # 4 days
  visibility_timeout_seconds = 300    # >= worker timeout (120s) + margin

  # Failed messages move to the existing DLQ after maxReceiveCount attempts.
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = var.tags
}