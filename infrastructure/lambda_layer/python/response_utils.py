"""
HTTP response utilities for Lambda functions
"""
import json
from typing import Dict, Any, Optional
import os


def create_response(
    status_code: int,
    body: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Create standardized HTTP response for API Gateway"""
    
    # Default headers with CORS — allow localhost in local dev, CloudFront in production
    cors_origin = (
        'http://localhost:5173'
        if os.environ.get('LOCAL_DEV') == 'true'
        else 'https://d3awlgby2429wc.cloudfront.net'
    )
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': cors_origin,
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Credentials': 'true'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body, default=str)  # default=str handles datetime serialization
    }


def create_success_response(data: Any, message: str = None) -> Dict[str, Any]:
    """Create success response (200)"""
    body = {'success': True, 'data': data}
    if message:
        body['message'] = message
    
    return create_response(200, body)


def create_created_response(data: Any, message: str = None) -> Dict[str, Any]:
    """Create created response (201)"""
    body = {'success': True, 'data': data}
    if message:
        body['message'] = message
    
    return create_response(201, body)


def create_error_response(
    status_code: int,
    error_message: str,
    error_code: str = None,
    details: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Create error response"""
    body = {
        'success': False,
        'error': {
            'message': error_message
        }
    }
    
    if error_code:
        body['error']['code'] = error_code
    
    if details:
        body['error']['details'] = details
    
    return create_response(status_code, body)


def create_validation_error_response(validation_errors: Dict[str, str]) -> Dict[str, Any]:
    """Create validation error response (400)"""
    return create_error_response(
        400,
        'Validation failed',
        'VALIDATION_ERROR',
        {'validation_errors': validation_errors}
    )


def create_unauthorized_response(message: str = 'Unauthorized') -> Dict[str, Any]:
    """Create unauthorized response (401)"""
    return create_error_response(401, message, 'UNAUTHORIZED')


def create_forbidden_response(message: str = 'Forbidden') -> Dict[str, Any]:
    """Create forbidden response (403)"""
    return create_error_response(403, message, 'FORBIDDEN')


def create_not_found_response(message: str = 'Resource not found') -> Dict[str, Any]:
    """Create not found response (404)"""
    return create_error_response(404, message, 'NOT_FOUND')


def create_internal_error_response(message: str = 'Internal server error') -> Dict[str, Any]:
    """Create internal server error response (500)"""
    return create_error_response(500, message, 'INTERNAL_ERROR')


def handle_error(error: Exception) -> Dict[str, Any]:
    """Handle and format exceptions into appropriate HTTP responses"""
    error_message = str(error)
    
    # Log error for debugging (in production, use proper logging)
    print(f"Lambda error: {error_message}")
    
    # Determine appropriate status code based on error type
    if 'validation' in error_message.lower():
        return create_error_response(400, error_message, 'VALIDATION_ERROR')
    elif 'unauthorized' in error_message.lower() or 'authentication' in error_message.lower():
        return create_unauthorized_response(error_message)
    elif 'forbidden' in error_message.lower() or 'permission' in error_message.lower():
        return create_forbidden_response(error_message)
    elif 'not found' in error_message.lower():
        return create_not_found_response(error_message)
    else:
        # Generic internal server error
        return create_internal_error_response('An unexpected error occurred')


def parse_request_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and validate request body from Lambda event"""
    body = event.get('body', '{}')
    
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON in request body')
    
    return body


def get_path_parameters(event: Dict[str, Any]) -> Dict[str, str]:
    """Get path parameters from Lambda event"""
    return event.get('pathParameters') or {}


def get_query_parameters(event: Dict[str, Any]) -> Dict[str, str]:
    """Get query parameters from Lambda event"""
    return event.get('queryStringParameters') or {}