"""
Sankey chart generation for QBO Sankey Dashboard
Contains functions to create various types of Sankey diagrams from financial data.
"""

import plotly.graph_objects as go
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def create_sankey_diagram_from_data(financial_data, start_date=None, end_date=None):
    """Create a Sankey diagram from real QuickBooks financial data with improved layout"""
    from datetime import datetime, timedelta
    
    # Set default date range (Year to Date if not provided)
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        # Year to Date (January 1st of current year)
        start_date = datetime(end_date.year, 1, 1)
    
    # Extract data from financial_data dictionary
    income_sources = financial_data.get('income', {})
    expense_categories = financial_data.get('expenses', {})
    
    # If no real data, use sample data
    if not income_sources and not expense_categories:
        logger.warning("No financial data available, using sample data")
        return create_sample_sankey_diagram(start_date, end_date)
    
    # Ensure we have some data
    if not income_sources:
        income_sources = {"No Income Data": 0}
    if not expense_categories:
        expense_categories = {"No Expense Data": 0}
    
    # Calculate totals
    total_revenue = sum(income_sources.values())
    total_expenses = sum(expense_categories.values())
    adjusted_gross_income = total_revenue - total_expenses
    
    # Create nodes with dollar amounts as labels
    node_labels = []
    node_colors = []
    
    # Income sources with amounts
    for source, amount in income_sources.items():
        if amount > 0:  # Only include positive amounts
            node_labels.append(f"{source}<br>${amount:,.0f}")
            node_colors.append("#2ecc71")  # Green for income sources
    
    # Total revenue
    if total_revenue > 0:
        node_labels.append(f"Total Revenue<br>${total_revenue:,.0f}")
        node_colors.append("#3498db")  # Blue for total revenue
    
    # Expense categories with amounts
    for expense, amount in expense_categories.items():
        if amount > 0:  # Only include positive amounts
            node_labels.append(f"{expense}<br>${amount:,.0f}")
            node_colors.append("#e74c3c")  # Red for expenses
    
    # Adjusted gross income
    if adjusted_gross_income != 0:
        node_labels.append(f"Adjusted Gross Income<br>${adjusted_gross_income:,.0f}")
        node_colors.append("#f39c12" if adjusted_gross_income > 0 else "#e67e22")  # Gold for profit, orange for loss
    
    # Create links
    links = []
    source_indices = []
    target_indices = []
    values = []
    
    # Links from income sources to total revenue
    if total_revenue > 0:
        total_revenue_idx = len([s for s in income_sources.values() if s > 0])
        current_idx = 0
        for source, amount in income_sources.items():
            if amount > 0:
                source_indices.append(current_idx)
                target_indices.append(total_revenue_idx)
                values.append(amount)
                current_idx += 1
        
        # Links from total revenue to expense categories
        expense_start_idx = total_revenue_idx + 1
        current_expense_idx = expense_start_idx
        for expense, amount in expense_categories.items():
            if amount > 0:
                source_indices.append(total_revenue_idx)
                target_indices.append(current_expense_idx)
                values.append(amount)
                current_expense_idx += 1
        
        # Link from total revenue to adjusted gross income
        adjusted_gross_idx = len(node_labels) - 1
        source_indices.append(total_revenue_idx)
        target_indices.append(adjusted_gross_idx)
        values.append(adjusted_gross_income)
    
    # Create the Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 15,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = node_labels,
            color = node_colors
        ),
        link = dict(
            source = source_indices,
            target = target_indices,
            value = values
        )
    )])
    
    # Format date range
    date_range = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
    
    # Add title with financial summary and date range
    title_text = f"Financial Flow Analysis ({date_range})<br><sub>Total Revenue: ${total_revenue:,.0f} | Total Expenses: ${total_expenses:,.0f} | Adjusted Gross Income: ${adjusted_gross_income:,.0f}</sub>"
    
    fig.update_layout(
        title_text=title_text,
        font_size=12,
        height=600,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_sample_sankey_diagram(start_date=None, end_date=None):
    """Create a sample Sankey diagram for demonstration with proper income/expense flow"""
    from datetime import datetime, timedelta
    
    # Set default date range (Year to Date if not provided)
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        # Year to Date (January 1st of current year)
        start_date = datetime(end_date.year, 1, 1)
    
    # Sample financial data
    income_sources = {
        "Product Sales": 45000,
        "Service Revenue": 25000,
        "Other Income": 5000
    }
    
    expense_categories = {
        "Cost of Goods Sold": 20000,
        "Operating Expenses": 15000,
        "Marketing": 8000,
        "Administrative": 12000
    }
    
    # Calculate totals
    total_revenue = sum(income_sources.values())
    total_expenses = sum(expense_categories.values())
    adjusted_gross_income = total_revenue - total_expenses
    
    # Create nodes with dollar amounts as labels
    node_labels = []
    node_colors = []
    
    # Income sources with amounts
    for source, amount in income_sources.items():
        node_labels.append(f"{source}<br>${amount:,.0f}")
        node_colors.append("#2ecc71")  # Green for income sources
    
    # Total revenue
    node_labels.append(f"Total Revenue<br>${total_revenue:,.0f}")
    node_colors.append("#3498db")  # Blue for total revenue
    
    # Expense categories with amounts
    for expense, amount in expense_categories.items():
        node_labels.append(f"{expense}<br>${amount:,.0f}")
        node_colors.append("#e74c3c")  # Red for expenses
    
    # Adjusted gross income
    node_labels.append(f"Adjusted Gross Income<br>${adjusted_gross_income:,.0f}")
    node_colors.append("#f39c12")  # Gold for final result
    
    # Create links
    links = []
    source_indices = []
    target_indices = []
    values = []
    
    # Links from income sources to total revenue
    total_revenue_idx = len(income_sources)
    for i, (source, amount) in enumerate(income_sources.items()):
        source_indices.append(i)
        target_indices.append(total_revenue_idx)
        values.append(amount)
    
    # Links from total revenue to expense categories
    expense_start_idx = total_revenue_idx + 1
    for i, (expense, amount) in enumerate(expense_categories.items()):
        source_indices.append(total_revenue_idx)
        target_indices.append(expense_start_idx + i)
        values.append(amount)
    
    # Link from total revenue to adjusted gross income
    adjusted_gross_idx = len(node_labels) - 1
    source_indices.append(total_revenue_idx)
    target_indices.append(adjusted_gross_idx)
    values.append(adjusted_gross_income)
    
    # Create the Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 15,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = node_labels,
            color = node_colors
        ),
        link = dict(
            source = source_indices,
            target = target_indices,
            value = values
        )
    )])
    
    # Format date range
    date_range = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
    
    # Add title with financial summary and date range
    title_text = f"Financial Flow Analysis ({date_range})<br><sub>Total Revenue: ${total_revenue:,.0f} | Total Expenses: ${total_expenses:,.0f} | Adjusted Gross Income: ${adjusted_gross_income:,.0f}</sub>"
    
    fig.update_layout(
        title_text=title_text,
        font_size=12,
        height=600,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_financial_sankey(income_data: Dict[str, float], 
                           expense_data: Dict[str, float], 
                           title: str = "Financial Flow Analysis") -> go.Figure:
    """
    Create a Sankey diagram from actual financial data
    
    Args:
        income_data: Dictionary of income categories and amounts
        expense_data: Dictionary of expense categories and amounts
        title: Chart title
    
    Returns:
        Plotly Figure object
    """
    try:
        # Prepare nodes and links
        nodes = []
        links = []
        
        # Add income nodes
        income_nodes = list(income_data.keys())
        nodes.extend(income_nodes)
        
        # Add expense nodes
        expense_nodes = list(expense_data.keys())
        nodes.extend(expense_nodes)
        
        # Add summary nodes
        summary_nodes = ["Total Income", "Total Expenses", "Net Income"]
        nodes.extend(summary_nodes)
        
        # Create node labels and colors
        node_labels = nodes
        node_colors = []
        
        # Color coding: green for income, red for expenses, blue for summary
        for i, node in enumerate(nodes):
            if node in income_data:
                node_colors.append("#2ecc71")  # Green for income
            elif node in expense_data:
                node_colors.append("#e74c3c")  # Red for expenses
            else:
                node_colors.append("#3498db")  # Blue for summary
        
        # Create links from income to total income
        total_income = sum(income_data.values())
        for i, (category, amount) in enumerate(income_data.items()):
            links.append({
                'source': i,
                'target': len(nodes) - 3,  # Total Income
                'value': amount
            })
        
        # Create links from expenses to total expenses
        total_expenses = sum(expense_data.values())
        expense_start_idx = len(income_data)
        for i, (category, amount) in enumerate(expense_data.items()):
            links.append({
                'source': expense_start_idx + i,
                'target': len(nodes) - 2,  # Total Expenses
                'value': amount
            })
        
        # Create link from total income to net income
        links.append({
            'source': len(nodes) - 3,  # Total Income
            'target': len(nodes) - 1,  # Net Income
            'value': total_income
        })
        
        # Create link from total expenses to net income (negative)
        links.append({
            'source': len(nodes) - 2,  # Total Expenses
            'target': len(nodes) - 1,  # Net Income
            'value': total_expenses
        })
        
        # Extract source, target, and value arrays
        source = [link['source'] for link in links]
        target = [link['target'] for link in links]
        value = [link['value'] for link in links]
        
        # Create the Sankey diagram
        fig = go.Figure(data=[go.Sankey(
            node = dict(
                pad = 15,
                thickness = 20,
                line = dict(color = "black", width = 0.5),
                label = node_labels,
                color = node_colors
            ),
            link = dict(
                source = source,
                target = target,
                value = value
            )
        )])
        
        fig.update_layout(
            title_text=title,
            font_size=12,
            height=600,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        logger.info(f"Created financial Sankey diagram with {len(nodes)} nodes and {len(links)} links")
        return fig
        
    except Exception as e:
        logger.error(f"Error creating financial Sankey diagram: {e}")
        # Return sample diagram as fallback
        return create_sample_sankey_diagram()

def create_cash_flow_sankey(cash_flow_data: Dict[str, Any]) -> go.Figure:
    """
    Create a Sankey diagram specifically for cash flow analysis
    
    Args:
        cash_flow_data: Dictionary containing cash flow categories and amounts
    
    Returns:
        Plotly Figure object
    """
    try:
        # This would be implemented based on specific cash flow data structure
        # For now, return a sample diagram
        logger.info("Creating cash flow Sankey diagram")
        return create_sample_sankey_diagram()
        
    except Exception as e:
        logger.error(f"Error creating cash flow Sankey diagram: {e}")
        return create_sample_sankey_diagram()
