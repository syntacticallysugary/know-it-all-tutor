"""
User Profile Lambda Function
Handles user profile operations (get, update)
Uses Lambda Bridge pattern: calls DB Proxy Lambda for database access
"""
import json
import sys
import os
import logging

# Add shared modules to path
sys.path.append('/opt/python')

from db_proxy_client import DBProxyClient
from response_utils import create_success_response, create_error_response
from auth_utils import extract_user_from_cognito_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize DB Proxy client
db_proxy = DBProxyClient(os.environ.get('DB_PROXY_FUNCTION_NAME'))


def lambda_handler(event, context):
    """
    Handle user profile requests
    
    Routes:
    - GET /profile - Get current user's profile
    - PUT /profile - Update current user's profile
    """
    try:
        http_method = event.get('httpMethod')
        
        auth_result = extract_user_from_cognito_event(event)
        if not auth_result['valid']:
            return create_error_response(401, 'Unauthorized - No user identity found')
        cognito_sub = auth_result['user_id']
        
        if http_method == 'GET':
            return handle_get_profile(cognito_sub)
        elif http_method == 'PUT':
            return handle_update_profile(cognito_sub, event)
        else:
            return create_error_response(405, f'Method {http_method} not allowed')
            
    except Exception as e:
        logger.error(f"Profile handler error: {e}", exc_info=True)
        return create_error_response(500, f'Internal server error: {str(e)}')


def handle_get_profile(cognito_sub):
    """Get user profile from database"""
    try:
        # Query user by cognito_sub
        query = """
            SELECT id, cognito_sub, email, first_name, last_name, 
                   is_active, created_at, updated_at, last_login
            FROM users
            WHERE cognito_sub = %s
        """
        
        result = db_proxy.execute_query(query, params=[cognito_sub], return_dict=True)
        
        if not result or len(result) == 0:
            return create_error_response(404, 'User profile not found')
        
        user = result[0]
        
        # Return profile data
        return create_success_response({
            'user_id': user['id'],
            'email': user['email'],
            'first_name': user.get('first_name'),
            'last_name': user.get('last_name'),
            'is_active': user['is_active'],
            'created_at': user['created_at'],
            'last_login': user.get('last_login')
        })
        
    except Exception as e:
        logger.error(f"Get profile error: {e}", exc_info=True)
        return create_error_response(500, f'Failed to get profile: {str(e)}')


def handle_update_profile(cognito_sub, event):
    """Update user profile"""
    try:
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return create_error_response(400, 'Invalid JSON in request body')
        
        # Build update query dynamically based on provided fields
        allowed_fields = ['first_name', 'last_name']
        updates = []
        params = []
        
        for field in allowed_fields:
            if field in body:
                updates.append(f"{field} = %s")
                params.append(body[field])
        
        if not updates:
            return create_error_response(400, 'No valid fields to update')
        
        # Add cognito_sub to params for WHERE clause
        params.append(cognito_sub)
        
        # Execute update
        query = f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE cognito_sub = %s
            RETURNING id, email, first_name, last_name, is_active, updated_at
        """
        
        result = db_proxy.execute_query(query, params=params, return_dict=True)
        
        if not result or len(result) == 0:
            return create_error_response(404, 'User not found')
        
        user = result[0]
        
        return create_success_response({
            'message': 'Profile updated successfully',
            'user': {
                'user_id': user['id'],
                'email': user['email'],
                'first_name': user.get('first_name'),
                'last_name': user.get('last_name'),
                'is_active': user['is_active'],
                'updated_at': user['updated_at']
            }
        })
        
    except Exception as e:
        logger.error(f"Update profile error: {e}", exc_info=True)
        return create_error_response(500, f'Failed to update profile: {str(e)}')
