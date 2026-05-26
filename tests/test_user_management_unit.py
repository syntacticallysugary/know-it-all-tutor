import json
import pytest
from unittest.mock import MagicMock, patch, ANY
from src.lambda_functions.user_management.handler import lambda_handler

@pytest.fixture
def admin_event():
    """Event from a user in the admin group."""
    return {
        "httpMethod": "GET",
        "path": "/admin/users/pending",
        "requestContext": {
            "authorizer": {
                "claims": {
                    "cognito:groups": "admin"
                }
            }
        }
    }

@pytest.fixture
def non_admin_event():
    """Event from a user NOT in the admin group."""
    return {
        "httpMethod": "GET",
        "path": "/admin/users/pending",
        "requestContext": {
            "authorizer": {
                "claims": {
                    "cognito:groups": "user"
                }
            }
        }
    }

@pytest.mark.unit
def test_require_admin_enforcement(non_admin_event):
    """Verify that non-admin users are blocked with 403."""
    response = lambda_handler(non_admin_event, None)
    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert "Admin access required" in body["error"]

@pytest.mark.unit
def test_handle_list_pending_success(admin_event, mocker):
    """Verify listing pending users with mock pagination."""
    mock_cognito = mocker.patch("src.lambda_functions.user_management.handler.cognito_client")
    
    # Mock paginator
    mock_paginator = MagicMock()
    mock_cognito.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [
        {
            "Users": [
                {
                    "Username": "user1",
                    "UserCreateDate": MagicMock(isoformat=lambda: "2024-05-24T10:00:00"),
                    "Attributes": [
                        {"Name": "email", "Value": "user1@example.com"},
                        {"Name": "custom:status", "Value": "pending"}
                    ]
                },
                {
                    "Username": "user2",
                    "UserCreateDate": MagicMock(isoformat=lambda: "2024-05-24T11:00:00"),
                    "Attributes": [
                        {"Name": "email", "Value": "user2@example.com"},
                        {"Name": "custom:status", "Value": "approved"} # Should be filtered out
                    ]
                }
            ]
        }
    ]

    response = lambda_handler(admin_event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body["users"]) == 1
    assert body["users"][0]["username"] == "user1"
    assert body["users"][0]["email"] == "user1@example.com"

@pytest.mark.unit
def test_handle_approve_success(admin_event, mocker):
    """Verify user approval updates Cognito and sends SES email."""
    # Mock both clients and the module-level constant
    mock_cognito = mocker.patch("src.lambda_functions.user_management.handler.cognito_client")
    mock_ses = mocker.patch("src.lambda_functions.user_management.handler.ses_client")
    mocker.patch("src.lambda_functions.user_management.handler.SES_FROM_EMAIL", "admin@example.com")
    
    admin_event["httpMethod"] = "POST"
    admin_event["path"] = "/admin/users/approve"
    admin_event["pathParameters"] = {"username": "test_user"}
    
    # Mock admin_get_user to provide email
    mock_cognito.admin_get_user.return_value = {
        "UserAttributes": [{"Name": "email", "Value": "test@example.com"}]
    }

    response = lambda_handler(admin_event, None)
    
    assert response["statusCode"] == 200
    # Check Cognito Update
    mock_cognito.admin_update_user_attributes.assert_called_once_with(
        UserPoolId=ANY,
        Username="test_user",
        UserAttributes=[{"Name": "custom:status", "Value": "approved"}]
    )
    # Check SES Email
    mock_ses.send_email.assert_called_once()
    args, kwargs = mock_ses.send_email.call_args
    assert "approved" in kwargs["Message"]["Subject"]["Data"].lower()
    assert "test@example.com" in kwargs["Destination"]["ToAddresses"]

@pytest.mark.unit
def test_handle_deny_with_reason(admin_event, mocker):
    """Verify user denial updates Cognito and sends email with reason."""
    mock_cognito = mocker.patch("src.lambda_functions.user_management.handler.cognito_client")
    mock_ses = mocker.patch("src.lambda_functions.user_management.handler.ses_client")
    mocker.patch("src.lambda_functions.user_management.handler.SES_FROM_EMAIL", "admin@example.com")
    
    admin_event["httpMethod"] = "POST"
    admin_event["path"] = "/admin/users/deny"
    admin_event["pathParameters"] = {"username": "test_user"}
    admin_event["body"] = json.dumps({"reason": "Incomplete profile"})
    
    mock_cognito.admin_get_user.return_value = {
        "UserAttributes": [{"Name": "email", "Value": "test@example.com"}]
    }

    response = lambda_handler(admin_event, None)
    
    assert response["statusCode"] == 200
    mock_cognito.admin_update_user_attributes.assert_called_with(
        UserPoolId=ANY,
        Username="test_user",
        UserAttributes=[{"Name": "custom:status", "Value": "denied"}]
    )
    
    # Verify reason is in email body
    assert mock_ses.send_email.called
    args, kwargs = mock_ses.send_email.call_args
    assert "Incomplete profile" in kwargs["Message"]["Body"]["Text"]["Data"]

@pytest.mark.unit
def test_cognito_error_handling(admin_event, mocker):
    """Verify that Cognito service errors are handled gracefully."""
    mock_cognito = mocker.patch("src.lambda_functions.user_management.handler.cognito_client")
    from botocore.exceptions import ClientError
    
    admin_event["httpMethod"] = "POST"
    admin_event["path"] = "/admin/users/approve"
    admin_event["pathParameters"] = {"username": "test_user"}
    
    # Simulate a ClientError
    mock_cognito.admin_get_user.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "User not found"}},
        "admin_get_user"
    )

    response = lambda_handler(admin_event, None)
    
    # response_utils.handle_error returns 404 if 'not found' is in message
    assert response["statusCode"] in [400, 404, 500]
    body = json.loads(response["body"])
    assert "error" in body["error"]["message"].lower()
