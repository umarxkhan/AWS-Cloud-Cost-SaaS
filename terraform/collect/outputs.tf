output "worker_arn" {
  value = aws_lambda_function.worker.arn
}

output "worker_name" {
  value = aws_lambda_function.worker.function_name
}

output "enqueue_arn" {
  value = aws_lambda_function.enqueue.arn
}

output "collection_queue_url" {
  value = aws_sqs_queue.queue.url
}

output "collection_queue_arn" {
  value = aws_sqs_queue.queue.arn
}

output "collection_dlq_url" {
  value = aws_sqs_queue.dlq.url
}