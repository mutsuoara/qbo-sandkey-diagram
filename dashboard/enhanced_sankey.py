"""
Enhanced Sankey diagram with zoom, pan, and dynamic sizing
"""

import plotly.graph_objects as go
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def create_enhanced_sankey_diagram(financial_data, start_date=None, end_date=None):
    """Create an enhanced Sankey diagram with zoom, pan, and dynamic sizing"""
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
    
    # Income sources (left column)
    for source, amount in income_sources.items():
        node_labels.append(f"{source}<br>${amount:,.0f}")
        node_colors.append("#27ae60")  # Green for income
    
    # Total revenue (center column)
    node_labels.append(f"Total Revenue<br>${total_revenue:,.0f}")
    node_colors.append("#3498db")  # Blue for total revenue
    
    # Expense categories (right column) - limit to top 10 for readability
    expense_items = list(expense_categories.items())
    if len(expense_items) > 10:
        # Sort by amount and take top 10
        expense_items = sorted(expense_items, key=lambda x: x[1], reverse=True)[:10]
        # Add "Other Expenses" for remaining
        other_amount = sum(amount for _, amount in list(expense_categories.items())[10:])
        if other_amount > 0:
            expense_items.append(("Other Expenses", other_amount))
    
    for expense, amount in expense_items:
        node_labels.append(f"{expense}<br>${amount:,.0f}")
        node_colors.append("#e74c3c")  # Red for expenses
    
    # Adjusted gross income
    node_labels.append(f"Adjusted Gross Income<br>${adjusted_gross_income:,.0f}")
    node_colors.append("#f39c12")  # Gold for final result
    
    # Create links
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
    for i, (expense, amount) in enumerate(expense_items):
        source_indices.append(total_revenue_idx)
        target_indices.append(expense_start_idx + i)
        values.append(amount)
    
    # Link from total revenue to adjusted gross income
    adjusted_gross_idx = len(node_labels) - 1
    source_indices.append(total_revenue_idx)
    target_indices.append(adjusted_gross_idx)
    values.append(adjusted_gross_income)
    
    # Create the enhanced Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 40,  # Much more padding between nodes
            thickness = 30,  # Thicker nodes for better visibility
            line = dict(color = "black", width = 1),
            label = node_labels,
            color = node_colors,
            x = [0.1, 0.5, 0.9],  # Spread columns across the width
            y = None  # Auto-arrange vertically
        ),
        link = dict(
            source = source_indices,
            target = target_indices,
            value = values,
            color = "rgba(0,0,0,0.2)"  # Subtle link colors
        )
    )])
    
    # Format date range
    date_range = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
    
    # Add title with financial summary and date range
    title_text = f"Financial Flow Analysis ({date_range})<br><sub>Total Revenue: ${total_revenue:,.0f} | Total Expenses: ${total_expenses:,.0f} | Adjusted Gross Income: ${adjusted_gross_income:,.0f}</sub>"
    
    # Calculate dynamic height based on number of categories
    num_categories = len(income_sources) + len(expense_items) + 2  # +2 for total revenue and adjusted gross
    # Much more generous height calculation - 80px per category with better min/max
    dynamic_height = max(800, min(2000, 300 + (num_categories * 80)))  # Min 800, max 2000, 80px per category
    
    fig.update_layout(
        title_text=title_text,
        font_size=18,  # Larger font for better readability
        height=dynamic_height,  # Dynamic height based on content
        margin=dict(l=80, r=80, t=120, b=80),  # More margin space
        plot_bgcolor='white',
        paper_bgcolor='white',
        title_x=0.5,  # Center the title
        title_font_size=20,
        # Enable zooming and panning
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        # Make it responsive
        autosize=True,
        # Enable zoom and pan
        dragmode='zoom',
        # Add zoom controls
        showlegend=False
    )
    
    # Add zoom and pan controls
    fig.update_layout(
        # Enable zoom and pan
        dragmode='zoom',
        # Add selection mode
        selectdirection='d',  # 'd' for diagonal selection
        # Enable hover
        hovermode='closest'
    )
    
    return fig

def create_sample_sankey_diagram(start_date=None, end_date=None):
    """Create a sample Sankey diagram for demonstration with enhanced features"""
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
        "Marketing": 5000,
        "Administrative": 8000
    }
    
    # Calculate totals
    total_revenue = sum(income_sources.values())
    total_expenses = sum(expense_categories.values())
    adjusted_gross_income = total_revenue - total_expenses
    
    # Create nodes with dollar amounts as labels
    node_labels = []
    node_colors = []
    
    # Income sources (left column)
    for source, amount in income_sources.items():
        node_labels.append(f"{source}<br>${amount:,.0f}")
        node_colors.append("#27ae60")  # Green for income
    
    # Total revenue (center column)
    node_labels.append(f"Total Revenue<br>${total_revenue:,.0f}")
    node_colors.append("#3498db")  # Blue for total revenue
    
    # Expense categories (right column)
    for expense, amount in expense_categories.items():
        node_labels.append(f"{expense}<br>${amount:,.0f}")
        node_colors.append("#e74c3c")  # Red for expenses
    
    # Adjusted gross income
    node_labels.append(f"Adjusted Gross Income<br>${adjusted_gross_income:,.0f}")
    node_colors.append("#f39c12")  # Gold for final result
    
    # Create links
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
    
    # Create the enhanced Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 40,  # Much more padding between nodes
            thickness = 30,  # Thicker nodes for better visibility
            line = dict(color = "black", width = 1),
            label = node_labels,
            color = node_colors,
            x = [0.1, 0.5, 0.9],  # Spread columns across the width
            y = None  # Auto-arrange vertically
        ),
        link = dict(
            source = source_indices,
            target = target_indices,
            value = values,
            color = "rgba(0,0,0,0.2)"  # Subtle link colors
        )
    )])
    
    # Format date range
    date_range = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
    
    # Add title with financial summary and date range
    title_text = f"Financial Flow Analysis ({date_range})<br><sub>Total Revenue: ${total_revenue:,.0f} | Total Expenses: ${total_expenses:,.0f} | Adjusted Gross Income: ${adjusted_gross_income:,.0f}</sub>"
    
    # Calculate dynamic height based on number of categories
    num_categories = len(income_sources) + len(expense_categories) + 2  # +2 for total revenue and adjusted gross
    # Much more generous height calculation - 80px per category with better min/max
    dynamic_height = max(800, min(2000, 300 + (num_categories * 80)))  # Min 800, max 2000, 80px per category
    
    fig.update_layout(
        title_text=title_text,
        font_size=18,  # Larger font for better readability
        height=dynamic_height,  # Dynamic height based on content
        margin=dict(l=80, r=80, t=120, b=80),  # More margin space
        plot_bgcolor='white',
        paper_bgcolor='white',
        title_x=0.5,  # Center the title
        title_font_size=20,
        # Enable zooming and panning
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        # Make it responsive
        autosize=True,
        # Enable zoom and pan
        dragmode='zoom',
        # Add zoom controls
        showlegend=False
    )
    
    # Add zoom and pan controls
    fig.update_layout(
        # Enable zoom and pan
        dragmode='zoom',
        # Add selection mode
        selectdirection='d',  # 'd' for diagonal selection
        # Enable hover
        hovermode='closest'
    )
    
    return fig
