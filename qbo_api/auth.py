"""
QuickBooks Online OAuth 2.0 authentication and token management
"""

import requests
import json
import logging
from typing import Dict, Optional, Any
from urllib.parse import urlencode, parse_qs
import webbrowser
from utils.credentials import CredentialManager

logger = logging.getLogger(__name__)

class QBOAuth:
    """Handles OAuth 2.0 authentication with QuickBooks Online"""
    
    def __init__(self):
        self.credential_manager = CredentialManager()
        self.credentials = None
        self.access_token = None
        self.refresh_token = None
        self.realm_id = None
        self.company_info = None
        
        # Load credentials
        self._load_credentials()
    
    def _load_credentials(self):
        """Load stored credentials"""
        try:
            self.credentials = self.credential_manager.get_credentials()
            if not self.credentials:
                logger.warning("No credentials found")
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
    
    def initialize_auth_client(self) -> bool:
        """Initialize OAuth client with stored credentials"""
        if not self.credentials:
            logger.error("No credentials available")
            return False
        
        try:
            # Validate credentials
            required_fields = ['client_id', 'client_secret', 'environment']
            for field in required_fields:
                if field not in self.credentials:
                    logger.error(f"Missing credential field: {field}")
                    return False
            
            logger.info("OAuth client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OAuth client: {e}")
            return False
    
    def get_authorization_url(self) -> str:
        """Generate OAuth authorization URL"""
        if not self.credentials:
            raise Exception("No credentials available")
        
        try:
            # OAuth 2.0 parameters
            params = {
                'client_id': self.credentials['client_id'],
                'scope': 'com.intuit.quickbooks.accounting',
                'redirect_uri': 'http://localhost:8050/callback',
                'response_type': 'code',
                'access_type': 'offline'
            }
            
            # Build authorization URL
            base_url = "https://appcenter.intuit.com/connect/oauth2"
            auth_url = f"{base_url}?{urlencode(params)}"
            
            logger.info("Generated authorization URL")
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise
    
    def start_oauth_flow(self) -> str:
        """Start OAuth flow and return authorization URL"""
        if not self.initialize_auth_client():
            raise Exception("Failed to initialize OAuth client")
        
        auth_url = self.get_authorization_url()
        
        # Open browser for authorization
        try:
            webbrowser.open(auth_url)
            logger.info("Opened browser for OAuth authorization")
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")
        
        return auth_url
    
    def handle_callback(self, code: str, realm_id: str) -> bool:
        """Handle OAuth callback and exchange code for tokens"""
        if not self.credentials:
            raise Exception("No credentials available")
        
        try:
            # Prepare token request
            token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
            
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': 'http://localhost:8050/callback'
            }
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Make token request
            response = requests.post(
                token_url,
                data=data,
                headers=headers,
                auth=(self.credentials['client_id'], self.credentials['client_secret'])
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Store tokens
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.realm_id = realm_id
                
                # Store tokens securely
                self._store_tokens(token_data, realm_id)
                
                # Fetch company info
                self.company_info = self._fetch_company_info()
                
                logger.info("OAuth callback handled successfully")
                return True
            else:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to handle OAuth callback: {e}")
            return False
    
    def _store_tokens(self, token_data: Dict[str, Any], realm_id: str):
        """Store tokens securely"""
        try:
            # Store individual tokens
            self.credential_manager.store_token('access_token', token_data.get('access_token', ''))
            self.credential_manager.store_token('refresh_token', token_data.get('refresh_token', ''))
            self.credential_manager.store_token('realm_id', realm_id)
            
            logger.info("Tokens stored successfully")
            
        except Exception as e:
            logger.error(f"Failed to store tokens: {e}")
            raise
    
    def _fetch_company_info(self) -> Optional[Dict[str, Any]]:
        """Fetch company information from QBO API"""
        if not self.access_token or not self.realm_id:
            return None
        
        try:
            # Determine API base URL based on environment
            if self.credentials.get('environment') == 'production':
                base_url = "https://quickbooks.intuit.com"
            else:
                base_url = "https://sandbox-quickbooks.intuit.com"
            
            # Fetch company info
            company_url = f"{base_url}/v3/company/{self.realm_id}/companyinfo/{self.realm_id}"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(company_url, headers=headers)
            
            if response.status_code == 200:
                company_data = response.json()
                company_info = company_data.get('QueryResponse', {}).get('CompanyInfo', [{}])[0]
                
                # Store company info
                self.credential_manager.store_token('company_info', json.dumps(company_info))
                
                logger.info(f"Company info fetched: {company_info.get('CompanyName', 'Unknown')}")
                return company_info
            else:
                logger.error(f"Failed to fetch company info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch company info: {e}")
            return None
    
    def load_stored_tokens(self) -> bool:
        """Load stored tokens from keyring"""
        try:
            self.access_token = self.credential_manager.get_token('access_token')
            self.refresh_token = self.credential_manager.get_token('refresh_token')
            self.realm_id = self.credential_manager.get_token('realm_id')
            
            # Load company info
            company_info_json = self.credential_manager.get_token('company_info')
            if company_info_json:
                self.company_info = json.loads(company_info_json)
            
            if self.access_token and self.realm_id:
                logger.info("Stored tokens loaded successfully")
                return True
            else:
                logger.warning("No stored tokens found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load stored tokens: {e}")
            return False
    
    def refresh_access_token(self) -> bool:
        """Refresh access token using refresh token"""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
        
        try:
            token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(
                token_url,
                data=data,
                headers=headers,
                auth=(self.credentials['client_id'], self.credentials['client_secret'])
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                
                # Update stored access token
                self.credential_manager.store_token('access_token', self.access_token)
                
                logger.info("Access token refreshed successfully")
                return True
            else:
                logger.error(f"Token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.access_token is not None and self.realm_id is not None
    
    def get_company_info(self) -> Optional[Dict[str, Any]]:
        """Get company information"""
        return self.company_info
    
    def logout(self):
        """Logout and clear stored tokens"""
        try:
            self.credential_manager.clear_tokens()
            self.access_token = None
            self.refresh_token = None
            self.realm_id = None
            self.company_info = None
            
            logger.info("User logged out successfully")
            
        except Exception as e:
            logger.error(f"Failed to logout: {e}")
            raise

