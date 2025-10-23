#!/usr/bin/env python3
"""
Clear stored credentials from keyring
"""

import keyring
from utils.credentials import CredentialManager

def clear_all_credentials():
    """Clear all stored credentials"""
    try:
        credential_manager = CredentialManager()
        
        # Clear credentials
        credential_manager.clear_credentials()
        print("✓ Credentials cleared")
        
        # Clear tokens
        credential_manager.clear_tokens()
        print("✓ Tokens cleared")
        
        print("All credentials have been cleared. You can now set up new credentials.")
        
    except Exception as e:
        print(f"Error clearing credentials: {e}")

if __name__ == "__main__":
    clear_all_credentials()
