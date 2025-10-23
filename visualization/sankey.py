"""
Sankey diagram creation and visualization
"""

import plotly.graph_objects as go
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class SankeyDiagram:
    """Creates and manages Sankey diagrams for financial data"""
    
    def __init__(self):
        self.default_colors = {
            'revenue': '#2E8B57',      # Green
            'expense': '#DC143C',       # Red
            'net_income': '#4169E1',    # Blue
            'net_loss': '#FF6347'       # Orange
        }
    
    def create_sankey_diagram(self, sankey_data: Dict[str, Any]) -> go.Figure:
        """Create Sankey diagram from parsed data"""
        try:
            if not sankey_data or not sankey_data.get('nodes'):
                logger.warning("No data provided for Sankey diagram")
                return self._create_empty_data_diagram()
            
            nodes = sankey_data.get('nodes', [])
            links = sankey_data.get('links', [])
            metadata = sankey_data.get('metadata', {})
            
            if not nodes or not links:
                logger.warning("Empty nodes or links data")
                return self._create_empty_data_diagram()
            
            # Create the Sankey diagram
            fig = self._create_full_sankey(nodes, links, metadata)
            
            # Add interactive features
            self._add_interactive_features(fig)
            
            # Apply custom styling
            self._apply_custom_styling(fig, metadata)
            
            logger.info("Sankey diagram created successfully")
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create Sankey diagram: {e}")
            return self._create_error_diagram(str(e))
    
    def _create_full_sankey(self, nodes: List[Dict[str, Any]], 
                           links: List[Dict[str, Any]], 
                           metadata: Dict[str, Any]) -> go.Figure:
        """Create the main Sankey diagram"""
        try:
            # Prepare node data
            node_labels = [node['label'] for node in nodes]
            node_colors = [node.get('color', '#808080') for node in nodes]
            
            # Prepare link data
            link_sources = [link['source'] for link in links]
            link_targets = [link['target'] for link in links]
            link_values = [abs(link['value']) for link in links]  # Use absolute values for display
            link_colors = self._get_link_colors(links, nodes)
            
            # Create Sankey trace
            sankey_trace = go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=node_labels,
                    color=node_colors
                ),
                link=dict(
                    source=link_sources,
                    target=link_targets,
                    value=link_values,
                    color=link_colors
                )
            )
            
            # Create figure
            fig = go.Figure(data=[sankey_trace])
            
            # Set layout
            fig.update_layout(
                title_text=f"Financial Flow - {metadata.get('total_revenue', 0):,.2f} Revenue, {metadata.get('total_expenses', 0):,.2f} Expenses",
                font_size=12,
                height=600,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create full Sankey: {e}")
            raise
    
    def _get_link_colors(self, links: List[Dict[str, Any]], 
                        nodes: List[Dict[str, Any]]) -> List[str]:
        """Get colors for links based on source nodes"""
        link_colors = []
        
        for link in links:
            source_idx = link['source']
            if source_idx < len(nodes):
                source_color = nodes[source_idx].get('color', '#808080')
                # Make link color slightly transparent
                link_colors.append(f"rgba({self._hex_to_rgb(source_color)}, 0.6)")
            else:
                link_colors.append("rgba(128, 128, 128, 0.6)")
        
        return link_colors
    
    def _hex_to_rgb(self, hex_color: str) -> str:
        """Convert hex color to RGB string"""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"{r}, {g}, {b}"
        except:
            return "128, 128, 128"
    
    def _add_interactive_features(self, fig: go.Figure):
        """Add interactive features to the diagram"""
        try:
            # Add hover template
            fig.update_traces(
                hovertemplate='<b>%{label}</b><br>Value: %{value:,.2f}<extra></extra>'
            )
            
            # Add click events (if needed in the future)
            # This could be extended to show detailed information on click
            
        except Exception as e:
            logger.error(f"Failed to add interactive features: {e}")
    
    def _apply_custom_styling(self, fig: go.Figure, metadata: Dict[str, Any]):
        """Apply custom styling based on data"""
        try:
            # Update title with financial summary
            total_revenue = metadata.get('total_revenue', 0)
            total_expenses = metadata.get('total_expenses', 0)
            net_income = metadata.get('net_income', 0)
            
            title = f"Financial Flow Analysis<br>"
            title += f"Revenue: ${total_revenue:,.2f} | "
            title += f"Expenses: ${total_expenses:,.2f} | "
            title += f"Net Income: ${net_income:,.2f}"
            
            fig.update_layout(
                title_text=title,
                title_x=0.5,
                title_font_size=16,
                font=dict(family="Arial", size=12),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
        except Exception as e:
            logger.error(f"Failed to apply custom styling: {e}")
    
    def _create_empty_data_diagram(self) -> go.Figure:
        """Create diagram for empty data scenario"""
        fig = go.Figure()
        
        fig.add_annotation(
            text="No financial data available<br>Connect to QuickBooks and refresh data",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        
        fig.update_layout(
            title_text="No Data Available",
            showlegend=False,
            height=400,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return fig
    
    def _create_error_diagram(self, error_message: str) -> go.Figure:
        """Create diagram for error scenarios"""
        fig = go.Figure()
        
        fig.add_annotation(
            text=f"Error creating diagram:<br>{error_message}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="red")
        )
        
        fig.update_layout(
            title_text="Error",
            showlegend=False,
            height=400,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return fig
    
    def create_revenue_only_diagram(self, revenue_data: List[Dict[str, Any]]) -> go.Figure:
        """Create diagram showing only revenue sources"""
        try:
            if not revenue_data:
                return self._create_empty_data_diagram()
            
            # Create nodes for revenue sources
            nodes = []
            for item in revenue_data:
                nodes.append({
                    'label': item['name'],
                    'color': self.default_colors['revenue']
                })
            
            # Create links (revenue sources to total)
            links = []
            for i, item in enumerate(revenue_data):
                links.append({
                    'source': i,
                    'target': len(revenue_data),
                    'value': item['amount']
                })
            
            # Add total revenue node
            total_revenue = sum(item['amount'] for item in revenue_data)
            nodes.append({
                'label': f'Total Revenue (${total_revenue:,.2f})',
                'color': self.default_colors['net_income']
            })
            
            return self._create_full_sankey(nodes, links, {'total_revenue': total_revenue})
            
        except Exception as e:
            logger.error(f"Failed to create revenue-only diagram: {e}")
            return self._create_error_diagram(str(e))
    
    def create_expenses_only_diagram(self, expense_data: List[Dict[str, Any]]) -> go.Figure:
        """Create diagram showing only expense categories"""
        try:
            if not expense_data:
                return self._create_empty_data_diagram()
            
            # Create nodes for expense categories
            nodes = []
            for item in expense_data:
                nodes.append({
                    'label': item['name'],
                    'color': self.default_colors['expense']
                })
            
            # Create links (expense categories to total)
            links = []
            for i, item in enumerate(expense_data):
                links.append({
                    'source': i,
                    'target': len(expense_data),
                    'value': item['amount']
                })
            
            # Add total expenses node
            total_expenses = sum(item['amount'] for item in expense_data)
            nodes.append({
                'label': f'Total Expenses (${total_expenses:,.2f})',
                'color': self.default_colors['expense']
            })
            
            return self._create_full_sankey(nodes, links, {'total_expenses': total_expenses})
            
        except Exception as e:
            logger.error(f"Failed to create expenses-only diagram: {e}")
            return self._create_error_diagram(str(e))

