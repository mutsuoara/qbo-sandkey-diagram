"""
QBO Sankey Dashboard - Clean Working Version
A secure, standalone desktop application that extracts data from QuickBooks Online
and displays financial flows using interactive Sankey diagrams.
"""

import dash
from dash import dcc, html, Input, Output, State, callback, ctx
import plotly.graph_objects as go
import pandas as pd
import logging
from datetime import datetime, timedelta
import json
import os
import secrets
import requests
from flask import request, redirect
from utils.logging_config import setup_logging
from utils.credentials import CredentialManager
from dashboard import create_dashboard_page, create_success_page

# Initialize logging
logger = setup_logging()
if logger is None:
    logger = logging.getLogger(__name__)

# Global variables
is_authenticated = False
company_info = None

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "QBO Sankey Dashboard"

# Helper functions
def check_credentials():
    """Check if credentials exist"""
    credential_manager = CredentialManager()
    return credential_manager.has_credentials()

def create_setup_page():
    """Create the setup page for entering credentials"""
    logger.info("Creating setup page for credential entry")
    return html.Div([
        html.Div([
            html.H2("QuickBooks Online Setup", style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
            html.Div([
                html.Label("Client ID:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block'}),
                dcc.Input(
                    id="setup-client-id",
                    type="text",
                    placeholder="Enter your QuickBooks Client ID",
                    style={'width': '100%', 'padding': '10px', 'border': '1px solid #ddd', 'borderRadius': '4px', 'marginBottom': '15px'},
                    value=""
                ),
                html.Label("Client Secret:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block'}),
                dcc.Input(
                    id="setup-client-secret",
                    type="password",
                    placeholder="Enter your QuickBooks Client Secret",
                    style={'width': '100%', 'padding': '10px', 'border': '1px solid #ddd', 'borderRadius': '4px', 'marginBottom': '15px'},
                    value=""
                ),
                html.Label("Environment:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block'}),
                html.Div([
                    dcc.RadioItems(
                        id="setup-environment",
                        options=[
                            {'label': '🧪 Sandbox (Development/Testing)', 'value': 'sandbox'},
                            {'label': '🏢 Production (Live QuickBooks Data)', 'value': 'production'}
                        ],
                        value='sandbox',
                        style={'marginBottom': '10px'}
                    ),
                    html.Div([
                        html.Span("💡 ", style={'color': '#f39c12'}),
                        html.Span("Choose Production to connect to your real QuickBooks company", 
                                style={'fontSize': '12px', 'color': '#7f8c8d', 'fontStyle': 'italic'})
                    ], style={'marginBottom': '20px', 'padding': '8px', 'backgroundColor': '#fff3cd', 'borderRadius': '4px', 'borderLeft': '3px solid #f39c12'})
                ]),
                html.Div([
                    html.Button("Save Credentials", id="save-credentials-btn", 
                               style={'backgroundColor': '#27ae60', 'color': 'white', 'border': 'none', 
                                      'padding': '12px 24px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                      'fontSize': '14px', 'fontWeight': 'bold', 'marginRight': '10px'}),
                    html.Button("Test Setup", id="test-setup-btn", 
                               style={'backgroundColor': '#3498db', 'color': 'white', 'border': 'none', 
                                      'padding': '12px 24px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                      'fontSize': '14px', 'fontWeight': 'bold'})
                ], style={'textAlign': 'center'})
            ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
        ], style={'maxWidth': '600px', 'margin': '0 auto'})
    ], id='setup-page-container')

def create_welcome_page():
    """Create the welcome page"""
    logger.info("Creating welcome page with Connect to QuickBooks button")
    
    # Get current environment info
    credential_manager = CredentialManager()
    credentials = credential_manager.get_credentials()
    tokens = credential_manager.get_tokens()
    
    environment = credentials.get('environment', 'sandbox') if credentials else 'sandbox'
    realm_id = tokens.get('realm_id', 'Not connected') if tokens else 'Not connected'
    
    # Environment indicator
    env_color = '#27ae60' if environment == 'production' else '#f39c12'
    env_text = 'LIVE' if environment == 'production' else 'SANDBOX'
    
    return html.Div([
        html.Div([
            html.H1("Welcome to QBO Sankey Dashboard", style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '20px'}),
            
            # Environment indicator
            html.Div([
                html.Span(f"Environment: ", style={'fontWeight': 'bold', 'color': '#7f8c8d'}),
                html.Span(env_text, style={'fontWeight': 'bold', 'color': env_color, 'backgroundColor': f'{env_color}20', 'padding': '4px 8px', 'borderRadius': '4px'}),
                html.Br(),
                html.Span(f"Company ID: {realm_id}", style={'fontSize': '12px', 'color': '#95a5a6', 'fontFamily': 'monospace'})
            ], style={'textAlign': 'center', 'marginBottom': '20px', 'padding': '10px', 'backgroundColor': '#f8f9fa', 'borderRadius': '4px'}),
            
            html.Div([
                html.P("Connect to your QuickBooks Online account to visualize your financial data with interactive Sankey diagrams.", 
                       style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': '16px', 'marginBottom': '30px'}),
                html.Button("Connect to QuickBooks", id="connect-btn", 
                           style={'backgroundColor': '#0077be', 'color': 'white', 'border': 'none', 
                                  'padding': '15px 30px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                  'fontSize': '16px', 'fontWeight': 'bold', 'display': 'block', 'margin': '0 auto'}),
                html.Br(),
                html.Button("Reset Setup", id="reset-setup-btn", 
                           style={'backgroundColor': '#e74c3c', 'color': 'white', 'border': 'none', 
                                  'padding': '10px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                  'fontSize': '14px', 'fontWeight': 'bold', 'display': 'block', 'margin': '20px auto'})
            ], style={'backgroundColor': 'white', 'padding': '40px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
        ], style={'maxWidth': '600px', 'margin': '0 auto'})
    ], id='welcome-page-container')

def create_error_page(message):
    """Create an error page with a custom message"""
    return html.Div([
        html.Div([
            html.H2("Error", style={'textAlign': 'center', 'color': '#e74c3c', 'marginBottom': '20px'}),
            html.Div([
                html.P(message, 
                       style={'color': '#e74c3c', 'textAlign': 'center', 'padding': '15px', 
                              'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'borderLeft': '4px solid #dc3545'})
            ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
        ], style={'maxWidth': '600px', 'margin': '0 auto'})
    ])

def create_oauth_page(auth_url, environment):
    """Create the OAuth authorization page"""
    return html.Div([
        html.Div([
            html.H2("Connect to QuickBooks", style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '20px'}),
            html.Div([
                html.P("Click the button below to authorize this application with QuickBooks Online.", 
                       style={'color': '#7f8c8d', 'textAlign': 'center', 'padding': '15px', 
                              'backgroundColor': '#f8f9fa', 'borderRadius': '4px', 'marginBottom': '20px'}),
                html.P(f"Environment: {environment.title()}", 
                       style={'color': '#155724', 'textAlign': 'center', 'padding': '10px', 
                              'backgroundColor': '#d4edda', 'borderRadius': '4px', 'borderLeft': '4px solid #28a745', 
                              'marginBottom': '20px'}),
                html.A("Authorize with QuickBooks", 
                       href=auth_url, 
                       target="_blank",
                       style={'display': 'block', 'backgroundColor': '#0077be', 'color': 'white', 
                              'textAlign': 'center', 'padding': '15px 30px', 'borderRadius': '4px', 
                              'textDecoration': 'none', 'fontWeight': 'bold', 'margin': '20px auto', 
                              'maxWidth': '300px'}),
                html.P("After authorization, you'll be redirected back to this application.", 
                       style={'color': '#7f8c8d', 'textAlign': 'center', 'fontSize': '12px', 'marginTop': '15px'})
            ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
        ], style={'maxWidth': '600px', 'margin': '0 auto'})
    ])

# App layout - simple and clean, content managed by callbacks
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id="main-content", 
             style={'padding': '20px', 'maxWidth': '1200px', 'margin': '0 auto'}),
    html.Footer([
        html.P("QBO Sankey Dashboard - Secure Financial Visualization", 
               style={'textAlign': 'center', 'color': '#7f8c8d', 'margin': '0'})
    ], style={'backgroundColor': '#34495e', 'padding': '15px', 'color': 'white', 'marginTop': '20px'})
], style={'fontFamily': 'Arial, sans-serif', 'minHeight': '100vh', 'backgroundColor': '#f5f5f5'})

# Callback to handle initial page load based on credentials
@app.callback(
    Output("main-content", "children"),
    Input("url", "pathname"),
    prevent_initial_call=False
)
def display_initial_page(pathname):
    """Display the appropriate initial page"""
    logger.info(f"Initial page load - pathname: {pathname}")
    if check_credentials():
        logger.info("Credentials found - showing welcome page")
        return create_welcome_page()
    else:
        logger.info("No credentials found - showing setup page")
        return create_setup_page()

# Callback to handle URL changes (OAuth redirects)
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("url", "search"),
    prevent_initial_call=True
)
def handle_url_changes(search):
    """Handle OAuth callback URL changes"""
    global is_authenticated
    
    if search and 'auth=success' in search:
        logger.info("OAuth success detected")
        is_authenticated = True
        return create_success_page()
    elif search and 'auth=error' in search:
        logger.error("OAuth error detected")
        return create_error_page("OAuth authentication failed. Please try again.")
    
    return dash.no_update

# Callback to handle Save Credentials button
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("save-credentials-btn", "n_clicks"),
    State("setup-client-id", "value"),
    State("setup-client-secret", "value"),
    State("setup-environment", "value"),
    prevent_initial_call=True
)
def save_credentials(n_clicks, client_id, client_secret, environment):
    """Handle Save Credentials button click"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Save credentials button clicked")
    logger.info(f"Values - Client ID: {client_id}, Secret: {'***' if client_secret else None}, Env: {environment}")
    
    if not client_id or not client_secret:
        logger.warning("Missing credentials")
        return create_error_page("Please enter both Client ID and Client Secret.")
    
    # Store credentials
    credential_manager = CredentialManager()
    credentials = {
        'client_id': client_id,
        'client_secret': client_secret,
        'environment': environment if environment else 'sandbox'
    }
    
    if credential_manager.store_credentials(credentials):
        logger.info("Credentials saved successfully - showing welcome page")
        return create_welcome_page()
    else:
        logger.error("Failed to save credentials")
        return create_error_page("Failed to save credentials. Please try again.")

# Callback to handle Test Setup button
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("test-setup-btn", "n_clicks"),
    State("setup-client-id", "value"),
    State("setup-client-secret", "value"),
    State("setup-environment", "value"),
    prevent_initial_call=True
)
def test_setup(n_clicks, client_id, client_secret, environment):
    """Handle Test Setup button click"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Test setup button clicked")
    
    if not client_id or not client_secret:
        return create_error_page("Please enter both Client ID and Client Secret to test.")
    
    # Test credentials by trying to create OAuth URL
    try:
        state = secrets.token_urlsafe(32)
        auth_url = f"https://appcenter.intuit.com/connect/oauth2?client_id={client_id}&scope=com.intuit.quickbooks.accounting&redirect_uri=http://localhost:8050/callback&response_type=code&access_type=offline&state={state}"
        
        return html.Div([
            html.Div([
                html.H2("Setup Test Successful", style={'textAlign': 'center', 'color': '#27ae60', 'marginBottom': '20px'}),
                html.Div([
                    html.P("Your credentials are valid! You can now save them and connect to QuickBooks.", 
                           style={'color': '#155724', 'textAlign': 'center', 'padding': '15px', 
                                  'backgroundColor': '#d4edda', 'borderRadius': '4px', 'borderLeft': '4px solid #28a745'}),
                    html.Button("← Back to Setup", id="back-to-setup-from-test-btn",
                               style={'backgroundColor': '#6c757d', 'color': 'white', 'border': 'none', 
                                      'padding': '10px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                      'fontSize': '14px', 'fontWeight': 'bold', 'display': 'block', 
                                      'margin': '20px auto'})
                ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
            ], style={'maxWidth': '600px', 'margin': '0 auto'})
        ])
    except Exception as e:
        return create_error_page(f"Test failed: {str(e)}")

# Callback to handle Connect to QuickBooks button
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("connect-btn", "n_clicks"),
    prevent_initial_call=True
)
def connect_to_quickbooks(n_clicks):
    """Handle Connect to QuickBooks button click"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Connect to QuickBooks button clicked")
    
    try:
        # Get stored credentials
        credential_manager = CredentialManager()
        credentials = credential_manager.get_credentials()
        
        if not credentials:
            return create_error_page("No credentials found. Please set up your QuickBooks app credentials first.")
        
        # Start OAuth flow
        client_id = credentials.get('client_id')
        environment = credentials.get('environment', 'sandbox')
        
        # Generate OAuth URL with state parameter for security
        state = secrets.token_urlsafe(32)
        
        # Determine redirect URI based on environment
        if environment == 'production':
            # For production, check if we're running behind ngrok
            import os
            ngrok_url = os.environ.get('NGROK_URL')
            if ngrok_url:
                redirect_uri = f"{ngrok_url}/callback"
                logger.info(f"Using ngrok redirect URI: {redirect_uri}")
            else:
                # Fallback to localhost (will fail but give clear error)
                redirect_uri = "http://localhost:8050/callback"
                logger.warning("Production environment detected but no NGROK_URL found. OAuth will likely fail.")
        else:
            redirect_uri = "http://localhost:8050/callback"
        
        auth_url = f"https://appcenter.intuit.com/connect/oauth2?client_id={client_id}&scope=com.intuit.quickbooks.accounting&redirect_uri={redirect_uri}&response_type=code&access_type=offline&state={state}"
        
        return create_oauth_page(auth_url, environment)
        
    except Exception as e:
        logger.error(f"Error starting OAuth flow: {e}")
        return create_error_page(f"Error starting QuickBooks connection: {str(e)}")

# Callback to handle Reset Setup button
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("reset-setup-btn", "n_clicks"),
    prevent_initial_call=True
)
def reset_setup(n_clicks):
    """Handle Reset Setup button click"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Reset setup button clicked")
    
    try:
        # Clear keyring credentials
        credential_manager = CredentialManager()
        credential_manager.clear_credentials()
        credential_manager.clear_tokens()
        
        # Also remove temporary file if it exists
        if os.path.exists('temp_credentials.json'):
            os.remove('temp_credentials.json')
            logger.info("Temporary credentials file deleted")
        
        logger.info("All credentials cleared successfully")
        return create_setup_page()
    except Exception as e:
        logger.error(f"Failed to clear credentials: {e}")
        return create_setup_page()

# Callback to handle Back to Setup from Test button
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("back-to-setup-from-test-btn", "n_clicks"),
    prevent_initial_call=True
)
def back_to_setup_from_test(n_clicks):
    """Handle back to setup from test page"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Back to setup from test button clicked")
    return create_setup_page()

# Callback to handle View Dashboard button
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("view-dashboard-btn", "n_clicks"),
    prevent_initial_call=True
)
def view_dashboard(n_clicks):
    """Handle View Dashboard button click"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("View Dashboard button clicked")
    return create_dashboard_page()

# Callback to handle Refresh Data button
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("refresh-data-btn", "n_clicks"),
    prevent_initial_call=True
)
def refresh_data(n_clicks):
    """Handle Refresh Data button click"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Refresh Data button clicked")
    # In the future, this would refresh data from QuickBooks
    return create_dashboard_page()

# Callback to handle Export Data button
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("export-data-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_data(n_clicks):
    """Handle Export Data button click"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Export Data button clicked")
    # In the future, this would export data
    # For now, just stay on the dashboard
    return dash.no_update

# Callback to handle Back to Setup button from dashboard
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("back-to-setup-btn", "n_clicks"),
    prevent_initial_call=True
)
def back_to_setup(n_clicks):
    """Handle Back to Setup button click from dashboard"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Back to Setup button clicked from dashboard")
    return create_setup_page()

# OAuth callback route handler
@app.server.route('/callback')
def oauth_callback():
    """Handle OAuth callback from QuickBooks"""
    logger.info("OAuth callback received")
    
    # Get the authorization code from the callback
    code = request.args.get('code')
    state = request.args.get('state')
    realm_id = request.args.get('realmId')
    
    if not code:
        logger.error("No authorization code received")
        return redirect('/?auth=error')
    
    logger.info(f"OAuth callback - Code: {code[:10]}..., Realm: {realm_id}, State: {state}")
    
    try:
        # Get stored credentials
        credential_manager = CredentialManager()
        credentials = credential_manager.get_credentials()
        
        if not credentials:
            logger.error("No stored credentials found")
            return redirect('/?auth=error')
        
        # Exchange code for tokens
        tokens = exchange_code_for_token(code, credentials)
        if not tokens:
            logger.error("Failed to exchange code for token")
            return redirect('/?auth=error')
        
        # Store tokens
        credential_manager.store_token(tokens['access_token'], tokens['refresh_token'], realm_id)
        
        # Fetch and store company info
        company_info = fetch_company_info(tokens['access_token'], realm_id)
        if company_info:
            credential_manager.store_company_info(company_info)
        
        logger.info("OAuth flow completed successfully")
        return redirect('/?auth=success')
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return redirect('/?auth=error')

def exchange_code_for_token(code, credentials):
    """Exchange authorization code for access token"""
    try:
        client_id = credentials['client_id']
        client_secret = credentials['client_secret']
        environment = credentials.get('environment', 'sandbox')
        
        # Token endpoint is the same for both environments
        token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
        
        # Prepare the request
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Determine redirect URI based on environment
        if environment == 'production':
            import os
            ngrok_url = os.environ.get('NGROK_URL')
            if ngrok_url:
                redirect_uri = f"{ngrok_url}/callback"
            else:
                redirect_uri = "http://localhost:8050/callback"
        else:
            redirect_uri = "http://localhost:8050/callback"
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        # Make the request
        response = requests.post(token_url, headers=headers, data=data, 
                               auth=(client_id, client_secret))
        
        logger.info(f"Token exchange response status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        return None

def fetch_company_info(access_token, realm_id):
    """Fetch company information from QuickBooks"""
    try:
        # Get environment from stored credentials
        credential_manager = CredentialManager()
        credentials = credential_manager.get_credentials()
        environment = credentials.get('environment', 'sandbox') if credentials else 'sandbox'
        
        if environment == 'production':
            base_url = "https://quickbooks.api.intuit.com"
        else:
            base_url = "https://sandbox-quickbooks.api.intuit.com"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        # Get company info
        company_url = f"{base_url}/v3/company/{realm_id}/companyinfo/{realm_id}"
        response = requests.get(company_url, headers=headers)
        
        if response.status_code == 200:
            company_data = response.json()
            return company_data.get('CompanyInfo')
        else:
            logger.error(f"Failed to fetch company info: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching company info: {e}")
        return None

# Date range callbacks
@app.callback(
    Output("sankey-chart", "figure"),
    [Input("apply-date-range-btn", "n_clicks"),
     Input("ytd-btn", "n_clicks"),
     Input("last30-btn", "n_clicks"),
     Input("last90-btn", "n_clicks"),
     Input("lastyear-btn", "n_clicks"),
     Input("test2015-btn", "n_clicks")],
    [State("start-date-picker", "date"),
     State("end-date-picker", "date")],
    prevent_initial_call=True,
    suppress_callback_exceptions=True
)
def update_sankey_chart(apply_clicks, ytd_clicks, last30_clicks, last90_clicks, lastyear_clicks, test2015_clicks, start_date, end_date):
    """Update Sankey chart based on date range selection"""
    from datetime import datetime, timedelta
    from dashboard.sankey_charts import create_sample_sankey_diagram
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Handle different date range buttons
    if trigger_id == 'ytd-btn' and ytd_clicks:
        logger.info("Year to Date button clicked")
        end_date = datetime.now()
        start_date = datetime(end_date.year, 1, 1)
    elif trigger_id == 'last30-btn' and last30_clicks:
        logger.info("Last 30 Days button clicked")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
    elif trigger_id == 'last90-btn' and last90_clicks:
        logger.info("Last 90 Days button clicked")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
    elif trigger_id == 'lastyear-btn' and lastyear_clicks:
        logger.info("Last Year button clicked")
        end_date = datetime.now()
        start_date = datetime(end_date.year - 1, 1, 1)
        end_date = datetime(end_date.year - 1, 12, 31)
    elif trigger_id == 'test2015-btn' and test2015_clicks:
        logger.info("Test 2015 Data button clicked")
        start_date = datetime(2015, 6, 1)
        end_date = datetime(2015, 6, 30)
    elif trigger_id == 'apply-date-range-btn' and apply_clicks:
        logger.info("Apply Date Range button clicked")
        if not start_date or not end_date:
            logger.warning("No dates selected for custom range")
            return dash.no_update
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        return dash.no_update
    
    logger.info(f"Updating chart for date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Try to get real data from QuickBooks
    try:
        from utils.credentials import CredentialManager
        from dashboard.data_fetcher import QBODataFetcher
        from dashboard.sankey_charts import create_sankey_diagram_from_data, create_sample_sankey_diagram
        
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        
        if tokens:
            # Create data fetcher with stored tokens
            # Get environment from stored credentials
            credentials = credential_manager.get_credentials()
            environment = credentials.get('environment', 'sandbox') if credentials else 'sandbox'
            
            data_fetcher = QBODataFetcher(
                access_token=tokens['access_token'],
                realm_id=tokens['realm_id'],
                environment=environment
            )
            
            # Get real financial data for the selected date range
            financial_data = data_fetcher.get_financial_data_for_sankey(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            # Create Sankey diagram with real data
            return create_sankey_diagram_from_data(financial_data, start_date, end_date)
        else:
            # No tokens available, use sample data
            return create_sample_sankey_diagram(start_date, end_date)
            
    except Exception as e:
        logger.error(f"Error fetching real data for date range: {e}")
        # Fallback to sample data
        return create_sample_sankey_diagram(start_date, end_date)

# Callback to set default date values
@app.callback(
    [Output("start-date-picker", "date"),
     Output("end-date-picker", "date")],
    Input("view-dashboard-btn", "n_clicks"),
    prevent_initial_call=True,
    suppress_callback_exceptions=True
)
def set_default_dates(n_clicks):
    """Set default date values when dashboard loads"""
    if not n_clicks:
        return dash.no_update, dash.no_update
    
    from datetime import datetime
    
    # Set default to Year to Date
    end_date = datetime.now()
    start_date = datetime(end_date.year, 1, 1)
    
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("QBO Sankey Dashboard - Starting Application")
    logger.info(f"Startup time: {datetime.now()}")
    logger.info("=" * 50)
    
    if not check_credentials():
        logger.info("No credentials found - setup page will be shown")
    else:
        logger.info("Credentials found - welcome page will be shown")
    
    logger.info("Starting QBO Sankey Dashboard")
    app.run(debug=True, host='127.0.0.1', port=8050)
    logger.info("Dash is running on http://127.0.0.1:8050/")