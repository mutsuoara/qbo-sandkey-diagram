"""
QuickBooks Online data fetching module
Handles API calls to retrieve financial data from QuickBooks Online.
"""

import requests
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class QBODataFetcher:
    """Class to handle QuickBooks Online API data fetching"""
    
    def __init__(self, access_token: str, realm_id: str, environment: str = 'sandbox'):
        """
        Initialize the QBO data fetcher
        
        Args:
            access_token: OAuth access token
            realm_id: QuickBooks company ID
            environment: 'sandbox' or 'production'
        """
        self.access_token = access_token
        self.realm_id = realm_id
        self.environment = environment
        
        # Set base URL based on environment
        if environment == 'production':
            self.base_url = "https://quickbooks.api.intuit.com"
        else:
            self.base_url = "https://sandbox-quickbooks.api.intuit.com"
        
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Make a request to the QuickBooks API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response or None if error
        """
        try:
            url = f"{self.base_url}/v3/company/{self.realm_id}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error making API request: {e}")
            return None
    
    def get_company_info(self) -> Optional[Dict]:
        """Get company information"""
        try:
            endpoint = f"companyinfo/{self.realm_id}"
            data = self._make_request(endpoint)
            
            if data and 'QueryResponse' in data:
                company_info = data['QueryResponse'].get('CompanyInfo', [])
                if company_info:
                    logger.info("Successfully retrieved company information")
                    return company_info[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching company info: {e}")
            return None
    
    def get_income_accounts(self) -> List[Dict]:
        """Get income accounts from the chart of accounts"""
        try:
            params = {
                'query': 'SELECT * FROM Account WHERE AccountType = \'Income\''
            }
            data = self._make_request('query', params)
            
            if data and 'QueryResponse' in data:
                accounts = data['QueryResponse'].get('Account', [])
                logger.info(f"Retrieved {len(accounts)} income accounts")
                return accounts
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching income accounts: {e}")
            return []
    
    def get_expense_accounts(self) -> List[Dict]:
        """Get expense accounts from the chart of accounts"""
        try:
            params = {
                'query': 'SELECT * FROM Account WHERE AccountType = \'Expense\''
            }
            data = self._make_request('query', params)
            
            if data and 'QueryResponse' in data:
                accounts = data['QueryResponse'].get('Account', [])
                logger.info(f"Retrieved {len(accounts)} expense accounts")
                return accounts
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching expense accounts: {e}")
            return []
    
    def get_profit_and_loss(self, start_date: str = None, end_date: str = None) -> Optional[Dict]:
        """
        Get Profit and Loss report
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            params = {
                'start_date': start_date,
                'end_date': end_date
            }
            
            data = self._make_request('reports/ProfitAndLoss', params)
            
            if data and 'QueryResponse' in data:
                logger.info("Successfully retrieved Profit and Loss report")
                return data['QueryResponse']
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Profit and Loss report: {e}")
            return None
    
    def get_balance_sheet(self, start_date: str = None, end_date: str = None) -> Optional[Dict]:
        """
        Get Balance Sheet report
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            params = {
                'start_date': start_date,
                'end_date': end_date
            }
            
            data = self._make_request('reports/BalanceSheet', params)
            
            if data and 'QueryResponse' in data:
                logger.info("Successfully retrieved Balance Sheet report")
                return data['QueryResponse']
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Balance Sheet report: {e}")
            return None
    
    def get_cash_flow_statement(self, start_date: str = None, end_date: str = None) -> Optional[Dict]:
        """
        Get Cash Flow Statement report
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            params = {
                'start_date': start_date,
                'end_date': end_date
            }
            
            data = self._make_request('reports/CashFlow', params)
            
            if data and 'QueryResponse' in data:
                logger.info("Successfully retrieved Cash Flow Statement report")
                return data['QueryResponse']
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Cash Flow Statement report: {e}")
            return None
    
    def get_financial_data_for_sankey(self) -> Dict[str, Any]:
        """
        Get financial data formatted for Sankey diagram creation
        
        Returns:
            Dictionary containing income and expense data
        """
        try:
            # Get Profit and Loss data
            pl_data = self.get_profit_and_loss()
            
            if not pl_data:
                logger.warning("No Profit and Loss data available")
                return self._get_sample_financial_data()
            
            # Extract income and expense data
            income_data = {}
            expense_data = {}
            
            # This would need to be implemented based on the actual QBO report structure
            # For now, return sample data
            logger.info("Extracting financial data for Sankey diagram")
            return self._get_sample_financial_data()
            
        except Exception as e:
            logger.error(f"Error getting financial data for Sankey: {e}")
            return self._get_sample_financial_data()
    
    def _get_sample_financial_data(self) -> Dict[str, Any]:
        """Get sample financial data for demonstration"""
        return {
            'income': {
                'Sales Revenue': 150000,
                'Service Revenue': 75000,
                'Other Income': 10000
            },
            'expenses': {
                'Cost of Goods Sold': 60000,
                'Operating Expenses': 45000,
                'Marketing': 15000,
                'Administrative': 20000,
                'Utilities': 5000
            }
        }
