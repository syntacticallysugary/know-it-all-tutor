"""
Cognito-based Authentication Lambda Function Handler
Handles user registration, login, and session management using AWS Cognito with security middleware
Supports environment-aware authentication for LocalStack and production environments
"""
import json
import boto3
import os
import sys
import base64
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

# Add shared modules to path
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from response_utils import create_response, handle_error
from security_controls import extract_client_info
from security_monitoring import SecurityMonitor
from security_middleware import security_middleware, create_secure_response, validate_email
from db_proxy_client import DBProxyClient


# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Initialize DB client
db_proxy = DBProxyClient(os.environ.get('DB_PROXY_FUNCTION_NAME'))

# Get Cognito configuration from environment
USER_POOL_ID = os.environ.get('USER_POOL_ID')
USER_POOL_CLIENT_ID = os.environ.get('USER_POOL_CLIENT_ID')
STAGE = os.environ.get('STAGE', 'local')


def resolve_identity(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Resolve user identity based on environment stage
    
    Args:
        event: Lambda event containing request context and headers
        
    Returns:
        Dictionary containing user identity information or None if not authenticated
    """
    stage = os.environ.get("STAGE", "local")
    
    if stage == "prod":
        # Production: Extract from Cognito authorizer claims
        try:
            authorizer_claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
            if not authorizer_claims:
                return None
                
            return {
                "sub": authorizer_claims.get("sub"),
                "email": authorizer_claims.get("email"),
                "cognito:groups": authorizer_claims.get("cognito:groups", "").split(",") if authorizer_claims.get("cognito:groups") else [],
                "given_name": authorizer_claims.get("given_name", ""),
                "family_name": authorizer_claims.get("family_name", ""),
                "email_verified": authorizer_claims.get("email_verified") == "true"
            }
        except Exception as e:
            print(f"Error extracting production identity: {e}")
            return None
    
    else:
        # Local: Manually decode JWT token without signature verification
        try:
            headers = event.get('headers', {})
            auth_header = headers.get('Authorization', '') or headers.get('authorization', '')
            
            if not auth_header:
                return None
            
            # Remove 'Bearer ' prefix if present
            token = auth_header[7:] if auth_header.startswith('Bearer ') else auth_header
            
            # Split JWT token
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode payload (second part)
            payload_part = parts[1]
            
            # Add padding if necessary
            missing_padding = len(payload_part) % 4
            if missing_padding:
                payload_part += '=' * (4 - missing_padding)
            
            # Decode base64
            payload_bytes = base64.b64decode(payload_part)
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            # Extract relevant claims
            return {
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "cognito:groups": payload.get("cognito:groups", []),
                "given_name": payload.get("given_name", ""),
                "family_name": payload.get("family_name", ""),
                "email_verified": payload.get("email_verified", False),
                "token_use": payload.get("token_use"),
                "aud": payload.get("aud"),
                "iss": payload.get("iss"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
            
        except Exception as e:
            print(f"Error decoding local JWT token: {e}")
            return None


@security_middleware
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for Cognito authentication operations
    """
    try:
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        if http_method == 'POST':
            if path.endswith('/register'):
                return handle_register(event)
            elif path.endswith('/login'):
                return handle_login(event)
            elif path.endswith('/logout'):
                return handle_logout(event)
            elif path.endswith('/confirm'):
                return handle_confirm_signup(event)
            elif path.endswith('/resend-confirmation'):
                return handle_resend_confirmation(event)
            elif path.endswith('/forgot-password'):
                return handle_forgot_password(event)
            elif path.endswith('/confirm-forgot-password'):
                return handle_confirm_forgot_password(event)
            elif path.endswith('/change-password'):
                return handle_change_password(event)
        elif http_method == 'GET':
            if path.endswith('/validate'):
                return handle_validate_token(event)
        
        return create_response(404, {'error': 'Endpoint not found'})
        
    except Exception as e:
        return handle_error(e)


def handle_register(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user registration using Cognito SignUp with enhanced security"""
    client_info = extract_client_info(event)
    
    try:
        # Use sanitized body data from security middleware
        body = event.get('sanitized_body', {})
        if not body:
            return create_secure_response(400, {'error': 'Request body is required'})

        raw_body = event.get('body', '')
        if raw_body and len(raw_body) > 4096:
            return create_secure_response(400, {'error': 'Request body too large'})

        email = body.get('email', '').strip().lower()
        password = body.get('password', '')
        first_name = body.get('first_name', '').strip()
        last_name = body.get('last_name', '').strip()

        # Enhanced validation
        if not email:
            return create_secure_response(400, {'error': 'Email is required'})

        if len(email) > 254:
            return create_secure_response(400, {'error': 'Email address too long'})

        if not validate_email(email):
            return create_secure_response(400, {'error': 'Invalid email format'})
        
        if not password:
            return create_secure_response(400, {'error': 'Password is required'})
        
        if len(password) < 8:
            return create_secure_response(400, {'error': 'Password must be at least 8 characters long'})
        
        # Validate name lengths
        if first_name and len(first_name) > 50:
            return create_secure_response(400, {'error': 'First name too long (max 50 characters)'})
        
        if last_name and len(last_name) > 50:
            return create_secure_response(400, {'error': 'Last name too long (max 50 characters)'})
        
        # Prepare user attributes
        user_attributes = [
            {'Name': 'email', 'Value': email}
        ]
        
        if first_name:
            user_attributes.append({'Name': 'given_name', 'Value': first_name})
        
        if last_name:
            user_attributes.append({'Name': 'family_name', 'Value': last_name})
        
        # Register user with Cognito
        response = cognito_client.sign_up(
            ClientId=USER_POOL_CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=user_attributes,
            ClientMetadata={
                'ip_address': client_info['ip_address'],
                'user_agent': client_info['user_agent']
            }
        )
        
        # Auto-confirm user for dev environment (no email verification)
        if STAGE in ['prod', 'dev'] and not response.get('UserConfirmed', False):
            try:
                cognito_client.admin_confirm_sign_up(
                    UserPoolId=USER_POOL_ID,
                    Username=email
                )
                user_confirmed = True
            except Exception as confirm_error:
                print(f"Warning: Failed to auto-confirm user: {confirm_error}")
                user_confirmed = False
        else:
            user_confirmed = response.get('UserConfirmed', False)
        
        # Create user record in database
        try:
            db_proxy.execute_query(
                """
                INSERT INTO users (cognito_sub, email, first_name, last_name, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (cognito_sub) DO NOTHING
                """,
                params=[response['UserSub'], email, first_name or None, last_name or None, True]
            )
            print(f"Created user record in database for {email}")
        except Exception as db_error:
            print(f"Warning: Failed to create user in database: {db_error}")
            # Don't fail registration if DB insert fails
        
        return create_secure_response(201, {
            'message': 'User registered successfully',
            'user_sub': response['UserSub'],
            'confirmation_required': not user_confirmed,
            'delivery_details': response.get('CodeDeliveryDetails', {})
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UsernameExistsException':
            return create_secure_response(409, {'error': 'User with this email already exists'})
        elif error_code == 'InvalidPasswordException':
            return create_secure_response(400, {'error': 'Password does not meet requirements'})
        elif error_code == 'InvalidParameterException':
            return create_secure_response(400, {'error': 'Invalid parameters provided'})
        elif error_code == 'TooManyRequestsException':
            return create_secure_response(429, {'error': 'Too many requests. Please try again later.'})
        else:
            return create_secure_response(400, {'error': error_message})
            
    except Exception as e:
        return handle_error(e)


def handle_login(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user login using Cognito InitiateAuth"""
    client_info = extract_client_info(event)
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip().lower()
        password = body.get('password', '')
        
        # Validate required fields
        if not email or not password:
            return create_response(400, {'error': 'Email and password are required'})
        
        # Authenticate with Cognito
        response = cognito_client.initiate_auth(
            ClientId=USER_POOL_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            },
            ClientMetadata={
                'ip_address': client_info['ip_address'],
                'user_agent': client_info['user_agent']
            }
        )
        
        # Handle different authentication results
        if 'ChallengeName' in response:
            # Handle MFA or other challenges
            return handle_auth_challenge(response)
        
        # Successful authentication
        auth_result = response['AuthenticationResult']
        
        # Get user attributes
        user_info = get_user_info(auth_result['AccessToken'])
        
        return create_response(200, {
            'message': 'Login successful',
            'user': user_info,
            'tokens': {
                'access_token': auth_result['AccessToken'],
                'id_token': auth_result['IdToken'],
                'refresh_token': auth_result['RefreshToken'],
                'expires_in': auth_result['ExpiresIn']
            }
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'NotAuthorizedException':
            return create_response(401, {'error': 'Invalid credentials'})
        elif error_code == 'UserNotConfirmedException':
            return create_response(401, {'error': 'User email not confirmed'})
        elif error_code == 'UserNotFoundException':
            return create_response(401, {'error': 'Invalid credentials'})
        elif error_code == 'TooManyRequestsException':
            return create_response(429, {'error': 'Too many requests. Please try again later.'})
        else:
            return create_response(400, {'error': error_message})
            
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        return handle_error(e)


def handle_logout(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user logout using Cognito GlobalSignOut"""
    try:
        # Extract access token from Authorization header
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization', '') or headers.get('authorization', '')
        
        if not auth_header:
            return create_response(400, {'error': 'Authorization header required for logout'})
        
        # Remove 'Bearer ' prefix if present
        access_token = auth_header[7:] if auth_header.startswith('Bearer ') else auth_header
        
        # Sign out user globally (invalidates all tokens)
        cognito_client.global_sign_out(
            AccessToken=access_token
        )
        
        return create_response(200, {
            'message': 'Logout successful',
            'tokens_invalidated': True
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'NotAuthorizedException':
            # Token might already be invalid, but logout is still successful
            return create_response(200, {'message': 'Logout successful'})
        else:
            return create_response(200, {'message': 'Logout successful'})
            
    except Exception as e:
        # Don't expose internal errors for logout
        return create_response(200, {'message': 'Logout successful'})


def handle_confirm_signup(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle email verification confirmation"""
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip().lower()
        confirmation_code = body.get('confirmation_code', '')
        
        if not email or not confirmation_code:
            return create_response(400, {'error': 'Email and confirmation code are required'})
        
        # Confirm signup with Cognito
        cognito_client.confirm_sign_up(
            ClientId=USER_POOL_CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code
        )
        
        return create_response(200, {
            'message': 'Email confirmed successfully'
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'CodeMismatchException':
            return create_response(400, {'error': 'Invalid confirmation code'})
        elif error_code == 'ExpiredCodeException':
            return create_response(400, {'error': 'Confirmation code has expired'})
        elif error_code == 'UserNotFoundException':
            return create_response(404, {'error': 'User not found'})
        else:
            return create_response(400, {'error': error_message})
            
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        return handle_error(e)


def handle_resend_confirmation(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle resending confirmation code"""
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip().lower()
        
        if not email:
            return create_response(400, {'error': 'Email is required'})
        
        # Resend confirmation code
        response = cognito_client.resend_confirmation_code(
            ClientId=USER_POOL_CLIENT_ID,
            Username=email
        )
        
        return create_response(200, {
            'message': 'Confirmation code sent',
            'delivery_details': response.get('CodeDeliveryDetails', {})
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UserNotFoundException':
            return create_response(404, {'error': 'User not found'})
        elif error_code == 'InvalidParameterException':
            return create_response(400, {'error': 'User is already confirmed'})
        else:
            return create_response(400, {'error': error_message})
            
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        return handle_error(e)


def handle_forgot_password(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle forgot password request"""
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip().lower()
        
        if not email:
            return create_response(400, {'error': 'Email is required'})
        
        # Initiate forgot password flow
        response = cognito_client.forgot_password(
            ClientId=USER_POOL_CLIENT_ID,
            Username=email
        )
        
        return create_response(200, {
            'message': 'Password reset code sent',
            'delivery_details': response.get('CodeDeliveryDetails', {})
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UserNotFoundException':
            # Don't reveal if user exists or not
            return create_response(200, {'message': 'If the email exists, a reset code has been sent'})
        else:
            return create_response(400, {'error': error_message})
            
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        return handle_error(e)


def handle_confirm_forgot_password(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle password reset confirmation"""
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip().lower()
        confirmation_code = body.get('confirmation_code', '')
        new_password = body.get('new_password', '')
        
        if not email or not confirmation_code or not new_password:
            return create_response(400, {'error': 'Email, confirmation code, and new password are required'})
        
        # Confirm forgot password
        cognito_client.confirm_forgot_password(
            ClientId=USER_POOL_CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code,
            Password=new_password
        )
        
        return create_response(200, {
            'message': 'Password reset successful'
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'CodeMismatchException':
            return create_response(400, {'error': 'Invalid confirmation code'})
        elif error_code == 'ExpiredCodeException':
            return create_response(400, {'error': 'Confirmation code has expired'})
        elif error_code == 'InvalidPasswordException':
            return create_response(400, {'error': 'Password does not meet requirements'})
        else:
            return create_response(400, {'error': error_message})
            
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        return handle_error(e)


def handle_change_password(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle password change for authenticated users"""
    try:
        # Extract access token from Authorization header
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization', '') or headers.get('authorization', '')
        
        if not auth_header:
            return create_response(401, {'error': 'Authorization header required'})
        
        access_token = auth_header[7:] if auth_header.startswith('Bearer ') else auth_header
        
        body = json.loads(event.get('body', '{}'))
        previous_password = body.get('previous_password', '')
        proposed_password = body.get('proposed_password', '')
        
        if not previous_password or not proposed_password:
            return create_response(400, {'error': 'Previous password and new password are required'})
        
        # Change password
        cognito_client.change_password(
            AccessToken=access_token,
            PreviousPassword=previous_password,
            ProposedPassword=proposed_password
        )
        
        return create_response(200, {
            'message': 'Password changed successfully'
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'NotAuthorizedException':
            return create_response(401, {'error': 'Invalid current password or token'})
        elif error_code == 'InvalidPasswordException':
            return create_response(400, {'error': 'New password does not meet requirements'})
        else:
            return create_response(400, {'error': error_message})
            
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        return handle_error(e)


def handle_validate_token(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle token validation using environment-aware identity resolution"""
    try:
        # Use environment-aware identity resolution
        identity = resolve_identity(event)
        
        if not identity:
            return create_response(401, {'error': 'Invalid or missing authentication'})
        
        # For local environment, we trust the decoded token
        # For production, Cognito authorizer has already validated it
        if STAGE == "local":
            # Additional validation for local environment
            if not identity.get('sub') or not identity.get('email'):
                return create_response(401, {'error': 'Invalid token payload'})
        
        return create_response(200, {
            'valid': True,
            'user': {
                'id': identity.get('sub'),
                'email': identity.get('email'),
                'first_name': identity.get('given_name', ''),
                'last_name': identity.get('family_name', ''),
                'email_verified': identity.get('email_verified', False),
                'groups': identity.get('cognito:groups', [])
            },
            'stage': STAGE,
            'identity_source': 'cognito_authorizer' if STAGE == 'prod' else 'jwt_decode'
        })
        
    except Exception as e:
        return handle_error(e)


def get_user_info(access_token: str) -> Dict[str, Any]:
    """Get user information from Cognito using access token"""
    response = cognito_client.get_user(AccessToken=access_token)
    
    # Parse user attributes
    user_attributes = {}
    for attr in response['UserAttributes']:
        user_attributes[attr['Name']] = attr['Value']
    
    return {
        'id': user_attributes.get('sub'),
        'email': user_attributes.get('email'),
        'first_name': user_attributes.get('given_name', ''),
        'last_name': user_attributes.get('family_name', ''),
        'email_verified': user_attributes.get('email_verified') == 'true',
        'username': response['Username']
    }


def handle_auth_challenge(response: Dict[str, Any]) -> Dict[str, Any]:
    """Handle authentication challenges like MFA"""
    challenge_name = response['ChallengeName']
    session = response['Session']
    
    if challenge_name == 'SMS_MFA':
        return create_response(200, {
            'challenge': 'SMS_MFA',
            'session': session,
            'message': 'SMS verification code sent'
        })
    elif challenge_name == 'SOFTWARE_TOKEN_MFA':
        return create_response(200, {
            'challenge': 'SOFTWARE_TOKEN_MFA',
            'session': session,
            'message': 'Enter code from your authenticator app'
        })
    else:
        return create_response(400, {
            'error': f'Unsupported challenge: {challenge_name}'
        })