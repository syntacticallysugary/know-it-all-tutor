"""Local development Lambda authorizer for SAM.

Decodes the fake JWT from the Authorization header and returns a context
dict that mirrors what the real Cognito User Pool authorizer produces.
This lets all production handlers read requestContext.authorizer.claims
without any LOCAL_DEV guards.

NOT deployed to AWS — local dev only (wired via template.yaml).
"""

import base64
import json


def lambda_handler(event, context):
    token = event.get("authorizationToken", "")
    if token.startswith("Bearer "):
        token = token[7:]

    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("not a JWT")
        padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        raise Exception("Unauthorized")

    sub = payload.get("sub", "")
    email = payload.get("email", "")
    username = payload.get("cognito:username", email)

    return {
        "principalId": sub,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Allow",
                    "Resource": event.get("methodArn", "*"),
                }
            ],
        },
        # Mirrors the Cognito User Pool authorizer claims shape.
        # SAM local passes this dict through as requestContext.authorizer.claims.
        "context": {
            "claims": {
                "sub": sub,
                "email": email,
                "cognito:username": username,
                "email_verified": "true",
                "cognito:groups": "admin",
                "token_use": "id",
            }
        },
    }
