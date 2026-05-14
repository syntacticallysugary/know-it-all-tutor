"""Admin user management Lambda
Handles listing, approving, and denying pending user registrations.
All routes require the caller to be in the Cognito 'admin' group.
"""

import json
import logging
import os
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError

sys.path.append("/opt/python")

from response_utils import create_response, handle_error

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito_client = boto3.client("cognito-idp", region_name=os.environ.get("AWS_REGION", "us-east-1"))
ses_client = boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))

USER_POOL_ID = os.environ.get("USER_POOL_ID", "")
SES_FROM_EMAIL = os.environ.get("SES_FROM_EMAIL", "")
APP_URL = os.environ.get("APP_URL", "")


def _require_admin(event: dict[str, Any]) -> bool:
    """Returns True if the caller is in the admin Cognito group."""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups_str = claims.get("cognito:groups", "")
    groups = groups_str.split(",") if groups_str else []
    return "admin" in groups


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route dispatcher for admin user management endpoints."""
    try:
        if not _require_admin(event):
            return create_response(403, {"error": "Admin access required"})

        method = event.get("httpMethod", "")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}

        if method == "GET" and path.endswith("/pending"):
            return handle_list_pending()

        username = path_params.get("username")
        if not username:
            return create_response(400, {"error": "Missing username path parameter"})

        if method == "POST" and path.endswith("/approve"):
            return handle_approve(username)
        if method == "POST" and path.endswith("/deny"):
            body = json.loads(event.get("body") or "{}")
            return handle_deny(username, reason=body.get("reason", ""))

        return create_response(404, {"error": "Endpoint not found"})

    except Exception as exc:
        return handle_error(exc)


def handle_list_pending() -> dict[str, Any]:
    """Return all users whose custom:status is 'pending'."""
    try:
        users = []
        paginator = cognito_client.get_paginator("list_users")
        for page in paginator.paginate(UserPoolId=USER_POOL_ID):
            for user in page["Users"]:
                attrs = {a["Name"]: a["Value"] for a in user["UserAttributes"]}
                if attrs.get("custom:status") != "pending":
                    continue
                users.append(
                    {
                        "username": user["Username"],
                        "email": attrs.get("email", ""),
                        "given_name": attrs.get("given_name", ""),
                        "family_name": attrs.get("family_name", ""),
                        "created_at": user["UserCreateDate"].isoformat(),
                    }
                )
        return create_response(200, {"users": users})
    except ClientError as exc:
        return handle_error(exc)


def handle_approve(username: str) -> dict[str, Any]:
    """Set custom:status = approved and notify the user."""
    try:
        user = cognito_client.admin_get_user(UserPoolId=USER_POOL_ID, Username=username)
        attrs = {a["Name"]: a["Value"] for a in user["UserAttributes"]}
        email = attrs.get("email", "")

        cognito_client.admin_update_user_attributes(
            UserPoolId=USER_POOL_ID,
            Username=username,
            UserAttributes=[{"Name": "custom:status", "Value": "approved"}],
        )
        logger.info(f"Approved user: {email}")

        _send_decision_email(email, approved=True)
        return create_response(200, {"message": f"Approved {email}"})
    except ClientError as exc:
        return handle_error(exc)


def handle_deny(username: str, reason: str = "") -> dict[str, Any]:
    """Set custom:status = denied and notify the user."""
    try:
        user = cognito_client.admin_get_user(UserPoolId=USER_POOL_ID, Username=username)
        attrs = {a["Name"]: a["Value"] for a in user["UserAttributes"]}
        email = attrs.get("email", "")

        cognito_client.admin_update_user_attributes(
            UserPoolId=USER_POOL_ID,
            Username=username,
            UserAttributes=[{"Name": "custom:status", "Value": "denied"}],
        )
        logger.info(f"Denied user: {email}")

        _send_decision_email(email, approved=False, reason=reason)
        return create_response(200, {"message": f"Denied {email}"})
    except ClientError as exc:
        return handle_error(exc)


def _send_decision_email(email: str, approved: bool, reason: str = "") -> None:
    if not SES_FROM_EMAIL or not email:
        return
    if approved:
        subject = "Your Know-It-All Tutor account has been approved"
        body = (
            "Great news — your account has been approved!\n\n"
            f"You can now log in at: {APP_URL}\n\n"
            "Welcome aboard."
        )
    else:
        subject = "Know-It-All Tutor — registration update"
        body = "Thank you for your interest in Know-It-All Tutor.\n\n"
        body += "After review, your registration request was not approved."
        if reason:
            body += f"\n\nReason: {reason}"
    try:
        ses_client.send_email(
            Source=SES_FROM_EMAIL,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )
    except Exception as exc:
        logger.warning(f"Failed to send decision email to {email}: {exc}")
