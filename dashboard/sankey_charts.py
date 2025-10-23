"""
Sankey chart generation for QBO Sankey Dashboard
Contains functions to create various types of Sankey diagrams from financial data.
"""

import plotly.graph_objects as go
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def create_sample_sankey_diagram():
    """Create a sample Sankey diagram for demonstration"""
    # Sample data for demonstration
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 15,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = ["Revenue", "Operating Expenses", "COGS", "Net Income", "Cash Flow", "Investments"],
            color = ["#2ecc71", "#e74c3c", "#f39c12", "#3498db", "#9b59b6", "#1abc9c"]
        ),
        link = dict(
            source = [0, 0, 1, 1, 2, 3],  # indices correspond to labels
            target = [1, 2, 3, 4, 4, 5],
            value = [50000, 30000, 20000, 10000, 15000, 25000]
        )
    )])
    
    fig.update_layout(
        title_text="Sample Financial Flow - QuickBooks Data Integration Coming Soon",
        font_size=12,
        height=600,
        margin=dict(l=20, r=20, t=40, b=20)
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
