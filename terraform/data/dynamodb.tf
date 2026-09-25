# ---------------------------------------------------------------------------
# DynamoDB: shared multi-tenant tables.
# All tables are partitioned by tenant/account. NO per-tenant tables.
#
# - billing_mode = PAY_PER_REQUEST on all tables (no capacity planning; write
#   volume is small — one daily cost record per (tenant, account)).
# - Encryption-at-rest is ALWAYS ON for DynamoDB by AWS; no extra config needed.
# - point_in_time_recovery enabled where historical data answer is valuable
#   (users, accounts, cost data) and jobs (cheap, protects the audit trail).
# ---------------------------------------------------------------------------

# saas-users — backend authorization source of truth (sub -> tenant/role).
resource "aws_dynamodb_table" "users" {
  name         = "${var.name_prefix}users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sub"

  attribute {
    name = "sub"
    type = "S"
  }
  attribute {
    name = "tenant_id"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "tenant_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }
  tags = var.tags
}

# saas-tenants
resource "aws_dynamodb_table" "tenants" {
  name         = "${var.name_prefix}tenants"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tenant_id"

  attribute {
    name = "tenant_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
  tags = var.tags
}

# customer-accounts — one tenant -> many AWS accounts (1-to-many).
# key: hash=tenant_id, range=account#<accountId>; GSI on account_id.
resource "aws_dynamodb_table" "customer_accounts" {
  name         = "${var.name_prefix}customer-accounts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tenant_id"
  range_key    = "account_id"

  attribute {
    name = "tenant_id"
    type = "S"
  }
  attribute {
    name = "account_id"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "account_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }
  tags = var.tags
}

# cost-data — daily, tenant-aware.
# key: hash=pk (tenant#<tenant_id>#account#<account_id>), range=sk (YYYY-MM-DD).
resource "aws_dynamodb_table" "cost_data" {
  name         = "${var.name_prefix}cost-data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }

  # Access pattern: Query(PK=tenant#T#account#A, SK BETWEEN start..end) for
  # daily charts; monthly totals are summed from daily records in the worker.
  # A tenant-wide GSI (on tenant_id) is intentionally NOT added for the MVP to
  # avoid write amplification — most tenants have a single account, and per-account
  # queries are cheap. Add one later only if multi-account tenants need a single
  # cross-account chart query.
  point_in_time_recovery {
    enabled = true
  }
  tags = var.tags
}

# collection-jobs — audit/status records for the collector pipeline.
resource "aws_dynamodb_table" "collection_jobs" {
  name         = "${var.name_prefix}collection-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tenant_id"
  range_key    = "job_id"

  attribute {
    name = "tenant_id"
    type = "S"
  }
  attribute {
    name = "job_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
  tags = var.tags
}