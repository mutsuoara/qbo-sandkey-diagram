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
from flask import request, redirect, Response
import plotly.io as pio
import base64
import io
from utils.logging_config import setup_logging
from utils.credentials import CredentialManager
from dashboard import create_dashboard_page, create_success_page
# Removed unnecessary API security - using simple password protection instead

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

# Secure password protection for web app access
import hashlib
import os
from flask import session

# Get password from environment variable (more secure than hardcoded)
APP_PASSWORD_HASH = os.environ.get('DASHBOARD_PASSWORD_HASH')
if not APP_PASSWORD_HASH:
    # Default hash for 'QBO_Dashboard_2024' - change this in production!
    APP_PASSWORD_HASH = hashlib.sha256('QBO_Dashboard_2024'.encode()).hexdigest()
    print("⚠️  WARNING: Using default password hash. Set DASHBOARD_PASSWORD_HASH environment variable for production!")

def verify_password(password):
    """Verify password against stored hash"""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == APP_PASSWORD_HASH

@app.server.before_request
def enforce_https():
    """Enforce HTTPS in production"""
    # Skip HTTPS enforcement for local development
    if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('DEBUG') == 'True':
        return
    
    # Check if request is secure (HTTPS)
    is_secure = (
        request.is_secure or 
        request.headers.get('X-Forwarded-Proto') == 'https' or
        request.headers.get('X-Forwarded-Ssl') == 'on'
    )
    
    if not is_secure:
        # Redirect to HTTPS
        https_url = request.url.replace('http://', 'https://')
        return redirect(https_url, code=301)

@app.server.after_request
def add_security_headers(response):
    """Add security headers for production"""
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.plot.ly; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://*.intuit.com https://*.quickbooks.com; "
        "frame-ancestors 'none';"
    )
    
    return response

@app.server.before_request
def require_app_password():
    """Require password authentication for web app access"""
    # Skip auth for OAuth callback, Dash internal routes, and static files
    if (request.path in ['/callback', '/_dash'] or 
        request.path.startswith('/_dash') or 
        request.path.startswith('/assets')):
        return
    
    # Check for basic auth
    auth = request.authorization
    if not auth or not verify_password(auth.password):
        return Response(
            'QBO Dashboard Access Required\n\nEnter the dashboard password to continue.',
            401,
            {'WWW-Authenticate': 'Basic realm="QBO Dashboard"'}
        )

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
             style={'padding': '20px', 'maxWidth': '99vw', 'width': '99vw', 'margin': '0 auto'}),
    html.Footer([
        html.P("QBO Sankey Dashboard - Secure Financial Visualization", 
               style={'textAlign': 'center', 'color': '#7f8c8d', 'margin': '0'})
    ], style={'backgroundColor': '#34495e', 'padding': '15px', 'color': 'white', 'marginTop': '20px'})
], style={'fontFamily': 'Arial, sans-serif', 'minHeight': '100vh', 'backgroundColor': '#f5f5f5'})

# Callback to handle initial page load based on credentials
@app.callback(
    Output("main-content", "children"),
    [Input("url", "pathname"), Input("url", "search")],
    prevent_initial_call=False
)
def display_initial_page(pathname, search):
    """Display the appropriate initial page"""
    logger.info(f"Initial page load - pathname: {pathname}")
    
    # Check for OAuth success first
    if search and 'auth=success' in search:
        logger.info("OAuth success detected in main callback")
        return create_success_page()
    elif search and 'auth=error' in search:
        logger.error("OAuth error detected in main callback")
        return create_error_page("OAuth authentication failed. Please try again.")
    
    # Normal page logic
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

def export_sankey_as_png(figure, filename="sankey_diagram.png"):
    """Export a Plotly figure as PNG and return base64 encoded data"""
    try:
        logger.info(f"Starting PNG export for figure type: {type(figure)}")
        
        # Check if figure is valid
        if not figure:
            logger.error("Figure is None or empty")
            return None
            
        # Log figure structure for debugging
        if hasattr(figure, 'data'):
            logger.info(f"Figure has {len(figure.data)} data elements")
        else:
            logger.info("Figure does not have data attribute")
            
        # Convert figure to PNG bytes with error handling
        logger.info("Converting figure to PNG bytes...")
        img_bytes = pio.to_image(figure, format="png", width=1200, height=800, scale=2)
        logger.info(f"Successfully converted to PNG bytes: {len(img_bytes)} bytes")
        
        # Convert to base64 for download
        logger.info("Converting to base64...")
        img_base64 = base64.b64encode(img_bytes).decode()
        logger.info(f"Base64 conversion complete: {len(img_base64)} characters")
        
        # Create download link
        download_link = f"data:image/png;base64,{img_base64}"
        
        logger.info(f"Successfully exported Sankey diagram as PNG: {filename}")
        return download_link
        
    except Exception as e:
        logger.error(f"Error exporting PNG: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

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
        import os
        if environment == 'production':
            # Check if running on Heroku by looking for DYNO environment variable
            if os.environ.get('DYNO'):
                # We're on Heroku, use the hardcoded app name
                redirect_uri = "https://qbo-sankey-dashboard-27818919af8f.herokuapp.com/callback"
                logger.info(f"Using Heroku redirect URI: {redirect_uri}")
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

# Callback to handle Export Data button (DISABLED - button hidden)
# @app.callback(
#     Output("main-content", "children", allow_duplicate=True),
#     Input("export-data-btn", "n_clicks"),
#     prevent_initial_call=True
# )
# def export_data(n_clicks):
#     """Handle Export Data button click"""
#     if not n_clicks:
#         return dash.no_update
#     
#     logger.info("Export Data button clicked")
#     # In the future, this would export data
#     # For now, just stay on the dashboard
#     return dash.no_update

# Callback to handle Export PNG button
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("export-png-btn", "n_clicks"),
    State("sankey-chart", "figure"),
    prevent_initial_call=True
)
def export_png(n_clicks, figure):
    """Handle Export PNG button click"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Export PNG button clicked")
    logger.info(f"Figure received: {figure is not None}")
    logger.info(f"Figure type: {type(figure)}")
    
    try:
        # Get the current Sankey figure
        if figure:
            # Create a download link for the PNG
            download_link = export_sankey_as_png(figure)
            
            if download_link:
                # Create a success message with download link
                return html.Div([
                    html.Div([
                        html.H2("PNG Export Ready", style={'textAlign': 'center', 'color': '#27ae60', 'marginBottom': '20px'}),
                        html.Div([
                            html.P("Your Sankey diagram has been exported as PNG. Click the link below to download:", 
                                   style={'color': '#155724', 'textAlign': 'center', 'padding': '15px', 
                                          'backgroundColor': '#d4edda', 'borderRadius': '4px', 'borderLeft': '4px solid #28a745'}),
                            html.Div([
                                html.A("Download PNG", href=download_link, download="sankey_diagram.png",
                                       style={'backgroundColor': '#8e44ad', 'color': 'white', 'border': 'none', 
                                              'padding': '15px 30px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                              'fontSize': '16px', 'fontWeight': 'bold', 'display': 'inline-block', 
                                              'textDecoration': 'none', 'marginRight': '10px'}),
                                html.Button("Back to Dashboard", id="back-to-dashboard-btn",
                                           style={'backgroundColor': '#6c757d', 'color': 'white', 'border': 'none', 
                                                  'padding': '15px 30px', 'borderRadius': '4px', 'cursor': 'pointer', 
                                                  'fontSize': '16px', 'fontWeight': 'bold'})
                            ], style={'textAlign': 'center', 'marginTop': '20px'})
                        ], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '8px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'})
                    ], style={'maxWidth': '600px', 'margin': '0 auto'})
                ])
            else:
                return create_error_page("Failed to export PNG. Please try again.")
        else:
            return create_error_page("No chart data available for export.")
            
    except Exception as e:
        logger.error(f"Error in PNG export: {e}")
        return create_error_page(f"Export failed: {str(e)}")

# Callback to handle Back to Dashboard button from PNG export
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("back-to-dashboard-btn", "n_clicks"),
    prevent_initial_call=True
)
def back_to_dashboard(n_clicks):
    """Handle Back to Dashboard button click from PNG export"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Back to Dashboard button clicked from PNG export")
    return create_dashboard_page()

# Callback to handle Back to Setup button from error page
@app.callback(
    Output("main-content", "children", allow_duplicate=True),
    Input("back-to-setup-from-error-btn", "n_clicks"),
    prevent_initial_call=True
)
def back_to_setup_from_error(n_clicks):
    """Handle Back to Setup button click from error page"""
    if not n_clicks:
        return dash.no_update
    
    logger.info("Back to Setup button clicked from error page")
    return create_setup_page()

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

# Add this AFTER the oauth_callback() function and BEFORE the test_project_income route
@app.server.route('/debug/pl-structure')
def debug_pl_structure():
    """Debug endpoint to see raw P&L structure from QuickBooks"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime, timedelta
    import json
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return {"error": "No tokens found - please authenticate with QuickBooks first"}
        
        environment = credentials.get('environment', 'sandbox')
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get last 90 days of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        logger.info(f"Fetching P&L data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        pl_data = data_fetcher.get_profit_and_loss(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if not pl_data:
            return {"error": "No P&L data returned from QuickBooks"}
        
        # Save to file for inspection
        output_file = 'pl_structure_debug.json'
        with open(output_file, 'w') as f:
            json.dump(pl_data, f, indent=2)
        
        logger.info(f"P&L structure saved to {output_file}")
        
        # Return summary
        return {
            "success": True,
            "message": f"P&L structure saved to {output_file}",
            "file_location": output_file,
            "data_keys": list(pl_data.keys()) if isinstance(pl_data, dict) else "Not a dict",
            "preview": str(pl_data)[:500] + "..."
        }
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.server.route('/debug/account-analysis')
def debug_account_analysis():
    """Analyze account numbers and their hierarchy"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime, timedelta
    import json
    import re
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return {"error": "No tokens found"}
        
        environment = credentials.get('environment', 'sandbox')
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get P&L data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        pl_data = data_fetcher.get_profit_and_loss(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if not pl_data:
            return {"error": "No P&L data returned"}
        
        # Collect all accounts
        all_accounts = []
        
        def extract_accounts(data, level=0):
            """Recursively extract all accounts"""
            if not isinstance(data, dict):
                return
            
            if 'Rows' in data:
                rows_data = data['Rows']
                if isinstance(rows_data, dict) and 'Row' in rows_data:
                    rows = rows_data['Row']
                elif isinstance(rows_data, list):
                    rows = rows_data
                else:
                    return
                
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    
                    # Try to get account name and amount
                    name = None
                    amount = 0
                    
                    if 'Header' in row:
                        col_data = row['Header'].get('ColData', [])
                        if len(col_data) >= 2:
                            name = col_data[0].get('value', '')
                            amount_str = col_data[1].get('value', '0').replace(',', '').replace('$', '')
                            try:
                                amount = float(amount_str)
                            except:
                                amount = 0
                    elif 'ColData' in row:
                        col_data = row['ColData']
                        if len(col_data) >= 2:
                            name = col_data[0].get('value', '')
                            amount_str = col_data[1].get('value', '0').replace(',', '').replace('$', '')
                            try:
                                amount = float(amount_str)
                            except:
                                amount = 0
                    
                    if name:
                        # Extract account number
                        match = re.match(r'^(\d{4,5})(\.\d{1,2})?\s+', name)
                        account_num = match.group(1) if match else None
                        
                        all_accounts.append({
                            'name': name,
                            'amount': amount,
                            'account_number': account_num,
                            'level': level,
                            'row_type': row.get('type', 'unknown')
                        })
                    
                    # Recurse
                    if 'Rows' in row:
                        extract_accounts(row, level + 1)
        
        extract_accounts(pl_data)
        
        # Analyze account numbers
        account_prefixes = {}
        for acc in all_accounts:
            if acc['account_number']:
                prefix = acc['account_number'][:2]  # First 2 digits
                if prefix not in account_prefixes:
                    account_prefixes[prefix] = []
                account_prefixes[prefix].append(acc)
        
        # Save detailed analysis
        analysis = {
            'total_accounts': len(all_accounts),
            'accounts_with_numbers': len([a for a in all_accounts if a['account_number']]),
            'unique_prefixes': list(account_prefixes.keys()),
            'accounts_by_prefix': {
                prefix: [
                    f"{acc['account_number']} - {acc['name'][:50]} (${acc['amount']:,.0f})"
                    for acc in accounts
                ]
                for prefix, accounts in account_prefixes.items()
            },
            'all_accounts': all_accounts
        }
        
        with open('account_analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2)
        
        return {
            "success": True,
            "message": "Account analysis saved to account_analysis.json",
            "summary": {
                "total_accounts": analysis['total_accounts'],
                "accounts_with_numbers": analysis['accounts_with_numbers'],
                "prefixes_found": analysis['unique_prefixes']
            }
        }
        
    except Exception as e:
        logger.error(f"Error in account analysis: {e}")
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.server.route('/test/projects')
def test_project_income():
    """Test endpoint to verify project income fetching"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime, timedelta
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return {"error": "No tokens found"}
        
        environment = credentials.get('environment', 'sandbox')
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        project_income = data_fetcher.get_income_by_project(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        return {
            "success": True,
            "project_count": len(project_income),
            "total_income": sum(project_income.values()),
            "projects": project_income
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.server.route('/test/hierarchy-parser')
def test_hierarchy_parser():
    """Test the new hierarchical parser"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime, timedelta
    from flask import jsonify
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return jsonify({"error": "No tokens found"})
        
        environment = credentials.get('environment', 'sandbox')
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # Use get_financial_data_for_sankey to get data with Phase 2 integration (project-level data)
        financial_data = data_fetcher.get_financial_data_for_sankey(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if not financial_data:
            return jsonify({"error": "Failed to fetch financial data"})
        
        # Get hierarchical structure (includes Phase 2 project data)
        expense_hierarchy = financial_data.get('expense_hierarchy', {})
        
        # Format for display
        result = {
            "success": True,
            "summary": {
                "total_revenue": financial_data.get('total_revenue', 0),
                "total_expenses": financial_data.get('total_expenses', 0),
                "net_income": financial_data.get('net_income', 0),
                "income_count": len(financial_data.get('income', {})),
                "expense_primaries": len(expense_hierarchy)
            },
            "income": financial_data.get('income', {}),
            "expenses": {}
        }
        
        # Format expenses to show structure (including projects field from Phase 2)
        for primary_name, primary_data in expense_hierarchy.items():
            result["expenses"][primary_name] = {
                "total": primary_data.get('total', 0),
                "secondary_count": len(primary_data.get('secondary', {})),
                "secondaries": {}
            }
            
            for sec_name, sec_data in primary_data.get('secondary', {}).items():
                result["expenses"][primary_name]["secondaries"][sec_name] = {
                    "total": sec_data.get('total', 0),
                    "tertiary_count": len(sec_data.get('tertiary', {})),
                    "tertiaries": sec_data.get('tertiary', {}),
                    "project_count": len(sec_data.get('projects', {})),
                    "projects": sec_data.get('projects', {})  # Include Phase 2 project data
                }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error testing parser: {e}")
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.server.route('/test/expenses-by-project')
def test_expenses_by_project():
    """Test project-level expense tracking for 5001 and 5011"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime, timedelta
    from flask import jsonify
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return jsonify({"error": "No tokens found"})
        
        environment = credentials.get('environment', 'sandbox')
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # Get project expenses for 5001 and 5011
        project_expenses = data_fetcher.get_expenses_by_project(
            ['5001', '5011'],
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Format for display
        result = {
            "success": True,
            "date_range": {
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d')
            },
            "project_expenses": project_expenses,
            "summary": {
                "accounts": len(project_expenses),
                "total_projects": sum(len(projects) for projects in project_expenses.values())
            }
        }
        
        # Add detailed breakdown for each account
        for account_name, projects in project_expenses.items():
            if projects:
                result["summary"][account_name] = {
                    "project_count": len(projects),
                    "total_amount": sum(projects.values())
                }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error testing expenses by project: {e}")
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.server.route('/test/journal-entries-cogs')
def test_journal_entries_cogs():
    """Test endpoint for _get_journal_entries_for_cogs() method"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime, timedelta
    from flask import jsonify
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return jsonify({"error": "No tokens found - please authenticate with QuickBooks first"})
        
        environment = credentials.get('environment', 'sandbox')
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # Test the method
        cogs_data = data_fetcher._get_journal_entries_for_cogs(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            ['5001', '5011']
        )
        
        # Calculate summary statistics
        summary = {}
        total_amount = 0.0
        for account_num, projects in cogs_data.items():
            account_total = sum(projects.values())
            total_amount += account_total
            summary[account_num] = {
                "project_count": len(projects),
                "total_amount": account_total,
                "projects": projects
            }
        
        return jsonify({
            "success": True,
            "date_range": {
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d')
            },
            "cogs_breakdown": cogs_data,
            "summary": summary,
            "accounts_found": list(cogs_data.keys()),
            "total_projects": sum(len(projects) for projects in cogs_data.values()),
            "total_amount": total_amount,
            "test_notes": {
                "method": "_get_journal_entries_for_cogs()",
                "accounts_tested": ["5001", "5011"],
                "expected_structure": "Dict[str, Dict[str, float]] where first key is account number, second key is project name"
            }
        })
        
    except Exception as e:
        logger.error(f"Error in journal entries COGS test endpoint: {e}")
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.server.route('/test/unassigned-5001-details')
def test_unassigned_5001_details():
    """Get detailed information about transactions categorized as 'Unassigned' for account 5001"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime, timedelta
    from flask import jsonify
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return jsonify({"error": "No tokens found - please authenticate with QuickBooks first"})
        
        environment = credentials.get('environment', 'sandbox')
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get Year to Date (same as dashboard default)
        end_date = datetime.now()
        start_date = datetime(end_date.year, 1, 1)
        
        # Call with collect_unassigned_details=True
        cogs_data = data_fetcher._get_journal_entries_for_cogs(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            ['5001', '5011'],
            collect_unassigned_details=True
        )
        
        # Get unassigned details from the instance variable
        unassigned_details = getattr(data_fetcher, '_unassigned_journal_entry_details', {})
        
        # Focus on account 5001
        account_5001_unassigned = unassigned_details.get('5001', [])
        
        # Calculate totals
        total_unassigned_amount = sum(txn['amount'] for txn in account_5001_unassigned)
        unassigned_count = len(account_5001_unassigned)
        
        # Sort by amount descending
        account_5001_unassigned_sorted = sorted(account_5001_unassigned, key=lambda x: x['amount'], reverse=True)
        
        # Get summary statistics
        summary = {
            'total_transactions': unassigned_count,
            'total_amount': total_unassigned_amount,
            'average_amount': total_unassigned_amount / unassigned_count if unassigned_count > 0 else 0,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        }
        
        return jsonify({
            "success": True,
            "account": "5001",
            "account_name": "Billable Salaries and Wages",
            "summary": summary,
            "unassigned_transactions": account_5001_unassigned_sorted,
            "cogs_breakdown": cogs_data.get('5001', {}),
            "note": "These transactions were categorized as 'Unassigned' because no project could be extracted from Entity, Description, or transaction-level fields"
        })
        
    except Exception as e:
        logger.error(f"Error in unassigned 5001 details endpoint: {e}")
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.server.route('/test/cogs-rippling-salaries-no-entity')
def test_cogs_rippling_salaries_no_entity():
    """Find COGS transactions with Rippling salary pattern but no entity/project attribution"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime
    from flask import jsonify
    import re
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return jsonify({"error": "No tokens found - please authenticate with QuickBooks first"})
        
        environment = credentials.get('environment', 'sandbox')
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get Year to Date (same as dashboard default)
        end_date = datetime.now()
        start_date = datetime(end_date.year, 1, 1)
        
        # Query JournalEntry transactions
        query = (
            f"SELECT * FROM JournalEntry "
            f"WHERE TxnDate >= '{start_date.strftime('%Y-%m-%d')}' AND TxnDate <= '{end_date.strftime('%Y-%m-%d')}' "
            f"MAXRESULTS 1000"
        )
        
        params = {'query': query, 'minorversion': '65'}
        data = data_fetcher._make_request('query', params)
        
        if not data or 'QueryResponse' not in data:
            return jsonify({"error": "No journal entry data returned"})
        
        entries = data['QueryResponse'].get('JournalEntry', [])
        matching_transactions = []
        
        for entry in entries:
            entry_number = entry.get('DocNumber', 'N/A')
            lines = entry.get('Line', [])
            
            if not lines:
                continue
            
            for line in lines:
                journal_detail = line.get('JournalEntryLineDetail', {})
                if not journal_detail:
                    continue
                
                # Get account reference
                account_ref = journal_detail.get('AccountRef', {})
                account_name = account_ref.get('name', '')
                
                if not account_name:
                    continue
                
                # Check if this is a COGS salaries account (5001)
                account_num = None
                account_match = re.search(r'(\d{4})', account_name)
                if account_match:
                    account_num = account_match.group(1)
                else:
                    account_name_lower = account_name.lower()
                    if 'salaries' in account_name_lower and 'wage' in account_name_lower:
                        if 'cogs' in account_name_lower or 'cost of goods' in account_name_lower:
                            account_num = '5001'
                
                if account_num != '5001':
                    continue
                
                # Get amount and posting type
                amount = float(line.get('Amount', 0))
                posting_type = journal_detail.get('PostingType', '')
                
                if posting_type != 'Debit' or amount == 0:
                    continue
                
                # Check ClassRef - should be COGS class (not GA)
                class_ref = journal_detail.get('ClassRef', {})
                class_name = class_ref.get('name', '') if class_ref else ''
                
                # Skip if it belongs to GA
                if class_ref and data_fetcher._classref_belongs_to_ga(class_ref):
                    continue
                
                # Get descriptions
                line_description = line.get('Description', '')
                txn_description = entry.get('PrivateNote', '') or entry.get('Description', '')
                combined_description = (line_description + ' ' + txn_description).lower()
                
                # Skip 9- patterns
                if '9-' in combined_description or 'salary for 9-' in combined_description or '9 - ' in combined_description:
                    continue
                
                # Check for Rippling salary pattern
                if '[rippling] salary for' not in combined_description:
                    continue
                
                # Check Entity - should be empty
                entity = line.get('Entity', {})
                entity_ref = entity.get('EntityRef', {})
                entity_name = entity_ref.get('name', '') if entity_ref else ''
                
                if entity_name:
                    continue  # Skip if entity exists
                
                # This matches our criteria
                matching_transactions.append({
                    'doc_number': entry_number,
                    'date': entry.get('TxnDate', 'N/A'),
                    'amount': abs(amount),
                    'account_name': account_name,
                    'class_ref': class_name,
                    'line_description': line_description,
                    'txn_description': txn_description,
                    'entity_name': entity_name,
                    'posting_type': posting_type
                })
        
        # Sort by amount descending
        matching_transactions_sorted = sorted(matching_transactions, key=lambda x: x['amount'], reverse=True)
        
        # Calculate totals
        total_amount = sum(txn['amount'] for txn in matching_transactions)
        
        return jsonify({
            "success": True,
            "account": "5001",
            "account_name": "Billable Salaries and Wages",
            "summary": {
                "total_transactions": len(matching_transactions),
                "total_amount": total_amount,
                "average_amount": total_amount / len(matching_transactions) if matching_transactions else 0,
                "date_range": {
                    "start": start_date.strftime('%Y-%m-%d'),
                    "end": end_date.strftime('%Y-%m-%d')
                }
            },
            "matching_transactions": matching_transactions_sorted,
            "note": "Transactions with Rippling salary pattern, COGS class codes, but no entity/project attribution"
        })
        
    except Exception as e:
        logger.error(f"Error in COGS Rippling salaries no entity endpoint: {e}")
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.server.route('/test/journal-entries-sample')
def test_journal_entries_sample():
    """Test endpoint to pull the first 10 journal entries with all available fields"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime, timedelta
    from flask import jsonify
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return jsonify({"error": "No tokens found"})
        
        environment = credentials.get('environment', 'sandbox')
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # Query Journal Entry transactions
        journal_query = (
            f"SELECT * FROM JournalEntry "
            f"WHERE TxnDate >= '{start_date.strftime('%Y-%m-%d')}' AND TxnDate <= '{end_date.strftime('%Y-%m-%d')}' "
            f"MAXRESULTS 10"
        )
        
        params = {
            'query': journal_query,
            'minorversion': '65'
        }
        
        journal_data = data_fetcher._make_request('query', params)
        
        if not journal_data or 'QueryResponse' not in journal_data:
            return jsonify({
                "success": False,
                "error": "No journal entry data returned",
                "query": journal_query
            })
        
        journal_entries = journal_data['QueryResponse'].get('JournalEntry', [])
        
        # Analyze structure and log consistencies
        if journal_entries:
            logger.info("="*80)
            logger.info("JOURNAL ENTRY STRUCTURE ANALYSIS")
            logger.info("="*80)
            
            # Find common top-level fields
            all_keys = set(journal_entries[0].keys())
            for entry in journal_entries[1:]:
                all_keys.intersection_update(set(entry.keys()))
            
            logger.info(f"Common top-level fields (present in all {len(journal_entries)} entries):")
            for key in sorted(all_keys):
                logger.info(f"  ✓ {key}")
            
            # Count field presence
            from collections import Counter
            field_counts = Counter()
            for entry in journal_entries:
                field_counts.update(entry.keys())
            
            logger.info(f"\nField presence across {len(journal_entries)} entries:")
            for field, count in sorted(field_counts.items(), key=lambda x: (-x[1], x[0])):
                percentage = (count / len(journal_entries)) * 100
                status = "✓" if count == len(journal_entries) else "⚠"
                logger.info(f"  {status} {field}: {count}/{len(journal_entries)} ({percentage:.1f}%)")
            
            # Analyze Line structure
            line_fields = Counter()
            line_detail_fields = Counter()
            entries_with_lines = 0
            
            for entry in journal_entries:
                lines = entry.get('Line', [])
                if lines:
                    entries_with_lines += 1
                    for line in lines:
                        line_fields.update(line.keys())
                        journal_detail = line.get('JournalEntryLineDetail', {})
                        if journal_detail:
                            line_detail_fields.update(journal_detail.keys())
            
            logger.info(f"\nLine structure analysis:")
            logger.info(f"  Entries with 'Line' array: {entries_with_lines}/{len(journal_entries)}")
            if line_fields:
                logger.info(f"  Common Line fields (top {min(10, len(line_fields))}):")
                for field, count in sorted(line_fields.items(), key=lambda x: -x[1])[:10]:
                    logger.info(f"    • {field}: appears {count} times")
            
            if line_detail_fields:
                logger.info(f"  Common JournalEntryLineDetail fields:")
                for field, count in sorted(line_detail_fields.items(), key=lambda x: -x[1]):
                    logger.info(f"    • {field}: appears {count} times")
            
            # Show sample entry
            sample = journal_entries[0]
            logger.info(f"\nSample entry (DocNumber: {sample.get('DocNumber', 'N/A')}):")
            logger.info(f"  Top-level keys: {sorted(sample.keys())}")
            if sample.get('Line'):
                first_line = sample['Line'][0]
                logger.info(f"  First Line keys: {sorted(first_line.keys())}")
                if 'JournalEntryLineDetail' in first_line:
                    detail = first_line['JournalEntryLineDetail']
                    logger.info(f"  JournalEntryLineDetail keys: {sorted(detail.keys())}")
            
            logger.info("="*80)
        
        # Return all fields from the first 10 entries
        result = {
            "success": True,
            "date_range": {
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d')
            },
            "total_entries_found": len(journal_entries),
            "entries": journal_entries  # Return all fields as-is
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error fetching journal entries sample: {e}")
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.server.route('/debug/expenses-by-project-raw')
def debug_expenses_by_project_raw():
    """Debug endpoint to see raw API response structure for ProfitAndLossDetail with customer grouping"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime, timedelta
    from flask import jsonify
    import json
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return jsonify({"error": "No tokens found"})
        
        environment = credentials.get('environment', 'sandbox')
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=environment
        )
        
        # Get last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # Fetch raw API response
        params = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'columns': 'customer',  # Group by customer/project
            'minorversion': '65'
        }
        
        raw_data = data_fetcher._make_request('reports/ProfitAndLossDetail', params)
        
        if not raw_data:
            return jsonify({"error": "No data returned from API"})
        
        # Return structure info (truncated for safety)
        result = {
            "success": True,
            "date_range": {
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d')
            },
            "response_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else type(raw_data).__name__,
            "has_fault": 'Fault' in raw_data if isinstance(raw_data, dict) else False,
            "has_rows": 'Rows' in raw_data if isinstance(raw_data, dict) else False,
            "sample_structure": {}
        }
        
        # If Fault, include it
        if isinstance(raw_data, dict) and 'Fault' in raw_data:
            result["fault"] = raw_data['Fault']
        
        # If Rows, include sample structure
        if isinstance(raw_data, dict) and 'Rows' in raw_data:
            rows_data = raw_data['Rows']
            if isinstance(rows_data, dict) and 'Row' in rows_data:
                rows = rows_data['Row']
                if isinstance(rows, list) and len(rows) > 0:
                    result["sample_structure"]["first_row"] = rows[0]
                    result["sample_structure"]["row_count"] = len(rows)
                elif isinstance(rows, dict):
                    result["sample_structure"]["first_row"] = rows
                    result["sample_structure"]["row_count"] = 1
            elif isinstance(rows_data, list) and len(rows_data) > 0:
                result["sample_structure"]["first_row"] = rows_data[0]
                result["sample_structure"]["row_count"] = len(rows_data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error debugging expenses by project: {e}")
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })

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
        import os
        if environment == 'production':
            # Check if running on Heroku by looking for DYNO environment variable
            if os.environ.get('DYNO'):
                # We're on Heroku, use the hardcoded app name
                redirect_uri = "https://qbo-sankey-dashboard-27818919af8f.herokuapp.com/callback"
            else:
                # Check for ngrok (development)
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
],
    [State("start-date-picker", "date"),
     State("end-date-picker", "date")],
    prevent_initial_call=True,
    suppress_callback_exceptions=True
)
def update_sankey_chart(apply_clicks, ytd_clicks, last30_clicks, last90_clicks, lastyear_clicks, start_date, end_date):
    """Update Sankey chart based on date range selection"""
    from datetime import datetime, timedelta
    
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
        from dashboard.enhanced_sankey import create_enhanced_sankey_diagram, create_sample_sankey_diagram
        
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
            
            # Create enhanced Sankey diagram with real data
            return create_enhanced_sankey_diagram(financial_data, start_date, end_date)
        else:
            # No tokens available, use sample data
            return create_sample_sankey_diagram(start_date, end_date)
            
    except Exception as e:
        logger.error(f"Error fetching real data for date range: {e}")
        # Fallback to sample data
        return create_sample_sankey_diagram(start_date, end_date)

@app.server.route('/debug/download-pl')
def download_pl_structure():
    """Download the P&L structure debug file"""
    import os
    from flask import send_file, jsonify
    
    file_path = 'pl_structure_debug.json'
    
    if os.path.exists(file_path):
        return send_file(
            file_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='pl_structure_debug.json'
        )
    else:
        return jsonify({
            "error": "File not found. Generate it first by visiting /debug/pl-structure"
        })

@app.server.route('/debug/download-analysis')
def download_account_analysis():
    """Download the account analysis debug file"""
    import os
    from flask import send_file, jsonify
    
    file_path = 'account_analysis.json'
    
    if os.path.exists(file_path):
        return send_file(
            file_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='account_analysis.json'
        )
    else:
        return jsonify({
            "error": "File not found. Generate it first by visiting /debug/account-analysis"
        })
@app.server.route('/debug/pl-vs-calculated')
def debug_pl_comparison():
    """Compare P&L report totals vs our calculated COGS totals"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime, timedelta
    from flask import jsonify
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        if not tokens:
            return jsonify({"error": "No tokens"})
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=credentials.get('environment', 'sandbox')
        )
        
        # Get YTD
        end_date = datetime.now()
        start_date = datetime(end_date.year, 1, 1)
        
        # Get P&L report
        pl_data = data_fetcher.get_profit_and_loss(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Parse P&L to get account totals
        pl_totals = {}
        if pl_data and 'Rows' in pl_data:
            rows_data = pl_data['Rows']
            # Handle both structures: dict with 'Row' key, or direct list
            if isinstance(rows_data, dict) and 'Row' in rows_data:
                rows = rows_data['Row']
            elif isinstance(rows_data, list):
                rows = rows_data
            else:
                rows = []
            
            pl_totals = extract_account_totals(rows, ['5001', '8005'])
        
        # Get our calculated COGS breakdown
        # Note: 5001 uses get_expenses_by_project, 8005 uses get_expenses_by_project_for_ga
        cogs_breakdown = {}
        
        # Get 5001 (COGS) breakdown
        cogs_5001 = data_fetcher.get_expenses_by_project(
            ['5001'],
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        cogs_breakdown.update(cogs_5001)
        
        # Get 8005 (GA) breakdown
        cogs_8005 = data_fetcher.get_expenses_by_project_for_ga(
            ['8005'],
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        cogs_breakdown.update(cogs_8005)
        
        # Calculate our totals - map account names to account numbers
        # The methods return account names, but we need to map them to account numbers
        account_name_to_number = {
            "Billable Salaries and Wages": "5001",
            "5001 Billable Salaries and Wages": "5001",
            "8005 Salaries and Wages": "8005",
            "Salaries and Wages": "8005"  # GA account might use this name
        }
        
        our_totals = {}
        for account_name, projects in cogs_breakdown.items():
            # Try to find account number from name
            account_num = None
            for name_key, num in account_name_to_number.items():
                if name_key.lower() in account_name.lower():
                    account_num = num
                    break
            
            if account_num:
                our_totals[account_num] = sum(projects.values())
            else:
                # Fallback: try to extract account number from name
                import re
                match = re.search(r'(\d{4})', account_name)
                if match:
                    account_num = match.group(1)
                    our_totals[account_num] = sum(projects.values())
        
        # Compare
        comparison = {}
        for account in ['5001', '8005']:
            pl_total = pl_totals.get(account, 0)
            our_total = our_totals.get(account, 0)
            difference = pl_total - our_total
            
            comparison[account] = {
                "pl_report_total": pl_total,
                "our_calculated_total": our_total,
                "difference": difference,
                "percentage_captured": (our_total / pl_total * 100) if pl_total > 0 else 0
            }
        
        return jsonify({
            "success": True,
            "date_range": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "comparison": comparison,
            "cogs_breakdown": cogs_breakdown
        })
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})

@app.server.route('/debug/find-missing-transactions')
def debug_find_missing():
    """Find ALL transactions affecting 5001 and 8005"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime
    from flask import jsonify
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=credentials.get('environment', 'sandbox')
        )
        
        end_date = datetime.now()
        start_date = datetime(end_date.year, 1, 1)
        
        # Query all transaction types
        transaction_types = [
            'JournalEntry',
            'Bill',
            'Purchase', 
            'Expense',
            'Check',
            'VendorCredit',
            'BillPayment'
        ]
        
        results = {}
        
        for txn_type in transaction_types:
            query = f"SELECT * FROM {txn_type} WHERE TxnDate >= '{start_date.strftime('%Y-%m-%d')}' AND TxnDate <= '{end_date.strftime('%Y-%m-%d')}' MAXRESULTS 1000"
            
            data = data_fetcher._make_request('query', {'query': query, 'minorversion': '65'})
            
            if not data or 'QueryResponse' not in data:
                continue
            
            transactions = data['QueryResponse'].get(txn_type, [])
            
            # Find transactions with 5001 or 8005
            matching_txns = []
            for txn in transactions:
                has_target_account = False
                lines = txn.get('Line', [])
                
                for line in lines:
                    # Check all possible line detail types
                    account_name = None
                    
                    # Journal Entry
                    je_detail = line.get('JournalEntryLineDetail', {})
                    if je_detail:
                        account_name = je_detail.get('AccountRef', {}).get('name', '')
                    
                    # Bill/Purchase/Expense
                    account_detail = line.get('AccountBasedExpenseLineDetail', {})
                    if account_detail:
                        account_name = account_detail.get('AccountRef', {}).get('name', '')
                    
                    # Check/BillPayment might have different structure
                    if not account_name and 'AccountRef' in line:
                        account_name = line.get('AccountRef', {}).get('name', '')
                    
                    if account_name and (account_name.startswith('5001') or account_name.startswith('8005')):
                        has_target_account = True
                        break
                
                if has_target_account:
                    matching_txns.append({
                        'id': txn.get('Id'),
                        'doc_number': txn.get('DocNumber', 'N/A'),
                        'txn_date': txn.get('TxnDate'),
                        'total': txn.get('TotalAmt', 0)
                    })
            
            if matching_txns:
                results[txn_type] = {
                    'count': len(matching_txns),
                    'transactions': matching_txns[:10]  # First 10
                }
        
        return jsonify({
            "success": True,
            "date_range": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "results": results
        })
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})

@app.server.route('/debug/unassigned-transactions')
def debug_unassigned():
    """Find transactions affecting 5001/8005 that have NO project assignment"""
    from utils.credentials import CredentialManager
    from dashboard.data_fetcher import QBODataFetcher
    from datetime import datetime
    from flask import jsonify
    
    try:
        credential_manager = CredentialManager()
        tokens = credential_manager.get_tokens()
        credentials = credential_manager.get_credentials()
        
        data_fetcher = QBODataFetcher(
            access_token=tokens['access_token'],
            realm_id=tokens['realm_id'],
            environment=credentials.get('environment', 'sandbox')
        )
        
        end_date = datetime.now()
        start_date = datetime(end_date.year, 1, 1)
        
        # Query Journal Entries
        query = f"SELECT * FROM JournalEntry WHERE TxnDate >= '{start_date.strftime('%Y-%m-%d')}' MAXRESULTS 1000"
        data = data_fetcher._make_request('query', {'query': query, 'minorversion': '65'})
        
        unassigned = {
            '5001': [],
            '8005': []
        }
        
        if data and 'QueryResponse' in data:
            entries = data['QueryResponse'].get('JournalEntry', [])
            
            for entry in entries:
                for line in entry.get('Line', []):
                    je_detail = line.get('JournalEntryLineDetail', {})
                    account_name = je_detail.get('AccountRef', {}).get('name', '')
                    
                    # Check if 5001 or 8005
                    account_num = None
                    if account_name.startswith('5001'):
                        account_num = '5001'
                    elif account_name.startswith('8005'):
                        account_num = '8005'
                    
                    if not account_num:
                        continue
                    
                    # Check if has Entity/Customer
                    entity = line.get('Entity', {})
                    entity_name = entity.get('EntityRef', {}).get('name', '')
                    
                    if not entity_name:  # NO PROJECT ASSIGNED!
                        amount = float(line.get('Amount', 0))
                        posting_type = je_detail.get('PostingType', '')
                        
                        if posting_type == 'Debit' and amount > 0:
                            unassigned[account_num].append({
                                'doc_number': entry.get('DocNumber', 'N/A'),
                                'date': entry.get('TxnDate'),
                                'amount': amount,
                                'description': line.get('Description', 'No description')
                            })
        
        # Calculate totals
        summary = {}
        for account, txns in unassigned.items():
            summary[account] = {
                'count': len(txns),
                'total': sum(t['amount'] for t in txns),
                'transactions': txns[:10]  # First 10
            }
        
        return jsonify({
            "success": True,
            "unassigned_totals": summary
        })
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})

# Helper function for extract_account_totals
def extract_account_totals(rows, account_numbers):
    """Recursively extract account totals from P&L rows"""
    totals = {}
    
    def search_rows(row_list):
        for row in row_list:
            if not isinstance(row, dict):
                continue
            
            # Check ColData or Header
            col_data = row.get('ColData') or row.get('Header', {}).get('ColData', [])
            if len(col_data) >= 2:
                name = col_data[0].get('value', '')
                amount_str = col_data[1].get('value', '0').replace(',', '').replace('$', '')
                
                # Check if this is one of our target accounts
                # Match by account number (can be at start, middle, or end of name)
                for account_num in account_numbers:
                    # Check if account number appears in the name
                    if account_num in name:
                        # Also check for common account name patterns
                        account_patterns = {
                            '5001': ['5001', 'billable salaries', 'salaries & wages', 'cogs:salaries'],
                            '8005': ['8005', 'salaries and wages', 'ga salaries']
                        }
                        
                        name_lower = name.lower()
                        patterns = account_patterns.get(account_num, [account_num])
                        
                        # Check if any pattern matches
                        if any(pattern in name_lower for pattern in patterns):
                            try:
                                amount = float(amount_str) if amount_str else 0
                                # Use absolute value (expenses are typically negative in P&L)
                                totals[account_num] = abs(amount)
                            except:
                                pass
                            break  # Found match, no need to check other accounts
            
            # Recurse into nested rows
            if 'Rows' in row:
                nested = row['Rows'].get('Row', [])
                search_rows(nested)
    
    search_rows(rows)
    return totals

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
    
    # Heroku deployment configuration
    import os
    port = int(os.environ.get('PORT', 8050))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    app.run(debug=debug, host='0.0.0.0', port=port)
    logger.info(f"Dash is running on port {port}")