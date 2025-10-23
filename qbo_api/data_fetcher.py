"""
QuickBooks Online API data fetching
"""

import requests
import logging
from typing import Dict, Optional, Any
from datetime import datetime, date
from utils.credentials import CredentialManager

logger = logging.getLogger(__name__)

class QBODataFetcher:
    """Handles data fetching from QuickBooks Online API"""
    
    def __init__(self):
        self.credential_manager = CredentialManager()
        self.credentials = None
        self.access_token = None
        self.realm_id = None
        self.base_url = None
        
        # Load credentials and tokens
        self._load_credentials()
        self._load_tokens()
    
    def _load_credentials(self):
        """Load stored credentials"""
        try:
            self.credentials = self.credential_manager.get_credentials()
            if not self.credentials:
                logger.warning("No credentials found")
                return
            
            # Set base URL based on environment
            if self.credentials.get('environment') == 'production':
                self.base_url = "https://quickbooks.intuit.com"
            else:
                self.base_url = "https://sandbox-quickbooks.intuit.com"
                
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
    
    def _load_tokens(self):
        """Load stored tokens"""
        try:
            self.access_token = self.credential_manager.get_token('access_token')
            self.realm_id = self.credential_manager.get_token('realm_id')
            
            if self.access_token and self.realm_id:
                logger.info("Tokens loaded successfully")
            else:
                logger.warning("No tokens found")
                
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
    
    def get_company_info(self) -> Optional[Dict[str, Any]]:
        """Get company information"""
        if not self._validate_auth():
            return None
        
        try:
            company_url = f"{self.base_url}/v3/company/{self.realm_id}/companyinfo/{self.realm_id}"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(company_url, headers=headers)
            
            if response.status_code == 200:
                company_data = response.json()
                company_info = company_data.get('QueryResponse', {}).get('CompanyInfo', [{}])[0]
                logger.info(f"Company info retrieved: {company_info.get('CompanyName', 'Unknown')}")
                return company_info
            else:
                logger.error(f"Failed to get company info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get company info: {e}")
            return None
    
    def fetch_profit_loss_report(self, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """Fetch Profit & Loss report from QBO API"""
        if not self._validate_auth():
            return None
        
        try:
            # Format dates for QBO API
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Build report URL
            report_url = f"{self.base_url}/v3/company/{self.realm_id}/reports/ProfitAndLoss"
            
            # Query parameters
            params = {
                'start_date': start_date_obj.strftime('%Y-%m-%d'),
                'end_date': end_date_obj.strftime('%Y-%m-%d')
            }
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }
            
            logger.info(f"Fetching P&L report from {start_date} to {end_date}")
            
            response = requests.get(report_url, params=params, headers=headers)
            
            if response.status_code == 200:
                report_data = response.json()
                logger.info("P&L report fetched successfully")
                return report_data
            else:
                logger.error(f"Failed to fetch P&L report: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch P&L report: {e}")
            return None
    
    def validate_report_data(self, report_data: Dict[str, Any]) -> bool:
        """Validate report data structure"""
        try:
            if not report_data:
                logger.warning("No report data provided")
                return False
            
            # Check for required structure
            if 'QueryResponse' not in report_data:
                logger.warning("Invalid report structure: missing QueryResponse")
                return False
            
            query_response = report_data['QueryResponse']
            if 'Report' not in query_response:
                logger.warning("Invalid report structure: missing Report")
                return False
            
            report = query_response['Report']
            if 'Rows' not in report:
                logger.warning("Invalid report structure: missing Rows")
                return False
            
            logger.info("Report data structure validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate report data: {e}")
            return False
    
    def _validate_auth(self) -> bool:
        """Validate authentication status"""
        if not self.access_token or not self.realm_id:
            logger.error("Not authenticated: missing access token or realm ID")
            return False
        
        if not self.base_url:
            logger.error("Not authenticated: missing base URL")
            return False
        
        return True
    
    def test_connection(self) -> bool:
        """Test connection to QBO API"""
        try:
            company_info = self.get_company_info()
            return company_info is not None
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

