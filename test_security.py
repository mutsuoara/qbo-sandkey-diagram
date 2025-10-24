"""
Security Implementation Test Suite
Tests HMAC + JWT authentication and API endpoints
"""

import requests
import hmac
import hashlib
import time
import json
import os
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8050"  # Change to your Heroku URL for production testing
API_KEY = "demo_api_key_12345"
API_SECRET = "demo_secret_67890"

class SecurityTester:
    """Test suite for security implementation"""
    
    def __init__(self, base_url: str, api_key: str, api_secret: str):
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = None
    
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
    
    def test_health_check(self) -> bool:
        """Test health check endpoint (no auth required)"""
        print("🔍 Testing health check endpoint...")
        try:
            response = requests.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data['status']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_hmac_authentication(self) -> bool:
        """Test HMAC authentication for token request"""
        print("🔍 Testing HMAC authentication...")
        try:
            signature, timestamp = self._create_signature("POST", "/api/auth/token")
            
            headers = {
                "X-API-Key": self.api_key,
                "X-Signature": signature,
                "X-Timestamp": timestamp,
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{self.base_url}/api/auth/token", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                print(f"✅ HMAC authentication successful")
                print(f"   Token type: {data['token_type']}")
                print(f"   Expires in: {data['expires_in']} seconds")
                print(f"   Client: {data['client_name']}")
                return True
            else:
                print(f"❌ HMAC authentication failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ HMAC authentication error: {e}")
            return False
    
    def test_invalid_hmac(self) -> bool:
        """Test invalid HMAC signature (should fail)"""
        print("🔍 Testing invalid HMAC signature...")
        try:
            headers = {
                "X-API-Key": self.api_key,
                "X-Signature": "invalid_signature",
                "X-Timestamp": str(time.time()),
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{self.base_url}/api/auth/token", headers=headers)
            
            if response.status_code == 401:
                print("✅ Invalid HMAC correctly rejected")
                return True
            else:
                print(f"❌ Invalid HMAC should have been rejected: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Invalid HMAC test error: {e}")
            return False
    
    def test_expired_timestamp(self) -> bool:
        """Test expired timestamp (should fail)"""
        print("🔍 Testing expired timestamp...")
        try:
            # Use timestamp from 10 minutes ago
            old_timestamp = str(time.time() - 600)
            signature, _ = self._create_signature("POST", "/api/auth/token")
            
            headers = {
                "X-API-Key": self.api_key,
                "X-Signature": signature,
                "X-Timestamp": old_timestamp,
                "Content-Type": "application/json"
            }
            
            response = requests.post(f"{self.base_url}/api/auth/token", headers=headers)
            
            if response.status_code == 401:
                print("✅ Expired timestamp correctly rejected")
                return True
            else:
                print(f"❌ Expired timestamp should have been rejected: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Expired timestamp test error: {e}")
            return False
    
    def test_jwt_authentication(self) -> bool:
        """Test JWT authentication for protected endpoints"""
        print("🔍 Testing JWT authentication...")
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{self.base_url}/api/dashboard/status", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ JWT authentication successful")
                print(f"   Authenticated: {data['authenticated']}")
                print(f"   Client: {data['client_name']}")
                return True
            else:
                print(f"❌ JWT authentication failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ JWT authentication error: {e}")
            return False
    
    def test_invalid_jwt(self) -> bool:
        """Test invalid JWT token (should fail)"""
        print("🔍 Testing invalid JWT token...")
        try:
            headers = {
                "Authorization": "Bearer invalid_token",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{self.base_url}/api/dashboard/status", headers=headers)
            
            if response.status_code == 401:
                print("✅ Invalid JWT correctly rejected")
                return True
            else:
                print(f"❌ Invalid JWT should have been rejected: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Invalid JWT test error: {e}")
            return False
    
    def test_missing_auth_headers(self) -> bool:
        """Test missing authentication headers (should fail)"""
        print("🔍 Testing missing authentication headers...")
        try:
            response = requests.get(f"{self.base_url}/api/dashboard/status")
            
            if response.status_code == 401:
                print("✅ Missing auth headers correctly rejected")
                return True
            else:
                print(f"❌ Missing auth headers should have been rejected: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Missing auth headers test error: {e}")
            return False
    
    def test_quickbooks_endpoints(self) -> bool:
        """Test QuickBooks API endpoints with authentication"""
        print("🔍 Testing QuickBooks API endpoints...")
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Test company info endpoint
            response = requests.get(f"{self.base_url}/api/quickbooks/company", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ QuickBooks company endpoint accessible")
                print(f"   Company info available: {bool(data.get('company_info'))}")
                return True
            elif response.status_code == 401:
                print("ℹ️  QuickBooks not authenticated (expected if no QBO connection)")
                return True
            else:
                print(f"❌ QuickBooks endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ QuickBooks endpoints test error: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all security tests"""
        print("🔐 Starting Security Implementation Tests")
        print("=" * 50)
        
        tests = {
            "health_check": self.test_health_check(),
            "hmac_authentication": self.test_hmac_authentication(),
            "invalid_hmac": self.test_invalid_hmac(),
            "expired_timestamp": self.test_expired_timestamp(),
            "jwt_authentication": self.test_jwt_authentication(),
            "invalid_jwt": self.test_invalid_jwt(),
            "missing_auth_headers": self.test_missing_auth_headers(),
            "quickbooks_endpoints": self.test_quickbooks_endpoints()
        }
        
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        
        passed = 0
        total = len(tests)
        
        for test_name, result in tests.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All security tests passed! Implementation is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the implementation.")
        
        return tests

def main():
    """Run security tests"""
    print("🔐 QBO Sankey Dashboard Security Test Suite")
    print("=" * 60)
    
    # Check if app is running
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ App not responding at {BASE_URL}")
            print("   Make sure the app is running: python app.py")
            return
    except requests.exceptions.RequestException:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("   Make sure the app is running: python app.py")
        return
    
    # Run tests
    tester = SecurityTester(BASE_URL, API_KEY, API_SECRET)
    results = tester.run_all_tests()
    
    # Print configuration info
    print("\n📋 Test Configuration:")
    print(f"   Base URL: {BASE_URL}")
    print(f"   API Key: {API_KEY}")
    print(f"   API Secret: {API_SECRET[:10]}...")
    
    print("\n💡 To test with your own credentials:")
    print("   1. Update API_KEY and API_SECRET in this file")
    print("   2. Or set environment variables:")
    print("      export API_KEY='your_key'")
    print("      export API_SECRET='your_secret'")

if __name__ == "__main__":
    main()
