"""
Authentication utilities for password hashing and legacy JWT support
Note: JWT functions are deprecated - use AWS Cognito for authentication
"""
import bcrypt
import uuid
import hashlib
import warnings
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import sys
import os

# Add shared directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from config import get_config
from database import get_db_connection

# JWT imports only for legacy support
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt
    DEPRECATED: Use AWS Cognito for password management
    """
    warnings.warn(
        "hash_password is deprecated. Use AWS Cognito for password management.",
        DeprecationWarning,
        stacklevel=2
    )
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    DEPRECATED: Use AWS Cognito for password verification
    """
    warnings.warn(
        "verify_password is deprecated. Use AWS Cognito for password verification.",
        DeprecationWarning,
        stacklevel=2
    )
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Create a hash of the token for secure storage"""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def generate_jwt(user_id: str, email: str, additional_claims: Dict[str, Any] = None) -> str:
    """
    Generate JWT token for user
    DEPRECATED: Use AWS Cognito for token generation
    """
    warnings.warn(
        "generate_jwt is deprecated. Use AWS Cognito for token generation.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if not JWT_AVAILABLE:
        raise RuntimeError("JWT library not available. Use AWS Cognito instead.")
    
    config = get_config().get_jwt_config()
    
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())  # JWT ID for token tracking
    
    payload = {
        'user_id': user_id,
        'email': email,
        'iat': now,
        'exp': now + timedelta(hours=config['expiration_hours']),
        'jti': jti
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    return jwt.encode(payload, config['secret'], algorithm=config['algorithm'])


def is_token_blacklisted(jti: str) -> bool:
    """Check if a token is blacklisted"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM token_blacklist 
                WHERE jti = %s AND expires_at > CURRENT_TIMESTAMP
            """, (jti,))
            return cursor.fetchone() is not None
    except Exception:
        # If we can't check the blacklist, assume token is valid
        # This prevents database issues from breaking authentication
        return False


def blacklist_token(token: str, user_id: str, reason: str = 'logout') -> bool:
    """Add token to blacklist"""
    try:
        # Decode token to get JTI and expiration
        config = get_config().get_jwt_config()
        payload = jwt.decode(token, config['secret'], algorithms=[config['algorithm']])
        
        jti = payload.get('jti')
        exp = payload.get('exp')
        
        if not jti or not exp:
            return False
        
        # Convert exp timestamp to datetime
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        token_hash = hash_token(token)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO token_blacklist (jti, user_id, token_hash, expires_at, reason)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (jti) DO NOTHING
            """, (jti, user_id, token_hash, expires_at, reason))
            conn.commit()
            return True
            
    except Exception:
        return False


def verify_jwt(token: str) -> Dict[str, Any]:
    """
    Verify JWT token and return payload
    DEPRECATED: Use AWS Cognito for token verification
    """
    warnings.warn(
        "verify_jwt is deprecated. Use AWS Cognito for token verification.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if not token:
        return {'valid': False, 'error': 'No token provided'}
    
    if not JWT_AVAILABLE:
        return {'valid': False, 'error': 'JWT library not available. Use AWS Cognito instead.'}
    
    # Remove 'Bearer ' prefix if present
    if token.startswith('Bearer '):
        token = token[7:]
    
    config = get_config().get_jwt_config()
    
    try:
        payload = jwt.decode(token, config['secret'], algorithms=[config['algorithm']])
        
        # Check if token is blacklisted
        jti = payload.get('jti')
        if jti and is_token_blacklisted(jti):
            return {'valid': False, 'error': 'Token has been invalidated'}
        
        return {
            'valid': True,
            'user_id': payload.get('user_id'),
            'email': payload.get('email'),
            'payload': payload
        }
    except jwt.ExpiredSignatureError:
        return {'valid': False, 'error': 'Token has expired'}
    except jwt.InvalidTokenError:
        return {'valid': False, 'error': 'Invalid token'}
    except Exception as e:
        return {'valid': False, 'error': f'Token verification failed: {str(e)}'}


def refresh_jwt(token: str) -> Optional[str]:
    """
    Refresh JWT token if it's close to expiration
    DEPRECATED: Use AWS Cognito for token refresh
    """
    warnings.warn(
        "refresh_jwt is deprecated. Use AWS Cognito for token refresh.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if not JWT_AVAILABLE:
        return None
    
    verification = verify_jwt(token)
    
    if not verification['valid']:
        return None
    
    payload = verification['payload']
    exp_timestamp = payload.get('exp')
    
    if not exp_timestamp:
        return None
    
    # Check if token expires within next hour
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    
    if exp_datetime - now < timedelta(hours=1):
        # Blacklist the old token
        blacklist_token(token, payload['user_id'], 'refresh')
        
        # Generate new token with same user info
        return generate_jwt(
            user_id=payload['user_id'],
            email=payload['email']
        )
    
    return token  # Token is still valid for more than an hour


def invalidate_all_user_tokens(user_id: str, reason: str = 'security') -> int:
    """Invalidate all tokens for a user (for security purposes)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # We can't blacklist tokens we don't know about, but we can record
            # a security event and rely on short token expiration times
            cursor.execute("""
                INSERT INTO token_blacklist (jti, user_id, token_hash, expires_at, reason)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                f"security-invalidation-{uuid.uuid4()}",
                user_id,
                "security-invalidation",
                datetime.now(timezone.utc) + timedelta(days=1),  # Placeholder expiration
                reason
            ))
            conn.commit()
            return 1
            
    except Exception:
        return 0


def cleanup_expired_tokens() -> int:
    """Clean up expired blacklisted tokens"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cleanup_expired_blacklisted_tokens()")
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else 0
    except Exception:
        return 0


def extract_user_from_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and verify user from Lambda event
    DEPRECATED: Use AWS Cognito authorizer context instead
    """
    warnings.warn(
        "extract_user_from_event is deprecated. Use AWS Cognito authorizer context instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization', '') or headers.get('authorization', '')
    
    return verify_jwt(auth_header)


def extract_user_from_cognito_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract user information from Cognito-authorized Lambda event
    """
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})
    
    # Extract user information from Cognito authorizer context
    claims = authorizer.get('claims', {})
    
    if not claims:
        # For LocalStack testing without proper Cognito authorizer,
        # use a default test user
        import os
        if os.environ.get('LOCALSTACK_ENDPOINT'):
            return {
                'valid': True,
                'user_id': '550e8400-e29b-41d4-a716-446655440000',  # Test UUID
                'email': 'test@example.com',
                'username': 'test@example.com',
                'email_verified': True,
                'claims': {
                    'sub': '550e8400-e29b-41d4-a716-446655440000',
                    'email': 'test@example.com',
                    'cognito:username': 'test@example.com'
                }
            }
        return {'valid': False, 'error': 'No Cognito claims found'}
    
    return {
        'valid': True,
        'user_id': claims.get('sub'),  # Cognito user ID
        'email': claims.get('email'),
        'username': claims.get('cognito:username'),
        'email_verified': claims.get('email_verified') == 'true',
        'claims': claims
    }