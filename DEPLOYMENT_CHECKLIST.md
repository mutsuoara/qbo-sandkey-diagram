# ✅ Heroku Deployment Checklist

## 📋 Pre-Deployment (Manual Steps)

### 1. Install Heroku CLI
- [ ] Download from https://devcenter.heroku.com/articles/heroku-cli
- [ ] Install and verify: `heroku --version`
- [ ] Login: `heroku login`

### 2. Create Heroku Account
- [ ] Sign up at https://heroku.com
- [ ] Verify email address
- [ ] Complete account setup

### 3. Update Intuit Developer Console
- [ ] Go to https://developer.intuit.com
- [ ] Navigate to your app settings
- [ ] Add redirect URI: `https://qbo-sankey-dashboard.herokuapp.com/callback`
- [ ] Save changes

## 🚀 Deployment (Automated)

### Option 1: Use Deployment Script
- [ ] Run: `python deploy_to_heroku.py`
- [ ] Follow prompts and verify success

### Option 2: Manual Commands
- [ ] Create app: `heroku create qbo-sankey-dashboard`
- [ ] Set config: `heroku config:set DEBUG=False`
- [ ] Deploy: `git push heroku main`

## ✅ Post-Deployment Verification

### 1. Check App Status
- [ ] Run: `heroku apps:info`
- [ ] Verify app is running
- [ ] Check logs: `heroku logs --tail`

### 2. Test OAuth Flow
- [ ] Visit your Heroku app URL
- [ ] Click "Connect to QuickBooks"
- [ ] Complete OAuth authentication
- [ ] Verify redirect to dashboard

### 3. Test Dashboard Functionality
- [ ] Verify Sankey diagram loads
- [ ] Test date range selection
- [ ] Test data fetching (if using production)
- [ ] Test all buttons and interactions

### 4. Monitor Performance
- [ ] Check response times
- [ ] Monitor memory usage
- [ ] Watch for any errors in logs

## 🔧 Troubleshooting

### If Build Fails:
- [ ] Check `requirements.txt` for missing dependencies
- [ ] Verify Python version in `runtime.txt`
- [ ] Check `Procfile` format

### If OAuth Fails:
- [ ] Verify redirect URI in Intuit Developer Console
- [ ] Check environment variables
- [ ] Test with sandbox first

### If App Crashes:
- [ ] Check logs: `heroku logs --tail`
- [ ] Restart app: `heroku restart`
- [ ] Verify all dependencies are installed

## 📊 Success Criteria

- [ ] App deploys without errors
- [ ] OAuth flow completes successfully
- [ ] Dashboard loads and functions properly
- [ ] Data fetching works (if using production)
- [ ] All buttons and interactions work
- [ ] App stays running (doesn't crash)

## 🎯 Next Steps After Deployment

1. **Test thoroughly** with both sandbox and production data
2. **Monitor logs** for any issues
3. **Update documentation** with production URL
4. **Share with users** for testing
5. **Consider upgrading** to paid Heroku plan for production use

## 📞 Support Resources

- Heroku Documentation: https://devcenter.heroku.com/
- Intuit Developer Docs: https://developer.intuit.com/
- Heroku Status: https://status.heroku.com/
- Heroku Support: https://help.heroku.com/

