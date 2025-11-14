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
        
        Uses transaction-level queries (Journal Entries, Bills, Expenses) to get
        COGS project breakdown. This is more reliable than ProfitAndLossDetail reports
        as it directly accesses Entity/CustomerRef fields with project information.
        
        Args:
            account_numbers: List of account numbers to query (e.g., ['5001', '5011'])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            Dictionary mapping account names to project breakdowns:
            {
                '5001 Billable Salaries and Wages': {
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
            logger.info(f"FETCHING EXPENSES BY PROJECT (Transaction-Level Queries)")
            logger.info(f"Accounts: {account_numbers}")
            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info("="*80)
            
            # Initialize result structure keyed by account number
            cogs_data = {}
            for account_num in account_numbers:
                cogs_data[account_num] = {}
            
            # Query 1: Journal Entries (most reliable for COGS allocation)
            logger.info("Step 1: Querying Journal Entries...")
            journal_data = self._get_journal_entries_for_cogs(start_date, end_date, account_numbers)
            self._merge_cogs_data(cogs_data, journal_data)
            
            # Query 2: Bills with COGS line items
            logger.info("Step 2: Querying Bills...")
            bill_data = self._get_bills_for_cogs(start_date, end_date, account_numbers)
            self._merge_cogs_data(cogs_data, bill_data)
            
            # Query 3: Expense transactions (Checks, Purchases)
            logger.info("Step 3: Querying Expenses/Purchases...")
            expense_data = self._get_expenses_for_cogs(start_date, end_date, account_numbers)
            self._merge_cogs_data(cogs_data, expense_data)
            
            # Convert from account number keys to account name keys for compatibility
            # Map account numbers to account names
            expense_by_project = {}
            for account_num, projects in cogs_data.items():
                if not projects:
                    continue
                
                # Map account number to account name
                if account_num == '5001':
                    account_name = "Billable Salaries and Wages"
                elif account_num == '5011':
                    account_name = "5011 Direct 1099 Labor"
                else:
                    # Try to find account name from first transaction (fallback)
                    account_name = f"{account_num} COGS Account"
                
                expense_by_project[account_name] = projects
            
            # Log summary
            logger.info("="*80)
            logger.info("EXPENSES BY PROJECT SUMMARY (All Sources Combined):")
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
    
    def get_expenses_by_project_for_ga(
        self,
        account_numbers: List[str],
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Get expenses for GA accounts (e.g., 8005) broken down by project/customer
        
        Similar to get_expenses_by_project but specifically for GA accounts.
        Filters FOR transactions with ClassRef belonging to GA (8005).
        
        Args:
            account_numbers: List of account numbers to query (e.g., ['8005'])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            Dictionary mapping account names to project breakdowns
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info("="*80)
            logger.info(f"FETCHING GA EXPENSES BY PROJECT (Transaction-Level Queries)")
            logger.info(f"Accounts: {account_numbers}")
            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info("="*80)
            
            # Initialize result structure keyed by account number
            ga_data = {}
            for account_num in account_numbers:
                ga_data[account_num] = {}
            
            # Query 1: Journal Entries
            logger.info("Step 1: Querying Journal Entries for GA...")
            journal_data = self._get_journal_entries_for_ga(start_date, end_date, account_numbers)
            self._merge_cogs_data(ga_data, journal_data)
            
            # Query 2: Bills with GA line items
            logger.info("Step 2: Querying Bills for GA...")
            bill_data = self._get_bills_for_ga(start_date, end_date, account_numbers)
            self._merge_cogs_data(ga_data, bill_data)
            
            # Query 3: Expense transactions (Checks, Purchases)
            logger.info("Step 3: Querying Expenses/Purchases for GA...")
            expense_data = self._get_expenses_for_ga(start_date, end_date, account_numbers)
            self._merge_cogs_data(ga_data, expense_data)
            
            # Convert from account number keys to account name keys
            expense_by_project = {}
            for account_num, projects in ga_data.items():
                if not projects:
                    continue
                
                # Map account number to account name
                if account_num == '8005':
                    account_name = "8005 Salaries and Wages"
                else:
                    account_name = f"{account_num} GA Account"
                
                expense_by_project[account_name] = projects
            
            # Log summary
            logger.info("="*80)
            logger.info("GA EXPENSES BY PROJECT SUMMARY (All Sources Combined):")
            for account_name, projects in expense_by_project.items():
                if projects:
                    total = sum(projects.values())
                    logger.info(f"  {account_name}: {len(projects)} projects, Total: ${total:,.2f}")
                    for project_name, project_amount in sorted(projects.items(), key=lambda x: x[1], reverse=True)[:5]:
                        logger.info(f"    • {project_name}: ${project_amount:,.2f}")
            logger.info("="*80)
            
            return expense_by_project
            
        except Exception as e:
            logger.error(f"Error fetching GA expenses by project: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def _get_journal_entries_for_cogs(
        self,
        start_date: str,
        end_date: str,
        account_numbers: List[str],
        collect_unassigned_details: bool = False
    ) -> Dict[str, Dict[str, float]]:
        """
        Query journal entries that allocate COGS to projects
        
        Extracts COGS project data from JournalEntry transactions by:
        1. Querying JournalEntry transactions in date range
        2. Filtering lines where AccountRef.name starts with account number (5001 or 5011)
        3. Extracting project from Entity.EntityRef.name (format: "Parent:Project" or just "Project")
        4. Handling Debit/Credit posting types (Debits increase COGS)
        5. Aggregating amounts by project
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            account_numbers: List of account numbers to query (e.g., ['5001', '5011'])
        
        Returns:
            Dictionary mapping account numbers to project breakdowns:
            {
                '5001': {'A6 Enterprise Services': 45000.00, 'CDSP': 40000.00, ...},
                '5011': {'A6 Enterprise Services': 15000.00, 'A6 DHO': 12000.00, ...}
            }
        """
        try:
            logger.info("="*80)
            logger.info("FETCHING COGS FROM JOURNAL ENTRIES")
            logger.info(f"Accounts: {account_numbers}")
            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info("="*80)
            
            # Query JournalEntry transactions
            query = (
                f"SELECT * FROM JournalEntry "
                f"WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' "
                f"MAXRESULTS 1000"
            )
            
            params = {'query': query, 'minorversion': '65'}
            data = self._make_request('query', params)
            
            if not data or 'QueryResponse' not in data:
                logger.warning("No journal entry data returned from query")
                return {}
            
            # Initialize result structure keyed by account number
            cogs_data = {}
            for account_num in account_numbers:
                cogs_data[account_num] = {}
            
            # Store detailed unassigned transaction info if requested
            unassigned_details = {}
            if collect_unassigned_details:
                for account_num in account_numbers:
                    unassigned_details[account_num] = []
            
            # Track "Labor Allocation" totals for account 5001
            labor_allocation_total = 0.0
            
            entries = data['QueryResponse'].get('JournalEntry', [])
            logger.info(f"Processing {len(entries)} journal entries for COGS")
            
            processed_count = 0
            skipped_count = 0
            
            for entry in entries:
                entry_number = entry.get('DocNumber', 'N/A')
                lines = entry.get('Line', [])
                
                if not lines:
                    continue
                
                for line in lines:
                    # Get journal entry line detail
                    journal_detail = line.get('JournalEntryLineDetail', {})
                    if not journal_detail:
                        continue
                    
                    # Check ClassRef first - if it belongs to GA (8005), skip this line
                    class_ref = journal_detail.get('ClassRef', {})
                    if class_ref and self._classref_belongs_to_ga(class_ref):
                        logger.debug(f"  ⚠️ Skipping JE #{entry_number} line - ClassRef belongs to GA (8005): {class_ref.get('name', 'N/A')}")
                        skipped_count += 1
                        continue
                    
                    # Get account reference
                    account_ref = journal_detail.get('AccountRef', {})
                    account_name = account_ref.get('name', '')
                    
                    if not account_name:
                        continue
                    
                    # Extract account number from account name
                    # Account names can be: "5001 Billable Salaries and Wages", "COGS:5001 Salaries", etc.
                    account_num = None
                    account_match = re.search(r'(\d{4})', account_name)
                    if account_match:
                        account_num = account_match.group(1)
                    else:
                        # Try to match by name patterns
                        account_name_lower = account_name.lower()
                        if 'salaries' in account_name_lower and 'wage' in account_name_lower:
                            if 'cogs' in account_name_lower or 'cost of goods' in account_name_lower:
                                account_num = '5001'
                        elif 'direct' in account_name_lower and '1099' in account_name_lower and 'labor' in account_name_lower:
                            account_num = '5011'
                    
                    # Check if this line is for one of our COGS accounts
                    if not account_num or account_num not in account_numbers:
                        continue
                    
                    # Get amount and posting type
                    amount = float(line.get('Amount', 0))
                    posting_type = journal_detail.get('PostingType', '')
                    
                    # Debits increase COGS (expenses), Credits decrease COGS
                    # We only want Debits for expense accounts
                    if posting_type != 'Debit':
                        logger.debug(f"  ⚠️ Skipping JE #{entry_number} line - PostingType is '{posting_type}' (not Debit)")
                        skipped_count += 1
                        continue
                    
                    if amount == 0:
                        logger.debug(f"  ⚠️ Skipping JE #{entry_number} line - Zero amount")
                        skipped_count += 1
                        continue
                    
                    # Get descriptions for checking patterns
                    line_description = line.get('Description', '')
                    txn_description = entry.get('PrivateNote', '') or entry.get('Description', '')
                    combined_description = (line_description + ' ' + txn_description).lower()
                    
                    # Track "Labor Allocation" totals for account 5001
                    if account_num == '5001' and 'labor allocation' in combined_description:
                        labor_allocation_total += abs(amount)
                        logger.debug(f"  📊 Labor Allocation transaction: JE #{entry_number}, Amount: ${abs(amount):,.2f}")
                    
                    # Check if this is an internal charge (Salary for 9-*)
                    # These don't belong in COGS accounts 5001/5011, they have their own accounts
                    # Map 9- patterns to target accounts and skip from COGS
                    if '9-' in combined_description or 'salary for 9-' in combined_description or '9 - ' in combined_description:
                        # Map 9- patterns to target accounts
                        target_account = None
                        if '9-overhead' in combined_description:
                            target_account = '7001'
                        elif '9-general' in combined_description or '9-general & administrative' in combined_description or '9-general and administrative' in combined_description:
                            target_account = '8005'
                        elif '9-it' in combined_description:
                            target_account = '8005'
                        elif '9-research' in combined_description or '9-research & development' in combined_description or '9-research and development' in combined_description:
                            target_account = '8601'
                        elif '9-business' in combined_description or '9-business development' in combined_description:
                            target_account = '8005'
                        
                        if target_account:
                            logger.debug(f"  ⚠️ Skipping JE #{entry_number} line - Internal charge (9-*) routed to {target_account}: {line_description[:100] if line_description else 'N/A'}")
                        else:
                            logger.debug(f"  ⚠️ Skipping JE #{entry_number} line - Internal charge (9-*) with unknown pattern: {line_description[:100] if line_description else 'N/A'}")
                        skipped_count += 1
                        continue
                    
                    # Extract project name from Entity
                    project_name = None
                    entity = line.get('Entity', {})
                    entity_ref = entity.get('EntityRef', {})
                    
                    if entity_ref:
                        entity_name = entity_ref.get('name', '')
                        if entity_name:
                            # Handle "Parent:Project" format - extract project part
                            if ':' in entity_name:
                                # Format: "Agile Six Applications Inc:A6 Enterprise Services"
                                project_name = entity_name.split(':')[-1].strip()
                            else:
                                # Standalone project name
                                project_name = entity_name.strip()
                            
                            # Normalize project name to match income-side names
                            normalized = self._normalize_project_name(project_name)
                            if normalized:
                                project_name = normalized
                            else:
                                # If normalization returns None, try extracting from name directly
                                extracted = self._extract_project_name(project_name)
                                if extracted:
                                    project_name = extracted
                                else:
                                    # If still no match, use the name as-is (might be a valid project)
                                    # Only use if it contains project indicators
                                    project_indicators = ['a6', 'tws', 'cdsp', 'perigean', 'dmva']
                                    if not any(indicator in project_name.lower() for indicator in project_indicators):
                                        project_name = None
                    
                    # If no project from Entity, try line Description
                    # (Note: line_description was already extracted above for the 9- check)
                    if not project_name:
                        if line_description:
                            extracted = self._extract_project_from_description(line_description)
                            if extracted:
                                project_name = extracted
                    
                    # Also try transaction-level description (PrivateNote or Description)
                    # (Note: txn_description was already extracted above for the 9- check)
                    if not project_name:
                        if txn_description:
                            extracted = self._extract_project_from_description(txn_description)
                            if extracted:
                                project_name = extracted
                    
                    # If still no project name, categorize as "Unassigned"
                    if not project_name:
                        project_name = "Unassigned"
                        logger.debug(f"  ⚠️ JE #{entry_number}: No project name found for {account_name} (Amount: ${amount:,.2f}) - Categorizing as 'Unassigned'")
                        
                        # Collect detailed information about unassigned transactions
                        if collect_unassigned_details:
                            unassigned_details[account_num].append({
                                'doc_number': entry_number,
                                'date': entry.get('TxnDate', 'N/A'),
                                'amount': abs(amount),
                                'account_name': account_name,
                                'line_description': line_description,
                                'txn_description': txn_description,
                                'entity_name': entity_ref.get('name', '') if entity_ref else '',
                                'class_ref': class_ref.get('name', '') if class_ref else '',
                                'posting_type': posting_type
                            })
                    
                    # Add to result
                    if project_name not in cogs_data[account_num]:
                        cogs_data[account_num][project_name] = 0.0
                    
                    cogs_data[account_num][project_name] += abs(amount)
                    processed_count += 1
                    
                    logger.info(f"  ✅ JE #{entry_number}: {account_num} → {project_name} = ${abs(amount):,.2f}")
            
            # Log summary
            logger.info("="*80)
            logger.info("JOURNAL ENTRIES COGS SUMMARY:")
            logger.info(f"  Processed: {processed_count} lines")
            logger.info(f"  Skipped: {skipped_count} lines")
            for account_num, projects in cogs_data.items():
                if projects:
                    total = sum(projects.values())
                    logger.info(f"  Account {account_num}: {len(projects)} projects, Total: ${total:,.2f}")
                    for project_name, project_amount in sorted(projects.items(), key=lambda x: x[1], reverse=True)[:5]:
                        logger.info(f"    • {project_name}: ${project_amount:,.2f}")
            if labor_allocation_total > 0:
                logger.info(f"  📊 Account 5001 Labor Allocation Total: ${labor_allocation_total:,.2f}")
            logger.info("="*80)
            
            # Store unassigned details as instance variable if collected
            if collect_unassigned_details:
                self._unassigned_journal_entry_details = unassigned_details
            
            return cogs_data
            
        except Exception as e:
            logger.error(f"Error querying journal entries for COGS: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def _get_bills_for_cogs(
        self,
        start_date: str,
        end_date: str,
        account_numbers: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Query bills with COGS account line items
        
        Extracts COGS project data from Bill transactions by:
        1. Querying Bill transactions in date range
        2. Filtering lines where AccountBasedExpenseLineDetail.AccountRef.name starts with account number
        3. Extracting project from AccountBasedExpenseLineDetail.CustomerRef.name
        4. Aggregating amounts by project
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            account_numbers: List of account numbers to query (e.g., ['5001', '5011'])
        
        Returns:
            Dictionary mapping account numbers to project breakdowns:
            {
                '5001': {'A6 Enterprise Services': 45000.00, 'CDSP': 40000.00, ...},
                '5011': {'A6 Enterprise Services': 15000.00, 'A6 DHO': 12000.00, ...}
            }
        """
        try:
            logger.info("="*80)
            logger.info("FETCHING COGS FROM BILLS")
            logger.info(f"Accounts: {account_numbers}")
            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info("="*80)
            
            # Query Bill transactions
            query = (
                f"SELECT * FROM Bill "
                f"WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' "
                f"MAXRESULTS 1000"
            )
            
            params = {'query': query, 'minorversion': '65'}
            data = self._make_request('query', params)
            
            if not data or 'QueryResponse' not in data:
                logger.warning("No bill data returned from query")
                return {}
            
            # Initialize result structure keyed by account number
            cogs_data = {}
            for account_num in account_numbers:
                cogs_data[account_num] = {}
            
            bills = data['QueryResponse'].get('Bill', [])
            logger.info(f"Processing {len(bills)} bills for COGS")
            
            processed_count = 0
            skipped_count = 0
            
            for bill in bills:
                bill_id = bill.get('Id', 'N/A')
                lines = bill.get('Line', [])
                
                if not lines:
                    continue
                
                # Get transaction-level customer reference (fallback)
                transaction_customer_ref = bill.get('CustomerRef', {})
                transaction_customer_name = transaction_customer_ref.get('name', '')
                
                for line in lines:
                    # Skip group lines
                    if line.get('GroupLineDetail'):
                        continue
                    
                    # Get account-based expense line detail
                    line_detail = (
                        line.get('AccountBasedExpenseLineDetail') or
                        line.get('ExpenseLineDetail') or
                        line.get('ItemBasedExpenseLineDetail')
                    )
                    
                    if not line_detail:
                        continue
                    
                    # Check ClassRef first - if it belongs to GA (8005), skip this line
                    class_ref = line_detail.get('ClassRef', {})
                    if class_ref and self._classref_belongs_to_ga(class_ref):
                        logger.debug(f"  ⚠️ Skipping Bill {bill_id} line - ClassRef belongs to GA (8005): {class_ref.get('name', 'N/A')}")
                        skipped_count += 1
                        continue
                    
                    # Get account reference
                    account_ref = line_detail.get('AccountRef', {})
                    account_name = account_ref.get('name', '')
                    
                    if not account_name:
                        continue
                    
                    # Extract account number from account name
                    account_num = None
                    account_match = re.search(r'(\d{4})', account_name)
                    if account_match:
                        account_num = account_match.group(1)
                    else:
                        # Try to match by name patterns
                        account_name_lower = account_name.lower()
                        if 'salaries' in account_name_lower and 'wage' in account_name_lower:
                            if 'cogs' in account_name_lower or 'cost of goods' in account_name_lower:
                                account_num = '5001'
                        elif 'direct' in account_name_lower and '1099' in account_name_lower and 'labor' in account_name_lower:
                            account_num = '5011'
                    
                    # Check if this line is for one of our COGS accounts
                    if not account_num or account_num not in account_numbers:
                        continue
                    
                    # Get amount
                    amount = float(line.get('Amount', 0))
                    if amount == 0:
                        logger.debug(f"  ⚠️ Skipping Bill {bill_id} line - Zero amount")
                        skipped_count += 1
                        continue
                    
                    # Extract project name from CustomerRef
                    project_name = None
                    
                    # Priority 1: Line-level CustomerRef
                    line_customer_ref = line_detail.get('CustomerRef', {})
                    if line_customer_ref:
                        customer_name = line_customer_ref.get('name', '')
                        if customer_name:
                            # Handle "Parent:Project" format
                            if ':' in customer_name:
                                project_name = customer_name.split(':')[-1].strip()
                            else:
                                project_name = customer_name.strip()
                            
                            # Normalize project name
                            normalized = self._normalize_project_name(project_name)
                            if normalized:
                                project_name = normalized
                            else:
                                extracted = self._extract_project_name(project_name)
                                if extracted:
                                    project_name = extracted
                    
                    # Priority 2: Transaction-level CustomerRef
                    if not project_name and transaction_customer_name:
                        if ':' in transaction_customer_name:
                            project_name = transaction_customer_name.split(':')[-1].strip()
                        else:
                            project_name = transaction_customer_name.strip()
                        
                        normalized = self._normalize_project_name(project_name)
                        if normalized:
                            project_name = normalized
                        else:
                            extracted = self._extract_project_name(project_name)
                            if extracted:
                                project_name = extracted
                    
                    # Priority 3: For 5011 items, use VendorRef as fallback
                    # Note: Only use vendor mapping if the vendor name contains project indicators
                    # Do not map vendors to projects that belong to 5001 (e.g., A6 Enterprise Services)
                    if not project_name and account_num == '5011':
                        vendor_ref = bill.get('VendorRef', {})
                        vendor_name = vendor_ref.get('name', '') if vendor_ref else ''
                        
                        if vendor_name:
                            # Try to extract project from vendor name if it contains project indicators
                            # This will only match if the vendor name itself contains project keywords
                            normalized = self._normalize_project_name(vendor_name)
                            if normalized:
                                # Double-check: Don't assign 5001 projects to 5011 items
                                # A6 Enterprise Services should only appear in 5001
                                if normalized == 'A6 Enterprise Services':
                                    logger.debug(f"  ⚠️ Skipping vendor '{vendor_name}' - A6 Enterprise Services belongs to 5001, not 5011")
                                else:
                                    project_name = normalized
                                    logger.info(f"  ✓ Extracted project '{project_name}' from vendor name '{vendor_name}' (5011 item)")
                    
                    # If still no project name, categorize as "Unassigned"
                    if not project_name:
                        project_name = "Unassigned"
                        logger.debug(f"  ⚠️ Bill {bill_id}: No project name found for {account_name} (Amount: ${amount:,.2f}) - Categorizing as 'Unassigned'")
                    
                    # Add to result
                    if project_name not in cogs_data[account_num]:
                        cogs_data[account_num][project_name] = 0.0
                    
                    cogs_data[account_num][project_name] += abs(amount)
                    processed_count += 1
                    
                    logger.info(f"  ✅ Bill {bill_id}: {account_num} → {project_name} = ${abs(amount):,.2f}")
            
            # Log summary
            logger.info("="*80)
            logger.info("BILLS COGS SUMMARY:")
            logger.info(f"  Processed: {processed_count} lines")
            logger.info(f"  Skipped: {skipped_count} lines")
            for account_num, projects in cogs_data.items():
                if projects:
                    total = sum(projects.values())
                    logger.info(f"  Account {account_num}: {len(projects)} projects, Total: ${total:,.2f}")
                    for project_name, project_amount in sorted(projects.items(), key=lambda x: x[1], reverse=True)[:5]:
                        logger.info(f"    • {project_name}: ${project_amount:,.2f}")
            logger.info("="*80)
            
            return cogs_data
            
        except Exception as e:
            logger.error(f"Error querying bills for COGS: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def _get_expenses_for_cogs(
        self,
        start_date: str,
        end_date: str,
        account_numbers: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Query expense transactions (Purchase, Expense) with COGS accounts
        
        Extracts COGS project data from Purchase and Expense transactions by:
        1. Querying Purchase and Expense transactions in date range
        2. Filtering lines where AccountBasedExpenseLineDetail.AccountRef.name starts with account number
        3. Extracting project from AccountBasedExpenseLineDetail.CustomerRef.name
        4. Aggregating amounts by project
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            account_numbers: List of account numbers to query (e.g., ['5001', '5011'])
        
        Returns:
            Dictionary mapping account numbers to project breakdowns:
            {
                '5001': {'A6 Enterprise Services': 45000.00, 'CDSP': 40000.00, ...},
                '5011': {'A6 Enterprise Services': 15000.00, 'A6 DHO': 12000.00, ...}
            }
        """
        try:
            logger.info("="*80)
            logger.info("FETCHING COGS FROM EXPENSES/PURCHASES")
            logger.info(f"Accounts: {account_numbers}")
            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info("="*80)
            
            # Query both Purchase and Expense transaction types
            queries = [
                f"SELECT * FROM Purchase WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' MAXRESULTS 1000",
                f"SELECT * FROM Expense WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' MAXRESULTS 1000"
            ]
            
            # Initialize result structure keyed by account number
            cogs_data = {}
            for account_num in account_numbers:
                cogs_data[account_num] = {}
            
            total_processed = 0
            total_skipped = 0
            
            for query in queries:
                txn_type = 'Purchase' if 'Purchase' in query else 'Expense'
                logger.info(f"Querying {txn_type} transactions...")
                
                params = {'query': query, 'minorversion': '65'}
                data = self._make_request('query', params)
                
                if not data or 'QueryResponse' not in data:
                    logger.warning(f"No {txn_type} data returned from query")
                    continue
                
                transactions = data['QueryResponse'].get(txn_type, [])
                logger.info(f"Processing {len(transactions)} {txn_type} transactions for COGS")
                
                processed_count = 0
                skipped_count = 0
                
                for txn in transactions:
                    txn_id = txn.get('Id', 'N/A')
                    lines = txn.get('Line', [])
                    
                    if not lines:
                        continue
                    
                    # Get transaction-level customer reference (fallback)
                    transaction_customer_ref = txn.get('CustomerRef', {})
                    transaction_customer_name = transaction_customer_ref.get('name', '')
                    
                    for line in lines:
                        # Skip group lines
                        if line.get('GroupLineDetail'):
                            continue
                        
                        # Get account-based expense line detail
                        line_detail = (
                            line.get('AccountBasedExpenseLineDetail') or
                            line.get('ExpenseLineDetail') or
                            line.get('ItemBasedExpenseLineDetail')
                        )
                        
                        if not line_detail:
                            continue
                        
                        # Check ClassRef first - if it belongs to GA (8005), skip this line
                        class_ref = line_detail.get('ClassRef', {})
                        if class_ref and self._classref_belongs_to_ga(class_ref):
                            logger.debug(f"  ⚠️ Skipping {txn_type} {txn_id} line - ClassRef belongs to GA (8005): {class_ref.get('name', 'N/A')}")
                            skipped_count += 1
                            continue
                        
                        # Get account reference
                        account_ref = line_detail.get('AccountRef', {})
                        account_name = account_ref.get('name', '')
                        
                        if not account_name:
                            continue
                        
                        # Extract account number from account name
                        account_num = None
                        account_match = re.search(r'(\d{4})', account_name)
                        if account_match:
                            account_num = account_match.group(1)
                        else:
                            # Try to match by name patterns
                            account_name_lower = account_name.lower()
                            if 'salaries' in account_name_lower and 'wage' in account_name_lower:
                                if 'cogs' in account_name_lower or 'cost of goods' in account_name_lower:
                                    account_num = '5001'
                            elif 'direct' in account_name_lower and '1099' in account_name_lower and 'labor' in account_name_lower:
                                account_num = '5011'
                        
                        # Check if this line is for one of our COGS accounts
                        if not account_num or account_num not in account_numbers:
                            continue
                        
                        # Get amount
                        amount = float(line.get('Amount', 0))
                        if amount == 0:
                            logger.debug(f"  ⚠️ Skipping {txn_type} {txn_id} line - Zero amount")
                            skipped_count += 1
                            continue
                        
                        # Extract project name from CustomerRef
                        project_name = None
                        
                        # Priority 1: Line-level CustomerRef
                        line_customer_ref = line_detail.get('CustomerRef', {})
                        if line_customer_ref:
                            customer_name = line_customer_ref.get('name', '')
                            if customer_name:
                                # Handle "Parent:Project" format
                                if ':' in customer_name:
                                    project_name = customer_name.split(':')[-1].strip()
                                else:
                                    project_name = customer_name.strip()
                                
                                # Normalize project name
                                normalized = self._normalize_project_name(project_name)
                                if normalized:
                                    project_name = normalized
                                else:
                                    extracted = self._extract_project_name(project_name)
                                    if extracted:
                                        project_name = extracted
                        
                        # Priority 2: Transaction-level CustomerRef
                        if not project_name and transaction_customer_name:
                            if ':' in transaction_customer_name:
                                project_name = transaction_customer_name.split(':')[-1].strip()
                            else:
                                project_name = transaction_customer_name.strip()
                            
                            normalized = self._normalize_project_name(project_name)
                            if normalized:
                                project_name = normalized
                            else:
                                extracted = self._extract_project_name(project_name)
                                if extracted:
                                    project_name = extracted
                        
                        # If still no project name, categorize as "Unassigned"
                        if not project_name:
                            project_name = "Unassigned"
                            logger.debug(f"  ⚠️ {txn_type} {txn_id}: No project name found for {account_name} (Amount: ${amount:,.2f}) - Categorizing as 'Unassigned'")
                        
                        # Add to result
                        if project_name not in cogs_data[account_num]:
                            cogs_data[account_num][project_name] = 0.0
                        
                        cogs_data[account_num][project_name] += abs(amount)
                        processed_count += 1
                        total_processed += 1
                        
                        logger.info(f"  ✅ {txn_type} {txn_id}: {account_num} → {project_name} = ${abs(amount):,.2f}")
                
                total_skipped += skipped_count
                logger.info(f"  {txn_type}: Processed {processed_count} lines, skipped {skipped_count} lines")
            
            # Log summary
            logger.info("="*80)
            logger.info("EXPENSES/PURCHASES COGS SUMMARY:")
            logger.info(f"  Total Processed: {total_processed} lines")
            logger.info(f"  Total Skipped: {total_skipped} lines")
            for account_num, projects in cogs_data.items():
                if projects:
                    total = sum(projects.values())
                    logger.info(f"  Account {account_num}: {len(projects)} projects, Total: ${total:,.2f}")
                    for project_name, project_amount in sorted(projects.items(), key=lambda x: x[1], reverse=True)[:5]:
                        logger.info(f"    • {project_name}: ${project_amount:,.2f}")
            logger.info("="*80)
            
            return cogs_data
            
        except Exception as e:
            logger.error(f"Error querying expenses for COGS: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def _get_journal_entries_for_ga(
        self,
        start_date: str,
        end_date: str,
        account_numbers: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Query journal entries for GA accounts (e.g., 8005)
        
        Similar to _get_journal_entries_for_cogs but filters FOR GA transactions
        (ClassRef belongs to GA) instead of filtering them out.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            account_numbers: List of account numbers to query (e.g., ['8005'])
        
        Returns:
            Dictionary mapping account numbers to project breakdowns
        """
        try:
            logger.info("="*80)
            logger.info("FETCHING GA EXPENSES FROM JOURNAL ENTRIES")
            logger.info(f"Accounts: {account_numbers}")
            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info("="*80)
            
            # Query JournalEntry transactions
            query = (
                f"SELECT * FROM JournalEntry "
                f"WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' "
                f"MAXRESULTS 1000"
            )
            
            params = {'query': query, 'minorversion': '65'}
            data = self._make_request('query', params)
            
            if not data or 'QueryResponse' not in data:
                logger.warning("No journal entry data returned from query")
                return {}
            
            # Initialize result structure keyed by account number
            ga_data = {}
            for account_num in account_numbers:
                ga_data[account_num] = {}
            
            entries = data['QueryResponse'].get('JournalEntry', [])
            logger.info(f"Processing {len(entries)} journal entries for GA")
            
            processed_count = 0
            skipped_count = 0
            
            for entry in entries:
                entry_number = entry.get('DocNumber', 'N/A')
                lines = entry.get('Line', [])
                
                if not lines:
                    continue
                
                for line in lines:
                    # Get journal entry line detail
                    journal_detail = line.get('JournalEntryLineDetail', {})
                    if not journal_detail:
                        continue
                    
                    # Get account reference first
                    account_ref = journal_detail.get('AccountRef', {})
                    account_name = account_ref.get('name', '')
                    
                    if not account_name:
                        continue
                    
                    # Extract account number from account name
                    account_num = None
                    account_match = re.search(r'(\d{4})', account_name)
                    if account_match:
                        account_num = account_match.group(1)
                    else:
                        # Try to match by name patterns
                        account_name_lower = account_name.lower()
                        if 'salaries' in account_name_lower and 'wage' in account_name_lower:
                            if 'ga' in account_name_lower or 'general' in account_name_lower or 'administrative' in account_name_lower:
                                account_num = '8005'
                    
                    # Check if this line is for one of our GA accounts
                    if not account_num or account_num not in account_numbers:
                        continue
                    
                    # Check ClassRef - ONLY include if it belongs to GA (8005) OR if account is 8005 (some transactions may not have ClassRef)
                    class_ref = journal_detail.get('ClassRef', {})
                    if class_ref:
                        # If ClassRef exists, it must belong to GA
                        if not self._classref_belongs_to_ga(class_ref):
                            logger.debug(f"  ⚠️ Skipping JE #{entry_number} line - ClassRef does not belong to GA (8005): {class_ref.get('name', 'N/A')}")
                            skipped_count += 1
                            continue
                    # If no ClassRef but account is 8005, include it (assume it's GA)
                    elif account_num != '8005':
                        # If no ClassRef and not account 8005, skip
                        logger.debug(f"  ⚠️ Skipping JE #{entry_number} line - No ClassRef and account is not 8005")
                        skipped_count += 1
                        continue
                    
                    # Get amount and posting type
                    amount = float(line.get('Amount', 0))
                    posting_type = journal_detail.get('PostingType', '')
                    
                    # Debits increase expenses, Credits decrease expenses
                    if posting_type != 'Debit':
                        logger.debug(f"  ⚠️ Skipping JE #{entry_number} line - PostingType is '{posting_type}' (not Debit)")
                        skipped_count += 1
                        continue
                    
                    if amount == 0:
                        logger.debug(f"  ⚠️ Skipping JE #{entry_number} line - Zero amount")
                        skipped_count += 1
                        continue
                    
                    # Extract project name from Entity
                    project_name = None
                    entity = line.get('Entity', {})
                    entity_ref = entity.get('EntityRef', {})
                    
                    if entity_ref:
                        entity_name = entity_ref.get('name', '')
                        if entity_name:
                            # Handle "Parent:Project" format
                            if ':' in entity_name:
                                project_name = entity_name.split(':')[-1].strip()
                            else:
                                project_name = entity_name.strip()
                            
                            # Normalize project name
                            normalized = self._normalize_project_name(project_name)
                            if normalized:
                                project_name = normalized
                    
                    # Try line Description
                    line_description = line.get('Description', '')
                    if not project_name and line_description:
                        extracted = self._extract_project_from_description(line_description)
                        if extracted:
                            project_name = extracted
                    
                    # Try transaction-level description
                    txn_description = entry.get('PrivateNote', '') or entry.get('Description', '')
                    if not project_name and txn_description:
                        extracted = self._extract_project_from_description(txn_description)
                        if extracted:
                            project_name = extracted
                    
                    # If still no project name, categorize as "Unassigned"
                    if not project_name:
                        project_name = "Unassigned"
                        logger.debug(f"  ⚠️ JE #{entry_number}: No project name found for {account_name} (Amount: ${amount:,.2f}) - Categorizing as 'Unassigned'")
                    
                    # Add to result
                    if project_name not in ga_data[account_num]:
                        ga_data[account_num][project_name] = 0.0
                    
                    ga_data[account_num][project_name] += abs(amount)
                    processed_count += 1
                    
                    logger.info(f"  ✅ JE #{entry_number}: {account_num} → {project_name} = ${abs(amount):,.2f}")
            
            # Log summary
            logger.info("="*80)
            logger.info("JOURNAL ENTRIES GA SUMMARY:")
            logger.info(f"  Processed: {processed_count} lines")
            logger.info(f"  Skipped: {skipped_count} lines")
            for account_num, projects in ga_data.items():
                if projects:
                    total = sum(projects.values())
                    logger.info(f"  Account {account_num}: {len(projects)} projects, Total: ${total:,.2f}")
                    for project_name, project_amount in sorted(projects.items(), key=lambda x: x[1], reverse=True)[:5]:
                        logger.info(f"    • {project_name}: ${project_amount:,.2f}")
            logger.info("="*80)
            
            return ga_data
            
        except Exception as e:
            logger.error(f"Error querying journal entries for GA: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def _get_bills_for_ga(
        self,
        start_date: str,
        end_date: str,
        account_numbers: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Query bills for GA accounts (e.g., 8005)
        
        Similar to _get_bills_for_cogs but filters FOR GA transactions.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            account_numbers: List of account numbers to query (e.g., ['8005'])
        
        Returns:
            Dictionary mapping account numbers to project breakdowns
        """
        try:
            logger.info("="*80)
            logger.info("FETCHING GA EXPENSES FROM BILLS")
            logger.info(f"Accounts: {account_numbers}")
            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info("="*80)
            
            # Query Bill transactions
            query = (
                f"SELECT * FROM Bill "
                f"WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' "
                f"MAXRESULTS 1000"
            )
            
            params = {'query': query, 'minorversion': '65'}
            data = self._make_request('query', params)
            
            if not data or 'QueryResponse' not in data:
                logger.warning("No bill data returned from query")
                return {}
            
            # Initialize result structure
            ga_data = {}
            for account_num in account_numbers:
                ga_data[account_num] = {}
            
            bills = data['QueryResponse'].get('Bill', [])
            logger.info(f"Processing {len(bills)} bills for GA")
            
            processed_count = 0
            skipped_count = 0
            
            for bill in bills:
                bill_id = bill.get('Id', 'N/A')
                lines = bill.get('Line', [])
                
                if not lines:
                    continue
                
                for line in lines:
                    expense_line = line.get('ExpenseLineDetail', {})
                    if not expense_line:
                        continue
                    
                    # Get account reference first
                    account_ref = expense_line.get('AccountRef', {})
                    account_name = account_ref.get('name', '')
                    
                    if not account_name:
                        continue
                    
                    # Extract account number
                    account_num = None
                    account_match = re.search(r'(\d{4})', account_name)
                    if account_match:
                        account_num = account_match.group(1)
                    
                    # Check if this is for one of our GA accounts
                    if not account_num or account_num not in account_numbers:
                        continue
                    
                    # Check ClassRef - ONLY include if it belongs to GA (8005) OR if account is 8005 (some transactions may not have ClassRef)
                    class_ref = expense_line.get('ClassRef', {})
                    if class_ref:
                        # If ClassRef exists, it must belong to GA
                        if not self._classref_belongs_to_ga(class_ref):
                            skipped_count += 1
                            continue
                    # If no ClassRef but account is 8005, include it (assume it's GA)
                    elif account_num != '8005':
                        # If no ClassRef and not account 8005, skip
                        skipped_count += 1
                        continue
                    
                    # Get amount
                    amount = float(line.get('Amount', 0))
                    if amount == 0:
                        continue
                    
                    # Extract project from CustomerRef
                    project_name = None
                    customer_ref = expense_line.get('CustomerRef', {})
                    if customer_ref:
                        customer_name = customer_ref.get('name', '')
                        if customer_name:
                            normalized = self._normalize_project_name(customer_name)
                            if normalized:
                                project_name = normalized
                    
                    # If still no project name, categorize as "Unassigned"
                    if not project_name:
                        project_name = "Unassigned"
                    
                    # Add to result
                    if project_name not in ga_data[account_num]:
                        ga_data[account_num][project_name] = 0.0
                    
                    ga_data[account_num][project_name] += abs(amount)
                    processed_count += 1
                    
                    logger.info(f"  ✅ Bill {bill_id}: {account_num} → {project_name} = ${abs(amount):,.2f}")
            
            # Log summary
            logger.info("="*80)
            logger.info("BILLS GA SUMMARY:")
            logger.info(f"  Processed: {processed_count} lines")
            logger.info(f"  Skipped: {skipped_count} lines")
            for account_num, projects in ga_data.items():
                if projects:
                    total = sum(projects.values())
                    logger.info(f"  Account {account_num}: {len(projects)} projects, Total: ${total:,.2f}")
            logger.info("="*80)
            
            return ga_data
            
        except Exception as e:
            logger.error(f"Error querying bills for GA: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def _get_expenses_for_ga(
        self,
        start_date: str,
        end_date: str,
        account_numbers: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Query expense/purchase transactions for GA accounts (e.g., 8005)
        
        Similar to _get_expenses_for_cogs but filters FOR GA transactions.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            account_numbers: List of account numbers to query (e.g., ['8005'])
        
        Returns:
            Dictionary mapping account numbers to project breakdowns
        """
        try:
            logger.info("="*80)
            logger.info("FETCHING GA EXPENSES FROM EXPENSES/PURCHASES")
            logger.info(f"Accounts: {account_numbers}")
            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info("="*80)
            
            # Query Purchase transactions
            purchase_query = (
                f"SELECT * FROM Purchase "
                f"WHERE TxnDate >= '{start_date}' AND TxnDate <= '{end_date}' "
                f"MAXRESULTS 1000"
            )
            
            params = {'query': purchase_query, 'minorversion': '65'}
            purchase_data = self._make_request('query', params)
            
            # Initialize result structure
            ga_data = {}
            for account_num in account_numbers:
                ga_data[account_num] = {}
            
            total_processed = 0
            total_skipped = 0
            
            # Process Purchase transactions
            if purchase_data and 'QueryResponse' in purchase_data:
                purchases = purchase_data['QueryResponse'].get('Purchase', [])
                logger.info(f"Processing {len(purchases)} Purchase transactions for GA")
                
                processed_count = 0
                skipped_count = 0
                
                for purchase in purchases:
                    txn_id = purchase.get('Id', 'N/A')
                    lines = purchase.get('Line', [])
                    
                    for line in lines:
                        expense_line = line.get('ExpenseLineDetail', {})
                        if not expense_line:
                            continue
                        
                        # Get account reference first
                        account_ref = expense_line.get('AccountRef', {})
                        account_name = account_ref.get('name', '')
                        
                        if not account_name:
                            continue
                        
                        # Extract account number
                        account_num = None
                        account_match = re.search(r'(\d{4})', account_name)
                        if account_match:
                            account_num = account_match.group(1)
                        
                        # Check if this is for one of our GA accounts
                        if not account_num or account_num not in account_numbers:
                            continue
                        
                        # Check ClassRef - ONLY include if it belongs to GA (8005) OR if account is 8005 (some transactions may not have ClassRef)
                        class_ref = expense_line.get('ClassRef', {})
                        if class_ref:
                            # If ClassRef exists, it must belong to GA
                            if not self._classref_belongs_to_ga(class_ref):
                                skipped_count += 1
                                continue
                        # If no ClassRef but account is 8005, include it (assume it's GA)
                        elif account_num != '8005':
                            # If no ClassRef and not account 8005, skip
                            skipped_count += 1
                            continue
                        
                        # Get amount
                        amount = float(line.get('Amount', 0))
                        if amount == 0:
                            continue
                        
                        # Extract project from CustomerRef
                        project_name = None
                        customer_ref = expense_line.get('CustomerRef', {})
                        if customer_ref:
                            customer_name = customer_ref.get('name', '')
                            if customer_name:
                                normalized = self._normalize_project_name(customer_name)
                                if normalized:
                                    project_name = normalized
                        
                        # If still no project name, categorize as "Unassigned"
                        if not project_name:
                            project_name = "Unassigned"
                        
                        # Add to result
                        if project_name not in ga_data[account_num]:
                            ga_data[account_num][project_name] = 0.0
                        
                        ga_data[account_num][project_name] += abs(amount)
                        processed_count += 1
                        total_processed += 1
                        
                        logger.info(f"  ✅ Purchase {txn_id}: {account_num} → {project_name} = ${abs(amount):,.2f}")
                
                total_skipped += skipped_count
                logger.info(f"  Purchase: Processed {processed_count} lines, skipped {skipped_count} lines")
            
            # Log summary
            logger.info("="*80)
            logger.info("EXPENSES/PURCHASES GA SUMMARY:")
            logger.info(f"  Total Processed: {total_processed} lines")
            logger.info(f"  Total Skipped: {total_skipped} lines")
            for account_num, projects in ga_data.items():
                if projects:
                    total = sum(projects.values())
                    logger.info(f"  Account {account_num}: {len(projects)} projects, Total: ${total:,.2f}")
            logger.info("="*80)
            
            return ga_data
            
        except Exception as e:
            logger.error(f"Error querying expenses for GA: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def _merge_cogs_data(
        self,
        target: Dict[str, Dict[str, float]],
        source: Dict[str, Dict[str, float]]
    ) -> None:
        """
        Merge COGS data from multiple sources (Journal Entries + Bills + Expenses)
        
        Combines project breakdowns from different transaction types, summing amounts
        for the same account + project combinations.
        
        Args:
            target: Target dictionary to merge into (modified in place)
            source: Source dictionary to merge from
        """
        for account_num, projects in source.items():
            if account_num not in target:
                target[account_num] = {}
            
            for project, amount in projects.items():
                if project in target[account_num]:
                    target[account_num][project] += amount
                else:
                    target[account_num][project] = amount
    
    def _parse_pl_detail_row(
        self,
        row: Dict,
        account_numbers: List[str],
        expense_by_project: Dict[str, Dict[str, float]],
        parent_customer_name: str = None
    ):
        """
        Parse a row from ProfitAndLossDetail report to extract expenses by project
        
        When columns=customer, the report structure shows:
        - Top-level Section: Income, COGS, Expenses
        - Nested Section: Customer groups (customer name in Header)
        - Data rows: Account rows with ColData containing account info and amounts
        
        Args:
            row: Row dictionary from ProfitAndLossDetail report
            account_numbers: List of account numbers to filter (e.g., ['5001', '5011'])
            expense_by_project: Dictionary to accumulate results
            parent_customer_name: Customer name from parent Section (for tracking)
        """
        try:
            # Handle different row types (Section, Data, Summary)
            row_type = row.get('type', '')
            
            # Extract customer name from Section Header if this is a Section
            current_customer_name = parent_customer_name
            if row_type == 'Section' and 'Header' in row:
                header = row.get('Header', {})
                if 'ColData' in header:
                    header_cols = header.get('ColData', [])
                    # Customer name is typically in the first column of Section header
                    if header_cols and len(header_cols) > 0:
                        header_value = header_cols[0].get('value', '').strip()
                        # Check if this looks like a customer/project name (not a section name like "Income", "COGS")
                        section_keywords = ['income', 'cogs', 'cost of goods sold', 'expenses', 'other income', 'other expenses']
                        if header_value and not any(keyword in header_value.lower() for keyword in section_keywords):
                            # This might be a customer name
                            if any(indicator in header_value.lower() for indicator in ['a6', 'tws', 'cdsp', 'perigean', 'dmva', 'cross benefits']):
                                current_customer_name = header_value
                                logger.debug(f"  📍 Found customer name in Section Header: '{current_customer_name}'")
            
            # If this row has nested rows (Sections), process them recursively
            if 'Rows' in row and row.get('Rows'):
                nested_rows = row['Rows'].get('Row', [])
                if isinstance(nested_rows, list):
                    for nested_row in nested_rows:
                        self._parse_pl_detail_row(nested_row, account_numbers, expense_by_project, current_customer_name)
                elif isinstance(nested_rows, dict):
                    self._parse_pl_detail_row(nested_rows, account_numbers, expense_by_project, current_customer_name)
            
            # For Data rows, extract account and customer information
            if row_type == 'Data' or 'ColData' in row:
                col_data = row.get('ColData', [])
                if not col_data or len(col_data) < 2:
                    logger.debug(f"  ⚠️ Skipping row - insufficient ColData (length: {len(col_data) if col_data else 0})")
                    return
                
                # Log ColData for debugging (for first few rows)
                if account_numbers and ('5001' in account_numbers or '5011' in account_numbers):
                    logger.debug(f"  🔍 Row ColData: {[col.get('value', '')[:50] for col in col_data[:5]]}")
                
                # Extract account name from first column
                account_name = col_data[0].get('value', '').strip()
                if not account_name:
                    logger.debug(f"  ⚠️ Skipping row - no account name in ColData[0]")
                    return
                
                # Extract account number from account name
                account_match = re.match(r'^(\d{4})', account_name)
                if not account_match:
                    logger.debug(f"  ⚠️ Skipping row - no account number found in '{account_name}'")
                    return
                
                account_num = account_match.group(1)
                
                # Log for target accounts
                if account_num in account_numbers:
                    logger.info(f"  🔍 Processing row for account {account_num}: {account_name}")
                
                # Skip if not a target account
                if account_num not in account_numbers:
                    return
                
                # Extract amount from the appropriate column
                # The amount column varies - typically the last numeric column
                amount = 0.0
                for col in col_data:
                    amount_str = col.get('value', '').replace(',', '').replace('$', '').strip()
                    if amount_str:
                        try:
                            amount = float(amount_str)
                            if amount != 0:
                                break
                        except ValueError:
                            continue
                
                if amount == 0:
                    logger.debug(f"  ⚠️ Skipping row - zero amount for {account_name}")
                    return
                
                logger.info(f"  💰 Found {account_name}: ${amount:,.2f}")
                
                # Extract customer/project name from ColData
                # Based on the raw JSON structure:
                # - ColData[0]: Account name (e.g., "5001 Salaries & wages")
                # - ColData[1]: Date (e.g., "2025-02-25")
                # - ColData[2]: Transaction type (e.g., "JournalEntry")
                # - ColData[3]: Vendor/customer name (often empty or vendor name)
                # - ColData[4]: Class/department code (e.g., "04 Engineering", "02 Client Services")
                # - ColData[5]: Description (e.g., "[Rippling] Salary for 2-25-0022 VA CIE...")
                project_name = None
                
                # Priority 1: Check ColData[5] (description) for project names
                if len(col_data) > 5:
                    description = col_data[5].get('value', '').strip()
                    if description:
                        project_name = self._extract_project_from_description(description)
                        if project_name:
                            logger.debug(f"  ✓ Extracted project from description (ColData[5]): '{project_name}'")
                
                # Priority 2: Check ColData[4] (class code) - but skip if it's just a department code
                if not project_name and len(col_data) > 4:
                    class_code = col_data[4].get('value', '').strip()
                    if class_code:
                        # Try to normalize it (will skip if it's just a department code)
                        normalized = self._normalize_project_name(class_code)
                        if normalized:
                            project_name = normalized
                            logger.debug(f"  ✓ Extracted project from class code (ColData[4]): '{project_name}'")
                
                # Priority 3: Check ColData[3] (vendor/customer name) - but only if it looks like a project
                if not project_name and len(col_data) > 3:
                    vendor_name = col_data[3].get('value', '').strip()
                    if vendor_name:
                        normalized = self._normalize_project_name(vendor_name)
                        if normalized:
                            project_name = normalized
                            logger.debug(f"  ✓ Extracted project from vendor name (ColData[3]): '{project_name}'")
                
                # Priority 4: Check other ColData columns for project indicators
                if not project_name:
                    for i, col in enumerate(col_data[1:], start=1):  # Skip first column (account name)
                        col_value = col.get('value', '').strip()
                        if col_value and not col_value.replace(',', '').replace('$', '').replace('-', '').strip().isdigit():
                            # This might be a project name (not a number)
                            normalized = self._normalize_project_name(col_value)
                            if normalized:
                                project_name = normalized
                                logger.debug(f"  ✓ Extracted project from ColData[{i}]: '{project_name}'")
                                break
                
                # Priority 5: Check for customer reference in the row structure
                if not project_name:
                    customer_ref = row.get('CustomerRef', {})
                    if customer_ref:
                        customer_name = customer_ref.get('name', '')
                        if customer_name:
                            normalized = self._normalize_project_name(customer_name)
                            if normalized:
                                project_name = normalized
                                logger.debug(f"  ✓ Extracted project from CustomerRef: '{project_name}'")
                
                # Check ClassRef - if it belongs to GA (8005), skip this row
                class_ref = row.get('ClassRef', {})
                if class_ref and self._classref_belongs_to_ga(class_ref):
                    logger.debug(f"  ⚠️ Skipping P&L Detail row - ClassRef belongs to GA (8005): {class_ref.get('name', 'N/A')}")
                    return
                
                # Determine transaction type from row data
                # Bills map to 5011 (Direct Labor), other transactions map to 5001 (Billable Salaries)
                transaction_type = row.get('TransactionType', '')
                if transaction_type == 'Bill':
                    # Bills are Direct Labor (5011)
                    target_account = '5011'
                    account_full_name = "5011 COGS:Direct 1099 Labor"
                else:
                    # Other transactions (Journal Entry, etc.) are Billable Salaries (5001)
                    target_account = '5001'
                    if account_num == '5001' and 'salaries' in account_name.lower():
                        account_full_name = "Billable Salaries and Wages"
                    else:
                        account_full_name = account_name
                
                # Only process if this matches the target account
                if account_num != target_account:
                    logger.info(f"  ⚠️ Skipping row - account {account_num} != target {target_account} (transaction_type: {transaction_type})")
                    return
                
                logger.info(f"  ✓ Matched account {account_num} to target {target_account} ({transaction_type})")
                
                # If no project name found, try using parent customer name from Section
                if not project_name:
                    if parent_customer_name:
                        normalized = self._normalize_project_name(parent_customer_name)
                        if normalized:
                            project_name = normalized
                            logger.debug(f"  ✓ Extracted project from parent customer name: '{project_name}'")
                
                # If still no project name found, categorize as "Unallocated"
                if not project_name:
                    project_name = "Unallocated"
                    logger.debug(f"  ⚠️ No project name found for {account_name} (Amount: ${amount:,.2f}) - Categorizing as 'Unallocated'")
                
                # Add to result
                if account_full_name not in expense_by_project:
                    expense_by_project[account_full_name] = {}
                
                if project_name not in expense_by_project[account_full_name]:
                    expense_by_project[account_full_name][project_name] = 0.0
                
                # Use absolute value (expenses can be negative)
                expense_by_project[account_full_name][project_name] += abs(amount)
                
                logger.info(f"  ✅ SUCCESS: {account_full_name} → {project_name}: ${abs(amount):,.2f} ({transaction_type or 'Transaction'})")
        
        except Exception as e:
            logger.error(f"Error parsing P&L Detail row: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _process_expense_transaction(
        self,
        transaction: Dict,
        transaction_type: str,
        account_numbers: List[str],
        expense_by_project: Dict[str, Dict[str, float]]
    ):
        """
        Process a single Bill or Purchase transaction to extract expenses by project
        
        Args:
            transaction: Bill or Purchase transaction object
            transaction_type: 'Bill' or 'Purchase'
            account_numbers: List of account numbers to filter (e.g., ['5001', '5011'])
            expense_by_project: Dictionary to accumulate results
        """
        try:
            # Get transaction-level customer reference
            transaction_customer_ref = transaction.get('CustomerRef', {})
            transaction_customer_name = transaction_customer_ref.get('name', '')
            
            # Process Line items
            lines = transaction.get('Line', [])
            if not lines:
                return
            
            for line in lines:
                # Skip group lines (they don't have direct account references)
                if line.get('GroupLineDetail'):
                    continue
                
                # Check if this line item has an account reference
                # Bill transactions use ExpenseLineDetail, Purchase transactions may use various types
                line_detail = (
                    line.get('ExpenseLineDetail') or 
                    line.get('ItemBasedExpenseLineDetail') or 
                    line.get('AccountBasedExpenseLineDetail') or
                    line.get('SalesItemLineDetail')
                )
                if not line_detail:
                    continue
                
                account_ref = line_detail.get('AccountRef', {})
                account_name = account_ref.get('name', '')
                account_id = account_ref.get('value', '')
                
                # Check ClassRef first - if it belongs to GA (8005), skip this transaction
                class_ref = line_detail.get('ClassRef', {})
                if class_ref and self._classref_belongs_to_ga(class_ref):
                    logger.debug(f"  ⚠️ Skipping {transaction_type} transaction - ClassRef belongs to GA (8005): {class_ref.get('name', 'N/A')}")
                    continue
                
                # Extract account number from account name (e.g., "5001 Salaries & wages" -> "5001")
                account_num = None
                if account_name:
                    account_match = re.match(r'^(\d{4})', account_name)
                    if account_match:
                        account_num = account_match.group(1)
                
                # For Bills: they should map to 5011 (Direct Labor)
                # For other transactions: they should map to 5001 (Billable Salaries)
                if transaction_type == 'Bill':
                    # Bills are Direct Labor (5011)
                    target_account = '5011'
                else:
                    # Other transactions (Purchase, etc.) are Billable Salaries (5001)
                    target_account = '5001'
                
                # Skip if not a target account
                if not account_num or account_num not in account_numbers:
                    continue
                
                # Get amount from line
                amount = float(line.get('Amount', 0))
                if amount == 0:
                    continue
                
                # Extract project name from CustomerRef (Customer column)
                # This is the primary source for project assignment
                project_name = None
                
                # Priority 1: Line-level CustomerRef (if present)
                line_customer_ref = line_detail.get('CustomerRef', {})
                if line_customer_ref:
                    customer_name = line_customer_ref.get('name', '')
                    if customer_name:
                        # Use customer name directly (group same customer names together)
                        project_name = customer_name
                        logger.info(f"  ✓ Extracted project from line CustomerRef: '{project_name}'")
                
                # Priority 2: Transaction-level CustomerRef
                if not project_name and transaction_customer_name:
                    # Use customer name directly (group same customer names together)
                    project_name = transaction_customer_name
                    logger.info(f"  ✓ Extracted project from transaction CustomerRef: '{project_name}'")
                
                # Skip if no project name found
                if not project_name:
                    logger.debug(f"  ⚠️ No project name found for {transaction_type} transaction (Account: {account_name}, Amount: ${amount:,.2f})")
                    continue
                
                # Map account number to account name (handle renamed accounts)
                # Bills map to 5011 (Direct Labor), Journal Entries map to 5001 (Billable Salaries)
                if transaction_type == 'Bill':
                    account_full_name = "5011 COGS:Direct 1099 Labor"  # Direct Labor
                elif account_num == '5001' and 'salaries' in account_name.lower():
                    account_full_name = "Billable Salaries and Wages"
                else:
                    account_full_name = account_name
                
                # Add to result
                if account_full_name not in expense_by_project:
                    expense_by_project[account_full_name] = {}
                
                if project_name not in expense_by_project[account_full_name]:
                    expense_by_project[account_full_name][project_name] = 0.0
                
                # Use absolute value (expenses can be negative)
                expense_by_project[account_full_name][project_name] += abs(amount)
                
                logger.info(f"  📊 {account_full_name} → {project_name}: ${abs(amount):,.2f} ({transaction_type})")
        
        except Exception as e:
            logger.error(f"Error processing {transaction_type} transaction: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _process_journal_entry_expense(
        self,
        journal_entry: Dict,
        account_numbers: List[str],
        expense_by_project: Dict[str, Dict[str, float]],
        journal_entry_stats: Dict = None
    ):
        """
        Process a Journal Entry transaction to extract expenses by project
        
        Args:
            journal_entry: JournalEntry transaction object
            account_numbers: List of account numbers to filter (e.g., ['5001', '5011'])
            expense_by_project: Dictionary to accumulate results
        """
        try:
            # Get transaction-level fields (may contain project info)
            txn_description = journal_entry.get('PrivateNote', '') or journal_entry.get('Description', '')
            txn_doc_number = journal_entry.get('DocNumber', '')
            logger.info(f"  🔍 JournalEntry Transaction: DocNumber='{txn_doc_number}', Description='{txn_description[:200] if txn_description else ''}'")
            
            # Process Line items
            lines = journal_entry.get('Line', [])
            if not lines:
                return
            
            for line in lines:
                journal_detail = line.get('JournalEntryLineDetail', {})
                if not journal_detail:
                    continue
                
                # Check ClassRef first - if it belongs to GA (8005), skip this line
                class_ref = journal_detail.get('ClassRef', {})
                if class_ref and self._classref_belongs_to_ga(class_ref):
                    logger.debug(f"  ⚠️ Skipping JournalEntry line - ClassRef belongs to GA (8005): {class_ref.get('name', 'N/A')}")
                    continue
                
                # Get account reference
                account_ref = journal_detail.get('AccountRef', {})
                account_name = account_ref.get('name', '')
                
                # Log full line structure for debugging (for target accounts only)
                if account_name and ('500' in account_name or 'salar' in account_name.lower() or 'wage' in account_name.lower()):
                    logger.info(f"  🔍 JournalEntry Line structure keys: {list(line.keys())}")
                    logger.info(f"  🔍 JournalEntry Line Description field: {line.get('Description', 'NOT FOUND')}")
                    logger.info(f"  🔍 JournalEntry Line Detail keys: {list(journal_detail.keys())}")
                    logger.info(f"  🔍 JournalEntry Line Detail Description: {journal_detail.get('Description', 'NOT FOUND')}")
                
                # Log all accounts that might be relevant (for debugging)
                if account_name and ('500' in account_name or 'salar' in account_name.lower() or 'wage' in account_name.lower()):
                    logger.info(f"  🔍 JournalEntry: Found account '{account_name}' (checking if target...)")
                
                # Extract account number from account name
                # Account names can be in different formats:
                # - "5001 Salaries & wages" (starts with number)
                # - "COGS:Salaries & wages" (has prefix, need to match by name)
                # - "5011 Direct 1099 Labor" (starts with number)
                account_num = None
                if account_name:
                    # Try to extract 4-digit account number from anywhere in the name
                    account_match = re.search(r'(\d{4})', account_name)
                    if account_match:
                        account_num = account_match.group(1)
                    else:
                        # If no number found, try to match by account name patterns
                        account_name_lower = account_name.lower()
                        # Match account 5001 by name patterns
                        if 'salaries' in account_name_lower and 'wage' in account_name_lower:
                            # Check if it's in COGS (not G&A)
                            if 'cogs' in account_name_lower or 'cost of goods' in account_name_lower:
                                account_num = '5001'
                                logger.info(f"  🔍 JournalEntry: Matched account 5001 by name pattern: '{account_name}'")
                        # Match account 5011 by name patterns
                        elif 'direct' in account_name_lower and '1099' in account_name_lower and 'labor' in account_name_lower:
                            account_num = '5011'
                            logger.info(f"  🔍 JournalEntry: Matched account 5011 by name pattern: '{account_name}'")
                
                # Journal Entries should map to 5001 (Billable Salaries)
                # Only process if it's account 5001
                if account_num != '5001':
                    continue
                
                # Skip if not a target account
                if not account_num or account_num not in account_numbers:
                    continue
                
                # Log that we found a target account line
                logger.info(f"  🔍 Found target account in JournalEntry: {account_name} (Account #: {account_num})")
                
                # Get amount and posting type
                amount = float(line.get('Amount', 0))
                posting_type = journal_detail.get('PostingType', '')
                
                # For expense accounts, debits increase expenses
                # We want the absolute value of expenses
                if posting_type == 'Debit' and account_num in account_numbers:
                    expense_amount = abs(amount)
                    logger.info(f"  🔍 JournalEntry: {account_name} - Debit ${expense_amount:,.2f}")
                elif posting_type == 'Credit':
                    # Credits decrease expenses (negative), so we skip or treat as negative
                    logger.info(f"  🔍 JournalEntry: {account_name} - Credit ${abs(amount):,.2f} (skipping)")
                    continue
                else:
                    logger.info(f"  🔍 JournalEntry: {account_name} - Unknown posting type: {posting_type}")
                    continue
                
                if expense_amount == 0:
                    logger.info(f"  🔍 JournalEntry: {account_name} - Zero amount, skipping")
                    continue
                
                # Extract project name from various fields
                project_name = None
                
                # Priority 1: ProjectRef (if present at line level)
                project_ref = line.get('ProjectRef', {})
                if project_ref:
                    project_ref_name = project_ref.get('name', '')
                    if project_ref_name:
                        logger.info(f"  🔍 JournalEntry: Found ProjectRef name: '{project_ref_name}'")
                        project_name = self._extract_project_name(project_ref_name)
                        if project_name:
                            logger.info(f"  ✓ Extracted project from JournalEntry ProjectRef: '{project_name}'")
                        else:
                            logger.info(f"  ⚠️ ProjectRef name '{project_ref_name}' doesn't match project criteria")
                
                # Priority 2: EntityRef (if present)
                if not project_name:
                    entity = line.get('Entity', {})
                    entity_ref = entity.get('EntityRef', {})
                    if entity_ref:
                        entity_name = entity_ref.get('name', '')
                        if entity_name:
                            logger.info(f"  🔍 JournalEntry: Found EntityRef name: '{entity_name}'")
                            project_name = self._extract_project_name(entity_name)
                            if project_name:
                                logger.info(f"  ✓ Extracted project from JournalEntry EntityRef: '{project_name}'")
                            else:
                                logger.info(f"  ⚠️ EntityRef name '{entity_name}' doesn't match project criteria")
                        else:
                            logger.info(f"  🔍 JournalEntry: EntityRef present but no name field")
                    else:
                        logger.info(f"  🔍 JournalEntry: No EntityRef found in line")
                
                # Priority 3: Line-level Description (search for project keywords)
                # NOTE: Description is at the LINE level, not in journal_detail!
                # Map descriptions like "Agile Six Enterprise Services" to "A6 Enterprise Services"
                if not project_name:
                    line_description = line.get('Description', '')
                    if line_description:
                        logger.info(f"  🔍 JournalEntry: Checking line-level Description: '{line_description[:200]}...'")
                        # Project names used on income side (standard format)
                        project_keywords = [
                            'A6 Enterprise Services', 'A6 Surge Support', 'A6 DHO',
                            'A6 Financial Management', 'A6 CIE', 'A6 Cross Benefits',
                            'A6 CHAMPVA', 'A6 Toxic Exposure', 'A6 VA Form Engine',
                            'CDSP', 'TWS FLRA', 'Perigean', 'DMVA'
                        ]
                        # Mapping from variations to standard names
                        project_variations = {
                            'agile six enterprise services': 'A6 Enterprise Services',
                            'agile six surge support': 'A6 Surge Support',
                            'agile six dho': 'A6 DHO',
                            'agile six financial management': 'A6 Financial Management',
                            'agile six cie': 'A6 CIE',
                            'agile six cross benefits': 'A6 Cross Benefits',
                            'agile six champva': 'A6 CHAMPVA',
                            'agile six toxic exposure': 'A6 Toxic Exposure',
                            'agile six va form engine': 'A6 VA Form Engine',
                        }
                        
                        description_lower = line_description.lower()
                        
                        # First, check for exact project keyword matches
                        for keyword in project_keywords:
                            if keyword.lower() in description_lower:
                                project_name = keyword
                                logger.info(f"  ✓ Extracted project from JournalEntry line Description: '{project_name}'")
                                break
                        
                        # If no exact match, check for variations (e.g., "Agile Six Enterprise Services")
                        if not project_name:
                            for variation, standard_name in project_variations.items():
                                if variation in description_lower:
                                    project_name = standard_name
                                    logger.info(f"  ✓ Extracted project from JournalEntry line Description (variation match): '{variation}' -> '{project_name}'")
                                    break
                        
                        if not project_name:
                            logger.info(f"  ⚠️ JournalEntry: Line Description exists but no project keywords found")
                    else:
                        logger.info(f"  🔍 JournalEntry: No Description found at line level")
                
                # Priority 4: ClassRef (if present in journal_detail)
                if not project_name:
                    class_ref = journal_detail.get('ClassRef', {})
                    if class_ref:
                        class_name = class_ref.get('name', '')
                        if class_name:
                            logger.info(f"  🔍 JournalEntry: Found ClassRef name: '{class_name}'")
                            project_name = self._extract_project_name(class_name)
                            if project_name:
                                logger.info(f"  ✓ Extracted project from JournalEntry ClassRef: '{project_name}'")
                            else:
                                logger.info(f"  ⚠️ ClassRef name '{class_name}' doesn't match project criteria")
                
                # Priority 5: Transaction-level Description or PrivateNote (search for project keywords)
                if not project_name and txn_description:
                    logger.info(f"  🔍 JournalEntry: Checking transaction-level Description: '{txn_description[:200]}...'")
                    project_keywords = [
                        'A6 Enterprise Services', 'A6 Surge Support', 'A6 DHO',
                        'A6 Financial Management', 'A6 CIE', 'A6 Cross Benefits',
                        'A6 CHAMPVA', 'A6 Toxic Exposure', 'A6 VA Form Engine',
                        'CDSP', 'TWS FLRA', 'Perigean', 'DMVA'
                    ]
                    for keyword in project_keywords:
                        if keyword.lower() in txn_description.lower():
                            project_name = keyword
                            logger.info(f"  ✓ Extracted project from JournalEntry transaction Description: '{project_name}'")
                            break
                    if not project_name:
                        logger.info(f"  ⚠️ JournalEntry: Transaction Description exists but no project keywords found")
                
                # If no project name found, categorize as "Unallocated" to ensure all expenses are included
                if not project_name:
                    # Check if there's a pattern in the description that might indicate category
                    line_description = line.get('Description', '')
                    description_lower = line_description.lower() if line_description else ''
                    
                    # Check for common patterns
                    if 'general and administrative' in description_lower or '9-general' in description_lower:
                        project_name = "General & Administrative"
                        logger.info(f"  ✓ Categorized as 'General & Administrative' from description pattern")
                    elif 'business development' in description_lower or '9-business' in description_lower:
                        project_name = "Business Development"
                        logger.info(f"  ✓ Categorized as 'Business Development' from description pattern")
                    else:
                        # Default to "Unallocated" for expenses without project names
                        project_name = "Unallocated"
                        logger.info(f"  ⚠️ No project name found - categorizing as 'Unallocated' (Account: {account_name}, Amount: ${expense_amount:,.2f})")
                
                # Map account number to account name (handle renamed accounts)
                account_full_name = account_name
                if account_num == '5001' and 'salaries' in account_name.lower():
                    account_full_name = "Billable Salaries and Wages"
                elif account_num == '5011':
                    account_full_name = account_name  # Keep original name for 5011
                
                # Add to result
                if account_full_name not in expense_by_project:
                    expense_by_project[account_full_name] = {}
                
                if project_name not in expense_by_project[account_full_name]:
                    expense_by_project[account_full_name][project_name] = 0.0
                
                expense_by_project[account_full_name][project_name] += expense_amount
                
                logger.info(f"  📊 {account_full_name} → {project_name}: ${expense_amount:,.2f} (JournalEntry)")
                
                # Track journal entry statistics
                if journal_entry_stats is not None:
                    doc_number = journal_entry.get('DocNumber', 'N/A')
                    if project_name not in journal_entry_stats['by_project']:
                        journal_entry_stats['by_project'][project_name] = set()
                    journal_entry_stats['by_project'][project_name].add(doc_number)
        
        except Exception as e:
            logger.error(f"Error processing JournalEntry transaction: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _classref_belongs_to_ga(self, class_ref: Dict) -> bool:
        """
        Check if a ClassRef belongs to 8005 (GA) or should funnel to COGS
        
        Based on the QBO Classes mapping:
        - 8005 Salaries and Wages (GA) belongs to GA
        - All other ClassRefs (01-06, 11-17) should funnel to COGS
        
        Args:
            class_ref: ClassRef dictionary from transaction
            
        Returns:
            True if ClassRef belongs to 8005 (GA), False if it should go to COGS
        """
        if not class_ref:
            return False
        
        class_name = class_ref.get('name', '').lower()
        if not class_name:
            return False
        
        # Check if this is specifically the 8005 GA class
        # Look for patterns like "8005", "salaries and wages (ga)", "ga", etc.
        ga_indicators = [
            '8005',
            'salaries and wages (ga)',
            'salaries & wages (ga)',
            'general & administrative',
            'general and administrative',
            'g&a'
        ]
        
        # Check if class name contains GA indicators
        if any(indicator in class_name for indicator in ga_indicators):
            return True
        
        # All other ClassRefs (01-06, 11-17) should funnel to COGS
        return False
    
    def _extract_project_name(self, name: str) -> Optional[str]:
        """
        Extract and normalize project name from customer/class name
        
        Args:
            name: Customer or class name (may be in "Company:Project" format)
        
        Returns:
            Normalized project name, or None if not a valid project
        """
        if not name:
            return None
        
        # Normalize from "Company:Project" format if present
        if ':' in name:
            # Format: "Agile Six Applications Inc.:A6 CIE" -> extract "A6 CIE"
            project_part = name.split(':')[-1].strip()
            if project_part:
                name = project_part
        
        # Check if it looks like a project name (has project indicators)
        project_indicators = ['a6', 'tws', 'cdsp', 'perigean', 'dmva']
        if not any(indicator in name.lower() for indicator in project_indicators):
            return None
        
        # Validate that it's not an expense category
        expense_category_keywords = [
            'cost of goods sold', 'cogs', 'expenses', 'income', 'revenue',
            'ordinary income', 'ordinary expenses', 'other income', 'other expenses',
            'gross profit', 'net income', 'operating income'
        ]
        if any(keyword in name.lower() for keyword in expense_category_keywords):
            return None
        
        return name
    
    def _extract_project_from_description(self, description: str) -> Optional[str]:
        """
        Extract and normalize project name from transaction description
        
        Args:
            description: Transaction description (e.g., "[Rippling] Salary for 2-25-0022 VA CIE...")
        
        Returns:
            Normalized project name, or None if not found
        """
        if not description:
            return None
        
        description_lower = description.lower()
        
        # Map description keywords to standard project names
        # This mapping should match the project names used on the income side
        project_keyword_mapping = {
            # A6 projects
            'a6 enterprise services': 'A6 Enterprise Services',
            'agile six enterprise services': 'A6 Enterprise Services',
            'a6 surge support': 'A6 Surge Support',
            'a6 dho': 'A6 DHO',
            'a6 financial management': 'A6 Financial Management',
            'a6 cie': 'A6 CIE',
            'va cie': 'A6 CIE',
            'a6 cross benefits': 'A6 Cross Benefits',
            'cross benefits': 'A6 Cross Benefits',
            'a6 champva': 'A6 CHAMPVA',
            'champva': 'A6 CHAMPVA',
            'a6 toxic exposure': 'A6 Toxic Exposure',
            'a6 va form engine': 'A6 VA Form Engine',
            'va form engine': 'A6 VA Form Engine',  # Also match without "A6" prefix
            # Other projects
            'tws flra': 'TWS FLRA',
            'flra': 'TWS FLRA',  # FLRA alone maps to TWS FLRA
            'cdsp': 'CDSP',
            'perigean': 'Perigean',
            'dmva': 'DMVA',
        }
        
        # Search for project keywords in description
        for keyword, project_name in project_keyword_mapping.items():
            if keyword in description_lower:
                logger.debug(f"  ✓ Extracted project '{project_name}' from description keyword '{keyword}'")
                return project_name
        
        # Also check for project codes in format like "2-25-0022 VA CIE" or "2-25-0025 Financial Management"
        # Pattern 1: Extract project code pattern (e.g., "VA CIE" or "VA Form Engine" from descriptions)
        # Match 2-3 word patterns starting with uppercase letters
        project_code_pattern = r'\b([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})?)\b'
        matches = re.findall(project_code_pattern, description.upper())
        for match in matches:
            # Map project codes to standard names
            code_mapping = {
                'VA CIE': 'A6 CIE',
                'VA CHAMPVA': 'A6 CHAMPVA',
                'VA FORM ENGINE': 'A6 VA Form Engine',
            }
            if match in code_mapping:
                logger.debug(f"  ✓ Extracted project '{code_mapping[match]}' from description code '{match}'")
                return code_mapping[match]
        
        # Pattern 2: Extract project codes like "2-25-0025 Financial Management" or "2-24-0015 VA Form Engine" → "A6 Financial Management" or "A6 VA Form Engine"
        # Format: "2-XX-XXXX Project Name" where XX is 24 or 25 and XXXX is a number
        project_code_with_name_pattern = r'2-(24|25)-\d{4}\s+([A-Z][a-zA-Z\s]+)'
        matches = re.findall(project_code_with_name_pattern, description)
        for match in matches:
            # match is a tuple: (year_code, project_name)
            project_name_candidate = match[1].strip() if isinstance(match, tuple) else match.strip()
            # Map known project code names to standard project names
            project_code_name_mapping = {
                'Financial Management': 'A6 Financial Management',
                'Enterprise Services': 'A6 Enterprise Services',
                'Surge Support': 'A6 Surge Support',
                'DHO': 'A6 DHO',
                'CIE': 'A6 CIE',
                'Cross Benefits': 'A6 Cross Benefits',
                'CHAMPVA': 'A6 CHAMPVA',
                'Toxic Exposure': 'A6 Toxic Exposure',
                'VA Form Engine': 'A6 VA Form Engine',
            }
            
            # Check for exact match
            if project_name_candidate in project_code_name_mapping:
                project_name = project_code_name_mapping[project_name_candidate]
                logger.debug(f"  ✓ Extracted project '{project_name}' from project code pattern '{project_name_candidate}'")
                return project_name
            
            # Check for partial match (e.g., "Financial Management" contains "Financial Management")
            for code_name, standard_name in project_code_name_mapping.items():
                if code_name.lower() in project_name_candidate.lower():
                    logger.debug(f"  ✓ Extracted project '{standard_name}' from project code pattern '{project_name_candidate}' (matched '{code_name}')")
                    return standard_name
        
        # Pattern 3: Extract FLRA project codes like "2-24-0018 FLRA" or "2-25-0026 FLRA" → "TWS FLRA"
        # Format: "2-XX-XXXX FLRA" where XX is 24 or 25 and XXXX is a number
        flra_project_code_pattern = r'2-(24|25)-\d{4}\s+FLRA'
        flra_matches = re.findall(flra_project_code_pattern, description, re.IGNORECASE)
        if flra_matches:
            logger.debug(f"  ✓ Extracted project 'TWS FLRA' from FLRA project code pattern")
            return 'TWS FLRA'
        
        # Pattern 4: Check for "FLRA" followed by task order info (e.g., "FLRA TO11", "FLRA TO14/TO16")
        flra_task_order_pattern = r'FLRA\s+TO\d+'
        if re.search(flra_task_order_pattern, description, re.IGNORECASE):
            logger.debug(f"  ✓ Extracted project 'TWS FLRA' from FLRA task order pattern")
            return 'TWS FLRA'
        
        return None
    
    def _normalize_project_name(self, project_name: str) -> Optional[str]:
        """
        Normalize project name to match income-side project names
        
        Args:
            project_name: Raw project name from expense data
        
        Returns:
            Normalized project name, or None if not a valid project
        """
        if not project_name:
            return None
        
        # First, try direct extraction from name
        normalized = self._extract_project_name(project_name)
        if normalized:
            return normalized
        
        # If that fails, try extracting from description
        normalized = self._extract_project_from_description(project_name)
        if normalized:
            return normalized
        
        # Check if it's a class code (e.g., "04 Engineering", "02 Client Services")
        # These are department codes, not project names - skip them
        class_code_pattern = r'^\d{2}\s+[A-Z]'
        if re.match(class_code_pattern, project_name):
            logger.debug(f"  ⚠️ Skipping class code (not a project name): '{project_name}'")
            return None
        
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
            
            # PHASE 2: Integrate project-level expense data for accounts 5001, 5011, and 8005
            logger.info("="*80)
            logger.info("PHASE 2: INTEGRATING PROJECT-LEVEL EXPENSE DATA")
            logger.info("="*80)
            try:
                # Get COGS project expenses (5001, 5011)
                project_expenses = self.get_expenses_by_project(
                    ['5001', '5011'],
                    start_date,
                    end_date
                )
                
                # Get GA project expenses (8005)
                ga_project_expenses = self.get_expenses_by_project_for_ga(
                    ['8005'],
                    start_date,
                    end_date
                )
                
                # Merge GA expenses into project_expenses
                if ga_project_expenses:
                    for account_name, projects in ga_project_expenses.items():
                        project_expenses[account_name] = projects
                
                if project_expenses:
                    logger.info(f"Retrieved project expenses for {len(project_expenses)} accounts")
                    
                    # Find and update secondary nodes in expense_hierarchy
                    for account_name, projects in project_expenses.items():
                        logger.info(f"Processing {account_name}: {len(projects)} projects")
                        
                        # Extract account number from account_name (e.g., "5001" from "Billable Salaries and Wages" or "5011 Direct 1099 Labor")
                        account_num = None
                        account_match = re.search(r'(\d{4})', account_name)
                        if account_match:
                            account_num = account_match.group(1)
                        
                        # Fallback: Map known account names to account numbers if regex doesn't find one
                        if not account_num:
                            account_name_mapping = {
                                'Billable Salaries and Wages': '5001',
                                'Salaries and Wages': '5001',
                                'Salaries & wages': '5001',
                                '5011 Direct 1099 Labor': '5011',
                                'Direct 1099 Labor': '5011',
                                '8005 Salaries and Wages': '8005',
                                'Salaries and Wages (GA)': '8005',
                            }
                            account_name_lower = account_name.lower()
                            for mapped_name, mapped_num in account_name_mapping.items():
                                if mapped_name.lower() in account_name_lower or account_name_lower in mapped_name.lower():
                                    account_num = mapped_num
                                    logger.info(f"  ✓ Mapped account name '{account_name}' to account number {account_num}")
                                    break
                        
                        if not account_num:
                            logger.warning(f"  ⚠️ Could not extract account number from '{account_name}'")
                            continue
                        
                        # Find this account in the expense_hierarchy by matching account number
                        # The hierarchical parser may use different name formats, so we match by account number
                        found = False
                        for primary_name, primary_data in expense_hierarchy.items():
                            if 'secondary' not in primary_data:
                                continue
                            
                            # Search through secondaries to find one that matches the account number
                            matching_secondary_name = None
                            for secondary_name in primary_data['secondary'].keys():
                                # Extract account number from secondary name
                                sec_match = re.search(r'(\d{4})', secondary_name)
                                if sec_match and sec_match.group(1) == account_num:
                                    matching_secondary_name = secondary_name
                                    break
                            
                            if matching_secondary_name:
                                # Add projects data to this secondary node
                                secondary_data = primary_data['secondary'][matching_secondary_name]
                                secondary_data['projects'] = projects
                                
                                # Validate: Check if project total exceeds secondary total (log warning if it does)
                                project_total = sum(projects.values())
                                secondary_total = secondary_data.get('total', 0)
                                if project_total > secondary_total * 1.01:  # Allow 1% tolerance for rounding
                                    logger.warning(f"  ⚠️ Project total (${project_total:,.2f}) exceeds secondary total (${secondary_total:,.2f}) for {matching_secondary_name}")
                                
                                logger.info(f"  ✅ Added project breakdown to {matching_secondary_name} under {primary_name}")
                                logger.info(f"     Projects: {list(projects.keys())}")
                                logger.info(f"     Project Total: ${project_total:,.2f} (Secondary Total: ${secondary_total:,.2f})")
                                found = True
                                break
                        
                        if not found:
                            logger.warning(f"  ⚠️ Could not find account {account_num} ({account_name}) in expense_hierarchy")
                            all_secondaries = [sec for prim in expense_hierarchy.values() for sec in prim.get('secondary', {}).keys()]
                            logger.warning(f"     Available secondaries: {all_secondaries}")
                            # Show account numbers in available secondaries for debugging
                            sec_account_nums = []
                            for sec in all_secondaries:
                                sec_match = re.search(r'(\d{4})', sec)
                                if sec_match:
                                    sec_account_nums.append(f"{sec_match.group(1)} ({sec})")
                            if sec_account_nums:
                                logger.warning(f"     Available secondary account numbers: {sec_account_nums}")
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
