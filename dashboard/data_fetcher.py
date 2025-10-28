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
                
                # Process Line items to find project references in descriptions
                lines = entry.get('Line', [])
                
                # Track credits and debits per project in this entry
                entry_project_amounts = {}
                
                for line in lines:
                    description = line.get('Description', '').lower()
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
                    
                    # Only process lines that affect revenue accounts
                    if not is_revenue_account:
                        continue
                    
                    # Search for project names in the description
                    for project_keyword in project_keywords:
                        if project_keyword.lower() in description:
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
                            
                            logger.info(f"📝 JE #{entry_number} ({txn_date}): Found '{project_keyword}' - {posting_type} ${amount:,.2f} to {account_name}")
                            break  # Found a match, move to next line
                
                # Add all project adjustments from this entry
                for project, adjustment in entry_project_amounts.items():
                    if adjustment != 0:  # Only add non-zero adjustments
                        if project in project_adjustments:
                            project_adjustments[project] += adjustment
                        else:
                            project_adjustments[project] = adjustment
                        
                        logger.info(f"✅ JE #{entry_number}: {project} adjustment = ${adjustment:,.2f} (Running total: ${project_adjustments[project]:,.2f})")
            
            logger.info(f"Retrieved journal entry adjustments from {len(project_adjustments)} projects")
            for project, amount in project_adjustments.items():
                logger.info(f"  📊 {project}: ${amount:,.2f}")
            
            return project_adjustments
            
        except Exception as e:
            logger.error(f"Error fetching journal entries: {e}")
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
            invoice_income = self.get_income_by_project(start_date, end_date)
            
            # Get sales receipt income (if applicable)
            logger.info("Fetching project-level income from sales receipts...")
            receipt_income = self.get_sales_receipts_by_project(start_date, end_date)

            # Get journal entry adjustments
            logger.info("Fetching journal entry adjustments...")
            journal_adjustments = self.get_journal_entries_by_project(start_date, end_date)
            
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
            if pl_data:
                parsed_data = self._parse_profit_loss_report(pl_data)
                if parsed_data:
                    expense_categories = parsed_data.get('expenses', {})
            
            if not expense_categories:
                logger.warning("No expense data found")
            
            # Calculate totals
            total_revenue = sum(project_income.values())
            total_expenses = sum(expense_categories.values())
            net_income = total_revenue - total_expenses
            
            logger.info("="*60)
            logger.info("Financial Data Summary:")
            logger.info(f"  Projects with income: {len(project_income)}")
            logger.info(f"  Expense categories: {len(expense_categories)}")
            logger.info(f"  Total revenue: ${total_revenue:,.2f}")
            logger.info(f"  Total expenses: ${total_expenses:,.2f}")
            logger.info(f"  Net income: ${net_income:,.2f}")
            logger.info("="*60)
            
            return {
                'income': project_income,
                'expenses': expense_categories,
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
        Parse QuickBooks Profit & Loss report data
        
        Args:
            pl_data: Raw P&L report data from QBO API
            
        Returns:
            Parsed financial data for Sankey diagram
        """
        try:
            income_sources = {}
            expense_categories = {}
            
            logger.info(f"Parsing P&L report structure: {list(pl_data.keys())}")
            
            # Navigate through the report structure - QBO API format
            # The response has ['Header', 'Columns', 'Rows'] directly, not wrapped in 'Report'
            if 'Rows' in pl_data:
                rows_data = pl_data['Rows']
                logger.info(f"Rows type: {type(rows_data)}")
                
                # Handle the actual QBO structure: Rows contains a 'Row' key with the actual data
                if isinstance(rows_data, dict) and 'Row' in rows_data:
                    rows = rows_data['Row']
                    logger.info(f"Found {len(rows)} rows in report")
                elif isinstance(rows_data, list):
                    rows = rows_data
                    logger.info(f"Found {len(rows)} rows in report (direct list)")
                else:
                    logger.error(f"Unexpected Rows structure: {type(rows_data)} - {rows_data}")
                    return None
                
                for i, row in enumerate(rows):
                    logger.info(f"Row {i}: {list(row.keys()) if isinstance(row, dict) else type(row)}")
                    
                    # Log the full row structure for debugging
                    if isinstance(row, dict):
                        logger.info(f"Row {i} full structure: {row}")
                        
                        # **SKIP "Other Expenses" GROUP - these are typically unallowable costs**
                        if row.get('group') == 'OtherExpenses':
                            logger.info(f"Skipping 'Other Expenses' section (unallowable costs)")
                            continue
                    
                    # Handle different row structures
                    if isinstance(row, dict):
                        if 'ColData' in row:
                            # Standard row format
                            logger.info(f"Processing standard row {i} with ColData")
                            self._parse_row_data(row, income_sources, expense_categories)
                        elif 'Rows' in row:
                            # Nested rows (subcategories) - handle the QBO structure
                            logger.info(f"Found nested rows in row {i}")
                            nested_rows = row['Rows']
                            
                            # Handle nested Row structure
                            if isinstance(nested_rows, dict) and 'Row' in nested_rows:
                                nested_row_list = nested_rows['Row']
                                logger.info(f"Nested rows count: {len(nested_row_list)}")
                                for j, subrow in enumerate(nested_row_list):
                                    logger.info(f"Subrow {j}: {list(subrow.keys()) if isinstance(subrow, dict) else type(subrow)}")
                                    self._parse_nested_row(subrow, income_sources, expense_categories, row.get('group'))
                            elif isinstance(nested_rows, list):
                                logger.info(f"Nested rows count: {len(nested_rows)}")
                                for j, subrow in enumerate(nested_rows):
                                    logger.info(f"Subrow {j}: {list(subrow.keys()) if isinstance(subrow, dict) else type(subrow)}")
                                    self._parse_nested_row(subrow, income_sources, expense_categories, row.get('group'))
                        elif 'group' in row:
                            # Group header
                            logger.info(f"Group: {row.get('group', 'Unknown')}")
                            if 'Rows' in row:
                                self._parse_nested_row(row, income_sources, expense_categories, row.get('group'))
            else:
                logger.warning("No 'Rows' found in response")
                return None
            
            # If no data found, try alternative parsing
            if not income_sources and not expense_categories:
                logger.warning("No financial data found in P&L report, trying alternative parsing")
                # Check if this is a summary-only report (common for periods with no data)
                if self._is_summary_only_report(pl_data):
                    logger.info("Detected summary-only report - likely no transactions in this date range")
                    logger.info("This usually means no financial activity occurred in the selected date range")
                    sample_data = self._get_sample_financial_data()
                    sample_data['is_sample_data'] = True
                    return sample_data  # Use sample data for empty periods
                return self._parse_alternative_report_structure(pl_data)
            
            logger.info(f"Parsed data - Income sources: {len(income_sources)}, Expenses: {len(expense_categories)}")
            
            return {
                'income': income_sources,
                'expenses': expense_categories,
                'total_revenue': sum(income_sources.values()),
                'total_expenses': sum(expense_categories.values()),
                'net_income': sum(income_sources.values()) - sum(expense_categories.values())
            }
            
        except Exception as e:
            logger.error(f"Error parsing P&L report: {e}")
            return None
    
    def _parse_row_data(self, row: Dict, income_sources: Dict, expense_categories: Dict, parent_group: str = None):
        """Parse individual row data from P&L report"""
        try:
            if 'ColData' in row and len(row['ColData']) >= 2:
                # Extract account name and amount
                account_name = row['ColData'][0].get('value', '').strip()
                
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
                
                # **REPLACE THE EXISTING CODE WITH THIS:**
                # If this row has nested data, DON'T process it as a data row
                # Only process the nested rows (the details), not the parent
                if 'Rows' in row:
                    nested_rows = row['Rows']
                    if isinstance(nested_rows, dict) and 'Row' in nested_rows:
                        for subrow in nested_rows['Row']:
                            self._parse_nested_row(subrow, income_sources, expense_categories, current_group)
                    elif isinstance(nested_rows, list):
                        for subrow in nested_rows:
                            self._parse_nested_row(subrow, income_sources, expense_categories, current_group)
                    # Don't process ColData here - it would be a summary of the nested rows
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
