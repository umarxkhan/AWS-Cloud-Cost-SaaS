# Per-environment variable values for the SaaS control account.
region             = "eu-central-1"
tf_environment     = "prod"
environment_prefix = "saas-prod-"

# Account-safety guard: replace with the real SaaS AWS account id (provider `aws`
# refuses to run against any other account). Never commit the real value to
# source — supply it here locally or via GitHub Actions secrets/vars.
aws_account_id = "000000000000"

cognito_domain_prefix = "saas-cost-calculator"

# Populated after first deploy from `terraform output cloudfront_url`.
frontend_origin = ""

# Once per day (UTC 06:00) for MVP.
collection_schedule = "cron(0 6 * * ? *)"