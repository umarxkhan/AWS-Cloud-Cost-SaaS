# ---------------------------------------------------------------------------
# GitHub Actions OIDC: replace long-lived AWS keys with an OIDC provider +
# minimially-scoped PLAN (read/plan) and DEPLOY (apply) roles for the SaaS
# control account.
#
# Trust is restricted to the exact repository + branch/ref (NO wildcard repo
# trust). The subject uses GitHub's classic OIDC `sub` format:
#     repo:<owner>/<repo>:ref:refs/heads/main        (deploy)
#     repo:<owner>/<repo>:ref:refs/pull/*            (plan, PR)
# PRE-ACTIVATION VERIFY: if this repository enables the GitHub
# Actions -> OIDC "immutable subject claim" option, the `sub` claim format
# changes and these conditions must be updated to match it before activation.
# Do not activate until confirmed.
# ---------------------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # thumbprint_list is intentionally omitted: for GitHub, AWS relies on its own
  # managed root-CA library for certificate validation, so no server-certificate
  # thumbprint is required or verified. The provider treats it as optional.
}

locals {
  # Exact repository (never a wildcard).
  org_repo = "umarxkhan/AWS-Cloud-Cost-SaaS"

  # Project state-bucket naming convention: saas-prod-terraform-state-<AWS_ACCOUNT_ID>.
  state_bucket      = "${var.name_prefix}terraform-state-${var.account_id}"
  state_bucket_arn  = "arn:aws:s3:::${local.state_bucket}"
  state_objects_arn = "arn:aws:s3:::${local.state_bucket}/*"

  frontend_bucket      = "${var.name_prefix}frontend-${var.account_id}"
  frontend_bucket_arn  = "arn:aws:s3:::${local.frontend_bucket}"
  frontend_objects_arn = "arn:aws:s3:::${local.frontend_bucket}/*"
}

# ---------------------------------------------------------------------------
# PLAN ROLE (terraform init + terraform plan on pull requests).
# - Terraform S3 state backend access (state file + use_lockfile lock file):
#     s3:ListBucket (bucket) + s3:Get/Delete/PutObject (state + lock file).
# - Read-only permissions to REFRESH every managed resource namespace so a
#   normal `terraform plan` (refresh enabled) can run once infrastructure
#   exists. NO write permissions are granted to the managed services.
# ---------------------------------------------------------------------------
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
    Statement = [
      # ---- Terraform S3 state backend (state file + lock file; use_lockfile).
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = [local.state_bucket_arn]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = [local.state_objects_arn]
      },
      # ---- S3: read-only refresh of the frontend bucket Terraform manages.
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucket*", "s3:GetObject"]
        Resource = [local.frontend_bucket_arn, local.frontend_objects_arn]
      },
      # ---- Cognito: read-only refresh (pool, client, domain).
      {
        Effect   = "Allow"
        Action   = ["cognito-idp:Get*", "cognito-idp:List*"]
        Resource = ["arn:aws:cognito-idp:${var.region}:*"]
      },
      # ---- DynamoDB: read-only refresh (table definitions).
      {
        Effect   = "Allow"
        Action   = ["dynamodb:DescribeTable", "dynamodb:DescribeContinuousBackups"]
        Resource = ["arn:aws:dynamodb:${var.region}:${var.account_id}:table/${var.name_prefix}*"]
      },
      # ---- CloudFront: read-only refresh (distribution + OAC).
      {
        Effect   = "Allow"
        Action   = ["cloudfront:Get*", "cloudfront:List*"]
        Resource = ["arn:aws:cloudfront:*"]
      },
      # ---- SQS: read-only refresh (queue + DLQ).
      {
        Effect   = "Allow"
        Action   = ["sqs:Get*", "sqs:List*"]
        Resource = ["arn:aws:sqs:${var.region}:${var.account_id}:${var.name_prefix}*"]
      },
      # ---- EventBridge / CloudWatch Events: read-only refresh (schedule rule).
      {
        Effect   = "Allow"
        Action   = ["events:Get*", "events:List*", "events:Describe*"]
        Resource = ["arn:aws:events:${var.region}:${var.account_id}:rule/${var.name_prefix}*"]
      },
      # ---- Lambda: read-only refresh (functions, function policies, event-source mappings).
      {
        Effect   = "Allow"
        Action   = ["lambda:Get*", "lambda:List*"]
        Resource = ["arn:aws:lambda:${var.region}:${var.account_id}:function/${var.name_prefix}*"]
      },
      # ---- API Gateway: read-only refresh (Terraform uses dynamic rest-api ids).
      {
        Effect   = "Allow"
        Action   = ["apigateway:GET"]
        Resource = ["arn:aws:apigateway:${var.region}:${var.account_id}:restapis/*"]
      },
      # ---- IAM: read-only refresh (roles, inline policies, OIDC provider).
      {
        Effect = "Allow"
        Action = ["iam:Get*", "iam:List*"]
        Resource = [
          "arn:aws:iam::role/${var.name_prefix}*",
          "arn:aws:iam::policy/${var.name_prefix}*",
          "arn:aws:iam::oidc-provider/token.actions.githubusercontent.com",
        ]
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# DEPLOY ROLE (terraform apply on the main branch).
# Narrowest practical scope for the resources actually defined in this
# repository, scoped by account/region/name-prefix/ARN. No Action="*",
# no Resource="*".
# ---------------------------------------------------------------------------
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
          "token.actions.githubusercontent.com:sub" = "repo:${local.org_repo}:ref:refs/heads/main"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy_policy" {
  name = "${var.name_prefix}github-deploy"
  role = aws_iam_role.github_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ---- S3: Terraform state backend + the frontend bucket Terraform creates.
      {
        Effect = "Allow"
        Action = ["s3:*"]
        Resource = [
          local.state_bucket_arn, local.state_objects_arn,
          local.frontend_bucket_arn, local.frontend_objects_arn,
        ]
      },
      # ---- DynamoDB: the five shared tables (saas-prod- prefix).
      {
        Effect   = "Allow"
        Action   = ["dynamodb:*"]
        Resource = ["arn:aws:dynamodb:${var.region}:${var.account_id}:table/${var.name_prefix}*"]
      },
      # ---- Lambda: backend-api, collector-enqueue, collector-worker + their
      #      function policies and the SQS event-source mapping.
      {
        Effect   = "Allow"
        Action   = ["lambda:*"]
        Resource = ["arn:aws:lambda:${var.region}:${var.account_id}:function/${var.name_prefix}*"]
      },
      {
        Effect   = "Allow"
        Action   = ["lambda:PassRole"]
        Resource = ["arn:aws:iam::role/${var.name_prefix}*"]
      },
      # ---- SQS: cost-collection-queue + cost-collection-dlq.
      {
        Effect   = "Allow"
        Action   = ["sqs:*"]
        Resource = ["arn:aws:sqs:${var.region}:${var.account_id}:${var.name_prefix}*"]
      },
      # ---- EventBridge / CloudWatch Events: the daily scheduled rule -> enqueue.
      {
        Effect   = "Allow"
        Action   = ["events:*"]
        Resource = ["arn:aws:events:${var.region}:${var.account_id}:rule/${var.name_prefix}*"]
      },
      # ---- API Gateway REST API + resources/methods/integrations/authorizer
      #      (Terraform uses dynamic resource ids; scoped to the API namespace).
      {
        Effect   = "Allow"
        Action   = ["apigateway:*"]
        Resource = ["arn:aws:apigateway:${var.region}:${var.account_id}:restapis/*"]
      },
      # ---- CloudFront distribution + OAC. The distribution ARN/domain is
      #      provider-assigned and unknown at policy-authoring time, so it is
      #      scoped to the cloudfront namespace (not a bare Resource="*").
      {
        Effect   = "Allow"
        Action   = ["cloudfront:*"]
        Resource = ["arn:aws:cloudfront:*"]
      },
      # ---- Cognito user pool, Hosted-UI domain, app client (pool id is
      #      generated; scoped to the region).
      {
        Effect   = "Allow"
        Action   = ["cognito-idp:*"]
        Resource = ["arn:aws:cognito-idp:${var.region}:*"]
      },
      # ---- IAM: roles, inline policies, and the OIDC provider that Terraform
      #      creates/manages (saas-prod- prefix + the exact OIDC provider ARN).
      {
        Effect = "Allow"
        Action = ["iam:*"]
        Resource = [
          "arn:aws:iam::role/${var.name_prefix}*",
          "arn:aws:iam::policy/${var.name_prefix}*",
          "arn:aws:iam::oidc-provider/token.actions.githubusercontent.com",
        ]
      }
    ]
  })
}