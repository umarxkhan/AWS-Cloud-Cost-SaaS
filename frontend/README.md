# Frontend (multi-tenant SaaS)

Authenticated SPA served from the private S3 bucket via CloudFront (OAC origin).

## MVP scope (per approved architecture)
- **Auth**: Cognito Hosted UI / Managed Login — OAuth 2.0 Authorization Code +
  **PKCE**. Public client. No direct password flows.
- **Account linking**: "Connect AWS Account" -> enter AWS Account ID -> SaaS
  generates the ExternalId server-side and returns the Role ARN + ExternalId +
  CloudFormation template -> customer creates the role -> "Validate".
- **Cost dashboard**: reuses Chart.js line-trend + doughnut logic from the
  existing single-tenant `dashboard/index.html` (kept as reference), but the
  data source becomes the authenticated API Gateway (bearer token) instead of a
  static `cost_data.json`.

## Notes
- `dashboard/` and `lambda/fetch_costs.py` from the original single-tenant
  project are intentionally retained as reference/fallback and will only be
  removed after the replacement frontend is implemented and verified.
- The `frontend/src/` tree is scaffolded in the "frontend rewrite" stage; no
  AWS provisioning occurs for the frontend until the implementation is approved.