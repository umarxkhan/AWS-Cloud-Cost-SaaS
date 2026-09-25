# ---------------------------------------------------------------------------
# GitHub Actions OIDC: replace long-lived AWS keys with an OIDC provider +
# scoped deploy roles for the SaaS control account.
#
# >>> DEPLOYMENT BLOCKERS (MUST be resolved before OIDC is activated): <<<
#   1. locals.org_repo below (and the thumbprint_list) are placeholders.
#   2. The exact repo/branch `sub` conditions must match the real
#      <org>/<repo> and the exact refs. NO wildcard repository trust is used:
#      the PR role is pinned to refs/pull/*, the deploy role to refs/heads/main.
#   3. The github-deploy role policy below is a scoped-down-at-apply placeholder
#      and MUST be narrowed to the state bucket + the resources the deploy
#      workflow needs before use.
# Do not activate OIDC until all three blockers above are replaced.
# ---------------------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    # DEL BLOCKER: set the REAL SHA1 thumbprint of GitHub's OIDC cert (exactly
    # 40 hex chars) before activation. This is a placeholder.
    "1111111111111111111111111111111111111111"
  ]
}

locals {
  # DEL BLOCKER: set to the real <org>/<repo> (exact, never a wildcard).
  org_repo = "my-org/my-repo"
}

# Read-only role for PR-time `terraform plan`.
resource "aws_iam_role" "github_plan" {
  name = "${var.name_prefix}github-plan"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${local.org_repo}:ref:refs/pull/*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_plan_policy" {
  name = "${var.name_prefix}github-plan"
  role = aws_iam_role.github_plan.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject", "s3:ListBucket",
        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"
      ]
      Resource = "arn:aws:s3:::terraform-state-placeholder" # TODO: scope to state bucket/key after bootstrap
    }]
  })
}

# Deploy role for `terraform apply` on main merge.
resource "aws_iam_role" "github_deploy" {
  name = "${var.name_prefix}github-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${local.org_repo}:ref:refs/heads/main"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy_policy" {
  name = "${var.name_prefix}github-deploy"
  role = aws_iam_role.github_deploy.id

  # DEL BLOCKER: this is a placeholder "*" only until OIDC is activated. Before
  # use it MUST be narrowed to the state bucket/key and the specific resources
  # Terraform + the frontend deploy need. NO "*" permissions in production.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}