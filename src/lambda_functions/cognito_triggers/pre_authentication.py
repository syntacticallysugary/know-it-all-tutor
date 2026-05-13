"""Pre-authentication Lambda trigger for Cognito User Pool
Blocks login for accounts that have not yet been approved by an admin.
"""

import logging
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_MESSAGES = {
    "pending": "Your account is awaiting admin approval. You will receive an email once approved.",
    "denied": "Your registration request was not approved.",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Pre-authentication trigger — enforces approval gate."""
    user_attributes = event.get("request", {}).get("userAttributes", {})
    email = user_attributes.get("email", event.get("userName", "unknown"))
    status = user_attributes.get("custom:status")

    if status in _MESSAGES:
        logger.info(f"Blocking login for {email}: status={status}")
        raise Exception(_MESSAGES[status])

    logger.info(f"Pre-authentication passed for {email} (status={status!r})")
    return event
