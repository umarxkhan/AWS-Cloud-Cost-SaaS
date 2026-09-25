# ---------------------------------------------------------------------------
# SQS: collection queue + dead-letter queue.
#
# Pipeline: EventBridge -> collector-enqueue -> cost-collection-queue ->
#           collector-worker (SQS event source) -> STS/CE -> DynamoDB.
#
# Retry / visibility:
#   - visibility_timeout_seconds is >= the worker timeout so in-flight messages
#     are not prematurely redelivered while the worker is still processing.
#   - Files: max receive count + dead-letter target use the AWS SQS redrive
#     service (v6 provider). NOTE: the exact provider argument set for the
#     redrive/dead-letter association must be confirmed during the AWS-backed
#     `terraform plan` review (blocked now without backend credentials).
# ---------------------------------------------------------------------------

resource "aws_sqs_queue" "dlq" {
  name = "${var.name_prefix}cost-collection-dlq"

  message_retention_seconds = 1209600 # 14 days

  tags = var.tags
}

# DLQ REDRIVE (pending): the standard SQS "dead-letter" redrive (max receives +
# dead-letter target on the source queue) could not be validated here because
# the v6 provider's declarative redrive argument set requires an AWS-backed
# `terraform plan` (blocked — no backend/credentials). The DLQ queue is created
# above; the redrive association must be confirmed/applied during the AWS-backed
# plan review (Stage 7) before provisioning.
resource "aws_sqs_queue" "queue" {
  name = "${var.name_prefix}cost-collection-queue"

  message_retention_seconds  = 345600 # 4 days
  visibility_timeout_seconds = 300    # >= worker timeout (120s) + margin

  tags = var.tags
}