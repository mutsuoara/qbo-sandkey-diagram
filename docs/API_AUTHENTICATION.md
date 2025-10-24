# API Authentication Guide for Clients

## Overview

Our API uses a two-step authentication process:

1. **HMAC Request Signing** - Sign your initial request to prove your identity
2. **JWT Tokens** - Receive a short-lived token for subsequent requests

This ensures your credentials are never transmitted directly and requests can't be intercepted and replayed.

## Your Credentials

You will receive:

* **API Key**: `your_api_key_here` (public identifier)
* **API Secret**: `your_api_secret_here` (keep this secret!)

**⚠️ IMPORTANT**: Never share your API Secret or commit it to version control.

## Step 1: Get an Access Token

Every hour (or when your token expires), exchange your credentials for an access token.

**Endpoint**: `POST https://qbo-sankey-dashboard-27818919af8f.herokuapp.com/api/auth/token`

**Required Headers**:

* `X-API-Key`: Your API key
* `X-Signature`: HMAC SHA256 signature (see below)
* `X-Timestamp`: Current Unix timestamp

**How to Create the Signature**:

```python
import hmac
import hashlib
import time

# Your credentials
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"

# Request details
method = "POST"
path = "/api/auth/token"
timestamp = str(time.time())
body = ""  # Empty for token request

# Create signature
message = f"{method}:{path}:{timestamp}:{body}"
signature = hmac.new(
    API_SECRET.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

print(f"Signature: {signature}")
```

**Example Request**:

```bash
curl -X POST https://qbo-sankey-dashboard-27818919af8f.herokuapp.com/api/auth/token \
  -H "X-API-Key: your_api_key_here" \
  -H "X-Signature: computed_signature_here" \
  -H "X-Timestamp: 1234567890.123"
```

**Response**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "client_id": "client_123",
  "client_name": "Your Client Name"
}
```

## Step 2: Use the Access Token

Use the access token for all API requests.

**Required Header**:

* `Authorization: Bearer <your_access_token>`

**Example Request**:

```bash
curl -X GET https://qbo-sankey-dashboard-27818919af8f.herokuapp.com/api/quickbooks/company \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Complete Python Client Example

```python
import hmac
import hashlib
import time
import requests
from typing import Optional

class APIClient:
    """Client for authenticated API requests"""
    
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
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
        
        # Create signature for token request
        signature, timestamp = self._create_signature("POST", "/api/auth/token")
        
        headers = {
            "X-API-Key": self.api_key,
            "X-Signature": signature,
            "X-Timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        response = requests.post(f"{self.base_url}/api/auth/token", headers=headers)
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["access_token"]
        self.token_expires = time.time() + data["expires_in"]
        
        return self.access_token
    
    def _make_authenticated_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make authenticated API request"""
        token = self._get_access_token()
        
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"
        
        kwargs["headers"] = headers
        
        response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
        response.raise_for_status()
        
        return response.json()
    
    def get_company_info(self) -> dict:
        """Get QuickBooks company information"""
        return self._make_authenticated_request("GET", "/api/quickbooks/company")
    
    def get_financial_data(self, start_date: str, end_date: str) -> dict:
        """Get financial data for Sankey diagram"""
        params = {"start_date": start_date, "end_date": end_date}
        return self._make_authenticated_request("GET", "/api/quickbooks/financial-data", params=params)
    
    def get_profit_loss_report(self, start_date: str, end_date: str) -> dict:
        """Get Profit & Loss report"""
        params = {"start_date": start_date, "end_date": end_date}
        return self._make_authenticated_request("GET", "/api/quickbooks/profit-loss", params=params)
    
    def get_dashboard_status(self) -> dict:
        """Get dashboard status"""
        return self._make_authenticated_request("GET", "/api/dashboard/status")

# Usage example
if __name__ == "__main__":
    client = APIClient(
        api_key="your_api_key_here",
        api_secret="your_api_secret_here",
        base_url="https://qbo-sankey-dashboard-27818919af8f.herokuapp.com"
    )
    
    # Get company info
    company = client.get_company_info()
    print(f"Company: {company['company_info']['CompanyName']}")
    
    # Get financial data
    financial_data = client.get_financial_data("2024-01-01", "2024-12-31")
    print(f"Financial data: {len(financial_data['financial_data'])} categories")
```

## Available Endpoints

### Authentication
- `POST /api/auth/token` - Get JWT token (HMAC required)

### QuickBooks Data
- `GET /api/quickbooks/company` - Get company information
- `GET /api/quickbooks/financial-data` - Get financial data for Sankey
- `GET /api/quickbooks/profit-loss` - Get Profit & Loss report

### Dashboard
- `GET /api/dashboard/status` - Get dashboard status
- `GET /api/health` - Health check (no auth required)

## Error Handling

### Common Error Responses

```json
{
  "error": "Missing authentication headers"
}
```

```json
{
  "error": "Invalid API key"
}
```

```json
{
  "error": "Request expired. Check system clock."
}
```

```json
{
  "error": "Token expired"
}
```

```json
{
  "error": "Permission denied: read_financial_data required"
}
```

## Security Best Practices

1. **Never log or expose your API Secret**
2. **Use HTTPS for all requests**
3. **Store credentials securely** (environment variables, not code)
4. **Implement proper error handling**
5. **Refresh tokens before they expire**
6. **Validate server certificates** in production

## Rate Limiting

- **Token requests**: 10 per minute per client
- **API requests**: 100 per minute per client
- **Burst allowance**: 20 requests per 10 seconds

## Support

For API support or to request credentials, contact the development team.
