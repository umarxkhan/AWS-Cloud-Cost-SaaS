"""One-time local bootstrap for the first platform admin.

Run locally (not in CI) with bootstrap AWS credentials after Terraform has
provisioned Cognito + DynamoDB. Steps:
  1. Cognito adminCreateUser for the first platform admin (temporary
     invitation password; forced change on first login).
  2. Add the user to the `platform-admins` group (informational).
  3. Seed `saas-users` with role=platform_admin, tenant_id=platform, ACTIVE.
  4. Seed `saas-tenants` with the platform tenant.
  5. Revoke/remove the temporary bootstrap credentials afterward.

ExternalId is ALWAYS generated server-side by the backend during
`POST /accounts/link` (cryptographically secure), never by clients or scripts.
"""
from __future__ import annotations


def main() -> None:
    # TODO(bootstrap stage): implement using boto3 cognito-idp + dynamodb.
    raise NotImplementedError("Implemented in the bootstrap stage")


if __name__ == "__main__":
    main()