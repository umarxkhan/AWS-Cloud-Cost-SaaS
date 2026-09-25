output "backend_api_arn" {
  value = aws_lambda_function.backend_api.arn
}

output "backend_api_name" {
  value = aws_lambda_function.backend_api.function_name
}

output "api_gateway_url" {
  value = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${var.region}.amazonaws.com"
}

output "api_gateway_id" {
  value = aws_api_gateway_rest_api.api.id
}