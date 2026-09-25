"""Authentication / claim handling (skeleton).

The API Gateway Cognito authorizer validates the token at the edge, but the
backend must NOT rely on it alone: we re-read the claims from the event
gatewaypayload, extract `sub`, and resolve authorization from `saas-users`
(never from the Cognito group alone).
"""
from __future__ import annotations

from typing import Any


def extract_claims(event: dict[str, Any]) -> dict[str, Any] | None:
    # TODO(implementation stage): parse APIGW/CloudFront-style authorizer
    # context or validate the access token JWT to get `sub`.
    raise NotImplementedError("Implemented in stage 3")