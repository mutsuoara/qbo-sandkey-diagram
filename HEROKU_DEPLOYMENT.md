# 🚀 Heroku Deployment Guide

## Prerequisites (Manual Steps)

### 1. Install Heroku CLI
- **Windows**: Download from https://devcenter.heroku.com/articles/heroku-cli
- **Mac**: `brew install heroku/brew/heroku`
- **Linux**: Follow instructions at https://devcenter.heroku.com/articles/heroku-cli

### 2. Create Heroku Account
- Go to https://heroku.com
- Sign up for free account
- Verify your email address

### 3. Login to Heroku CLI
```bash
heroku login
# This will open your browser for authentication
```

### 4. Update Intuit Developer Console
- Go to https://developer.intuit.com
- Navigate to your app settings
- Add redirect URI: `https://qbo-sankey-dashboard.herokuapp.com/callback`
- Save changes

## Automated Deployment

### Option 1: Use the Deployment Script
```bash
python deploy_to_heroku.py
```

### Option 2: Manual Commands
```bash
# Create Heroku app
heroku create qbo-sankey-dashboard

# Set environment variables
heroku config:set DEBUG=False
heroku config:set FLASK_ENV=production

# Deploy
git push heroku main
```

## Verification

### 1. Check App Status
```bash
heroku apps:info
heroku logs --tail
```

### 2. Test OAuth Flow
- Visit your Heroku app URL
- Test the OAuth authentication
- Verify data fetching works

### 3. Monitor Logs
```bash
heroku logs --tail
```

## Troubleshooting

### Common Issues:

1. **Build Fails**: Check `requirements.txt` for missing dependencies
2. **OAuth Fails**: Verify redirect URI in Intuit Developer Console
3. **App Crashes**: Check logs with `heroku logs --tail`
4. **Port Issues**: Ensure app uses `os.environ.get('PORT')`

### Useful Commands:
```bash
# View logs
heroku logs --tail

# Restart app
heroku restart

# Check app info
heroku apps:info

# Open app in browser
heroku open
```

## Production Considerations

### Free Tier Limitations:
- App sleeps after 30 minutes of inactivity
- Limited to 550-1000 dyno hours per month
- No custom domains on free tier

### Upgrading to Paid:
- Consider upgrading for production use
- Enables custom domains
- No sleep limitations
- Better performance

## Security Notes

- Environment variables are secure on Heroku
- OAuth tokens are stored in keyring (local to dyno)
- Use production OAuth credentials only
- Monitor for any security issues

## Support

If you encounter issues:
1. Check Heroku logs: `heroku logs --tail`
2. Verify Intuit Developer Console settings
3. Test OAuth flow step by step
4. Contact support if needed
