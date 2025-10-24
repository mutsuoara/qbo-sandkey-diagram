"""
Security Configuration for QBO Sankey Dashboard
Handles JWT secrets, client credentials, and security settings
"""

import os
import json
import secrets
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def generate_jwt_secret() -> str:
    """Generate a secure JWT secret"""
    return secrets.token_urlsafe(32)

def get_default_clients() -> Dict[str, Any]:
    """Get default client configuration"""
    return {
        "demo_client": {
            "api_key": "demo_api_key_12345",
            "api_secret": "demo_secret_67890",
            "name": "Demo Client",
            "permissions": ["read_company", "read_financial_data", "read_reports"]
        },
        "admin_client": {
            "api_key": "admin_api_key_54321",
            "api_secret": "admin_secret_09876",
            "name": "Admin Client",
            "permissions": ["all"]
        }
    }

def setup_security_environment():
    """Set up security environment variables"""
    # Generate JWT secret if not set
    if not os.environ.get('JWT_SECRET'):
        jwt_secret = generate_jwt_secret()
        os.environ['JWT_SECRET'] = jwt_secret
        logger.info("Generated new JWT secret")
    
    # Set up client credentials if not set
    if not os.environ.get('API_CLIENTS'):
        clients = get_default_clients()
        os.environ['API_CLIENTS'] = json.dumps(clients)
        logger.info("Set up default client credentials")
    
    logger.info("Security environment configured")

def get_security_config() -> Dict[str, Any]:
    """Get current security configuration"""
    return {
        'jwt_secret_configured': bool(os.environ.get('JWT_SECRET')),
        'clients_configured': bool(os.environ.get('API_CLIENTS')),
        'num_clients': len(json.loads(os.environ.get('API_CLIENTS', '{}'))),
        'jwt_expiry': 3600,  # 1 hour
        'request_timeout': 300  # 5 minutes
    }

def add_client(api_key: str, api_secret: str, name: str, permissions: list) -> bool:
    """Add a new client to the configuration"""
    try:
        clients = json.loads(os.environ.get('API_CLIENTS', '{}'))
        client_id = f"client_{len(clients) + 1}"
        
        clients[client_id] = {
            "api_key": api_key,
            "api_secret": api_secret,
            "name": name,
            "permissions": permissions
        }
        
        os.environ['API_CLIENTS'] = json.dumps(clients)
        logger.info(f"Added new client: {name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add client: {e}")
        return False

def remove_client(client_id: str) -> bool:
    """Remove a client from the configuration"""
    try:
        clients = json.loads(os.environ.get('API_CLIENTS', '{}'))
        
        if client_id in clients:
            del clients[client_id]
            os.environ['API_CLIENTS'] = json.dumps(clients)
            logger.info(f"Removed client: {client_id}")
            return True
        else:
            logger.warning(f"Client not found: {client_id}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to remove client: {e}")
        return False

def list_clients() -> Dict[str, Any]:
    """List all configured clients (without secrets)"""
    try:
        clients = json.loads(os.environ.get('API_CLIENTS', '{}'))
        
        safe_clients = {}
        for client_id, client_data in clients.items():
            safe_clients[client_id] = {
                "name": client_data.get("name", "Unknown"),
                "api_key": client_data.get("api_key", ""),
                "permissions": client_data.get("permissions", []),
                "has_secret": bool(client_data.get("api_secret"))
            }
        
        return safe_clients
        
    except Exception as e:
        logger.error(f"Failed to list clients: {e}")
        return {}

# Initialize security environment on import
setup_security_environment()
