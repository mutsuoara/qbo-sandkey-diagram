"""
Enhanced Sankey diagram with zoom, pan, and dynamic sizing
"""

import plotly.graph_objects as go
import logging
import re
import math
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
        # Debug logging for account 8500 specifically
        if '8500' in expense_name or 'GA Travel' in expense_name:
            logger.info(f"🔍 Processing expense: '{expense_name}' = ${amount:,.2f}")
        
        # Extract account number from start of name (e.g., "6001 Some Expense" -> 6001)
        match = re.match(r'^(\d{3,4})', expense_name)
        
        if match and amount < threshold:
            account_num = int(match.group(1))
            
            # Debug logging for account 8500
            if account_num == 8500:
                logger.info(f"🔍 Account 8500 found: amount=${amount:,.2f}, threshold=${threshold:,.2f}")
            
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
                if account_num == 8500:
                    logger.info(f"✅ Account 8500 kept as individual expense: '{expense_name}' = ${amount:,.2f}")
        else:
            # Amount >= threshold OR no account number found - keep as individual
            grouped_expenses[expense_name] = amount
            if '8500' in expense_name or 'GA Travel' in expense_name:
                reason = "amount >= threshold" if match and amount >= threshold else "no account number found"
                logger.info(f"✅ Account 8500 kept as individual (reason: {reason}): '{expense_name}' = ${amount:,.2f}")
    
    logger.info(f"After grouping: {len(grouped_expenses)} expenses remain")
    if any('8500' in name or 'GA Travel' in name for name in grouped_expenses.keys()):
        logger.info(f"✅ Account 8500 found in final grouped expenses")
        for name, amt in grouped_expenses.items():
            if '8500' in name or 'GA Travel' in name:
                logger.info(f"  - '{name}': ${amt:,.2f}")
    else:
        logger.warning(f"⚠️ Account 8500 NOT found in final grouped expenses")
    
    return grouped_expenses

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
    
    # Store tertiary data for hover tooltips (map node index to tertiary data)
    node_tertiary_data = {}  # Map node index -> list of (tertiary_name, tertiary_amount) tuples
    
    # Income sources (left column, x=0)
    income_indices = {}
    for i, (source, amount) in enumerate(income_sources.items()):
        node_labels.append(f"{source}<br>${amount:,.0f}")
        node_colors.append("#27ae60")  # Green for income
        node_x_positions.append(0.0)
        income_indices[source] = i
    
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
        # Note: Tertiary categories are stored in expense_hierarchy but NOT displayed as nodes
        # They remain in the data structure for future hover tooltip implementation
        for primary_name, primary_data in expense_hierarchy.items():
            secondaries = primary_data.get('secondary', {})
            if secondaries:
                # This primary has secondaries - create secondary nodes
                for sec_name, sec_data in secondaries.items():
                    sec_amount = sec_data.get('total', 0)
                    if sec_amount > 0:
                        idx = len(node_labels)
                        node_labels.append(f"{sec_name}<br>${sec_amount:,.0f}")
                        node_colors.append("#e74c3c")  # Red for secondary expenses
                        node_x_positions.append(1.0)
                        
                        # Store tertiary data for this node if it exists
                        tertiaries = sec_data.get('tertiary', {})
                        if tertiaries:
                            # Store tertiary data as list of tuples for hover tooltip
                            tertiary_list = sorted(tertiaries.items(), key=lambda x: x[1], reverse=True)
                            node_tertiary_data[idx] = tertiary_list
                            logger.info(f"    Created secondary node with {len(tertiaries)} tertiaries (for hover tooltip): {sec_name} (idx={idx})")
                        else:
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
            node_labels.append(f"{expense}<br>${amount:,.0f}")
            node_colors.append("#e74c3c")  # Red for expenses
            node_x_positions.append(1.0)
            primary_indices[expense] = idx  # Use same dict for flat structure
    
    # Net Income is now displayed as text below Total Revenue, not as a separate node
    
    # Create links with logarithmic scaling for thickness
    # Values < $20,000 will appear as thin lines, larger values scale logarithmically
    source_indices = []
    target_indices = []
    values = []
    
    # Threshold: values below $20k will appear as thin lines (use minimum value)
    threshold = 20000
    min_log_value = 100  # Minimum for thin lines
    
    def scale_value(val):
        """Scale value logarithmically: values < $20k become thin lines"""
        if val < threshold:
            return min_log_value  # Thin line for values < $20k
        else:
            # Logarithmic scaling for values >= $20k (reduced scaling factor)
            # log10(val / threshold) * scale_factor + min_value
            log_factor = math.log10(max(val, 1) / threshold)
            return min_log_value + (log_factor * threshold * 0.15)  # Reduced from 0.3 to 0.15
    
    # Links from income sources to total revenue
    for i, (source, amount) in enumerate(income_sources.items()):
        source_indices.append(i)
        target_indices.append(total_revenue_idx)
        values.append(scale_value(amount))
    
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
                        values.append(scale_value(primary_amount))
                        logger.info(f"  Link: Total Revenue → {primary_name} (${primary_amount:,.0f})")
                        
                        # Then link Primary → each Secondary
                        for sec_name, sec_data in secondaries.items():
                            sec_amount = sec_data.get('total', 0)
                            if sec_amount > 0 and (primary_name, sec_name) in secondary_indices:
                                sec_idx = secondary_indices[(primary_name, sec_name)]
                                source_indices.append(primary_idx)
                                target_indices.append(sec_idx)
                                values.append(scale_value(sec_amount))
                                logger.info(f"    Link: {primary_name} → {sec_name} (${sec_amount:,.0f})")
                else:
                    # Primary has no secondaries - link directly from Total Revenue
                    if primary_name in primary_indices:
                        primary_idx = primary_indices[primary_name]
                        source_indices.append(total_revenue_idx)
                        target_indices.append(primary_idx)
                        values.append(scale_value(primary_amount))
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
                values.append(scale_value(amount))
    
    # No link to Net Income - it's displayed as text below Total Revenue
    
    # Note: Plotly Sankey only supports a single thickness value for all nodes
    # To make Total Revenue appear larger, we increase global thickness
    # The center node (Total Revenue) will benefit from this since it has the most connections
    
    # Create custom hover templates for nodes with tertiary data
    # Nodes with tertiaries get custom template, others use None for default Plotly behavior
    logger.info(f"Creating hover templates for {len(node_labels)} nodes")
    logger.info(f"Nodes with tertiary data: {list(node_tertiary_data.keys())}")
    
    hovertemplates = []
    for i in range(len(node_labels)):
        if i in node_tertiary_data:
            # This node has tertiary data - create custom hover template with breakdown
            tertiaries = node_tertiary_data[i]
            logger.info(f"  Node {i} ({node_labels[i].split('<br>')[0]}): Creating hover template with {len(tertiaries)} tertiaries")
            
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
            
            # Create custom hovertemplate with tertiary breakdown
            # %{label} shows the node label, then we add the breakdown
            breakdown_html = "<br><br><b>Breakdown:</b><br>" + "<br>".join(tertiary_lines)
            template = f"%{{label}}{breakdown_html}<extra></extra>"
            hovertemplates.append(template)
            
            # Debug: log first few lines of template
            logger.info(f"    Template preview (first 100 chars): {template[:100]}...")
            logger.info(f"    First 3 tertiary items: {tertiaries[:3]}")
        else:
            # No tertiary data - use None for default Plotly hover behavior
            hovertemplates.append(None)
    
    # Log summary
    custom_count = sum(1 for h in hovertemplates if h is not None)
    logger.info(f"Hover templates created: {custom_count} custom, {len(hovertemplates) - custom_count} default")
    
    # Create the enhanced Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 25,  # Reduced padding for tighter layout
            thickness = 35,  # Increased thickness for all nodes (was 22) - makes center node more prominent
            line = dict(color = "black", width = 1),
            label = node_labels,
            color = node_colors,
            x = node_x_positions if node_x_positions else [0.15, 0.5, 0.85],  # Use hierarchical positions if available
            y = None,  # Auto-arrange vertically
            hovertemplate = hovertemplates  # Custom templates for nodes with tertiaries, None for default behavior
        ),
        link = dict(
            source = source_indices,
            target = target_indices,
            value = values,  # Logarithmically scaled values for thickness
            color = "rgba(0,0,0,0.2)"  # Subtle link colors
        )
    )])
    
    # Format date range
    date_range = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
    
    # Add title with financial summary and date range
    # Check if income is by project or by account
    income_source_label = "Project Revenue" if len(income_sources) > 0 else "Account Revenue"
    
    title_text = f"Financial Flow Analysis - {income_source_label} ({date_range})<br><sub>Total Revenue: ${total_revenue:,.0f} | Total Expenses: ${total_expenses:,.0f} | Net Income: ${adjusted_gross_income:,.0f}</sub>"
    
    # Calculate dynamic height based on number of nodes (use node_labels length)
    num_nodes = len(node_labels)
    # Dynamic height: min 500px, max 1500px, 30px per node (more compact)
    dynamic_height = max(500, min(1500, 200 + (num_nodes * 30)))
    
    fig.update_layout(
        title_text=title_text,
        font_size=10,  # Smaller font size for better readability and compact display
        height=dynamic_height,   # Dynamic height to accommodate all categories (Option C)
        width=None,   # Let it be responsive to container width
        margin=dict(l=60, r=60, t=100, b=60),  # Reduced margins for more diagram space
        plot_bgcolor='white',
        paper_bgcolor='white',
        title_x=0.5,  # Center the title
        title_font_size=20,
        # Enable zooming and panning
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        # Make it responsive
        autosize=True,  # Enable responsive sizing
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
    
    # Create the enhanced Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 25,  # Reduced padding for tighter layout
            thickness = 22,  # Slightly thinner nodes for better fit
            line = dict(color = "black", width = 1),
            label = node_labels,
            color = node_colors,
            x = [0.15, 0.5, 0.85],  # More centered positioning for responsive layout
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
    # Check if income is by project or by account
    income_source_label = "Project Revenue" if len(income_sources) > 0 else "Account Revenue"
    
    title_text = f"Financial Flow Analysis - {income_source_label} ({date_range})<br><sub>Total Revenue: ${total_revenue:,.0f} | Total Expenses: ${total_expenses:,.0f} | Net Income: ${adjusted_gross_income:,.0f}</sub>"
    
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
