"""
Secure API Endpoints with HMAC + JWT Authentication
Provides authenticated access to QBO data and dashboard functionality
"""

import logging
from flask import jsonify, request
from auth.hmac_auth import require_hmac_auth, require_jwt_auth, require_permission
from utils.credentials import CredentialManager
from qbo_api.data_fetcher import QBODataFetcher
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

def create_secure_api_routes(app):
    """
    Create secure API routes with authentication
    """
    
    @app.server.route('/api/auth/token', methods=['POST'])
    @require_hmac_auth
    def get_access_token(client_info):
        """
        Exchange HMAC authentication for JWT token
        """
        try:
            from auth.hmac_auth import generate_jwt_token
            
            token = generate_jwt_token(client_info)
            
            return jsonify({
                'access_token': token,
                'token_type': 'Bearer',
                'expires_in': 3600,
                'client_id': client_info['client_id'],
                'client_name': client_info['client_name']
            })
            
        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            return jsonify({'error': 'Token generation failed'}), 500
    
    @app.server.route('/api/quickbooks/company', methods=['GET'])
    @require_jwt_auth
    @require_permission('read_company')
    def get_company_info(client_info):
        """
        Get QuickBooks company information
        """
        try:
            credential_manager = CredentialManager()
            tokens = credential_manager.get_tokens()
            
            if not tokens:
                return jsonify({'error': 'No QuickBooks authentication found'}), 401
            
            credentials = credential_manager.get_credentials()
            environment = credentials.get('environment', 'sandbox') if credentials else 'sandbox'
            
            data_fetcher = QBODataFetcher(
                access_token=tokens['access_token'],
                realm_id=tokens['realm_id'],
                environment=environment
            )
            
            company_info = data_fetcher.get_company_info()
            
            return jsonify({
                'company_info': company_info,
                'client_id': client_info['client_id'],
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to get company info: {e}")
            return jsonify({'error': 'Failed to get company information'}), 500
    
    @app.server.route('/api/quickbooks/financial-data', methods=['GET'])
    @require_jwt_auth
    @require_permission('read_financial_data')
    def get_financial_data(client_info):
        """
        Get financial data for Sankey diagram
        """
        try:
            # Get date range from query parameters
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            if not start_date or not end_date:
                return jsonify({'error': 'start_date and end_date parameters required'}), 400
            
            credential_manager = CredentialManager()
            tokens = credential_manager.get_tokens()
            
            if not tokens:
                return jsonify({'error': 'No QuickBooks authentication found'}), 401
            
            credentials = credential_manager.get_credentials()
            environment = credentials.get('environment', 'sandbox') if credentials else 'sandbox'
            
            data_fetcher = QBODataFetcher(
                access_token=tokens['access_token'],
                realm_id=tokens['realm_id'],
                environment=environment
            )
            
            financial_data = data_fetcher.get_financial_data_for_sankey(start_date, end_date)
            
            return jsonify({
                'financial_data': financial_data,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'client_id': client_info['client_id'],
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to get financial data: {e}")
            return jsonify({'error': 'Failed to get financial data'}), 500
    
    @app.server.route('/api/quickbooks/profit-loss', methods=['GET'])
    @require_jwt_auth
    @require_permission('read_reports')
    def get_profit_loss_report(client_info):
        """
        Get Profit & Loss report
        """
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            if not start_date or not end_date:
                return jsonify({'error': 'start_date and end_date parameters required'}), 400
            
            credential_manager = CredentialManager()
            tokens = credential_manager.get_tokens()
            
            if not tokens:
                return jsonify({'error': 'No QuickBooks authentication found'}), 401
            
            credentials = credential_manager.get_credentials()
            environment = credentials.get('environment', 'sandbox') if credentials else 'sandbox'
            
            data_fetcher = QBODataFetcher(
                access_token=tokens['access_token'],
                realm_id=tokens['realm_id'],
                environment=environment
            )
            
            pl_data = data_fetcher.get_profit_and_loss(start_date, end_date)
            
            return jsonify({
                'profit_loss_data': pl_data,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'client_id': client_info['client_id'],
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to get P&L report: {e}")
            return jsonify({'error': 'Failed to get Profit & Loss report'}), 500
    
    @app.server.route('/api/dashboard/status', methods=['GET'])
    @require_jwt_auth
    def get_dashboard_status(client_info):
        """
        Get dashboard status and authentication info
        """
        try:
            credential_manager = CredentialManager()
            tokens = credential_manager.get_tokens()
            company_info = credential_manager.get_company_info()
            
            is_authenticated = bool(tokens)
            
            return jsonify({
                'authenticated': is_authenticated,
                'company_info': company_info if is_authenticated else None,
                'client_id': client_info['client_id'],
                'client_name': client_info['client_name'],
                'permissions': client_info['permissions'],
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to get dashboard status: {e}")
            return jsonify({'error': 'Failed to get dashboard status'}), 500
    
    @app.server.route('/api/health', methods=['GET'])
    def health_check():
        """
        Health check endpoint (no authentication required)
        """
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })
    
    logger.info("Secure API routes created successfully")
