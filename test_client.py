"""
Example Client for Testing Security Implementation
Demonstrates how to use the secure API endpoints
"""

import hmac
import hashlib
import time
import requests
import json
from typing import Optional, Dict, Any

class SecureAPIClient:
    """Example client for testing secure API"""
    
    def __init__(self, base_url: str, api_key: str, api_secret: str):
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = None
        self.token_expires = 0
    
    def _create_signature(self, method: str, path: str, body: str = "") -> tuple:
        """Create HMAC signature for request"""
        timestamp = str(time.time())
        message = f"{method}:{path}:{timestamp}:{body}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature, timestamp
    
    def _get_access_token(self) -> str:
        """Get or refresh access token"""
        if self.access_token and time.time() < self.token_expires:
            return self.access_token
        
        print("🔑 Getting new access token...")
        
        # Create signature for token request
        signature, timestamp = self._create_signature("POST", "/api/auth/token")
        
        headers = {
            "X-API-Key": self.api_key,
            "X-Signature": signature,
            "X-Timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/auth/token", headers=headers)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data["access_token"]
            self.token_expires = time.time() + data["expires_in"]
            
            print(f"✅ Token obtained: {data['client_name']}")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get token: {e}")
            raise
    
    def _make_authenticated_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request"""
        token = self._get_access_token()
        
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"
        
        kwargs["headers"] = headers
        
        try:
            response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status (no auth required)"""
        print("🔍 Getting health status...")
        try:
            response = requests.get(f"{self.base_url}/api/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Health check failed: {e}")
            raise
    
    def get_dashboard_status(self) -> Dict[str, Any]:
        """Get dashboard status"""
        print("🔍 Getting dashboard status...")
        return self._make_authenticated_request("GET", "/api/dashboard/status")
    
    def get_company_info(self) -> Dict[str, Any]:
        """Get QuickBooks company information"""
        print("🔍 Getting company information...")
        return self._make_authenticated_request("GET", "/api/quickbooks/company")
    
    def get_financial_data(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get financial data for Sankey diagram"""
        print(f"🔍 Getting financial data ({start_date} to {end_date})...")
        params = {"start_date": start_date, "end_date": end_date}
        return self._make_authenticated_request("GET", "/api/quickbooks/financial-data", params=params)
    
    def get_profit_loss_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get Profit & Loss report"""
        print(f"🔍 Getting P&L report ({start_date} to {end_date})...")
        params = {"start_date": start_date, "end_date": end_date}
        return self._make_authenticated_request("GET", "/api/quickbooks/profit-loss", params=params)

def main():
    """Test the secure API client"""
    print("🔐 Secure API Client Test")
    print("=" * 40)
    
    # Configuration
    BASE_URL = "http://localhost:8050"  # Change to your Heroku URL for production
    API_KEY = "demo_api_key_12345"
    API_SECRET = "demo_secret_67890"
    
    try:
        # Create client
        client = SecureAPIClient(BASE_URL, API_KEY, API_SECRET)
        
        # Test health check
        print("\n1. Testing Health Check...")
        health = client.get_health_status()
        print(f"   Status: {health['status']}")
        print(f"   Version: {health['version']}")
        
        # Test dashboard status
        print("\n2. Testing Dashboard Status...")
        dashboard = client.get_dashboard_status()
        print(f"   Authenticated: {dashboard['authenticated']}")
        print(f"   Client: {dashboard['client_name']}")
        print(f"   Permissions: {dashboard['permissions']}")
        
        # Test company info (if QBO is connected)
        print("\n3. Testing Company Information...")
        try:
            company = client.get_company_info()
            if company.get('company_info'):
                print(f"   Company: {company['company_info'].get('CompanyName', 'Unknown')}")
            else:
                print("   No company info available (QBO not connected)")
        except Exception as e:
            print(f"   Company info not available: {e}")
        
        # Test financial data
        print("\n4. Testing Financial Data...")
        try:
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            financial = client.get_financial_data(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            print(f"   Financial data retrieved: {len(financial.get('financial_data', {}))} items")
        except Exception as e:
            print(f"   Financial data not available: {e}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure the app is running: python app.py")
        print("2. Check the BASE_URL is correct")
        print("3. Verify API credentials are correct")

if __name__ == "__main__":
    main()
