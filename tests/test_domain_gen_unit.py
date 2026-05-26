import json
import pytest
import sys
from unittest.mock import MagicMock, patch, ANY

# Mock database and auth modules before they are imported by the handler/shared modules
sys.modules['psycopg'] = MagicMock()
sys.modules['psycopg_pool'] = MagicMock()
sys.modules['bcrypt'] = MagicMock()

from src.lambda_functions.domain_gen.handler import lambda_handler

@pytest.fixture
def auth_event():
    """Event from an authenticated user."""
    return {
        "httpMethod": "GET",
        "path": "/domains/generate",
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "test-sub-123",
                    "cognito:groups": "user"
                }
            }
        }
    }

@pytest.mark.unit
def test_create_job_success(auth_event, mocker):
    """Verify job creation submits to DB Proxy."""
    mock_db = mocker.patch("src.lambda_functions.domain_gen.handler.db")
    
    auth_event["httpMethod"] = "POST"
    auth_event["body"] = json.dumps({
        "topic": "Quantum Mechanics",
        "hints": "Beginner level",
        "total_terms": 20
    })
    
    # Mock DB response
    mock_db.execute_query.return_value = [{
        "id": 1,
        "user_id": "test-sub-123",
        "topic": "Quantum Mechanics",
        "hints": "Beginner level",
        "total_terms": 20,
        "status": "pending",
        "created_at": "2024-05-24T12:00:00",
        "updated_at": "2024-05-24T12:00:00"
    }]

    response = lambda_handler(auth_event, None)
    
    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["topic"] == "Quantum Mechanics"
    assert body["status"] == "pending"
    
    # Verify DB query
    args, kwargs = mock_db.execute_query.call_args
    assert "INSERT INTO domain_gen_jobs" in args[0]
    assert "Quantum Mechanics" in kwargs["params"]

@pytest.mark.unit
def test_create_job_invalid_input(auth_event, mocker):
    """Verify validation for job creation."""
    auth_event["httpMethod"] = "POST"
    
    # Missing topic
    auth_event["body"] = json.dumps({"total_terms": 20})
    response = lambda_handler(auth_event, None)
    assert response["statusCode"] == 400
    assert "topic is required" in json.loads(response["body"])["error"]["message"]
    
    # Out of range total_terms
    auth_event["body"] = json.dumps({"topic": "Math", "total_terms": 500})
    response = lambda_handler(auth_event, None)
    assert response["statusCode"] == 400
    assert "between 1 and 200" in json.loads(response["body"])["error"]["message"]

@pytest.mark.unit
def test_approve_job_success(auth_event, mocker):
    """Verify job approval saves terms to tree_nodes."""
    mock_db = mocker.patch("src.lambda_functions.domain_gen.handler.db")
    
    auth_event["httpMethod"] = "POST"
    auth_event["path"] = "/domains/generate/1/approve"
    auth_event["pathParameters"] = {"id": "1", "action": "approve"}
    
    # 1. Mock job retrieval
    mock_db.execute_query.side_effect = [
        # First call: SELECT job
        [{
            "id": 1, "user_id": "test-sub-123", "status": "complete",
            "output_json": json.dumps({
                "domains": [{
                    "data": {"name": "Quantum Basics"},
                    "terms": [
                        {"data": {"term": "Qubit"}, "metadata": {"difficulty": "easy"}},
                        {"data": {"term": "Superposition"}, "metadata": {"difficulty": "hard"}}
                    ]
                }]
            })
        }],
        # Second call: Resolve user id
        [[101]],
        # Third call: INSERT domain
        [[ "new-domain-uuid" ]],
        # Fourth call: INSERT term 1 (no return_dict used in handler for terms)
        True,
        # Fifth call: INSERT term 2
        True,
        # Sixth call: UPDATE job status
        True
    ]

    response = lambda_handler(auth_event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["domains_saved"] == 1
    assert body["terms_saved"] == 2
    
    # Verify status update
    last_call = mock_db.execute_query.call_args_list[-1]
    assert "UPDATE domain_gen_jobs SET status = 'approved'" in last_call[0][0]

@pytest.mark.unit
def test_approve_job_not_found(auth_event, mocker):
    """Verify handling of non-existent job approval."""
    mock_db = mocker.patch("src.lambda_functions.domain_gen.handler.db")
    mock_db.execute_query.return_value = [] # No job found
    
    auth_event["httpMethod"] = "POST"
    auth_event["path"] = "/domains/generate/999/approve"
    auth_event["pathParameters"] = {"id": "999"}
    
    response = lambda_handler(auth_event, None)
    assert response["statusCode"] == 404
