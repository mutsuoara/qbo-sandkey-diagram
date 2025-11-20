"""
Enhanced Sankey diagram with hierarchical expense structure
Cleaned up to only include features that actually work with Plotly Sankey
"""

import plotly.graph_objects as go
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def group_expenses_by_account_number(expense_categories: Dict[str, float]) -> Dict[str, float]:
    """
    Group expenses based on account number ranges and dollar amounts.
    
    Rules:
    - If amount < $10,000, group by account number range
    - If amount >= $10,000, keep as individual expense
    - Group ranges:
      - Fringe & Benefits = 6000-6300
      - Facility Expenses = 6500-6999
      - OH Other Expenses = 7000-7500
      - GA Other Expenses = 8000-8499
    
    Args:
        expense_categories: Dictionary mapping expense names to amounts
        
    Returns:
        Dictionary with grouped and individual expenses
    """
    grouped_expenses = {}
    group_ranges = {
        'Fringe & Benefits': (6000, 6300),
        'Facility Expenses': (6500, 6999),
        'OH Other Expenses': (7000, 7500),
        'GA Other Expenses': (8000, 8499)
    }
    threshold = 10000  # Group if less than this amount
    
    logger.info(f"Grouping expenses: {len(expense_categories)} expenses before grouping")
    
    for expense_name, amount in expense_categories.items():
        # Extract account number from start of name (e.g., "6001 Some Expense" -> 6001)
        match = re.match(r'^(\d{3,4})', expense_name)
        
        if match and amount < threshold:
            account_num = int(match.group(1))
            
            # Check which group this account belongs to
            grouped = False
            for group_name, (min_num, max_num) in group_ranges.items():
                if min_num <= account_num <= max_num:
                    if group_name in grouped_expenses:
                        grouped_expenses[group_name] += amount
                    else:
                        grouped_expenses[group_name] = amount
                    grouped = True
                    logger.debug(f"Grouped '{expense_name}' (${amount:,.2f}) into '{group_name}'")
                    break
            
            # If not in any group range, keep as individual
            if not grouped:
                grouped_expenses[expense_name] = amount
        else:
            # Amount >= threshold OR no account number found - keep as individual
            grouped_expenses[expense_name] = amount
    
    logger.info(f"After grouping: {len(grouped_expenses)} expenses remain")
    
    return grouped_expenses

def create_enhanced_sankey_diagram(financial_data, start_date=None, end_date=None):
    """Create an enhanced Sankey diagram with hierarchical structure"""
    from datetime import datetime, timedelta
    
    # Set default date range (Year to Date if not provided)
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = datetime(end_date.year, 1, 1)
    
    # Extract data from financial_data dictionary
    income_sources = financial_data.get('income', {})
    expense_hierarchy = financial_data.get('expense_hierarchy', {})
    expense_categories = financial_data.get('expenses', {})  # Fallback if hierarchy not available
    
    # If no hierarchy, use flat structure (backward compatibility)
    if not expense_hierarchy and expense_categories:
        expense_categories = group_expenses_by_account_number(expense_categories)
        logger.info(f"Using flat expense structure: {len(expense_categories)} expense categories")
    
    # If no real data, log warning and return None
    if not income_sources and not expense_hierarchy and not expense_categories:
        logger.warning("No financial data available")
        return None
    
    # Ensure we have some data
    if not income_sources:
        income_sources = {"No Income Data": 0}
    
    # Calculate totals
    total_revenue = sum(income_sources.values())
    if expense_hierarchy:
        total_expenses = sum(prim_data.get('total', 0) for prim_data in expense_hierarchy.values())
    else:
        total_expenses = sum(expense_categories.values())
    adjusted_gross_income = total_revenue - total_expenses
    
    # Create nodes with dollar amounts as labels
    node_labels = []
    node_colors = []
    node_x_positions = []  # X positions for hierarchical layout
    
    # Store tertiary data for hover tooltips
    node_tertiary_data = {}  # Map node index -> list of (tertiary_name, tertiary_amount) tuples
    
    # Income sources (left column, x=0)
    income_indices = {}
    for i, (source, amount) in enumerate(income_sources.items()):
        # Calculate percentage of total revenue
        percentage = (amount / total_revenue * 100) if total_revenue > 0 else 0
        node_labels.append(f"{source}<br>${amount:,.0f} ({percentage:.1f}%)")
        node_colors.append("#27ae60")  # Green for income
        node_x_positions.append(0.0)
        income_indices[source] = i
        logger.info(f"Income source: {source} = ${amount:,.0f} ({percentage:.1f}% of revenue)")
    
    # Total revenue (center column, x=0.33)
    total_revenue_idx = len(income_sources)
    net_income_text = f"<br><br><b>Net Income:</b> ${adjusted_gross_income:,.0f}" if adjusted_gross_income != 0 else ""
    node_labels.append(f"<b>Total Revenue</b><br>${total_revenue:,.0f}{net_income_text}")
    node_colors.append("#3498db")  # Blue for total revenue
    node_x_positions.append(0.33)
    
    # Process hierarchical expenses
    primary_indices = {}  # Map primary names to node indices
    secondary_indices = {}  # Map (primary_name, secondary_name) to node indices
    
    if expense_hierarchy:
        logger.info(f"Building hierarchical Sankey structure with {len(expense_hierarchy)} primaries")
        
        # First pass: Create primary nodes for those with secondaries (x=0.67)
        for primary_name, primary_data in expense_hierarchy.items():
            secondaries = primary_data.get('secondary', {})
            if secondaries:
                # This primary has secondaries - create intermediate node
                primary_amount = primary_data.get('total', 0)
                if primary_amount > 0:
                    idx = len(node_labels)
                    node_labels.append(f"{primary_name}<br>${primary_amount:,.0f}")
                    node_colors.append("#e67e22")  # Orange for primary categories
                    node_x_positions.append(0.67)
                    primary_indices[primary_name] = idx
                    logger.info(f"  Created primary node: {primary_name} (idx={idx})")
        
        # Second pass: Create secondary nodes (x=1.0)
        for primary_name, primary_data in expense_hierarchy.items():
            secondaries = primary_data.get('secondary', {})
            if secondaries:
                # This primary has secondaries - create secondary nodes
                for sec_name, sec_data in secondaries.items():
                    sec_amount = sec_data.get('total', 0)
                    if sec_amount > 0:
                        idx = len(node_labels)
                        node_labels.append(f"{sec_name}<br>${sec_amount:,.0f}")
                        node_x_positions.append(1.0)
                        
                        # Store tertiary data for this node if it exists
                        tertiaries = sec_data.get('tertiary', {})
                        if tertiaries:
                            # Store tertiary data as list of tuples for hover tooltip
                            tertiary_list = sorted(tertiaries.items(), key=lambda x: x[1], reverse=True)
                            node_tertiary_data[idx] = tertiary_list
                            # Color code: Purple for nodes with tertiary breakdown
                            node_colors.append("#9b59b6")  # Purple for secondary expenses with tertiaries
                            logger.info(f"    Created secondary node with {len(tertiaries)} tertiaries: {sec_name} (idx={idx})")
                        else:
                            # Color code: Red for nodes without tertiaries
                            node_colors.append("#e74c3c")  # Red for secondary expenses without tertiaries
                            logger.info(f"    Created secondary node: {sec_name} (idx={idx})")
                        
                        secondary_indices[(primary_name, sec_name)] = idx
            else:
                # Primary has no secondaries - create direct expense node (x=1.0)
                primary_amount = primary_data.get('total', 0)
                if primary_amount > 0:
                    idx = len(node_labels)
                    node_labels.append(f"{primary_name}<br>${primary_amount:,.0f}")
                    node_colors.append("#e74c3c")  # Red for expenses
                    node_x_positions.append(1.0)
                    primary_indices[primary_name] = idx  # Direct link from Total Revenue
                    logger.info(f"  Created direct expense node: {primary_name} (idx={idx})")
    else:
        # Fallback to flat structure
        logger.info("Using flat expense structure (no hierarchy available)")
        expense_items = list(expense_categories.items())
        expense_items = sorted(expense_items, key=lambda x: x[1], reverse=True)
        
        for expense, amount in expense_items:
            idx = len(node_labels)
            # Calculate percentage of total expenses
            percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
            node_labels.append(f"{expense}<br>${amount:,.0f} ({percentage:.1f}%)")
            node_colors.append("#e74c3c")  # Red for expenses
            node_x_positions.append(1.0)
            primary_indices[expense] = idx  # Use same dict for flat structure
            logger.info(f"Flat expense: {expense} = ${amount:,.0f} ({percentage:.1f}% of expenses)")
    
    # Create links - use actual dollar amounts for proper node height alignment
    source_indices = []
    target_indices = []
    values = []
    
    # Links from income sources to total revenue
    for i, (source, amount) in enumerate(income_sources.items()):
        source_indices.append(i)
        target_indices.append(total_revenue_idx)
        values.append(amount)
    
    # Links for hierarchical expense structure
    if expense_hierarchy:
        for primary_name, primary_data in expense_hierarchy.items():
            secondaries = primary_data.get('secondary', {})
            primary_amount = primary_data.get('total', 0)
            
            if primary_amount > 0:
                if secondaries:
                    # Primary has secondaries - link Total Revenue → Primary
                    if primary_name in primary_indices:
                        primary_idx = primary_indices[primary_name]
                        source_indices.append(total_revenue_idx)
                        target_indices.append(primary_idx)
                        values.append(primary_amount)
                        logger.info(f"  Link: Total Revenue → {primary_name} (${primary_amount:,.0f})")
                        
                        # Then link Primary → each Secondary
                        for sec_name, sec_data in secondaries.items():
                            sec_amount = sec_data.get('total', 0)
                            if sec_amount > 0 and (primary_name, sec_name) in secondary_indices:
                                sec_idx = secondary_indices[(primary_name, sec_name)]
                                source_indices.append(primary_idx)
                                target_indices.append(sec_idx)
                                values.append(sec_amount)
                                logger.info(f"    Link: {primary_name} → {sec_name} (${sec_amount:,.0f})")
                else:
                    # Primary has no secondaries - link directly from Total Revenue
                    if primary_name in primary_indices:
                        primary_idx = primary_indices[primary_name]
                        source_indices.append(total_revenue_idx)
                        target_indices.append(primary_idx)
                        values.append(primary_amount)
                        logger.info(f"  Link: Total Revenue → {primary_name} (direct, ${primary_amount:,.0f})")
    else:
        # Fallback to flat structure
        expense_items = list(expense_categories.items())
        expense_items = sorted(expense_items, key=lambda x: x[1], reverse=True)
        for expense, amount in expense_items:
            if expense in primary_indices:
                expense_idx = primary_indices[expense]
                source_indices.append(total_revenue_idx)
                target_indices.append(expense_idx)
                values.append(amount)
    
    # Create custom hover data for nodes with tertiary data
    logger.info(f"Creating hover data for {len(node_labels)} nodes")
    logger.info(f"Nodes with tertiary data: {list(node_tertiary_data.keys())}")
    
    node_customdata = []
    
    for i in range(len(node_labels)):
        if i in node_tertiary_data:
            # This node has tertiary data - create custom data with breakdown
            tertiaries = node_tertiary_data[i]
            logger.info(f"  Node {i} ({node_labels[i].split('<br>')[0]}): Creating hover with {len(tertiaries)} tertiaries")
            
            # Format tertiary breakdown (show top 10, then summarize if more)
            max_items = 10
            tertiary_lines = []
            for tert_name, tert_amount in tertiaries[:max_items]:
                tertiary_lines.append(f"• {tert_name}: ${tert_amount:,.0f}")
            
            # If more than 10, add summary
            if len(tertiaries) > max_items:
                remaining_count = len(tertiaries) - max_items
                remaining_total = sum(amount for _, amount in tertiaries[max_items:])
                tertiary_lines.append(f"...and {remaining_count} more item{'s' if remaining_count > 1 else ''}: ${remaining_total:,.0f}")
            
            # Create custom data with tertiary breakdown
            breakdown_html = "<br><br><b>Breakdown:</b><br>" + "<br>".join(tertiary_lines)
            custom_text = f"{node_labels[i]}{breakdown_html}"
            node_customdata.append(custom_text)
        elif i < len(income_sources):
            # Income node - add percentage context to hover
            node_customdata.append(f"{node_labels[i]}<br><i>of Total Revenue</i>")
        elif i in [idx for idx, _, _, _ in primary_node_info]:
            # Primary expense node (orange) - add percentage and full label to customdata
            # Find the matching primary info
            for idx, primary_name, amount, percentage in primary_node_info:
                if idx == i:
                    custom_text = f"<b>{primary_name}</b><br>${amount:,.0f} ({percentage:.1f}%)<br><i>of Total Expenses</i>"
                    node_customdata.append(custom_text)
                    break
        else:
            # No special data - use the label as customdata
            node_customdata.append(node_labels[i])
    
    # Create single hovertemplate that uses customdata
    hovertemplate = "%{customdata}<extra></extra>"
    
    # Log summary
    custom_count = sum(1 for i in range(len(node_labels)) if i in node_tertiary_data)
    logger.info(f"Custom hover data created: {custom_count} with tertiary breakdown, {len(node_labels) - custom_count} with label only")
    
    # Store primary node info for left-side labels (only for hierarchical structure)
    primary_node_info = []  # Will store (node_index, primary_name, amount) for annotation
    
    if expense_hierarchy:
        # Collect info about orange primary nodes (those in the middle column with secondaries)
        for primary_name, primary_data in expense_hierarchy.items():
            secondaries = primary_data.get('secondary', {})
            if secondaries and primary_name in primary_indices:
                idx = primary_indices[primary_name]
                # Verify this is an orange node
                if idx < len(node_colors) and node_colors[idx] == "#e67e22":
                    amount = primary_data.get('total', 0)
                    # Calculate percentage of total expenses
                    percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
                    primary_node_info.append((idx, primary_name, amount, percentage))
                    # Remove the label from node_labels for these nodes (we'll add as annotation)
                    # Keep customdata intact for hover tooltips
                    node_labels[idx] = ""  # Empty label, we'll use annotations instead
                    logger.info(f"Will create left-side label for: {primary_name} (${amount:,.0f}, {percentage:.1f}% of expenses)")
        
        logger.info(f"Created {len(primary_node_info)} primary expense labels for left-side positioning")
    
    # Create the Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 25,
            thickness = 35,
            line = dict(color = "black", width = 1),
            label = node_labels,
            color = node_colors,
            x = node_x_positions,
            y = None,  # Auto-arrange vertically
            customdata = node_customdata,
            hovertemplate = hovertemplate
        ),
        link = dict(
            source = source_indices,
            target = target_indices,
            value = values,
            color = "rgba(0,0,0,0.2)"
        )
    )])
    
    # Format date range
    date_range = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
    
    # Add title with financial summary and date range
    income_source_label = "Project Revenue" if len(income_sources) > 0 else "Account Revenue"
    title_text = f"Financial Flow Analysis - {income_source_label} ({date_range})<br><sub>Total Revenue: ${total_revenue:,.0f} | Total Expenses: ${total_expenses:,.0f} | Net Income: ${adjusted_gross_income:,.0f}</sub>"
    
    # Calculate dynamic height based on number of nodes
    num_nodes = len(node_labels)
    # Dynamic height: min 500px, max 1500px, 30px per node
    dynamic_height = max(500, min(1500, 200 + (num_nodes * 30)))
    
    fig.update_layout(
        title_text=title_text,
        font_size=10,
        height=dynamic_height,
        width=None,  # Responsive to container width
        margin=dict(l=60, r=60, t=100, b=60),
        plot_bgcolor='white',
        paper_bgcolor='white',
        title_x=0.5,
        title_font_size=20,
        autosize=True,
        hovermode='closest',
        showlegend=False
    )
    
    # Add annotations for primary expense labels (left side of orange nodes)
    if primary_node_info:
        annotations = []
        
        # Calculate Y positions - distribute evenly in the middle section
        num_primaries = len(primary_node_info)
        # Account for title margin and distribute in the available space
        title_margin = 0.12  # Space taken by title
        bottom_margin = 0.08  # Space at bottom
        available_height = 1.0 - title_margin - bottom_margin
        
        # Start position and spacing
        start_y = 1.0 - title_margin - (available_height * 0.2)  # Start 20% from top
        spacing = (available_height * 0.6) / max(num_primaries - 1, 1)  # Use 60% of space
        
        for i, (node_idx, primary_name, amount, percentage) in enumerate(primary_node_info):
            y_position = start_y - (i * spacing)
            
            # Format the label text with percentage
            label_text = f"<b>{primary_name}</b><br>${amount:,.0f} ({percentage:.1f}%)"
            
            annotations.append(
                dict(
                    x=0.62,  # Just to the left of orange nodes (which are at x=0.67)
                    y=y_position,
                    text=label_text,
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    xanchor="right",  # Align text to the right (so it appears left of the node)
                    yanchor="middle",
                    font=dict(size=11, color="#2c3e50", family="Arial"),
                    bgcolor="rgba(255, 255, 255, 0.9)",
                    bordercolor="#e67e22",  # Orange border to match node
                    borderwidth=1,
                    borderpad=4
                )
            )
            
            logger.info(f"Added left-side annotation for {primary_name} at y={y_position:.2f} with {percentage:.1f}%")
        
        fig.update_layout(annotations=annotations)
        logger.info(f"Added {len(annotations)} primary expense annotations on the left side with percentages")
    
    return fig

def create_sample_sankey_diagram(start_date=None, end_date=None):
    """Create a sample Sankey diagram for demonstration"""
    from datetime import datetime, timedelta
    
    # Set default date range (Year to Date if not provided)
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
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
    
    # Total revenue (center column) with Net Income
    net_income_text = f"<br><br>Net Income: ${adjusted_gross_income:,.0f}" if adjusted_gross_income != 0 else ""
    node_labels.append(f"Total Revenue<br>${total_revenue:,.0f}{net_income_text}")
    node_colors.append("#3498db")  # Blue for total revenue
    
    # Expense categories (right column)
    for expense, amount in expense_categories.items():
        node_labels.append(f"{expense}<br>${amount:,.0f}")
        node_colors.append("#e74c3c")  # Red for expenses
    
    # Adjusted gross income
    node_labels.append(f"Net Income<br>${adjusted_gross_income:,.0f}")
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
    
    # Create the Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 25,
            thickness = 22,
            line = dict(color = "black", width = 1),
            label = node_labels,
            color = node_colors,
            x = [0.15, 0.5, 0.85],
            y = None  # Auto-arrange vertically
        ),
        link = dict(
            source = source_indices,
            target = target_indices,
            value = values,
            color = "rgba(0,0,0,0.2)"
        )
    )])
    
    # Format date range
    date_range = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
    
    # Add title with financial summary and date range
    income_source_label = "Project Revenue" if len(income_sources) > 0 else "Account Revenue"
    title_text = f"Financial Flow Analysis - {income_source_label} ({date_range})<br><sub>Total Revenue: ${total_revenue:,.0f} | Total Expenses: ${total_expenses:,.0f} | Net Income: ${adjusted_gross_income:,.0f}</sub>"
    
    # Calculate dynamic height based on number of categories
    num_categories = len(income_sources) + len(expense_categories) + 2  # +2 for total revenue and adjusted gross
    dynamic_height = max(800, min(2000, 300 + (num_categories * 80)))
    
    fig.update_layout(
        title_text=title_text,
        font_size=18,
        height=dynamic_height,
        margin=dict(l=80, r=80, t=120, b=80),
        plot_bgcolor='white',
        paper_bgcolor='white',
        title_x=0.5,
        title_font_size=20,
        autosize=True,
        hovermode='closest',
        showlegend=False
    )
    
    return fig