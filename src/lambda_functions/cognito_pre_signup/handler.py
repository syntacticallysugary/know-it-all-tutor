"""Cognito Pre-SignUp Trigger
Auto-confirms new users and sends an immediate notification to the admin.
The user's account is active in Cognito but blocked at login until approved.
"""

import json
import os

import boto3

ses_client = boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
SES_FROM_EMAIL = os.environ.get("SES_FROM_EMAIL", ADMIN_EMAIL)
APP_URL = os.environ.get("APP_URL", "")


def lambda_handler(event, context):
    """Pre-SignUp trigger — auto-confirms the user then emails the admin."""
    print(f"Pre-SignUp trigger: {json.dumps(event)}")

    event["response"]["autoConfirmUser"] = True
    event["response"]["autoVerifyEmail"] = True

    attrs = event.get("request", {}).get("userAttributes", {})
    email = attrs.get("email", "unknown")
    given = attrs.get("given_name", "")
    family = attrs.get("family_name", "")
    full_name = f"{given} {family}".strip() or "Not provided"

    if ADMIN_EMAIL and SES_FROM_EMAIL:
        try:
            ses_client.send_email(
                Source=SES_FROM_EMAIL,
                Destination={"ToAddresses": [ADMIN_EMAIL]},
                Message={
                    "Subject": {"Data": f"[Know-It-All Tutor] New registration: {email}"},
                    "Body": {
                        "Text": {
                            "Data": (
                                f"A new user has registered and is awaiting your approval.\n\n"
                                f"Email: {email}\n"
                                f"Name:  {full_name}\n\n"
                                f"The user cannot log in until you approve their account.\n\n"
                                f"Approve or deny at the admin panel:\n"
                                f"{APP_URL}/app/admin\n"
                            )
                        }
                    },
                },
            )
            print(f"Admin notification sent for: {email}")
        except Exception as exc:
            # Never block registration because of an email failure
            print(f"Warning: failed to send admin notification: {exc}")

    print(f"Auto-confirmed user: {email}")
    return event
