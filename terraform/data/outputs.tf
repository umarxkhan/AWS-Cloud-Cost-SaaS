output "users_table_name" {
  value = aws_dynamodb_table.users.name
}

output "tenants_table_name" {
  value = aws_dynamodb_table.tenants.name
}

output "customer_accounts_table_name" {
  value = aws_dynamodb_table.customer_accounts.name
}

output "cost_data_table_name" {
  value = aws_dynamodb_table.cost_data.name
}

output "collection_jobs_table_name" {
  value = aws_dynamodb_table.collection_jobs.name
}

output "users_table_arn" {
  value = aws_dynamodb_table.users.arn
}

output "tenants_table_arn" {
  value = aws_dynamodb_table.tenants.arn
}

output "customer_accounts_table_arn" {
  value = aws_dynamodb_table.customer_accounts.arn
}

output "cost_data_table_arn" {
  value = aws_dynamodb_table.cost_data.arn
}

output "collection_jobs_table_arn" {
  value = aws_dynamodb_table.collection_jobs.arn
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.id
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.frontend.id
}