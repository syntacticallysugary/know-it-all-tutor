"""
Unit tests for response_utils module
Tests HTTP response formatting and error handling
"""
import pytest
import json
from unittest.mock import patch
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.response_utils import (
    create_response,
    create_success_response,
    create_created_response,
    create_error_response,
    create_validation_error_response,
    create_unauthorized_response,
    create_forbidden_response,
    create_not_found_response,
    create_internal_error_response,
    handle_error,
    parse_request_body,
    get_path_parameters,
    get_query_parameters,
    init_request,
)


@pytest.mark.unit
class TestCreateResponse:
    """Test basic response creation"""
    
    def test_create_response_basic(self):
        """Test creating basic response — default origin is the first entry in ALLOWED_ORIGINS."""
        response = create_response(200, {'message': 'success'})

        assert response['statusCode'] == 200
        assert 'headers' in response
        assert 'body' in response
        assert response['headers']['Content-Type'] == 'application/json'
        assert response['headers']['Access-Control-Allow-Origin'] == 'https://d3awlgby2429wc.cloudfront.net'

    def test_create_response_reflects_allowed_origin(self):
        """Test that init_request causes the response to reflect the request origin when allowed."""
        init_request({'headers': {'origin': 'https://tutor.syntacticallysugary.dev'}})
        with patch.dict(os.environ, {'ALLOWED_ORIGINS': 'https://d3awlgby2429wc.cloudfront.net,https://tutor.syntacticallysugary.dev'}):
            response = create_response(200, {'message': 'ok'})
        assert response['headers']['Access-Control-Allow-Origin'] == 'https://tutor.syntacticallysugary.dev'
        # Reset context for other tests
        init_request({})

    def test_create_response_rejects_unknown_origin(self):
        """Test that an unrecognised origin falls back to the first allowed origin."""
        init_request({'headers': {'origin': 'https://evil.example.com'}})
        with patch.dict(os.environ, {'ALLOWED_ORIGINS': 'https://d3awlgby2429wc.cloudfront.net'}):
            response = create_response(200, {'message': 'ok'})
        assert response['headers']['Access-Control-Allow-Origin'] == 'https://d3awlgby2429wc.cloudfront.net'
        init_request({})
    
    def test_create_response_custom_headers(self):
        """Test creating response with custom headers"""
        custom_headers = {'X-Custom-Header': 'value'}
        response = create_response(200, {'data': 'test'}, headers=custom_headers)
        
        assert response['headers']['X-Custom-Header'] == 'value'
        assert response['headers']['Content-Type'] == 'application/json'
    
    def test_create_response_body_serialization(self):
        """Test response body is properly serialized"""
        response = create_response(200, {'key': 'value'})
        body = json.loads(response['body'])
        
        assert body['key'] == 'value'


@pytest.mark.unit
class TestSuccessResponses:
    """Test success response helpers"""
    
    def test_create_success_response(self):
        """Test creating success response"""
        response = create_success_response({'user_id': '123'})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['data']['user_id'] == '123'
    
    def test_create_success_response_with_message(self):
        """Test success response with message"""
        response = create_success_response({'id': '1'}, message='Created successfully')
        
        body = json.loads(response['body'])
        assert body['message'] == 'Created successfully'
    
    def test_create_created_response(self):
        """Test creating 201 created response"""
        response = create_created_response({'id': 'new-123'})
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['data']['id'] == 'new-123'


@pytest.mark.unit
class TestErrorResponses:
    """Test error response helpers"""
    
    def test_create_error_response_basic(self):
        """Test creating basic error response"""
        response = create_error_response(400, 'Bad request')
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error']['message'] == 'Bad request'
    
    def test_create_error_response_with_code(self):
        """Test error response with error code"""
        response = create_error_response(400, 'Invalid input', error_code='INVALID_INPUT')
        
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INVALID_INPUT'
    
    def test_create_error_response_with_details(self):
        """Test error response with details"""
        details = {'field': 'email', 'issue': 'invalid format'}
        response = create_error_response(400, 'Validation failed', details=details)
        
        body = json.loads(response['body'])
        assert body['error']['details'] == details
    
    def test_create_validation_error_response(self):
        """Test validation error response"""
        errors = {'email': 'Invalid email format', 'password': 'Too short'}
        response = create_validation_error_response(errors)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert body['error']['details']['validation_errors'] == errors
    
    def test_create_unauthorized_response(self):
        """Test unauthorized response"""
        response = create_unauthorized_response()
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['message'] == 'Unauthorized'
        assert body['error']['code'] == 'UNAUTHORIZED'
    
    def test_create_forbidden_response(self):
        """Test forbidden response"""
        response = create_forbidden_response('Access denied')
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['message'] == 'Access denied'
        assert body['error']['code'] == 'FORBIDDEN'
    
    def test_create_not_found_response(self):
        """Test not found response"""
        response = create_not_found_response('User not found')
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['message'] == 'User not found'
        assert body['error']['code'] == 'NOT_FOUND'
    
    def test_create_internal_error_response(self):
        """Test internal error response"""
        response = create_internal_error_response()
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error']['code'] == 'INTERNAL_ERROR'


@pytest.mark.unit
class TestHandleError:
    """Test error handling"""
    
    def test_handle_validation_error(self):
        """Test handling validation errors"""
        error = ValueError('Validation failed: invalid email')
        response = handle_error(error)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
    
    def test_handle_unauthorized_error(self):
        """Test handling unauthorized errors"""
        error = Exception('Unauthorized access')
        response = handle_error(error)
        
        assert response['statusCode'] == 401
    
    def test_handle_forbidden_error(self):
        """Test handling forbidden errors"""
        error = Exception('Forbidden: insufficient permissions')
        response = handle_error(error)
        
        assert response['statusCode'] == 403
    
    def test_handle_not_found_error(self):
        """Test handling not found errors"""
        error = Exception('Resource not found')
        response = handle_error(error)
        
        assert response['statusCode'] == 404
    
    def test_handle_generic_error(self):
        """Test handling generic errors"""
        error = Exception('Something went wrong')
        response = handle_error(error)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error']['message'] == 'An unexpected error occurred'


@pytest.mark.unit
class TestRequestParsing:
    """Test request parsing utilities"""
    
    def test_parse_request_body_json_string(self):
        """Test parsing JSON string body"""
        event = {'body': '{"key": "value"}'}
        body = parse_request_body(event)
        
        assert body['key'] == 'value'
    
    def test_parse_request_body_dict(self):
        """Test parsing dict body"""
        event = {'body': {'key': 'value'}}
        body = parse_request_body(event)
        
        assert body['key'] == 'value'
    
    def test_parse_request_body_empty(self):
        """Test parsing empty body"""
        event = {}
        body = parse_request_body(event)
        
        assert body == {}
    
    def test_parse_request_body_invalid_json(self):
        """Test parsing invalid JSON"""
        event = {'body': '{invalid json}'}
        
        with pytest.raises(ValueError, match='Invalid JSON'):
            parse_request_body(event)
    
    def test_get_path_parameters(self):
        """Test getting path parameters"""
        event = {'pathParameters': {'id': '123', 'name': 'test'}}
        params = get_path_parameters(event)
        
        assert params['id'] == '123'
        assert params['name'] == 'test'
    
    def test_get_path_parameters_empty(self):
        """Test getting path parameters when none exist"""
        event = {}
        params = get_path_parameters(event)
        
        assert params == {}
    
    def test_get_query_parameters(self):
        """Test getting query parameters"""
        event = {'queryStringParameters': {'page': '1', 'limit': '10'}}
        params = get_query_parameters(event)
        
        assert params['page'] == '1'
        assert params['limit'] == '10'
    
    def test_get_query_parameters_empty(self):
        """Test getting query parameters when none exist"""
        event = {}
        params = get_query_parameters(event)
        
        assert params == {}
