"""
QuickBooks Online data fetching module
Handles API calls to retrieve financial data from QuickBooks Online.
"""

import requests
import logging
import re
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
    
    def _make_request(self, endpoint: str, params: Dict = None, retry_on_auth_error: bool = True) -> Optional[Dict]:
        """
        Make a request to the QuickBooks API with automatic token refresh
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            retry_on_auth_error: Whether to retry after token refresh on 401/403
            
        Returns:
            JSON response or None if error
        """
        try:
            url = f"{self.base_url}/v3/company/{self.realm_id}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for Fault objects in successful responses
                if 'Fault' in data:
                    fault = data.get('Fault', {})
                    errors = fault.get('Error', [])
                    if errors:
                        error = errors[0]
                        error_msg = error.get('Message', 'Unknown error')
                        error_detail = error.get('Detail', '')
                        error_code = error.get('code', '')
                        logger.error(f"QuickBooks API Fault [{error_code}]: {error_msg}")
                        if error_detail:
                            logger.error(f"Fault detail: {error_detail}")
                    else:
                        logger.error(f"QuickBooks API Fault: {fault}")
                    return None
                
                return data
            elif response.status_code in [401, 403] and retry_on_auth_error:
                # Token expired, try to refresh and retry
                logger.warning(f"Authentication failed ({response.status_code}), attempting token refresh...")
                
                if self._refresh_token_and_retry(endpoint, params):
                    # Retry the request with new token
                    return self._make_request(endpoint, params, retry_on_auth_error=False)
                else:
                    logger.error("Token refresh failed, authentication required")
                    return None
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error making API request: {e}")
            return None
    
    def _refresh_token_and_retry(self, endpoint: str, params: Dict = None) -> bool:
        """
        Refresh access token and update headers
        
        Returns:
            True if token refresh successful, False otherwise
        """
        try:
            from utils.credentials import CredentialManager
            
            # Get credential manager and attempt token refresh
            credential_manager = CredentialManager()
            if credential_manager.refresh_access_token():
                # Get updated tokens
                tokens = credential_manager.get_tokens()
                if tokens and 'access_token' in tokens:
                    # Update the access token in this instance
                    self.access_token = tokens['access_token']
                    self.headers['Authorization'] = f'Bearer {self.access_token}'
                    logger.info("Token refreshed successfully, retrying request...")
                    return True
                else:
                    logger.error("Failed to get updated tokens after refresh")
                    return False
            else:
                logger.error("Token refresh failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during token refresh: {e}")
            return False
    
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
            
            logger.info(f"Fetching Profit & Loss report: {start_date} to {end_date}")
            logger.info("Using standard P&L format (income grouped by account, not by customer)")
            
            params = {
                'start_date': start_date,
                'end_date': end_date
            }
            
            data = self._make_request('reports/ProfitAndLoss', params)
            
            if data:
                logger.info("Successfully retrieved Profit and Loss report (standard format)")
                # Log the structure for debugging
                logger.info(f"P&L Report keys: {list(data.keys())}")
                if 'Rows' in data:
                    rows = data['Rows']
                    logger.info(f"Number of rows: {len(rows) if isinstance(rows, list) else 'Not a list'}")
                    logger.info(f"Rows type: {type(rows)}")
                    
                    # Only try to slice if it's actually a list
                    if isinstance(rows, list) and len(rows) > 0:
                        # Log first few rows for debugging (handle case where there might be only 1 row)
                        rows_to_log = rows[:min(3, len(rows))]
                        for i, row in enumerate(rows_to_log):
                            logger.info(f"Row {i} structure: {list(row.keys()) if isinstance(row, dict) else type(row)}")
                    else:
                        logger.warning(f"Rows is not a list or is empty: {rows}")
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Profit and Loss report: {e}")
            return None

    def get_income_by_project(self, start_date: str = None, end_date: str = None) -> Dict[str, float]:
        """
        Get income grouped by project (QuickBooks Jobs/Sub-customers)
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary mapping project names to income amounts
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Fetching income by project: {start_date} to {end_date}")
            
            # Query for paid invoices in date range
            # Note: We're looking for invoices where Balance = 0 (fully paid)
            query = (
                f"SELECT * FROM Invoice "
                f"WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' "
                f"MAXRESULTS 1000"
            )
            
            params = {
                'query': query,
                'minorversion': '65'
            }
            
            data = self._make_request('query', params)
            
            if not data or 'QueryResponse' not in data:
                logger.warning("No invoice data returned from query")
                return {}
            
            # Group income by project
            project_income = {}
            invoices = data['QueryResponse'].get('Invoice', [])
            
            logger.info(f"Processing {len(invoices)} invoices")
            
            for invoice in invoices:
                # Get customer/project reference
                customer_ref = invoice.get('CustomerRef', {})
                project_name = customer_ref.get('name', 'Unknown Project')
                
                # Get invoice total
                total_amt = float(invoice.get('TotalAmt', 0))
                
                # Debug: Log customer names to help identify project grouping issues
                if 'A6' in project_name:
                    logger.info(f"🔍 A6 PROJECT FOUND: '{project_name}' (Customer ID: {customer_ref.get('value', 'N/A')})")
                    logger.info(f"🔍 A6 TRANSACTION: Amount=${total_amt:,.2f}, TxnType='{invoice.get('TxnType', 'N/A')}', DocNumber='{invoice.get('DocNumber', 'N/A')}', TxnDate='{invoice.get('TxnDate', 'N/A')}'")
                
                # Debug: Log negative transactions to identify credits/refunds
                if total_amt < 0:
                    logger.info(f"⚠️ NEGATIVE TRANSACTION: '{project_name}' = ${total_amt:,.2f} (Invoice ID: {invoice.get('Id', 'N/A')})")
                    
                    # Log more details about the transaction for debugging
                    logger.info(f"🔍 TRANSACTION DETAILS: TxnType='{invoice.get('TxnType', 'N/A')}', DocNumber='{invoice.get('DocNumber', 'N/A')}', TxnDate='{invoice.get('TxnDate', 'N/A')}'")
                    
                    # Special logging for the specific $25,134.83 amount
                    if abs(total_amt) == 25134.83 or abs(total_amt) == 25134.84:
                        logger.info(f"🎯 FOUND TARGET AMOUNT: ${total_amt:,.2f} - This is the journal entry we're looking for!")
                    
                    # Check if this is a journal entry (transfer between projects)
                    # Journal entries often have negative amounts but represent positive transfers
                    invoice_type = invoice.get('TxnType', '')
                    doc_number = invoice.get('DocNumber', '').lower()
                    
                    # More comprehensive journal entry detection
                    is_journal_entry = (
                        invoice_type == 'JournalEntry' or 
                        'journal' in doc_number or
                        'je' in doc_number or
                        'transfer' in doc_number or
                        'adjustment' in doc_number
                    )
                    
                    if is_journal_entry:
                        logger.info(f"📝 JOURNAL ENTRY DETECTED: Treating negative amount as positive transfer")
                        logger.info(f"📝 BEFORE CONVERSION: ${total_amt:,.2f}")
                        total_amt = abs(total_amt)  # Convert to positive
                        logger.info(f"📝 AFTER CONVERSION: ${total_amt:,.2f}")
                    else:
                        # Skip actual credits/refunds
                        logger.info(f"💳 CREDIT/REFUND: Skipping negative transaction")
                        continue
                
                # Skip zero-amount invoices
                if total_amt <= 0:
                    continue
                
                # Add to project income
                if project_name in project_income:
                    project_income[project_name] += total_amt
                    logger.info(f"💰 ADDED TO EXISTING PROJECT: {project_name} += ${total_amt:,.2f} (Total: ${project_income[project_name]:,.2f})")
                else:
                    project_income[project_name] = total_amt
                    logger.info(f"💰 CREATED NEW PROJECT: {project_name} = ${total_amt:,.2f}")
                
                # Special logging for A6 Enterprise Services
                if 'A6 Enterprise Services' in project_name:
                    logger.info(f"🏢 A6 ENTERPRISE SERVICES UPDATE: Total now = ${project_income[project_name]:,.2f}")
            
            logger.info(f"Retrieved income from {len(project_income)} projects")
            
            # Debug: Log all project names and amounts
            logger.info("="*60)
            logger.info("PROJECT INCOME BREAKDOWN:")
            for project_name, amount in project_income.items():
                logger.info(f"  📊 {project_name}: ${amount:,.2f}")
            logger.info("="*60)
            logger.info(f"Total income: ${sum(project_income.values()):,.2f}")
            
            # Log top 5 projects for debugging
            sorted_projects = sorted(project_income.items(), key=lambda x: x[1], reverse=True)
            logger.info("Top 5 projects by income:")
            for project, amount in sorted_projects[:5]:
                logger.info(f"  - {project}: ${amount:,.2f}")
            
            return project_income
            
        except Exception as e:
            logger.error(f"Error fetching income by project: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def get_sales_receipts_by_project(self, start_date: str = None, end_date: str = None) -> Dict[str, float]:
        """
        Get cash sales grouped by project from SalesReceipt entities
        (for businesses that use sales receipts instead of invoices)
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary mapping project names to sales receipt amounts
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Fetching sales receipts by project: {start_date} to {end_date}")
            
            # Query for sales receipts in date range
            query = (
                f"SELECT * FROM SalesReceipt "
                f"WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' "
                f"MAXRESULTS 1000"
            )
            
            params = {
                'query': query,
                'minorversion': '65'
            }
            
            data = self._make_request('query', params)
            
            if not data or 'QueryResponse' not in data:
                logger.info("No sales receipt data returned")
                return {}
            
            # Group by project
            project_income = {}
            receipts = data['QueryResponse'].get('SalesReceipt', [])
            
            logger.info(f"Processing {len(receipts)} sales receipts")
            
            for receipt in receipts:
                # Get customer/project reference
                customer_ref = receipt.get('CustomerRef', {})
                project_name = customer_ref.get('name', 'Unknown Project')
                
                # Get receipt total
                total_amt = float(receipt.get('TotalAmt', 0))
                
                # Handle negative amounts (journal entries, credits, refunds)
                if total_amt < 0:
                    # Check if this is a journal entry (transfer between projects)
                    receipt_type = receipt.get('TxnType', '')
                    if receipt_type == 'JournalEntry' or 'journal' in receipt.get('DocNumber', '').lower():
                        logger.info(f"📝 JOURNAL ENTRY DETECTED in sales receipts: Treating negative amount as positive transfer")
                        total_amt = abs(total_amt)  # Convert to positive
                    else:
                        # Skip actual credits/refunds
                        continue
                
                if total_amt <= 0:
                    continue
                
                # Add to project income
                if project_name in project_income:
                    project_income[project_name] += total_amt
                else:
                    project_income[project_name] = total_amt
            
            logger.info(f"Retrieved sales receipts from {len(project_income)} projects")
            
            # Debug: Log all sales receipt project names and amounts
            logger.info("="*60)
            logger.info("SALES RECEIPT PROJECT BREAKDOWN:")
            for project_name, amount in project_income.items():
                logger.info(f"  💳 {project_name}: ${amount:,.2f}")
            logger.info("="*60)
            return project_income
            
        except Exception as e:
            logger.error(f"Error fetching sales receipts by project: {e}")
            return {}
    
    def get_journal_entries_by_project(self, start_date: str = None, end_date: str = None) -> Dict[str, float]:
        """
        Get journal entries that affect project income by parsing descriptions
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary mapping project names to journal entry adjustment amounts
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Fetching journal entries: {start_date} to {end_date}")
            
            query = (
                f"SELECT * FROM JournalEntry "
                f"WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' "
                f"MAXRESULTS 1000"
            )
            
            params = {'query': query, 'minorversion': '65'}
            data = self._make_request('query', params)
            
            if not data or 'QueryResponse' not in data:
                logger.info("No journal entry data returned")
                return {}
            
            project_adjustments = {}
            entries = data['QueryResponse'].get('JournalEntry', [])
            
            logger.info(f"Processing {len(entries)} journal entries")
            
            # Define project names to search for (add all your project names here)
            project_keywords = [
                'A6 Enterprise Services',
                'A6 Surge Support',
                'A6 DHO',
                'A6 Financial Management',
                'A6 CIE',
                'A6 Cross Benefits',
                'A6 CHAMPVA',
                'A6 Toxic Exposure',
                'A6 VA Form Engine',
                'CDSP',
                'TWS FLRA',
                'Perigean',
                'DMVA'
            ]
                    
            for entry in entries:
                entry_number = entry.get('DocNumber', 'N/A')
                txn_date = entry.get('TxnDate', 'N/A')
                
                # Process Line items to find project references in Entity names
                lines = entry.get('Line', [])
                
                # Track credits and debits per project in this entry
                entry_project_amounts = {}
                
                for line in lines:
                    # **LOOK IN ENTITY NAME, NOT DESCRIPTION**
                    entity = line.get('Entity', {})
                    entity_ref = entity.get('EntityRef', {})
                    entity_name = entity_ref.get('name', '').lower()  # This is "Agile Six Applications Inc:A6 Enterprise Services"
                    
                    amount = float(line.get('Amount', 0))
                    
                    # Get posting type
                    journal_detail = line.get('JournalEntryLineDetail', {})
                    posting_type = journal_detail.get('PostingType', '')
                    account_ref = journal_detail.get('AccountRef', {})
                    account_name = account_ref.get('name', '')
                    
                    # Check if this is a Revenue/Income account
                    is_revenue_account = (
                        'revenue' in account_name.lower() or
                        'income' in account_name.lower() or
                        '4005' in account_name  # Your specific Revenue - Commercial account
                    )
                    
                    # Only process lines that affect revenue accounts AND have an entity name
                    if not is_revenue_account or not entity_name:
                        continue
                    
                    logger.info(f"🔍 JE #{entry_number}: Found entity '{entity_name}' - {posting_type} ${amount:,.2f} to {account_name}")
                    
                    # Search for project names in the entity name
                    for project_keyword in project_keywords:
                        if project_keyword.lower() in entity_name:
                            # Credits increase income, debits decrease income
                            if posting_type == 'Credit':
                                adjustment = amount
                            elif posting_type == 'Debit':
                                adjustment = -amount
                            else:
                                continue
                            
                            # Track this project's adjustment
                            if project_keyword not in entry_project_amounts:
                                entry_project_amounts[project_keyword] = 0
                            entry_project_amounts[project_keyword] += adjustment
                            
                            logger.info(f"📝 JE #{entry_number} ({txn_date}): '{project_keyword}' {posting_type} ${amount:,.2f} (adjustment: ${adjustment:,.2f})")
                            break  # Found a match, move to next line
                
                # Add all project adjustments from this entry
                for project, adjustment in entry_project_amounts.items():
                    if adjustment != 0:  # Only add non-zero adjustments
                        if project in project_adjustments:
                            project_adjustments[project] += adjustment
                        else:
                            project_adjustments[project] = adjustment
                        
                        logger.info(f"✅ JE #{entry_number}: {project} total adjustment = ${adjustment:,.2f} (Running total: ${project_adjustments[project]:,.2f})")

            return project_adjustments
            
        except Exception as e:
            logger.error(f"Error fetching journal entries: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def get_expenses_by_project(
        self,
        account_numbers: List[str],
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Get expenses for specific accounts broken down by project/customer
        
        Uses Profit and Loss Detail report grouped by customer to avoid duplication
        and match what's visible in QuickBooks "Profit and Loss by Customer" report.
        
        Args:
            account_numbers: List of account numbers to query (e.g., ['5001', '5011'])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            Dictionary mapping account names to project breakdowns:
            {
                '5001 Salaries & wages': {
                    'A6 Enterprise Services': 150000.00,
                    'A6 Surge Support': 100000.00,
                    ...
                },
                '5011 Direct 1099 Labor': {
                    'A6 Enterprise Services': 120000.00,
                    'TWS FLRA': 80000.00,
                    ...
                }
            }
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info("="*80)
            logger.info(f"FETCHING EXPENSES BY PROJECT")
            logger.info(f"Accounts: {account_numbers}")
            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info("="*80)
            
            # Fetch Profit and Loss Detail report grouped by customer
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'columns': 'customer',  # Group by customer/project
                'minorversion': '65'
            }
            
            data = self._make_request('reports/ProfitAndLossDetail', params)
            
            if not data:
                logger.warning("No P&L Detail by Customer data returned")
                return {}
            
            # Check for Fault objects
            if 'Fault' in data:
                logger.error("QuickBooks API returned a Fault object")
                logger.error(f"Fault details: {data.get('Fault', {})}")
                return {}
            
            # Log the top-level keys to understand the response structure
            logger.info(f"API Response keys: {list(data.keys())}")
            logger.info("Successfully retrieved Profit and Loss Detail by Customer report")
            
            # Parse report structure
            # The report structure will be similar to standard P&L but with customer grouping
            # Each row will have account name, customer name, and amount
            
            # Initialize result structure - use account names as keys, not just numbers
            expense_by_project = {}
            
            # Extract rows from report
            if 'Rows' not in data:
                logger.warning("No 'Rows' found in P&L Detail by Customer report")
                logger.warning(f"Available keys in response: {list(data.keys())}")
                # Try to log the full response structure for debugging (truncated)
                import json
                logger.debug(f"Response structure (first 2000 chars): {str(data)[:2000]}")
                return {}
            
            rows_data = data['Rows']
            if isinstance(rows_data, dict) and 'Row' in rows_data:
                rows = rows_data['Row']
                logger.info(f"Rows is dict with 'Row' key, found {len(rows) if isinstance(rows, list) else 1} rows")
            elif isinstance(rows_data, list):
                rows = rows_data
                logger.info(f"Rows is a list with {len(rows)} items")
            else:
                logger.error(f"Unexpected Rows structure: {type(rows_data)}")
                logger.error(f"Rows data: {str(rows_data)[:500]}")
                return {}
            
            logger.info(f"Processing {len(rows)} rows from P&L Detail by Customer report")
            
            # Log report header structure to see if customer info is in headers
            if 'Header' in data:
                logger.info(f"Report Header structure: {list(data['Header'].keys()) if isinstance(data['Header'], dict) else type(data['Header'])}")
                if isinstance(data['Header'], dict):
                    if 'ColData' in data['Header']:
                        logger.info(f"Report Header ColData: {data['Header']['ColData']}")
            
            # Log first few rows to understand structure
            if rows:
                logger.info(f"First row structure: {list(rows[0].keys()) if isinstance(rows[0], dict) else type(rows[0])}")
                if isinstance(rows[0], dict):
                    if 'Header' in rows[0]:
                        logger.info(f"First row Header ColData: {rows[0]['Header'].get('ColData', [])}")
                    if 'ColData' in rows[0]:
                        logger.info(f"First row ColData: {rows[0]['ColData']}")
            
            # Recursively process nested structure to find target accounts
            def process_nested_rows(rows_to_process, depth=0, parent_account_name=None, parent_customer_name=None):
                """
                Recursively navigate through nested Rows structure to find target accounts
                and extract transaction-level customer/project data
                
                Args:
                    rows_to_process: Rows to process
                    depth: Current nesting depth (0 = top level)
                    parent_account_name: Account name from parent section
                    parent_customer_name: Customer/Project name from parent section (e.g., "A6 Enterprise Services")
                """
                if not rows_to_process:
                    return
                
                # Extract rows list from various structures
                if isinstance(rows_to_process, dict) and 'Row' in rows_to_process:
                    rows_list = rows_to_process['Row']
                elif isinstance(rows_to_process, list):
                    rows_list = rows_to_process
                else:
                    return
                
                for row in rows_list:
                    if not isinstance(row, dict):
                        continue
                    
                    # Get section name from Header if present
                    section_name = None
                    if 'Header' in row:
                        header_col_data = row['Header'].get('ColData', [])
                        if header_col_data:
                            section_name = header_col_data[0].get('value', '').strip()
                    
                    # Log ALL sections encountered (for debugging) - use INFO level so we can see them
                    if section_name:
                        logger.info(f"  [Depth {depth}] Section encountered: '{section_name}' (type={row.get('type', 'unknown')})")
                    
                    # Extract account number if present
                    account_num = None
                    if section_name:
                        account_match = re.match(r'^(\d{4})', section_name)
                        if account_match:
                            account_num = account_match.group(1)
                    
                    # Check if this section looks like a customer/project name (not an account number or expense category)
                    # Customer/project names typically don't start with 4 digits and aren't common expense category names
                    current_customer_name = parent_customer_name
                    if section_name and not account_num:
                        # Common expense category names to exclude (not customer/project names)
                        expense_category_keywords = [
                            'cost of goods sold', 'cogs', 'expenses', 'income', 'revenue',
                            'ordinary income', 'ordinary expenses', 'other income', 'other expenses',
                            'gross profit', 'net income', 'operating income'
                        ]
                        
                        # Check if it looks like a project name (contains project indicators)
                        # Project indicators can appear anywhere in the name (e.g., "Agile Six Applications Inc.:A6 CIE")
                        project_indicators = ['a6', 'tws', 'cdsp', 'perigean', 'dmva']
                        is_expense_category = any(keyword in section_name.lower() for keyword in expense_category_keywords)
                        has_project_indicator = any(indicator in section_name.lower() for indicator in project_indicators)
                        
                        # Only treat as customer/project if it has project indicators and is NOT an expense category
                        # Remove depth restriction to capture project names at any depth
                        if has_project_indicator and not is_expense_category:
                            # Extract project name from customer name format (e.g., "Company:Project" -> "Project")
                            if ':' in section_name:
                                # Format: "Agile Six Applications Inc.:A6 CIE" -> extract "A6 CIE"
                                project_part = section_name.split(':')[-1].strip()
                                if project_part:
                                    current_customer_name = project_part
                                    logger.info(f"  Found customer/project section at depth {depth}: '{section_name}' -> extracted project: '{current_customer_name}'")
                                else:
                                    current_customer_name = section_name
                                    logger.info(f"  Found customer/project section at depth {depth}: {current_customer_name}")
                            else:
                                current_customer_name = section_name
                                logger.info(f"  Found customer/project section at depth {depth}: {current_customer_name}")
                        elif is_expense_category:
                            logger.info(f"  [Depth {depth}] Skipping expense category section: '{section_name}'")
                        else:
                            logger.info(f"  [Depth {depth}] Section doesn't match project criteria: '{section_name}' (has_account_num={bool(account_num)}, has_project_indicator={has_project_indicator}, is_expense_category={is_expense_category})")
                    
                    # Update account name if we found an account section
                    current_account_name = parent_account_name
                    if account_num:
                        current_account_name = section_name
                    
                    # Check if this is a target account section (5001 or 5011)
                    if account_num and account_num in account_numbers:
                        logger.info(f"Found target account section: {account_num} ({current_account_name}) at depth {depth}, parent customer: {current_customer_name}")
                        
                        # This is a target account - process its nested transaction rows
                        if 'Rows' in row:
                            transaction_rows = self._extract_rows(row['Rows'])
                            logger.info(f"  Processing {len(transaction_rows)} transaction rows for account {account_num}")
                            
                            for i, transaction_row in enumerate(transaction_rows):
                                if not isinstance(transaction_row, dict):
                                    continue
                                
                                # Transaction rows have ColData with customer/project info
                                if 'ColData' in transaction_row:
                                    col_data = transaction_row.get('ColData', [])
                                    
                                    # Log ColData structure for first few transactions (for debugging)
                                    if i < 3:
                                        logger.info(f"  Transaction {i} ColData structure:")
                                        for idx, col in enumerate(col_data):
                                            logger.info(f"    ColData[{idx}]: '{col.get('value', '')}'")
                                    
                                    # Get amount from index 7
                                    amount_str = col_data[7].get('value', '0').replace(',', '').replace('$', '').strip() if len(col_data) > 7 else '0'
                                    
                                    try:
                                        amount = float(amount_str) if amount_str else 0.0
                                    except ValueError:
                                        amount = 0.0
                                    
                                    # Skip if zero amount
                                    if amount == 0:
                                        continue
                                    
                                    # Use parent customer name if available, otherwise try to extract from ColData
                                    # The class/department code (like "02 Client Services") is in ColData[4] or ColData[3]
                                    # But we want the actual project name (like "A6 Enterprise Services") from parent sections
                                    project_name = current_customer_name
                                    
                                    # Normalize project name (extract from "Company:Project" format if present)
                                    if project_name and ':' in project_name:
                                        # Format: "Agile Six Applications Inc.:A6 CIE" -> extract "A6 CIE"
                                        project_name = project_name.split(':')[-1].strip()
                                    
                                    # Validate that we have a valid project name (not an expense category)
                                    if project_name:
                                        expense_category_keywords = [
                                            'cost of goods sold', 'cogs', 'expenses', 'income', 'revenue',
                                            'ordinary income', 'ordinary expenses', 'other income', 'other expenses',
                                            'gross profit', 'net income', 'operating income'
                                        ]
                                        if any(keyword in project_name.lower() for keyword in expense_category_keywords):
                                            logger.warning(f"  ⚠️ Invalid project name detected (expense category): {project_name}, skipping")
                                            project_name = None
                                    
                                    if not project_name:
                                        # Fallback: try to extract from ColData if no parent customer found
                                        # But this will likely be a class/department code, not a project name
                                        if len(col_data) >= 5:
                                            customer_name = col_data[4].get('value', '').strip() if len(col_data) > 4 else ''
                                            if not customer_name and len(col_data) > 3:
                                                customer_name = col_data[3].get('value', '').strip()
                                            
                                            # Normalize from "Company:Project" format if present
                                            if customer_name and ':' in customer_name:
                                                customer_name = customer_name.split(':')[-1].strip()
                                            
                                            # Only use if it looks like a project name (has project indicators)
                                            project_indicators = ['a6', 'tws', 'cdsp', 'perigean', 'dmva']
                                            if customer_name and any(indicator in customer_name.lower() for indicator in project_indicators):
                                                project_name = customer_name
                                                logger.debug(f"  Extracted project name from ColData: '{project_name}'")
                                            else:
                                                logger.debug(f"  ⚠️ ColData value '{customer_name}' doesn't look like a project name, skipping")
                                    
                                    if not project_name:
                                        logger.warning(f"  ⚠️ No valid project name found for transaction (parent_customer='{parent_customer_name}', current_customer='{current_customer_name}'), skipping")
                                        continue
                                    
                                    # Map account number to account name (handle renamed accounts)
                                    account_full_name = current_account_name
                                    if account_num == '5001' and 'salaries' in current_account_name.lower():
                                        account_full_name = "Billable Salaries and Wages"
                                    elif account_num == '5011':
                                        account_full_name = current_account_name  # Keep original name for 5011
                                    
                                    # Add to result
                                    if account_full_name not in expense_by_project:
                                        expense_by_project[account_full_name] = {}
                                    
                                    if project_name not in expense_by_project[account_full_name]:
                                        expense_by_project[account_full_name][project_name] = 0.0
                                    
                                    # Use absolute value (expenses are negative in P&L)
                                    expense_by_project[account_full_name][project_name] += abs(amount)
                                    
                                    logger.info(f"  📊 {account_full_name} → {project_name}: ${abs(amount):,.2f}")
                    
                    # Recursively process nested rows (continue searching deeper)
                    if 'Rows' in row:
                        process_nested_rows(row['Rows'], depth + 1, current_account_name, current_customer_name)
            
            # Start recursive processing from top-level rows
            process_nested_rows(rows)
            
            # Log summary
            logger.info("="*80)
            logger.info("EXPENSES BY PROJECT SUMMARY:")
            for account_name, projects in expense_by_project.items():
                if projects:
                    total = sum(projects.values())
                    logger.info(f"  {account_name}: {len(projects)} projects, Total: ${total:,.2f}")
                    for project_name, project_amount in sorted(projects.items(), key=lambda x: x[1], reverse=True)[:5]:
                        logger.info(f"    • {project_name}: ${project_amount:,.2f}")
            logger.info("="*80)
            
            return expense_by_project
            
        except Exception as e:
            logger.error(f"Error fetching expenses by project: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
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
    
    def get_financial_data_for_sankey(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Get financial data formatted for Sankey diagram creation
        Uses project-level income and account-level expenses
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing:
            - income: Dict mapping project names to income amounts
            - expenses: Dict mapping expense account names to amounts
            - metadata: Summary statistics
        """
        try:
            logger.info("="*60)
            logger.info("Getting financial data for Sankey diagram...")
            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info("="*60)
            
            # Get project-level income (from invoices)
            logger.info("Fetching project-level income from invoices...")
            try:
                invoice_income = self.get_income_by_project(start_date, end_date)
                logger.info(f"Invoice income fetch completed: {len(invoice_income)} projects")
            except Exception as e:
                logger.error(f"Error fetching invoice income: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                invoice_income = {} 
            
            # Get sales receipt income (if applicable)
            logger.info("Fetching project-level income from sales receipts...")
            try:
                receipt_income = self.get_sales_receipts_by_project(start_date, end_date)
                logger.info(f"Sales receipt income fetch completed: {len(receipt_income)} projects")
            except Exception as e:
                logger.error(f"Error fetching sales receipt income: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                receipt_income = {}

            # Get journal entry adjustments
            logger.info("Fetching journal entry adjustments...")
            try:
                journal_adjustments = self.get_journal_entries_by_project(start_date, end_date)
                logger.info(f"Journal entry adjustments fetch completed: {len(journal_adjustments)} projects")
            except Exception as e:
                logger.error(f"Error fetching journal entry adjustments: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                journal_adjustments = {}
            
            # Combine invoice and sales receipt income by project
            project_income = {}
            for project, amount in invoice_income.items():
                project_income[project] = amount
            
            for project, amount in receipt_income.items():
                if project in project_income:
                    project_income[project] += amount
                else:
                    project_income[project] = amount

            # Add journal entry adjustments
            for project, amount in journal_adjustments.items():
                if project in project_income:
                    project_income[project] += amount
                else:
                    project_income[project] = amount
            
            if not project_income:
                logger.warning("No project income data found - using P&L account-level data as fallback")
                # Fallback to P&L report for account-level income
                pl_data = self.get_profit_and_loss(start_date, end_date)
                if pl_data:
                    parsed_data = self._parse_profit_loss_report(pl_data)
                    if parsed_data:
                        project_income = parsed_data.get('income', {})
            
            # Get expense data from P&L report
            logger.info("Fetching expense data from P&L report...")
            pl_data = self.get_profit_and_loss(start_date, end_date)
            
            expense_categories = {}
            expense_hierarchy = {}
            if pl_data:
                parsed_data = self._parse_profit_loss_report(pl_data)
                if parsed_data:
                    expense_categories = parsed_data.get('expenses', {})
                    expense_hierarchy = parsed_data.get('expense_hierarchy', {})
            
            if not expense_categories:
                logger.warning("No expense data found")
            
            # PHASE 2: Integrate project-level expense data for accounts 5001 and 5011
            logger.info("="*80)
            logger.info("PHASE 2: INTEGRATING PROJECT-LEVEL EXPENSE DATA")
            logger.info("="*80)
            try:
                project_expenses = self.get_expenses_by_project(
                    ['5001', '5011'],
                    start_date,
                    end_date
                )
                
                if project_expenses:
                    logger.info(f"Retrieved project expenses for {len(project_expenses)} accounts")
                    
                    # Find and update secondary nodes in expense_hierarchy
                    for account_name, projects in project_expenses.items():
                        logger.info(f"Processing {account_name}: {len(projects)} projects")
                        
                        # Map renamed account names to possible original names in expense_hierarchy
                        # The hierarchical parser uses original names, but get_expenses_by_project returns renamed names
                        possible_names = [account_name]  # Try the returned name first
                        
                        # Add original name variations
                        if account_name == "Billable Salaries and Wages":
                            possible_names.extend(["5001 Salaries & wages", "5001 Salaries and Wages", "Salaries & wages"])
                        elif account_name == "5011 Direct 1099 Labor":
                            possible_names.extend(["5011 Direct 1099 Labor"])  # This one might match as-is
                        
                        # Find this account in the expense_hierarchy
                        # These accounts should be under "5000 COGS" primary
                        found = False
                        for primary_name, primary_data in expense_hierarchy.items():
                            if 'secondary' not in primary_data:
                                continue
                            
                            # Try each possible name
                            matching_secondary_name = None
                            for possible_name in possible_names:
                                if possible_name in primary_data['secondary']:
                                    matching_secondary_name = possible_name
                                    break
                            
                            if matching_secondary_name:
                                # Add projects data to this secondary node
                                secondary_data = primary_data['secondary'][matching_secondary_name]
                                secondary_data['projects'] = projects
                                logger.info(f"  ✅ Added project breakdown to {matching_secondary_name} under {primary_name}")
                                logger.info(f"     Projects: {list(projects.keys())}")
                                logger.info(f"     Total: ${sum(projects.values()):,.2f}")
                                found = True
                                break
                        
                        if not found:
                            logger.warning(f"  ⚠️ Could not find {account_name} in expense_hierarchy")
                            all_secondaries = [sec for prim in expense_hierarchy.values() for sec in prim.get('secondary', {}).keys()]
                            logger.warning(f"     Available secondaries: {all_secondaries}")
                            logger.warning(f"     Tried names: {possible_names}")
                else:
                    logger.warning("No project expenses retrieved")
                    
            except Exception as e:
                logger.error(f"Error integrating project-level expense data: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Continue even if project expense integration fails
            
            logger.info("="*80)
            logger.info("PHASE 2 COMPLETE")
            logger.info("="*80)
            
            # Calculate totals
            total_revenue = sum(project_income.values())
            total_expenses = sum(expense_categories.values())
            net_income = total_revenue - total_expenses
            
            logger.info("="*60)
            logger.info("Financial Data Summary:")
            logger.info(f"  Projects with income: {len(project_income)}")
            logger.info(f"  Expense categories: {len(expense_categories)}")
            logger.info(f"  Expense primaries: {len(expense_hierarchy)}")
            logger.info(f"  Total revenue: ${total_revenue:,.2f}")
            logger.info(f"  Total expenses: ${total_expenses:,.2f}")
            logger.info(f"  Net income: ${net_income:,.2f}")
            logger.info("="*60)
            
            return {
                'income': project_income,
                'expenses': expense_categories,  # Flattened for compatibility
                'expense_hierarchy': expense_hierarchy,  # Hierarchical structure for Sankey
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_income': net_income,
                'income_source_type': 'projects'  # Metadata for UI
            }
            
        except Exception as e:
            logger.error(f"Error getting financial data for Sankey: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Return empty data structure
            return {
                'income': {},
                'expenses': {},
                'total_revenue': 0,
                'total_expenses': 0,
                'net_income': 0,
                'income_source_type': 'none'
            }
    
    def _parse_profit_loss_report(self, pl_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Parse QuickBooks Profit & Loss report with hierarchical structure
        Tailored to actual QBO data structure with proper primary/secondary/tertiary detection
        """
        try:
            logger.info("="*80)
            logger.info("PARSING P&L REPORT WITH HIERARCHY")
            logger.info("="*80)
            
            income_sources = {}
            expense_hierarchy = {}
            
            if 'Rows' not in pl_data:
                logger.warning("No 'Rows' found in P&L data")
                return None
            
            # Extract rows
            rows_data = pl_data['Rows']
            if isinstance(rows_data, dict) and 'Row' in rows_data:
                rows = rows_data['Row']
            elif isinstance(rows_data, list):
                rows = rows_data
            else:
                logger.error(f"Unexpected Rows structure: {type(rows_data)}")
                return None
            
            logger.info(f"Processing {len(rows)} top-level rows")
            
            # Process each top-level section
            for row in rows:
                if not isinstance(row, dict):
                    continue
                
                # **SKIP "Other Expenses" GROUP - these are typically unallowable costs**
                if row.get('group') == 'OtherExpenses':
                    logger.info(f"Skipping 'Other Expenses' section (unallowable costs)")
                    continue
                
                section_type = self._get_section_type(row)
                logger.info(f"Processing section: {section_type}")
                
                if section_type == 'Income':
                    self._parse_income_section(row, income_sources)
                elif section_type in ['Cost of Goods Sold', 'Expenses']:
                    self._parse_expense_section(row, expense_hierarchy)
            
            # Calculate totals
            total_revenue = sum(income_sources.values())
            total_expenses = self._calculate_hierarchy_total(expense_hierarchy)
            net_income = total_revenue - total_expenses
            
            logger.info("="*80)
            logger.info(f"PARSING COMPLETE:")
            logger.info(f"  Income sources: {len(income_sources)}")
            logger.info(f"  Expense primaries: {len(expense_hierarchy)}")
            logger.info(f"  Total Revenue: ${total_revenue:,.2f}")
            logger.info(f"  Total Expenses: ${total_expenses:,.2f}")
            logger.info(f"  Net Income: ${net_income:,.2f}")
            logger.info("="*80)
            
            # Convert expense hierarchy to flat structure for compatibility with existing code
            expense_categories = {}
            for primary_name, primary_data in expense_hierarchy.items():
                # Add primary total if it has a direct amount
                if primary_data.get('total', 0) != 0:
                    expense_categories[primary_name] = primary_data['total']
                
                # Flatten secondaries and tertiaries
                for secondary_name, secondary_data in primary_data.get('secondary', {}).items():
                    if secondary_data.get('total', 0) != 0:
                        expense_categories[secondary_name] = secondary_data['total']
                    
                    # Add tertiaries
                    for tertiary_name, tertiary_amount in secondary_data.get('tertiary', {}).items():
                        if tertiary_amount != 0:
                            expense_categories[tertiary_name] = tertiary_amount
            
            return {
                'income': income_sources,
                'expenses': expense_categories,  # Flattened for compatibility
                'expense_hierarchy': expense_hierarchy,  # Hierarchical structure for testing
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_income': net_income
            }
            
        except Exception as e:
            logger.error(f"Error parsing P&L report: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _get_section_type(self, row: Dict) -> Optional[str]:
        """Get the type of top-level section (Income, COGS, Expenses, etc.)"""
        if 'Header' in row:
            col_data = row['Header'].get('ColData', [])
            if col_data:
                name = col_data[0].get('value', '').strip()
                return name
        return None
    
    def _parse_income_section(self, row: Dict, income_sources: Dict):
        """Parse the Income section"""
        if 'Rows' not in row:
            return
        
        rows = self._extract_rows(row['Rows'])
        
        for income_row in rows:
            name, amount = self._extract_row_data(income_row)
            if name and amount != 0:
                logger.info(f"  Income: {name} = ${amount:,.2f}")
                income_sources[name] = amount
    
    def _parse_expense_section(self, row: Dict, expense_hierarchy: Dict):
        """
        Parse expense sections (COGS, Expenses)
        
        Structure:
        - Level 1: Primary categories (5000 COGS, 6000 Fringe, etc.) - Sections with $0
        - Level 2: Secondary categories (5001, 6001, etc.) - Data rows with amounts
        - Level 3: Tertiary items (6205, 6253, etc.) - Data rows under nested Sections
        """
        if 'Rows' not in row:
            return
        
        rows = self._extract_rows(row['Rows'])
        
        for primary_row in rows:
            # Skip if not a row dict
            if not isinstance(primary_row, dict):
                continue
            
            # Check if this is a primary category (Section with account number ending in 000)
            if primary_row.get('type') == 'Section':
                primary_name, primary_amount = self._extract_row_data(primary_row)
                
                if not primary_name:
                    continue
                
                # Extract account number
                match = re.match(r'^(\d{4})', primary_name)
                account_num = match.group(1) if match else None
                
                # Check if it's a primary (ends in 000 or has nested rows)
                is_primary = (
                    (account_num and account_num.endswith('000')) or
                    ('Rows' in primary_row)
                )
                
                if is_primary:
                    logger.info(f"PRIMARY: {primary_name}")
                    
                    # Initialize primary
                    expense_hierarchy[primary_name] = {
                        'total': 0,  # Will calculate from children
                        'secondary': {}
                    }
                    
                    # Parse secondaries under this primary
                    if 'Rows' in primary_row:
                        self._parse_secondaries(
                            primary_row, 
                            primary_name,
                            expense_hierarchy[primary_name]
                        )
    
    def _parse_secondaries(self, primary_row: Dict, primary_name: str, primary_data: Dict):
        """Parse secondary categories under a primary"""
        rows = self._extract_rows(primary_row['Rows'])
        
        for secondary_row in rows:
            if not isinstance(secondary_row, dict):
                continue
            
            row_type = secondary_row.get('type', '')
            
            # Check if this is a nested Section (like 6200 Employee Benefits or 8500 GA Travel)
            if row_type == 'Section':
                # This is a secondary with potential tertiaries
                secondary_name, secondary_amount = self._extract_row_data(secondary_row)
                
                if not secondary_name:
                    continue
                
                logger.info(f"  SECONDARY (Section): {secondary_name}")
                
                # Initialize secondary
                primary_data['secondary'][secondary_name] = {
                    'total': 0,  # Will calculate from tertiaries
                    'tertiary': {}
                }
                
                # Parse tertiaries under this secondary
                if 'Rows' in secondary_row:
                    self._parse_tertiaries(
                        secondary_row,
                        secondary_name,
                        primary_data['secondary'][secondary_name]
                    )
                
            else:
                # This is a simple secondary (Data row)
                secondary_name, secondary_amount = self._extract_row_data(secondary_row)
                
                if not secondary_name or secondary_amount == 0:
                    continue
                
                logger.info(f"  SECONDARY (Data): {secondary_name} = ${secondary_amount:,.2f}")
                
                # Add as secondary with no tertiaries
                primary_data['secondary'][secondary_name] = {
                    'total': secondary_amount,
                    'tertiary': {}
                }
        
        # Calculate primary total from secondaries
        primary_data['total'] = sum(
            sec['total'] for sec in primary_data['secondary'].values()
        )
    
    def _parse_tertiaries(self, secondary_row: Dict, secondary_name: str, secondary_data: Dict):
        """Parse tertiary items under a secondary Section"""
        
        def extract_all_tertiaries(row, depth=0):
            """Recursively extract all tertiary items (handles deep nesting like 8505.01)"""
            if 'Rows' not in row:
                return
            
            rows = self._extract_rows(row['Rows'])
            
            for tertiary_row in rows:
                if not isinstance(tertiary_row, dict):
                    continue
                
                # If this is a Section, recurse deeper
                if tertiary_row.get('type') == 'Section':
                    extract_all_tertiaries(tertiary_row, depth + 1)
                else:
                    # This is a Data row - extract it
                    tertiary_name, tertiary_amount = self._extract_row_data(tertiary_row)
                    
                    if tertiary_name and tertiary_amount != 0:
                        logger.info(f"    TERTIARY: {tertiary_name} = ${tertiary_amount:,.2f}")
                        secondary_data['tertiary'][tertiary_name] = tertiary_amount
        
        # Extract all tertiaries (handles nested Sections)
        extract_all_tertiaries(secondary_row)
        
        # Calculate secondary total from tertiaries
        secondary_data['total'] = sum(secondary_data['tertiary'].values())
    
    def _extract_rows(self, rows_data) -> list:
        """Extract rows list from Rows structure"""
        if isinstance(rows_data, dict) and 'Row' in rows_data:
            return rows_data['Row']
        elif isinstance(rows_data, list):
            return rows_data
        return []
    
    def _extract_row_data(self, row: Dict) -> tuple:
        """Extract name and amount from a row"""
        name = None
        amount = 0
        
        # Try Header first (for Section rows)
        if 'Header' in row:
            col_data = row['Header'].get('ColData', [])
            if len(col_data) >= 2:
                name = col_data[0].get('value', '').strip()
                amount_str = col_data[1].get('value', '0').replace(',', '').replace('$', '')
                try:
                    amount = float(amount_str) if amount_str else 0.0
                except ValueError:
                    amount = 0.0
        
        # Try ColData (for Data rows)
        elif 'ColData' in row:
            col_data = row['ColData']
            if len(col_data) >= 2:
                name = col_data[0].get('value', '').strip()
                amount_str = col_data[1].get('value', '0').replace(',', '').replace('$', '')
                try:
                    amount = float(amount_str) if amount_str else 0.0
                except ValueError:
                    amount = 0.0
        
        # Skip summary rows
        if name:
            skip_keywords = ['total', 'subtotal', 'net income', 'gross profit']
            if any(keyword in name.lower() for keyword in skip_keywords):
                return None, 0
        
        return name, amount
    
    def _calculate_hierarchy_total(self, hierarchy: Dict) -> float:
        """Calculate total from hierarchical expense structure"""
        total = 0
        for primary_data in hierarchy.values():
            total += primary_data.get('total', 0)
        return total
    
    def _parse_row_data(self, row: Dict, income_sources: Dict, expense_categories: Dict, parent_group: str = None):
        """Parse individual row data from P&L report"""
        try:
            if 'ColData' in row and len(row['ColData']) >= 2:
                # Extract account name and amount
                account_name = row['ColData'][0].get('value', '').strip()
                
                # **RENAME SALARY ACCOUNTS**
                if account_name == "5001 Salaries & wages":
                    account_name = "Billable Salaries and Wages"
                elif account_name == "8005 Salaries and Wages":
                    account_name = "G&A Salaries and Wages"
                
            # **SKIP SUMMARY/TOTAL ROWS**
                skip_keywords = [
                    'total', 'subtotal', 'net income', 'gross profit',
                    'operating income', 'income before', 'sum', 'balance'
                ]
                if any(keyword in account_name.lower() for keyword in skip_keywords):
                    logger.debug(f"Skipping summary row: {account_name}")
                    return
                
                # **SKIP ROWS WITH row.type == 'Section'**
                if row.get('type') == 'Section':
                    logger.debug(f"Skipping section header: {account_name}")
                    return
                
                # Continue with existing logic...
                amount_str = row['ColData'][1].get('value', '0').replace(',', '').replace('$', '')
                
                try:
                    amount = float(amount_str) if amount_str else 0.0
                except ValueError:
                    amount = 0.0
                
                # Skip zero amounts and empty names
                if amount == 0 or not account_name:
                    return
                
                logger.info(f"Processing: {account_name} = ${amount}")
                
                # Debug: Log all account names to help identify salary accounts
                if "salar" in account_name.lower() or "5001" in account_name or "8005" in account_name:
                    logger.info(f"🔍 SALARY ACCOUNT FOUND: '{account_name}' (original: {row['ColData'][0].get('value', '').strip()})")
                
                # Debug: Log any account starting with 5001
                original_name = row['ColData'][0].get('value', '').strip()
                if original_name.startswith("5001"):
                    logger.info(f"🔍 5001 ACCOUNT DETECTED: '{original_name}' -> '{account_name}'")
                
                # Create row context for better categorization
                row_context = {
                    'group': parent_group,
                    'type': row.get('type', ''),
                    'group_type': row.get('group', '')
                }
                
                # Debug logging to see what context we have
                logger.info(f"Row context for {account_name}: {row_context}")
                
                # Use dynamic categorization with context
                category = self._categorize_account_dynamically(account_name, amount, row_context)
                
                if category == 'income' and amount > 0:
                    if account_name in income_sources:
                        logger.warning(f"⚠️ DUPLICATE INCOME: {account_name} already exists with ${income_sources[account_name]:,.2f}, adding ${amount:,.2f}")
                        income_sources[account_name] += amount
                    else:
                        income_sources[account_name] = amount
                    logger.info(f"Added income: {account_name} = ${income_sources[account_name]:,.2f}")
                elif category == 'expense' and amount != 0:  # QBO reports expenses as positive values
                    if account_name in expense_categories:
                        logger.warning(f"⚠️ DUPLICATE EXPENSE: {account_name} already exists with ${expense_categories[account_name]:,.2f}, adding ${amount:,.2f}")
                        expense_categories[account_name] += amount
                    else:
                        expense_categories[account_name] = amount
                    logger.info(f"Added expense: {account_name} = ${expense_categories[account_name]:,.2f}")
                else:
                    logger.info(f"Skipped: {account_name} (category: {category}, amount: {amount})")
                    
        except Exception as e:
            logger.error(f"Error parsing row data: {e}")
    
    def _parse_nested_row(self, row: Dict, income_sources: Dict, expense_categories: Dict, parent_group: str = None):
        """Parse nested row data from P&L report"""
        try:
            if isinstance(row, dict):
                # Get the group context from the row
                current_group = row.get('group', parent_group)
                
                # **HANDLE HEADER ROWS WITH NESTED DATA:**
                # If this row has a Header with ColData AND nested rows, process both:
                # 1. The Header value (e.g., "8500 GA Travel" = $687.30)
                # 2. The nested rows (e.g., "8505.01 GA Auto - Teeple" = $19,332.54)
                if 'Header' in row and 'ColData' in row['Header']:
                    # Check if Header has a value (not just a name)
                    header_col_data = row['Header']['ColData']
                    if len(header_col_data) >= 2 and header_col_data[1].get('value'):
                        # Process the header as an expense/income item
                        # Set type to 'Data' (not 'Section') so it doesn't get skipped
                        header_row = {
                            'ColData': header_col_data,
                            'type': 'Data',  # Force to 'Data' so Header values are processed
                            'group': current_group
                        }
                        self._parse_row_data(header_row, income_sources, expense_categories, current_group)
                
                # Process nested rows if they exist
                if 'Rows' in row:
                    nested_rows = row['Rows']
                    if isinstance(nested_rows, dict) and 'Row' in nested_rows:
                        for subrow in nested_rows['Row']:
                            self._parse_nested_row(subrow, income_sources, expense_categories, current_group)
                    elif isinstance(nested_rows, list):
                        for subrow in nested_rows:
                            self._parse_nested_row(subrow, income_sources, expense_categories, current_group)
                    return
                
                # Only process ColData if there are NO nested rows
                if 'ColData' in row:
                    self._parse_row_data(row, income_sources, expense_categories, current_group)
                    
        except Exception as e:
            logger.error(f"Error parsing nested row data: {e}")
    
    def _is_summary_only_report(self, pl_data: Dict) -> bool:
        """Check if the report contains only summary data (no detailed accounts)"""
        try:
            if 'Rows' in pl_data:
                rows_data = pl_data['Rows']
                if isinstance(rows_data, dict) and 'Row' in rows_data:
                    rows = rows_data['Row']
                    # Check if all rows are summary rows (no ColData with actual amounts)
                    for row in rows:
                        if isinstance(row, dict):
                            # Look for rows with actual ColData (not just headers/summaries)
                            if 'ColData' in row and len(row['ColData']) >= 2:
                                # Check if the second column has a value (amount)
                                amount_str = row['ColData'][1].get('value', '')
                                if amount_str and amount_str != '':
                                    return False  # Found actual data
                            # Check nested rows
                            if 'Rows' in row:
                                nested_rows = row['Rows']
                                if isinstance(nested_rows, dict) and 'Row' in nested_rows:
                                    for subrow in nested_rows['Row']:
                                        if isinstance(subrow, dict) and 'ColData' in subrow:
                                            amount_str = subrow['ColData'][1].get('value', '')
                                            if amount_str and amount_str != '':
                                                return False  # Found actual data
            return True  # No actual data found, likely summary-only
        except Exception as e:
            logger.error(f"Error checking summary-only report: {e}")
            return False
    
    def _is_income_account(self, account_name: str) -> bool:
        """Determine if an account is an income account"""
        income_keywords = [
            'revenue', 'sales', 'income', 'receipts', 'fees', 'service',
            'product', 'consulting', 'commission', 'interest income',
            'gross profit', 'net sales', 'total income', 'other income',
            'interest earned', 'dividend', 'rental income', 'royalty'
        ]
        
        account_lower = account_name.lower()
        return any(keyword in account_lower for keyword in income_keywords)
    
    def _is_expense_account(self, account_name: str) -> bool:
        """Determine if an account is an expense account"""
        expense_keywords = [
            'expense', 'cost', 'fee', 'rent', 'utilities', 'office',
            'marketing', 'advertising', 'travel', 'meals', 'supplies',
            'equipment', 'insurance', 'payroll', 'benefits', 'taxes',
            'operating', 'administrative', 'professional', 'legal',
            'bank', 'interest', 'depreciation', 'amortization',
            'bad debt', 'wages', 'salaries', 'contractor', 'freelance'
        ]
        
        account_lower = account_name.lower()
        return any(keyword in account_lower for keyword in expense_keywords)
    
    def _categorize_account_dynamically(self, account_name: str, amount: float, row_context: dict = None) -> str:
        """Dynamically categorize accounts based on QuickBooks account structure and context"""
        account_lower = account_name.lower()
        
        # PRIORITY 1: Check row context first - this is the most reliable indicator
        if row_context and 'group' in row_context:
            group = row_context.get('group', '').lower()
            if 'expense' in group or 'cogs' in group:
                return 'expense'
            elif 'income' in group or 'revenue' in group:
                return 'income'
        
        # PRIORITY 2: Check for very specific income keywords (only clear income indicators)
        clear_income_keywords = [
            'revenue', 'sales', 'income', 'service', 'fees', 'consulting', 
            'design', 'product income', 'services', 'landscaping services',
            'pest control services', 'sales of product'
        ]
        
        # PRIORITY 3: Check for very specific expense keywords (only clear expense indicators)
        clear_expense_keywords = [
            'expense', 'cost', 'supplies', 'materials', 'rent', 'utilities', 
            'insurance', 'advertising', 'equipment', 'automobile', 'fuel', 
            'job expenses', 'legal', 'professional', 'meals', 'entertainment', 
            'office', 'lease', 'gas', 'electric', 'telephone', 'miscellaneous',
            'maintenance', 'repair', 'bookkeeper', 'lawyer', 'accounting'
        ]
        
        # Check for clear expense keywords first
        if any(keyword in account_lower for keyword in clear_expense_keywords):
            return 'expense'
        elif any(keyword in account_lower for keyword in clear_income_keywords):
            return 'income'
        
        # PRIORITY 4: Default based on amount sign (fallback)
        if amount > 0:
            return 'income'
        elif amount < 0:
            return 'expense'
        
        return 'other'
    
    def _parse_alternative_report_structure(self, pl_data: Dict) -> Optional[Dict[str, Any]]:
        """Try alternative parsing methods for different report structures"""
        try:
            # This is a fallback method for different QBO report formats
            logger.info("Attempting alternative report parsing")
            
            income_sources = {}
            expense_categories = {}
            
            # Try to extract data from any structure we can find
            def extract_from_any_structure(data, path=""):
                if isinstance(data, dict):
                    for key, value in data.items():
                        current_path = f"{path}.{key}" if path else key
                        
                        # Look for ColData patterns
                        if key == 'ColData' and isinstance(value, list) and len(value) >= 2:
                            try:
                                account_name = value[0].get('value', '').strip()
                                amount_str = value[1].get('value', '0').replace(',', '').replace('$', '')
                                amount = float(amount_str) if amount_str else 0.0
                                
                                if account_name and amount != 0:
                                    logger.info(f"Alternative parsing found: {account_name} = ${amount}")
                                    category = self._categorize_account_dynamically(account_name, amount, {'group': 'unknown'})
                                    
                                    if category == 'income' and amount > 0:
                                        income_sources[account_name] = amount
                                    elif category == 'expense' and amount < 0:
                                        expense_categories[account_name] = abs(amount)
                            except (ValueError, KeyError) as e:
                                logger.debug(f"Could not parse ColData at {current_path}: {e}")
                        
                        # Recursively search nested structures
                        elif isinstance(value, (dict, list)):
                            extract_from_any_structure(value, current_path)
                
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        extract_from_any_structure(item, f"{path}[{i}]")
            
            # Search the entire data structure
            extract_from_any_structure(pl_data)
            
            if income_sources or expense_categories:
                logger.info(f"Alternative parsing found: {len(income_sources)} income, {len(expense_categories)} expenses")
                return {
                    'income': income_sources,
                    'expenses': expense_categories,
                    'is_sample_data': False
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in alternative parsing: {e}")
            return None
    
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
