"""Post-confirmation Lambda trigger for Cognito User Pool
Creates the user record in the database and marks the account as pending approval.
"""

import logging
import os
import sys
from typing import Any

import boto3

sys.path.append("/opt/python")

from db_proxy_client import DBProxyClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

db_proxy = DBProxyClient(os.environ.get("DB_PROXY_FUNCTION_NAME"))
cognito_client = boto3.client("cognito-idp", region_name=os.environ.get("AWS_REGION", "us-east-1"))
USER_POOL_ID = os.environ.get("USER_POOL_ID", "")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Post-confirmation trigger — creates DB record and sets status to pending."""
    try:
        logger.info(f"Post-confirmation trigger for user: {event.get('userName')}")

        user_attributes = event.get("request", {}).get("userAttributes", {})
        username = event.get("userName")
        email = user_attributes.get("email", "")
        first_name = user_attributes.get("given_name")
        last_name = user_attributes.get("family_name")

        try:
            db_proxy.execute_query(
                """
                INSERT INTO users (cognito_sub, email, first_name, last_name, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (cognito_sub) DO NOTHING
                """,
                params=[username, email, first_name or None, last_name or None, True],
            )
            logger.info(f"Created user record for {email}")
        except Exception as db_error:
            logger.error(f"Failed to create user in database: {db_error}")

        if USER_POOL_ID and username:
            try:
                cognito_client.admin_update_user_attributes(
                    UserPoolId=USER_POOL_ID,
                    Username=username,
                    UserAttributes=[{"Name": "custom:status", "Value": "pending"}],
                )
                logger.info(f"Set custom:status = pending for {email}")
            except Exception as attr_error:
                logger.error(f"Failed to set custom:status: {attr_error}")

        return event

    except Exception as exc:
        logger.error(f"Post-confirmation trigger error: {exc}", exc_info=True)
        return event
