"""
QBO Sankey Dashboard - Clean Working Version
A secure, standalone desktop application that extracts data from QuickBooks Online
and displays financial flows using interactive Sankey diagrams.
"""

import dash
from dash import dcc, html, Input, Output, State, callback
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

# Initialize logging
logger = setup_logging()
if logger is None:
    logger = logging.getLogger(__name__)

# Global variables
is_authenticated = False
company_info = None

# Initialize Dash app
app = dash.Dash(__name__)
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
                dcc.RadioItems(
                    id="setup-environment",
                    options=[
                        {'label': 'Sandbox (Development)', 'value': 'sandbox'},
                        {'label': 'Production', 'value': 'production'}
                    ],
                    value='sandbox',
                    style={'marginBottom': '20px'}
                ),
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
    ])

def create_welcome_page():
    """Create the welcome page"""
    logger.info("Creating welcome page with Connect to QuickBooks button")
    return html.Div([
        html.Div([
            html.H1("Welcome to QBO Sankey Dashboard", style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
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
                html.P("Dashboard features coming soon...", 
                       style={'color': '#7f8c8d', 'textAlign': 'center', 'fontSize': '14px', 'marginTop': '20px'})
            ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
        ], style={'maxWidth': '600px', 'margin': '0 auto'})
    ])

# VALIDATION LAYOUT - Contains all components for callback validation
# This is the official Dash recommended approach for dynamic/multi-page apps
def create_validation_layout():
    """
    Create a complete layout containing ALL components used in callbacks.
    This allows Dash to validate all callbacks without raising exceptions.
    This layout is never shown to users - it's only for validation.
    """
    return html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id="main-content"),
        
        # Setup page components
        dcc.Input(id="setup-client-id"),
        dcc.Input(id="setup-client-secret"),
        dcc.RadioItems(id="setup-environment"),
        html.Button(id="save-credentials-btn"),
        html.Button(id="test-setup-btn"),
        
        # Welcome page components
        html.Button(id="connect-btn"),
        html.Button(id="reset-setup-btn"),
    ])

# Set validation layout (for callback validation)
app.validation_layout = create_validation_layout()

# App layout (what users actually see)
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id="main-content", children=create_setup_page() if not check_credentials() else create_welcome_page(), 
             style={'padding': '20px', 'maxWidth': '1200px', 'margin': '0 auto'}),
    html.Footer([
        html.P("QBO Sankey Dashboard - Secure Financial Visualization", 
               style={'textAlign': 'center', 'color': '#7f8c8d', 'margin': '0'})
    ], style={'backgroundColor': '#34495e', 'padding': '15px', 'color': 'white', 'marginTop': '20px'})
], style={'fontFamily': 'Arial, sans-serif', 'minHeight': '100vh', 'backgroundColor': '#f5f5f5'})

# Single callback for all page interactions using callback_context
@app.callback(
    Output("main-content", "children"),
    [
        Input("url", "search"), 
        Input("url", "pathname"),
        Input("save-credentials-btn", "n_clicks"),
        Input("test-setup-btn", "n_clicks"),
        Input("connect-btn", "n_clicks"),
        Input("reset-setup-btn", "n_clicks")
    ],
    [
        State("setup-client-id", "value"),
        State("setup-client-secret", "value"),
        State("setup-environment", "value")
    ],
    prevent_initial_call=True,  # Changed to True - this is the key fix!
)
def handle_all_interactions(search, pathname, save_clicks, test_clicks, connect_clicks, reset_clicks, 
                           client_id, client_secret, environment):
    """Handle all page interactions using callback_context"""
    global is_authenticated, company_info
    
    # Use callback_context to determine which input triggered the callback
    ctx = dash.callback_context
    if not ctx.triggered:
        # Initial load - show appropriate page
        if check_credentials():
            return create_welcome_page()
        else:
            return create_setup_page()
    
    # Get the triggered input
    triggered = ctx.triggered[0]
    trigger_id = triggered['prop_id'].split('.')[0]
    
    # Handle different triggers
    if trigger_id == 'url':
        # Handle URL changes (OAuth callback)
        if search and 'auth=success' in search:
            logger.info("OAuth success detected")
            is_authenticated = True
            return create_success_page()
        elif search and 'auth=error' in search:
            logger.error("OAuth error detected")
            return html.Div([
                html.Div([
                    html.H2("Authentication Failed", style={'textAlign': 'center', 'color': '#e74c3c', 'marginBottom': '20px'}),
                    html.Div([
                        html.P("OAuth authentication failed. Please try again.", 
                               style={'color': '#e74c3c', 'textAlign': 'center', 'padding': '15px', 
                                      'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'borderLeft': '4px solid #dc3545'})
                    ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
                ], style={'maxWidth': '600px', 'margin': '0 auto'})
            ])
    
    elif trigger_id == 'save-credentials-btn':
        # Handle Save Credentials button
        logger.info("Save credentials button clicked")
        if not client_id or not client_secret:
            return html.Div([
                html.Div([
                    html.H2("Setup Error", style={'textAlign': 'center', 'color': '#e74c3c', 'marginBottom': '20px'}),
                    html.Div([
                        html.P("Please enter both Client ID and Client Secret.", 
                               style={'color': '#e74c3c', 'textAlign': 'center', 'padding': '15px', 
                                      'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'borderLeft': '4px solid #dc3545'})
                    ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
                ], style={'maxWidth': '600px', 'margin': '0 auto'})
            ])
        
        # Store credentials
        credential_manager = CredentialManager()
        credentials = {
            'client_id': client_id,
            'client_secret': client_secret,
            'environment': environment if environment else 'sandbox'
        }
        
        if credential_manager.store_credentials(credentials):
            logger.info("Credentials saved successfully")
            return create_welcome_page()
        else:
            return html.Div([
                html.Div([
                    html.H2("Save Error", style={'textAlign': 'center', 'color': '#e74c3c', 'marginBottom': '20px'}),
                    html.Div([
                        html.P("Failed to save credentials. Please try again.", 
                               style={'color': '#e74c3c', 'textAlign': 'center', 'padding': '15px', 
                                      'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'borderLeft': '4px solid #dc3545'})
                    ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
                ], style={'maxWidth': '600px', 'margin': '0 auto'})
            ])
    
    elif trigger_id == 'test-setup-btn':
        # Handle Test Setup button
        logger.info("Test setup button clicked")
        if not client_id or not client_secret:
            return html.Div([
                html.Div([
                    html.H2("Test Error", style={'textAlign': 'center', 'color': '#e74c3c', 'marginBottom': '20px'}),
                    html.Div([
                        html.P("Please enter both Client ID and Client Secret to test.", 
                               style={'color': '#e74c3c', 'textAlign': 'center', 'padding': '15px', 
                                      'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'borderLeft': '4px solid #dc3545'})
                    ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
                ], style={'maxWidth': '600px', 'margin': '0 auto'})
            ])
        
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
                                      'backgroundColor': '#d4edda', 'borderRadius': '4px', 'borderLeft': '4px solid #28a745'})
                    ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
                ], style={'maxWidth': '600px', 'margin': '0 auto'})
            ])
        except Exception as e:
            return html.Div([
                html.Div([
                    html.H2("Test Failed", style={'textAlign': 'center', 'color': '#e74c3c', 'marginBottom': '20px'}),
                    html.Div([
                        html.P(f"Test failed: {str(e)}", 
                               style={'color': '#e74c3c', 'textAlign': 'center', 'padding': '15px', 
                                      'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'borderLeft': '4px solid #dc3545'})
                    ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
                ], style={'maxWidth': '600px', 'margin': '0 auto'})
            ])
    
    elif trigger_id == 'connect-btn':
        # Handle Connect to QuickBooks button
        logger.info("Connect to QuickBooks button clicked")
        try:
            # Get stored credentials
            credential_manager = CredentialManager()
            credentials = credential_manager.get_credentials()
            
            if not credentials:
                return html.Div([
                    html.Div([
                        html.H2("Setup Required", style={'textAlign': 'center', 'color': '#e74c3c', 'marginBottom': '20px'}),
                        html.Div([
                            html.P("No credentials found. Please set up your QuickBooks app credentials first.", 
                                   style={'color': '#e74c3c', 'textAlign': 'center', 'padding': '15px', 
                                          'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'borderLeft': '4px solid #dc3545'})
                        ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
                    ], style={'maxWidth': '600px', 'margin': '0 auto'})
                ])
            
            # Start OAuth flow
            client_id = credentials.get('client_id')
            environment = credentials.get('environment', 'sandbox')
            
            # Generate OAuth URL with state parameter for security
            state = secrets.token_urlsafe(32)
            auth_url = f"https://appcenter.intuit.com/connect/oauth2?client_id={client_id}&scope=com.intuit.quickbooks.accounting&redirect_uri=http://localhost:8050/callback&response_type=code&access_type=offline&state={state}"
            
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
            
        except Exception as e:
            logger.error(f"Error starting OAuth flow: {e}")
            return html.Div([
                html.Div([
                    html.H2("Connection Error", style={'textAlign': 'center', 'color': '#e74c3c', 'marginBottom': '20px'}),
                    html.Div([
                        html.P(f"Error starting QuickBooks connection: {str(e)}", 
                               style={'color': '#e74c3c', 'textAlign': 'center', 'padding': '15px', 
                                      'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'borderLeft': '4px solid #dc3545'})
                    ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
                ], style={'maxWidth': '600px', 'margin': '0 auto'})
            ])
    
    elif trigger_id == 'reset-setup-btn':
        # Handle Reset Setup button
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
    
    # Default: show appropriate page based on credentials
    if check_credentials():
        return create_welcome_page()
    else:
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
        
        # Determine the token endpoint based on environment
        if environment == 'production':
            token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
        else:
            token_url = "https://sandbox-quickbooks.api.intuit.com/oauth2/v1/tokens/bearer"
        
        # Prepare the request
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'http://localhost:8050/callback'
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
        environment = 'sandbox'  # You might want to get this from stored credentials
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
            return company_data.get('QueryResponse', {}).get('CompanyInfo', [{}])[0]
        else:
            logger.error(f"Failed to fetch company info: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching company info: {e}")
        return None

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("QBO Sankey Dashboard - Starting Application")
    logger.info(f"Startup time: {datetime.now()}")
    logger.info("=" * 50)
    
    if not check_credentials():
        logger.info("No credentials found - setup page will be shown")
    
    logger.info("Starting QBO Sankey Dashboard")
    app.run(debug=True, host='127.0.0.1', port=8050)
    logger.info("Dash is running on http://127.0.0.1:8050/")