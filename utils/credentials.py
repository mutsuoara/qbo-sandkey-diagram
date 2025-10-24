"""
Credential management using keyring for secure storage
"""

import keyring
import json
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class CredentialManager:
    """Manages secure storage of credentials using keyring"""
    
    def __init__(self):
        self.service_name = "qbo_sankey_dashboard"
        self.credentials_key = "qbo_credentials"
        self.tokens_key = "qbo_tokens"
    
    def store_credentials(self, credentials: Dict[str, str]) -> bool:
        """Store credentials securely using keyring"""
        try:
            # Validate required fields
            required_fields = ['client_id', 'client_secret', 'environment']
            for field in required_fields:
                if field not in credentials:
                    logger.error(f"Missing required credential field: {field}")
                    return False
            
            # Store credentials as JSON string
            credentials_json = json.dumps(credentials)
            keyring.set_password(self.service_name, self.credentials_key, credentials_json)
            logger.info("Credentials stored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False
    
    def get_credentials(self) -> Optional[Dict[str, str]]:
        """Retrieve stored credentials"""
        try:
            # First try keyring
            credentials_json = keyring.get_password(self.service_name, self.credentials_key)
            if credentials_json:
                return json.loads(credentials_json)
            
            # Fallback: check for temporary file
            import os
            if os.path.exists('temp_credentials.json'):
                with open('temp_credentials.json', 'r') as f:
                    temp_creds = json.load(f)
                logger.info("Using temporary credentials file")
                return temp_creds
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            return None
    
    def clear_credentials(self) -> bool:
        """Clear stored credentials"""
        try:
            keyring.delete_password(self.service_name, self.credentials_key)
            logger.info("Credentials cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear credentials: {e}")
            return False
    
    def has_credentials(self) -> bool:
        """Check if credentials are stored"""
        try:
            # First try keyring
            credentials = self.get_credentials()
            if credentials:
                return True
            
            # Fallback: check for temporary file
            import os
            import json
            if os.path.exists('temp_credentials.json'):
                with open('temp_credentials.json', 'r') as f:
                    temp_creds = json.load(f)
                if temp_creds:
                    logger.info("Found temporary credentials file")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check credentials: {e}")
            return False
    
    def store_token(self, access_token: str, refresh_token: str, realm_id: str) -> bool:
        """Store OAuth tokens and realm ID"""
        try:
            # Store tokens as JSON
            tokens = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'realm_id': realm_id
            }
            tokens_json = json.dumps(tokens)
            keyring.set_password(self.service_name, self.tokens_key, tokens_json)
            logger.info("OAuth tokens stored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store tokens: {e}")
            return False
    
    def get_token(self, token_name: str) -> Optional[str]:
        """Retrieve individual token"""
        try:
            tokens_json = keyring.get_password(self.service_name, self.tokens_key)
            if tokens_json:
                tokens = json.loads(tokens_json)
                return tokens.get(token_name)
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve token {token_name}: {e}")
            return None
    
    def get_tokens(self) -> Optional[Dict[str, str]]:
        """Retrieve all stored tokens"""
        try:
            tokens_json = keyring.get_password(self.service_name, self.tokens_key)
            if tokens_json:
                return json.loads(tokens_json)
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve tokens: {e}")
            return None
    
    def store_company_info(self, company_info: Dict[str, Any]) -> bool:
        """Store company information"""
        try:
            company_json = json.dumps(company_info)
            keyring.set_password(self.service_name, "company_info", company_json)
            logger.info("Company info stored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store company info: {e}")
            return False
    
    def get_company_info(self) -> Optional[Dict[str, Any]]:
        """Retrieve company information"""
        try:
            company_json = keyring.get_password(self.service_name, "company_info")
            if company_json:
                return json.loads(company_json)
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve company info: {e}")
            return None
    
    def clear_tokens(self) -> bool:
        """Clear all stored tokens"""
        try:
            # Clear the main tokens JSON object
            try:
                keyring.delete_password(self.service_name, self.tokens_key)
            except:
                pass  # Tokens might not exist
            
            # Clear company info separately
            try:
                keyring.delete_password(self.service_name, "company_info")
            except:
                pass  # Company info might not exist
            
            logger.info("All tokens cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear tokens: {e}")
            return False
