# ---------------------------------------------------------------------------
# EventBridge: once-per-day scheduled rule -> collector-enqueue Lambda.
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "daily" {
  name                = "${var.name_prefix}daily-enqueue"
  schedule_expression = var.collection_schedule
  description         = "Daily trigger for collector-enqueue"
}

resource "aws_cloudwatch_event_target" "enqueue" {
  rule      = aws_cloudwatch_event_rule.daily.name
  target_id = "collector-enqueue"
  arn       = aws_lambda_function.enqueue.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.enqueue.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily.arn
}