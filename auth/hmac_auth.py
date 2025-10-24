"""
HMAC Request Signing + JWT Token Authentication
Implements secure API authentication with HMAC signatures and JWT tokens
"""

import hmac
import hashlib
import time
import jwt
import os
import json
import logging
from functools import wraps
from flask import request, jsonify, abort
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_EXPIRY = 3600  # 1 hour
REQUEST_TIMEOUT = 300  # 5 minutes

# Load client credentials from environment
CLIENTS = json.loads(os.environ.get('API_CLIENTS', '{}'))

def verify_hmac_signature():
    """
    Verify HMAC signature on incoming request.
    
    Expected headers:
    - X-API-Key: Client's API key
    - X-Signature: HMAC signature of request
    - X-Timestamp: Unix timestamp of request
    
    Returns:
        dict: Client info if valid
    Raises:
        401: If authentication fails
    """
    api_key = request.headers.get('X-API-Key')
    signature = request.headers.get('X-Signature')
    timestamp = request.headers.get('X-Timestamp')
    
    if not all([api_key, signature, timestamp]):
        logger.warning("Missing authentication headers")
        abort(401, {'error': 'Missing authentication headers'})
    
    # Prevent replay attacks - request must be within 5 minutes
    try:
        request_time = float(timestamp)
    except ValueError:
        logger.warning("Invalid timestamp format")
        abort(401, {'error': 'Invalid timestamp'})
    
    if abs(time.time() - request_time) > REQUEST_TIMEOUT:
        logger.warning("Request expired")
        abort(401, {'error': 'Request expired. Check system clock.'})
    
    # Find client by API key
    client = None
    client_id = None
    for cid, client_data in CLIENTS.items():
        if client_data.get('api_key') == api_key:
            client = client_data
            client_id = cid
            break
    
    if not client:
        logger.warning(f"Invalid API key: {api_key}")
        abort(401, {'error': 'Invalid API key'})
    
    # Verify signature
    message = f"{request.method}:{request.path}:{timestamp}:{request.get_data().decode()}"
    expected_sig = hmac.new(
        client['api_secret'].encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_sig):
        logger.warning(f"Invalid signature for client {client_id}")
        abort(401, {'error': 'Invalid signature'})
    
    logger.info(f"HMAC verification successful for client {client_id}")
    return {
        'client_id': client_id,
        'client_name': client.get('name', 'Unknown'),
        'permissions': client.get('permissions', [])
    }

def generate_jwt_token(client_info: Dict[str, Any]) -> str:
    """
    Generate JWT token for authenticated client.
    
    Args:
        client_info: Client information from HMAC verification
        
    Returns:
        str: JWT token
    """
    if not JWT_SECRET:
        logger.error("JWT_SECRET not configured")
        abort(500, {'error': 'Server configuration error'})
    
    payload = {
        'client_id': client_info['client_id'],
        'client_name': client_info['client_name'],
        'permissions': client_info['permissions'],
        'iat': int(time.time()),
        'exp': int(time.time()) + JWT_EXPIRY,
        'iss': 'qbo-sankey-dashboard'
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    logger.info(f"JWT token generated for client {client_info['client_id']}")
    return token

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded token payload
    Raises:
        401: If token is invalid or expired
    """
    if not JWT_SECRET:
        logger.error("JWT_SECRET not configured")
        abort(500, {'error': 'Server configuration error'})
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        logger.info(f"JWT token verified for client {payload.get('client_id')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        abort(401, {'error': 'Token expired'})
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        abort(401, {'error': 'Invalid token'})

def require_hmac_auth(f):
    """
    Decorator to require HMAC authentication for API endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            client_info = verify_hmac_signature()
            return f(client_info=client_info, *args, **kwargs)
        except Exception as e:
            logger.error(f"HMAC authentication failed: {e}")
            return jsonify({'error': 'Authentication failed'}), 401
    
    return decorated_function

def require_jwt_auth(f):
    """
    Decorator to require JWT authentication for API endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                abort(401, {'error': 'Missing or invalid Authorization header'})
            
            token = auth_header.split(' ')[1]
            payload = verify_jwt_token(token)
            return f(client_info=payload, *args, **kwargs)
        except Exception as e:
            logger.error(f"JWT authentication failed: {e}")
            return jsonify({'error': 'Authentication failed'}), 401
    
    return decorated_function

def require_permission(permission: str):
    """
    Decorator to require specific permission for API endpoints.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(client_info=None, *args, **kwargs):
            if not client_info:
                abort(401, {'error': 'Authentication required'})
            
            permissions = client_info.get('permissions', [])
            if permission not in permissions and 'all' not in permissions:
                logger.warning(f"Permission denied for {permission}")
                abort(403, {'error': f'Permission denied: {permission} required'})
            
            return f(client_info=client_info, *args, **kwargs)
        return decorated_function
    return decorator

def get_client_info_from_request() -> Optional[Dict[str, Any]]:
    """
    Extract client information from request headers.
    Supports both HMAC and JWT authentication.
    
    Returns:
        dict: Client information if authenticated, None otherwise
    """
    try:
        # Try JWT first
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            return verify_jwt_token(token)
        
        # Try HMAC
        return verify_hmac_signature()
    except:
        return None
