"""
Security Setup Script
Sets up the security environment for testing
"""

import os
import json
import secrets
import logging

def setup_security_environment():
    """Set up security environment variables"""
    print("🔐 Setting up Security Environment")
    print("=" * 40)
    
    # Generate JWT secret if not set
    if not os.environ.get('JWT_SECRET'):
        jwt_secret = secrets.token_urlsafe(32)
        os.environ['JWT_SECRET'] = jwt_secret
        print(f"✅ Generated JWT secret: {jwt_secret[:10]}...")
    else:
        print("✅ JWT secret already configured")
    
    # Set up default client credentials
    if not os.environ.get('API_CLIENTS'):
        clients = {
            "demo_client": {
                "api_key": "demo_api_key_12345",
                "api_secret": "demo_secret_67890",
                "name": "Demo Client",
                "permissions": ["read_company", "read_financial_data", "read_reports"]
            },
            "admin_client": {
                "api_key": "admin_api_key_54321",
                "api_secret": "admin_secret_09876",
                "name": "Admin Client",
                "permissions": ["all"]
            }
        }
        os.environ['API_CLIENTS'] = json.dumps(clients)
        print("✅ Set up default client credentials")
        print("   Demo Client:")
        print(f"     API Key: {clients['demo_client']['api_key']}")
        print(f"     API Secret: {clients['demo_client']['api_secret']}")
        print("   Admin Client:")
        print(f"     API Key: {clients['admin_client']['api_key']}")
        print(f"     API Secret: {clients['admin_client']['api_secret']}")
    else:
        print("✅ Client credentials already configured")
    
    print("\n🎯 Security environment ready!")
    print("\nTo test the security implementation:")
    print("1. Start the app: python app.py")
    print("2. Run tests: python test_security.py")
    print("3. Test client: python test_client.py")

if __name__ == "__main__":
    setup_security_environment()
