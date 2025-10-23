"""
QBO Sankey Dashboard - Simple Working Version
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

# App layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id="main-content", children=create_setup_page() if not check_credentials() else create_welcome_page(), 
             style={'padding': '20px', 'maxWidth': '1200px', 'margin': '0 auto'}),
    html.Footer([
        html.P("QBO Sankey Dashboard - Secure Financial Visualization", 
               style={'textAlign': 'center', 'color': '#7f8c8d', 'margin': '0'})
    ], style={'backgroundColor': '#34495e', 'padding': '15px', 'color': 'white', 'marginTop': '20px'})
], style={'fontFamily': 'Arial, sans-serif', 'minHeight': '100vh', 'backgroundColor': '#f5f5f5'})

# Callback for setup page buttons only
@app.callback(
    Output("main-content", "children"),
    [Input("save-credentials-btn", "n_clicks"), Input("test-setup-btn", "n_clicks")],
    [State("setup-client-id", "value"), State("setup-client-secret", "value"), State("setup-environment", "value")],
    prevent_initial_call=False,
    suppress_callback_exceptions=True
)
def handle_setup_interactions(save_clicks, test_clicks, client_id, client_secret, environment):
    """Handle setup page button clicks"""
    global is_authenticated, company_info
    
    # Handle Save Credentials button
    if save_clicks:
        logger.info("Save credentials button clicked")
        if not client_id or not client_secret:
            return html.Div([
                html.Div([
                    html.H2("Setup Error", style={'textAlign': 'center', 'color': '#e74c3c', 'marginBottom': '20px'}),
                    html.Div([
                        html.P("Please enter both Client ID and Client Secret.", 
                               style={'color': '#e74c3c', 'textAlign': 'center', 'padding': '15px', 
                                      'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'borderLeft': '4px solid #dc3545'}),
                        html.Button("Back to Setup", id="back-to-setup-btn", 
                                   style={'backgroundColor': '#3498db', 'color': 'white', 'border': 'none', 
                                          'padding': '12px 24px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                          'fontSize': '14px', 'fontWeight': 'bold', 'display': 'block', 'margin': '20px auto'})
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
    
    # Handle Test Setup button
    if test_clicks:
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
    
    # Default: show setup page
    return create_setup_page()

# Callback for welcome page buttons
@app.callback(
    Output("main-content", "children"),
    [Input("url", "search"), Input("url", "pathname"), Input("connect-btn", "n_clicks"), Input("reset-setup-btn", "n_clicks")],
    prevent_initial_call=False,
    suppress_callback_exceptions=True
)
def handle_welcome_interactions(search, pathname, connect_clicks, reset_clicks):
    """Handle welcome page button clicks"""
    global is_authenticated, company_info
    
    # Check for OAuth callback success
    if search and 'auth=success' in search:
        logger.info("OAuth success detected")
        is_authenticated = True
        return create_success_page()
    
    # Check for OAuth callback error
    if search and 'auth=error' in search:
        logger.info("OAuth error detected")
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
    
    # Handle Connect to QuickBooks button
    if connect_clicks:
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
    
    # Handle Reset Setup button
    if reset_clicks:
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
    
    # Default: show welcome page
    return create_welcome_page()

# OAuth callback route handler
@app.server.route('/callback')
def oauth_callback():
    """Handle OAuth callback from QuickBooks"""
    global is_authenticated, company_info
    
    logger.info("OAuth callback received")
    
    # Get the authorization code from the URL
    code = request.args.get('code')
    state = request.args.get('state')
    realm_id = request.args.get('realmId')
    
    if code and realm_id:
        logger.info(f"OAuth callback - Code: {code[:10]}..., Realm: {realm_id}, State: {state}")
        
        try:
            # Exchange code for tokens
            tokens = exchange_code_for_token(code, realm_id)
            if tokens:
                # Store tokens
                credential_manager = CredentialManager()
                credential_manager.store_token(tokens['access_token'], tokens['refresh_token'], realm_id)
                
                # Fetch company info
                company_info = fetch_company_info(tokens['access_token'], realm_id)
                if company_info:
                    credential_manager.store_company_info(company_info)
                
                logger.info("OAuth flow completed successfully")
                return redirect('/?auth=success')
            else:
                logger.error("Failed to exchange code for token")
                return redirect('/?auth=error')
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return redirect('/?auth=error')
    else:
        logger.error("OAuth callback missing required parameters")
        return redirect('/?auth=error')

def exchange_code_for_token(code, realm_id):
    """Exchange authorization code for access token"""
    try:
        # Get stored credentials
        credential_manager = CredentialManager()
        credentials = credential_manager.get_credentials()
        
        if not credentials:
            logger.error("No credentials found for token exchange")
            return None
        
        # Prepare token exchange request
        token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'http://localhost:8050/callback'
        }
        
        auth = (credentials['client_id'], credentials['client_secret'])
        
        response = requests.post(token_url, data=data, auth=auth)
        logger.info(f"Token exchange response status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error in token exchange: {e}")
        return None

def fetch_company_info(access_token, realm_id):
    """Fetch company information from QuickBooks"""
    try:
        # This is a placeholder - you would implement actual QBO API calls here
        return {
            'company_name': 'Sample Company',
            'realm_id': realm_id
        }
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
    else:
        logger.info("Credentials found - welcome page will be shown")
    
    logger.info("Starting QBO Sankey Dashboard")
    app.run(debug=True, host='127.0.0.1', port=8050)
    logger.info("Dash is running on http://127.0.0.1:8050/")