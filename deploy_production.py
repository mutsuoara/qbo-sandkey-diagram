#!/usr/bin/env python3
"""
Production Deployment Script for QBO Sankey Dashboard
Configures HTTPS, security, and production environment
"""

import os
import subprocess
import sys
import secrets
import hashlib

def generate_secure_password():
    """Generate a secure random password"""
    return secrets.token_urlsafe(32)

def generate_password_hash(password):
    """Generate SHA-256 hash for password"""
    return hashlib.sha256(password.encode()).hexdigest()

def setup_production_environment():
    """Set up production environment variables"""
    print("🔐 Setting up production security...")
    
    # Generate secure password
    secure_password = generate_secure_password()
    password_hash = generate_password_hash(secure_password)
    
    print(f"\n🔑 Generated secure password: {secure_password}")
    print(f"🔐 Password hash: {password_hash}")
    
    # Environment variables for production
    env_vars = {
        'FLASK_ENV': 'production',
        'DEBUG': 'False',
        'DASHBOARD_PASSWORD_HASH': password_hash,
        'SECRET_KEY': secrets.token_urlsafe(32),
        'HTTPS_ENFORCE': 'True'
    }
    
    print(f"\n📋 Production Environment Variables:")
    for key, value in env_vars.items():
        print(f"  {key}={value}")
    
    return env_vars, secure_password

def deploy_to_heroku(env_vars, secure_password):
    """Deploy to Heroku with production configuration"""
    print(f"\n🚀 Deploying to Heroku...")
    
    try:
        # Set environment variables
        for key, value in env_vars.items():
            subprocess.run(['heroku', 'config:set', f'{key}={value}'], check=True)
            print(f"  ✅ Set {key}")
        
        # Deploy to Heroku
        subprocess.run(['git', 'push', 'heroku', 'main'], check=True)
        print(f"  ✅ Deployed to Heroku")
        
        # Get Heroku app URL
        result = subprocess.run(['heroku', 'info'], capture_output=True, text=True)
        if 'web_url' in result.stdout:
            app_url = result.stdout.split('web_url: ')[1].split()[0]
            print(f"  🌐 App URL: {app_url}")
        
        print(f"\n🔐 Production Credentials:")
        print(f"  URL: {app_url}")
        print(f"  Username: admin")
        print(f"  Password: {secure_password}")
        print(f"\n⚠️  IMPORTANT: Save these credentials securely!")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Heroku deployment failed: {e}")
        return False

def create_nginx_config():
    """Create nginx configuration for HTTPS"""
    nginx_config = """
# Nginx configuration for QBO Sankey Dashboard
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    # Proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Ssl on;
    }
}
"""
    
    with open('nginx.conf', 'w') as f:
        f.write(nginx_config)
    
    print("📄 Created nginx.conf for HTTPS configuration")
    print("   Configure your domain and SSL certificates")

def create_dockerfile():
    """Create Dockerfile for production deployment"""
    dockerfile = """
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_ENV=production
ENV DEBUG=False
ENV HTTPS_ENFORCE=True

# Expose port
EXPOSE 8050

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "4", "app:app"]
"""
    
    with open('Dockerfile', 'w') as f:
        f.write(dockerfile)
    
    print("🐳 Created Dockerfile for production deployment")

def main():
    """Main deployment function"""
    print("🚀 QBO Sankey Dashboard - Production Deployment")
    print("=" * 50)
    
    # Check if we're in a git repository
    try:
        subprocess.run(['git', 'status'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("❌ Not in a git repository. Please initialize git first.")
        sys.exit(1)
    
    # Setup production environment
    env_vars, secure_password = setup_production_environment()
    
    # Create production files
    create_nginx_config()
    create_dockerfile()
    
    print(f"\n🔧 Production Setup Options:")
    print(f"1. Deploy to Heroku (recommended)")
    print(f"2. Deploy with Docker")
    print(f"3. Deploy with nginx + SSL")
    print(f"4. Exit")
    
    choice = input("\nSelect deployment option (1-4): ").strip()
    
    if choice == '1':
        deploy_to_heroku(env_vars, secure_password)
    elif choice == '2':
        print("🐳 Docker deployment instructions:")
        print("  1. Build image: docker build -t qbo-sankey-dashboard .")
        print("  2. Run container: docker run -p 8050:8050 -e DASHBOARD_PASSWORD_HASH='<hash>' qbo-sankey-dashboard")
    elif choice == '3':
        print("🌐 nginx + SSL deployment instructions:")
        print("  1. Configure nginx.conf with your domain")
        print("  2. Install SSL certificate")
        print("  3. Set environment variables")
        print("  4. Run: python app.py")
    else:
        print("👋 Exiting deployment script")
    
    print(f"\n✅ Production deployment setup complete!")
    print(f"🔐 Save your credentials securely!")

if __name__ == "__main__":
    main()
