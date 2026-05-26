import json
import pytest
import sys
from unittest.mock import MagicMock, patch, ANY
from hypothesis import given, strategies as st, settings, HealthCheck

# Mock database and auth modules before they are imported by the handler/shared modules
sys.modules['psycopg'] = MagicMock()
sys.modules['psycopg_pool'] = MagicMock()
sys.modules['bcrypt'] = MagicMock()

from src.lambda_functions.domain_gen.handler import lambda_handler

@st.composite
def domain_gen_payload(draw):
    """Generate payloads for domain_gen job creation."""
    topic = draw(st.text(min_size=0, max_size=300))
    hints = draw(st.text(min_size=0, max_size=500))
    total_terms = draw(st.one_of(
        st.integers(min_value=-10, max_value=300),
        st.text(), # non-integer
        st.none()
    ))
    return {
        "topic": topic,
        "hints": hints,
        "total_terms": total_terms
    }

@pytest.fixture
def auth_event():
    """Basic event structure with auth claims."""
    return {
        "httpMethod": "POST",
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
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(payload=domain_gen_payload())
def test_create_job_properties(auth_event, payload):
    """Property-based test for job creation validation."""
    with patch("src.lambda_functions.domain_gen.handler.db") as mock_db:
        # Mock success response just in case validation passes
        mock_db.execute_query.return_value = [{
            "id": 1, "user_id": "test-sub-123", "topic": payload.get("topic"),
            "hints": payload.get("hints"), "total_terms": payload.get("total_terms"),
            "status": "pending", "created_at": "2024-05-24T12:00:00"
        }]

        auth_event["body"] = json.dumps(payload)
        
        response = lambda_handler(auth_event, None)
        
        status = response["statusCode"]
        
        # Validation Logic Invariants
        topic = (payload.get("topic") or "").strip()
        total_terms = payload.get("total_terms")
        
        if not topic:
            assert status == 400
        elif len(topic) > 200:
            assert status == 400
        elif not isinstance(total_terms, int) or not (1 <= total_terms <= 200):
            assert status == 400
        else:
            # If it passed validation, it MUST be 201 Created
            assert status == 201

@pytest.mark.unit
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(output_data=st.dictionaries(
    keys=st.text(),
    values=st.one_of(st.text(), st.integers(), st.lists(st.text()))
))
def test_approve_job_malformed_json_properties(auth_event, output_data):
    """Verify that approval handles random 'complete' output safely."""
    with patch("src.lambda_functions.domain_gen.handler.db") as mock_db:
        auth_event["path"] = "/domains/generate/1/approve"
        auth_event["pathParameters"] = {"id": "1", "action": "approve"}
        
        # Mock job retrieval with the randomized output_json
        mock_db.execute_query.side_effect = [
            [{
                "id": 1, "user_id": "test-sub-123", "status": "complete",
                "output_json": json.dumps(output_data)
            }],
            [[101]], # User ID resolution
            [[ "uuid" ]] # Domain insert
        ]

        # We don't expect a crash, regardless of how weird output_data is
        response = lambda_handler(auth_event, None)
        
        # If it's not a valid 'domains' list, domains_saved should be 0
        if "domains" not in output_data or not isinstance(output_data["domains"], list):
            body = json.loads(response["body"])
            if response["statusCode"] == 200:
                assert body.get("domains_saved", 0) == 0
