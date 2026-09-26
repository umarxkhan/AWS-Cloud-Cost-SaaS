variable "region" {
  type        = string
  description = "AWS region for all SaaS control-account resources."
  default     = "eu-central-1"
}

variable "tf_environment" {
  type        = string
  description = "Terraform environment name (prod / staging / dev)."
  default     = "prod"
}

variable "environment_prefix" {
  type        = string
  description = "Prefix for all AWS resource names (e.g. saas-prod-)."
}

# Account-safety guard input. NEVER hardcode the real account id in source.
# Supplied per-environment via terraform.tfvars and/or GitHub Actions vars.
variable "aws_account_id" {
  type        = string
  description = "SaaS control AWS account id. Required for the allowed_account_ids guard."
}

variable "cognito_domain_prefix" {
  type        = string
  description = "Prefix for the Cognito Hosted UI domain."
  default     = "saas-cost-calculator"
}

variable "frontend_origin" {
  type        = string
  description = "CloudFront frontend origin used for Cognito OAuth callback and logout URLs."
  default     = ""
}

variable "collection_schedule" {
  type        = string
  description = "EventBridge schedule expression for the daily collector-enqueue trigger (once per day MVP)."
  default     = "cron(0 6 * * ? *)"
}