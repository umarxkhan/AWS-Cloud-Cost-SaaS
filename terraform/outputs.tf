output "api_gateway_url" {
  value = module.backend.api_gateway_url
}

output "cloudfront_url" {
  value = "https://${module.data.cloudfront_domain}"
}

output "cognito_user_pool_id" {
  value = module.auth.user_pool_id
}

output "cognito_client_id" {
  value = module.auth.client_id
}

output "cognito_domain" {
  value = module.auth.domain
}

output "collection_queue_url" {
  value = module.collect.collection_queue_url
}

output "collection_dlq_url" {
  value = module.collect.collection_dlq_url
}

output "saas_state_bucket" {
  description = "Manually bootstrapped Terraform state bucket (NOT created by this config; globally-unique name incorporating the account id)."
  value       = "${var.environment_prefix}terraform-state-${var.aws_account_id}"
}