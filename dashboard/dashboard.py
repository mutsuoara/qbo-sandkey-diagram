"""
Dashboard UI components for QBO Sankey Dashboard
Contains the main dashboard page and success page creation functions.
"""

import logging
from dash import html, dcc
from .sankey_charts import create_sample_sankey_diagram

logger = logging.getLogger(__name__)

def create_success_page():
    """Create the success page after OAuth"""
    return html.Div([
        html.Div([
            html.H2("Authentication Successful!", style={'textAlign': 'center', 'color': '#27ae60', 'marginBottom': '20px'}),
            html.Div([
                html.P("You have successfully connected to QuickBooks Online. Your dashboard is ready!", 
                       style={'color': '#155724', 'textAlign': 'center', 'padding': '15px', 
                              'backgroundColor': '#d4edda', 'borderRadius': '4px', 'borderLeft': '4px solid #28a745'}),
                html.Div([
                    html.Button("View Dashboard", id="view-dashboard-btn", 
                               style={'backgroundColor': '#0077be', 'color': 'white', 'border': 'none', 
                                      'padding': '15px 30px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                      'fontSize': '16px', 'fontWeight': 'bold', 'display': 'block', 'margin': '20px auto'})
                ], style={'textAlign': 'center'})
            ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
        ], style={'maxWidth': '600px', 'margin': '0 auto'})
    ], id='success-page-container')

def create_dashboard_page():
    """Create the main dashboard page with Sankey diagrams"""
    logger.info("Creating dashboard page with Sankey diagrams")
    
    # Create sample Sankey diagram for now
    fig = create_sample_sankey_diagram()
    
    return html.Div([
        html.Div([
            html.H1("QBO Sankey Dashboard", style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
            html.Div([
                html.Div([
                    html.H3("Financial Flow Visualization", style={'textAlign': 'center', 'color': '#34495e', 'marginBottom': '20px'}),
                    dcc.Graph(
                        id='sankey-chart',
                        figure=fig,
                        style={'height': '600px'}
                    )
                ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)', 'marginBottom': '20px'}),
                
                html.Div([
                    html.Div([
                        html.H4("Quick Actions", style={'color': '#2c3e50', 'marginBottom': '15px'}),
                        html.Button("Refresh Data", id="refresh-data-btn", 
                                   style={'backgroundColor': '#27ae60', 'color': 'white', 'border': 'none', 
                                          'padding': '10px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                          'fontSize': '14px', 'fontWeight': 'bold', 'marginRight': '10px'}),
                        html.Button("Export Data", id="export-data-btn", 
                                   style={'backgroundColor': '#3498db', 'color': 'white', 'border': 'none', 
                                          'padding': '10px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                          'fontSize': '14px', 'fontWeight': 'bold', 'marginRight': '10px'}),
                        html.Button("Back to Setup", id="back-to-setup-btn", 
                                   style={'backgroundColor': '#e74c3c', 'color': 'white', 'border': 'none', 
                                          'padding': '10px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                          'fontSize': '14px', 'fontWeight': 'bold'})
                    ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
                ], style={'display': 'flex', 'justifyContent': 'center'})
            ])
        ], style={'maxWidth': '1200px', 'margin': '0 auto'})
    ])
