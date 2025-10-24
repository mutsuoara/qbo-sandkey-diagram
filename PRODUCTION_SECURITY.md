# 🔒 Production Security Guide

## Overview

This guide covers the complete production security setup for the QBO Sankey Dashboard, including HTTPS enforcement, secure password management, and deployment best practices.

## 🚀 Production Deployment Options

### Option 1: Heroku (Recommended)

**Advantages:**
- Automatic HTTPS with SSL certificates
- Easy environment variable management
- Built-in security features
- No server management required

**Setup Steps:**

1. **Generate Secure Password:**
   ```bash
   python generate_password_hash.py
   # Enter a strong password
   # Copy the generated hash
   ```

2. **Deploy to Heroku:**
   ```bash
   # Create Heroku app
   heroku create your-app-name
   
   # Set environment variables
   heroku config:set DASHBOARD_PASSWORD_HASH='your_hash_here'
   heroku config:set FLASK_ENV=production
   heroku config:set DEBUG=False
   
   # Deploy
   git push heroku main
   ```

3. **Update Intuit Developer Console:**
   - Add redirect URI: `https://your-app-name.herokuapp.com/callback`
   - Update production app settings

### Option 2: Docker + nginx + SSL

**Advantages:**
- Full control over server configuration
- Custom domain support
- Advanced security configurations

**Setup Steps:**

1. **Build Docker Image:**
   ```bash
   docker build -t qbo-sankey-dashboard .
   ```

2. **Configure nginx:**
   ```bash
   # Copy nginx.conf to your server
   # Update domain and SSL certificate paths
   # Restart nginx
   ```

3. **Run with SSL:**
   ```bash
   docker run -d \
     -p 8050:8050 \
     -e DASHBOARD_PASSWORD_HASH='your_hash_here' \
     -e FLASK_ENV=production \
     qbo-sankey-dashboard
   ```

### Option 3: VPS + nginx + Let's Encrypt

**Advantages:**
- Free SSL certificates with Let's Encrypt
- Full server control
- Cost-effective for multiple apps

**Setup Steps:**

1. **Install Dependencies:**
   ```bash
   sudo apt update
   sudo apt install nginx certbot python3-certbot-nginx
   ```

2. **Configure SSL:**
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

3. **Deploy Application:**
   ```bash
   # Set up virtual environment
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   
   # Set environment variables
   export DASHBOARD_PASSWORD_HASH='your_hash_here'
   export FLASK_ENV=production
   
   # Run application
   python app.py
   ```

## 🔐 Security Features

### 1. HTTPS Enforcement
- **Automatic redirect**: HTTP → HTTPS (301 redirect)
- **HSTS headers**: Strict-Transport-Security
- **SSL/TLS**: Modern cipher suites only

### 2. Password Security
- **SHA-256 hashing**: One-way password encryption
- **Environment variables**: No passwords in source code
- **Secure generation**: Random password generation

### 3. Security Headers
- **X-Frame-Options**: DENY (prevents clickjacking)
- **X-Content-Type-Options**: nosniff (prevents MIME sniffing)
- **X-XSS-Protection**: 1; mode=block (XSS protection)
- **Content-Security-Policy**: Restricts resource loading

### 4. OAuth Security
- **QuickBooks 2FA**: Enterprise-grade authentication
- **Token refresh**: Automatic token renewal
- **Secure storage**: Keyring-based credential storage

## 🛡️ Security Checklist

### Pre-Deployment
- [ ] Generate secure password hash
- [ ] Set production environment variables
- [ ] Configure HTTPS redirect
- [ ] Update Intuit redirect URIs
- [ ] Test OAuth flow in production

### Post-Deployment
- [ ] Verify HTTPS is working
- [ ] Test password authentication
- [ ] Verify security headers
- [ ] Test OAuth callback
- [ ] Monitor application logs

### Ongoing Security
- [ ] Regular password updates
- [ ] Monitor for security updates
- [ ] Review access logs
- [ ] Update dependencies
- [ ] Backup credentials securely

## 🔧 Environment Variables

### Required for Production
```bash
# Security
DASHBOARD_PASSWORD_HASH=your_secure_hash_here
SECRET_KEY=your_secret_key_here

# Flask
FLASK_ENV=production
DEBUG=False

# HTTPS
HTTPS_ENFORCE=True
```

### Optional Configuration
```bash
# Custom settings
PORT=8050
LOG_LEVEL=INFO
SESSION_TIMEOUT=3600
```

## 🚨 Security Warnings

### ⚠️ Critical Security Notes

1. **Password Management:**
   - Never commit passwords to git
   - Use environment variables only
   - Change default passwords immediately
   - Use strong, unique passwords

2. **HTTPS Requirements:**
   - HTTP Basic Auth requires HTTPS in production
   - Base64 encoding is easily decoded
   - Always use HTTPS for password transmission

3. **Environment Security:**
   - Secure environment variable storage
   - Limit access to production credentials
   - Regular credential rotation

4. **OAuth Security:**
   - Keep QuickBooks credentials secure
   - Monitor OAuth token usage
   - Implement token refresh logic

## 📋 Production Testing

### Security Tests
```bash
# Test HTTPS enforcement
curl -I http://your-domain.com
# Should redirect to HTTPS

# Test password protection
curl -u admin:wrong_password https://your-domain.com
# Should return 401 Unauthorized

# Test security headers
curl -I https://your-domain.com
# Should include security headers
```

### OAuth Testing
1. Navigate to production URL
2. Enter dashboard password
3. Click "Connect to QuickBooks"
4. Complete OAuth flow
5. Verify dashboard loads with data

## 🔄 Maintenance

### Regular Tasks
- **Monthly**: Review security logs
- **Quarterly**: Update dependencies
- **Annually**: Rotate passwords and keys

### Monitoring
- Monitor failed authentication attempts
- Check for unusual access patterns
- Review OAuth token usage
- Monitor application performance

## 📞 Support

For security issues or questions:
1. Check application logs
2. Verify environment variables
3. Test OAuth configuration
4. Review security headers
5. Contact support if needed

---

**Remember**: Security is an ongoing process. Regular updates and monitoring are essential for maintaining a secure production environment.
