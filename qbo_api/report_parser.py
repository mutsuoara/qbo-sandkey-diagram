"""
Parse QuickBooks Online reports for Sankey diagram visualization
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class ReportParser:
    """Parses QBO reports for Sankey diagram data"""
    
    def __init__(self):
        self.revenue_sources = []
        self.expense_categories = []
        self.net_income = 0.0
    
    def parse_for_sankey(self, report_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse report data for Sankey diagram"""
        try:
            if not self._validate_report_structure(report_data):
                return None
            
            # Extract data from report
            rows = report_data['QueryResponse']['Report']['Rows']
            
            # Parse revenue and expenses
            revenue_data = self._extract_revenue_sources(rows)
            expense_data = self._extract_expense_categories(rows)
            
            # Calculate net income
            total_revenue = sum(item['amount'] for item in revenue_data)
            total_expenses = sum(item['amount'] for item in expense_data)
            net_income = total_revenue - total_expenses
            
            # Create Sankey data structure
            sankey_data = {
                'nodes': self._create_nodes(revenue_data, expense_data, net_income),
                'links': self._create_links(revenue_data, expense_data, net_income),
                'metadata': {
                    'total_revenue': total_revenue,
                    'total_expenses': total_expenses,
                    'net_income': net_income,
                    'revenue_count': len(revenue_data),
                    'expense_count': len(expense_data)
                }
            }
            
            logger.info(f"Parsed report: {len(revenue_data)} revenue sources, {len(expense_data)} expense categories")
            return sankey_data
            
        except Exception as e:
            logger.error(f"Failed to parse report for Sankey: {e}")
            return None
    
    def _validate_report_structure(self, report_data: Dict[str, Any]) -> bool:
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
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate report structure: {e}")
            return False
    
    def _extract_revenue_sources(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract revenue sources from report rows"""
        revenue_sources = []
        
        try:
            for row in rows:
                if 'ColData' in row and len(row['ColData']) >= 2:
                    # Check if this is a revenue row
                    row_data = row['ColData']
                    if len(row_data) >= 2:
                        name = row_data[0].get('value', '').strip()
                        amount_str = row_data[1].get('value', '0').strip()
                        
                        # Parse amount
                        amount = self._safe_float_parse(amount_str)
                        
                        # Check if this looks like revenue (positive amount, common revenue keywords)
                        if amount > 0 and self._is_revenue_source(name):
                            revenue_sources.append({
                                'name': name,
                                'amount': amount,
                                'type': 'revenue'
                            })
            
            # If no revenue sources found, try alternative parsing
            if not revenue_sources:
                revenue_sources = self._alternative_revenue_parsing(rows)
            
            logger.info(f"Extracted {len(revenue_sources)} revenue sources")
            return revenue_sources
            
        except Exception as e:
            logger.error(f"Failed to extract revenue sources: {e}")
            return []
    
    def _extract_expense_categories(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract expense categories from report rows"""
        expense_categories = []
        
        try:
            for row in rows:
                if 'ColData' in row and len(row['ColData']) >= 2:
                    # Check if this is an expense row
                    row_data = row['ColData']
                    if len(row_data) >= 2:
                        name = row_data[0].get('value', '').strip()
                        amount_str = row_data[1].get('value', '0').strip()
                        
                        # Parse amount
                        amount = self._safe_float_parse(amount_str)
                        
                        # Check if this looks like an expense (negative amount or common expense keywords)
                        if amount < 0 or self._is_expense_category(name):
                            # Convert negative amounts to positive for display
                            expense_categories.append({
                                'name': name,
                                'amount': abs(amount),
                                'type': 'expense'
                            })
            
            logger.info(f"Extracted {len(expense_categories)} expense categories")
            return expense_categories
            
        except Exception as e:
            logger.error(f"Failed to extract expense categories: {e}")
            return []
    
    def _safe_float_parse(self, value_str: str) -> float:
        """Safely parse float value from string"""
        try:
            # Remove common formatting characters
            cleaned = value_str.replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0
    
    def _is_revenue_source(self, name: str) -> bool:
        """Check if a row name looks like a revenue source"""
        revenue_keywords = [
            'revenue', 'sales', 'income', 'service', 'product', 'fees',
            'interest', 'dividend', 'rental', 'commission', 'royalty'
        ]
        
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in revenue_keywords)
    
    def _is_expense_category(self, name: str) -> bool:
        """Check if a row name looks like an expense category"""
        expense_keywords = [
            'expense', 'cost', 'fee', 'charge', 'payment', 'rent', 'utilities',
            'salary', 'wage', 'benefit', 'insurance', 'tax', 'depreciation',
            'amortization', 'interest', 'penalty', 'fine'
        ]
        
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in expense_keywords)
    
    def _alternative_revenue_parsing(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Alternative method to parse revenue sources"""
        revenue_sources = []
        
        try:
            for row in rows:
                if 'ColData' in row and len(row['ColData']) >= 2:
                    row_data = row['ColData']
                    name = row_data[0].get('value', '').strip()
                    amount_str = row_data[1].get('value', '0').strip()
                    amount = self._safe_float_parse(amount_str)
                    
                    # Look for positive amounts that might be revenue
                    if amount > 0 and not self._is_expense_category(name):
                        revenue_sources.append({
                            'name': name,
                            'amount': amount,
                            'type': 'revenue'
                        })
            
            logger.info(f"Alternative parsing found {len(revenue_sources)} revenue sources")
            return revenue_sources
            
        except Exception as e:
            logger.error(f"Failed alternative revenue parsing: {e}")
            return []
    
    def _create_nodes(self, revenue_data: List[Dict[str, Any]], 
                     expense_data: List[Dict[str, Any]], 
                     net_income: float) -> List[Dict[str, Any]]:
        """Create nodes for Sankey diagram"""
        nodes = []
        
        # Add revenue sources
        for item in revenue_data:
            nodes.append({
                'label': item['name'],
                'color': '#2E8B57'  # Green for revenue
            })
        
        # Add expense categories
        for item in expense_data:
            nodes.append({
                'label': item['name'],
                'color': '#DC143C'  # Red for expenses
            })
        
        # Add net income node
        if net_income > 0:
            nodes.append({
                'label': 'Net Income',
                'color': '#4169E1'  # Blue for net income
            })
        else:
            nodes.append({
                'label': 'Net Loss',
                'color': '#FF6347'  # Orange for net loss
            })
        
        return nodes
    
    def _create_links(self, revenue_data: List[Dict[str, Any]], 
                     expense_data: List[Dict[str, Any]], 
                     net_income: float) -> List[Dict[str, Any]]:
        """Create links for Sankey diagram"""
        links = []
        
        # Create links from revenue sources to net income
        for i, item in enumerate(revenue_data):
            links.append({
                'source': i,
                'target': len(revenue_data) + len(expense_data),
                'value': item['amount']
            })
        
        # Create links from expenses to net income (negative flow)
        for i, item in enumerate(expense_data):
            links.append({
                'source': len(revenue_data) + i,
                'target': len(revenue_data) + len(expense_data),
                'value': -item['amount']  # Negative value for expenses
            })
        
        return links
    
    def validate_financial_data(self, sankey_data: Dict[str, Any]) -> bool:
        """Validate parsed financial data"""
        try:
            if not sankey_data:
                return False
            
            metadata = sankey_data.get('metadata', {})
            total_revenue = metadata.get('total_revenue', 0)
            total_expenses = metadata.get('total_expenses', 0)
            net_income = metadata.get('net_income', 0)
            
            # Basic validation
            if total_revenue < 0 or total_expenses < 0:
                logger.warning("Negative revenue or expenses found")
                return False
            
            # Check if net income calculation is reasonable
            calculated_net = total_revenue - total_expenses
            if abs(calculated_net - net_income) > 0.01:  # Allow for small floating point differences
                logger.warning("Net income calculation mismatch")
                return False
            
            logger.info("Financial data validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate financial data: {e}")
            return False

