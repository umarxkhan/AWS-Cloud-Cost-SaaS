# Fail-closed account-safety guard.
# - provider.aws.allowed_account_ids (in main.tf) rejects any other account.
# - This check additionally verifies the actual caller identity matches the
#   expected SaaS account before any apply proceeds.
data "aws_caller_identity" "current" {}

check "saas_account_matches" {
  assert {
    condition     = data.aws_caller_identity.current.account_id == var.aws_account_id
    error_message = "Terraform is running against an unexpected AWS account (expected ${var.aws_account_id}). Aborting."
  }
}