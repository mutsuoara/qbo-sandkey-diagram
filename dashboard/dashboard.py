"""
Dashboard UI components for QBO Sankey Dashboard
Contains the main dashboard page and success page creation functions.
"""

import logging
from dash import html, dcc
from .sankey_charts import create_sample_sankey_diagram

logger = logging.getLogger(__name__)

def create_error_page(message):
    """Create an error page with the given message"""
    return html.Div([
        html.Div([
            html.H2("Error", style={'textAlign': 'center', 'color': '#e74c3c', 'marginBottom': '20px'}),
            html.Div([
                html.P(message, style={'color': '#721c24', 'textAlign': 'center', 'padding': '15px', 
                                      'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'borderLeft': '4px solid #dc3545'}),
                html.Button("Back to Setup", id="back-to-setup-from-error-btn",
                           style={'backgroundColor': '#6c757d', 'color': 'white', 'border': 'none', 
                                  'padding': '10px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                  'fontSize': '14px', 'fontWeight': 'bold', 'display': 'block', 
                                  'margin': '20px auto'})
            ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
        ], style={'maxWidth': '600px', 'margin': '0 auto'})
    ])

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
    """Create the main dashboard page with Sankey diagrams and date range picker"""
    logger.info("Creating dashboard page with Sankey diagrams")
    
    # Create Sankey diagram with Year to Date as default
    from datetime import datetime
    from .data_fetcher import QBODataFetcher
    from .enhanced_sankey import create_enhanced_sankey_diagram, create_sample_sankey_diagram
    
    end_date = datetime.now()
    start_date = datetime(end_date.year, 1, 1)
    
    # Get real data from QuickBooks - NO FALLBACK TO SAMPLE DATA
    try:
        # Import credential manager to get stored tokens
        from utils.credentials import CredentialManager
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        
        if not tokens:
            logger.error("No authentication tokens found")
            return create_error_page("No authentication tokens found. Please connect to QuickBooks first.")
        
        # Get environment from stored credentials
        credentials = credential_manager.get_credentials()
        environment = credentials.get('environment', 'sandbox') if credentials else 'sandbox'
        
        # Create data fetcher with stored tokens (now with automatic token refresh)
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get real financial data
        financial_data = data_fetcher.get_financial_data_for_sankey(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Create enhanced Sankey diagram with real data
        fig = create_enhanced_sankey_diagram(financial_data, start_date, end_date)
        logger.info("Created dashboard with real QuickBooks data")
            
    except Exception as e:
        logger.error(f"Error fetching real data: {e}")
        return create_error_page(f"Failed to fetch QuickBooks data: {str(e)}")
    
    return html.Div([
        html.Div([
            html.H1("QBO Sankey Dashboard", style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
            
            # Date Range Picker Section
            html.Div([
                html.Div([
                    html.H4("Date Range Selection", style={'color': '#2c3e50', 'marginBottom': '15px'}),
                    html.Div([
                        html.Label("Start Date:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                        dcc.DatePickerSingle(
                            id='start-date-picker',
                            date=None,  # Will be set by callback
                            style={'marginRight': '20px'}
                        ),
                        html.Label("End Date:", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                        dcc.DatePickerSingle(
                            id='end-date-picker',
                            date=None,  # Will be set by callback
                            style={'marginRight': '20px'}
                        ),
                        html.Button("Apply Date Range", id="apply-date-range-btn", 
                                   style={'backgroundColor': '#0077be', 'color': 'white', 'border': 'none', 
                                          'padding': '8px 16px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                          'fontSize': '14px', 'fontWeight': 'bold', 'marginLeft': '10px'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '10px'}),
                    
                    # Quick date range buttons
                    html.Div([
                        html.Button("Year to Date", id="ytd-btn", 
                                   style={'backgroundColor': '#27ae60', 'color': 'white', 'border': 'none', 
                                          'padding': '6px 12px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                          'fontSize': '12px', 'fontWeight': 'bold', 'marginRight': '5px'}),
                        html.Button("Last 30 Days", id="last30-btn", 
                                   style={'backgroundColor': '#3498db', 'color': 'white', 'border': 'none', 
                                          'padding': '6px 12px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                          'fontSize': '12px', 'fontWeight': 'bold', 'marginRight': '5px'}),
                        html.Button("Last 90 Days", id="last90-btn", 
                                   style={'backgroundColor': '#9b59b6', 'color': 'white', 'border': 'none', 
                                          'padding': '6px 12px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                          'fontSize': '12px', 'fontWeight': 'bold', 'marginRight': '5px'}),
                        html.Button("Last Year", id="lastyear-btn", 
                                   style={'backgroundColor': '#e67e22', 'color': 'white', 'border': 'none', 
                                          'padding': '6px 12px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                          'fontSize': '12px', 'fontWeight': 'bold', 'marginRight': '5px'}),
                    ], style={'marginTop': '10px'})
                ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)', 'marginBottom': '20px'})
            ]),
            
            # Sankey Chart Section
            html.Div([
                html.Div([
                    html.H3("Financial Flow Visualization", style={'textAlign': 'center', 'color': '#34495e', 'marginBottom': '20px'}),
                    dcc.Graph(
                        id='sankey-chart',
                        figure=fig,
                        style={'height': 'auto', 'minHeight': '800px'}  # Dynamic height, minimum 800px
                    )
                ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)', 'marginBottom': '40px'}),
                
                # Quick Actions Section
                html.Div([
                    html.Div([
                        html.H4("Quick Actions", style={'color': '#2c3e50', 'marginBottom': '15px'}),
                        html.Button("Refresh Data", id="refresh-data-btn", 
                                   style={'backgroundColor': '#27ae60', 'color': 'white', 'border': 'none', 
                                          'padding': '10px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                          'fontSize': '14px', 'fontWeight': 'bold', 'marginRight': '10px'}),
                        # html.Button("Export Data", id="export-data-btn", 
                        #            style={'backgroundColor': '#3498db', 'color': 'white', 'border': 'none', 
                        #                   'padding': '10px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 
                        #                   'fontSize': '14px', 'fontWeight': 'bold', 'marginRight': '10px'}),
                        html.Button("Export PNG", id="export-png-btn", 
                                   style={'backgroundColor': '#8e44ad', 'color': 'white', 'border': 'none', 
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
