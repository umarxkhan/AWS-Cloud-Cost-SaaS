# ---------------------------------------------------------------------------
# Cloud Cost Calculator SaaS - root Terraform (SaaS control account only).
# Multi-tenant shared infrastructure. NO per-customer infrastructure.
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    # STATE-BUCKET BOOTSTRAP CONTRACT:
    # The bucket is a ONE-TIME manual bootstrap resource, created BEFORE this
    # configuration ever runs `terraform init` (Terraform cannot create the
    # backend it is already using). It is intentionally NOT defined anywhere in
    # this Terraform configuration. Name: "${environment_prefix}terraform-state-<aws_account_id>".
    # bucket / key / region are supplied via `terraform init -backend-config=...`.
    use_lockfile = true # modern S3-native locking (no DynamoDB lock table)
  }
}

provider "aws" {
  region = var.region
  # Account-safety: only operate within the intended SaaS control account.
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = local.tags
  }
}

# -- Modules ----------------------------------------------------------------

module "auth" {
  source          = "./auth"
  name_prefix     = local.prefix
  region          = local.region
  domain_prefix   = var.cognito_domain_prefix
  frontend_origin = var.frontend_origin
  tags            = local.tags
}

module "data" {
  source      = "./data"
  name_prefix = local.prefix
  region      = local.region
  account_id  = var.aws_account_id
  tags        = local.tags
}

module "collect" {
  source                      = "./collect"
  name_prefix                 = local.prefix
  region                      = local.region
  tags                        = local.tags
  collection_schedule         = var.collection_schedule
  users_table                 = module.data.users_table_name
  tenants_table               = module.data.tenants_table_name
  customer_accounts_table     = module.data.customer_accounts_table_name
  cost_data_table             = module.data.cost_data_table_name
  collection_jobs_table       = module.data.collection_jobs_table_name
  tenants_table_arn           = module.data.tenants_table_arn
  customer_accounts_table_arn = module.data.customer_accounts_table_arn
  cost_data_table_arn         = module.data.cost_data_table_arn
  collection_jobs_table_arn   = module.data.collection_jobs_table_arn
  users_table_arn             = module.data.users_table_arn
}

module "backend" {
  source                      = "./backend"
  name_prefix                 = local.prefix
  region                      = local.region
  tags                        = local.tags
  users_table                 = module.data.users_table_name
  tenants_table               = module.data.tenants_table_name
  customer_accounts_table     = module.data.customer_accounts_table_name
  cost_data_table             = module.data.cost_data_table_name
  users_table_arn             = module.data.users_table_arn
  tenants_table_arn           = module.data.tenants_table_arn
  customer_accounts_table_arn = module.data.customer_accounts_table_arn
  cost_data_table_arn         = module.data.cost_data_table_arn
  worker_arn                  = module.collect.worker_arn
  user_pool_id                = module.auth.user_pool_id
  user_pool_arn               = module.auth.user_pool_arn
  client_id                   = module.auth.client_id
}

module "oidc" {
  source      = "./oidc"
  name_prefix = local.prefix
  account_id  = var.aws_account_id
  region      = local.region
}
