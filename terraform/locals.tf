# Reusable local values shared across root provider settings.
locals {
  prefix = var.environment_prefix
  region = var.region

  tags = {
    Project     = "CloudCostCalculatorSaaS"
    Environment = var.tf_environment
    ManagedBy   = "Terraform"
  }
}