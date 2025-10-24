#!/usr/bin/env python3
"""
Heroku Deployment Script for QBO Sankey Dashboard
This script automates the deployment process to Heroku
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def check_heroku_cli():
    """Check if Heroku CLI is installed"""
    try:
        subprocess.run("heroku --version", shell=True, check=True, capture_output=True)
        print("✅ Heroku CLI is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Heroku CLI is not installed")
        print("Please install from: https://devcenter.heroku.com/articles/heroku-cli")
        return False

def check_git_repo():
    """Check if we're in a git repository"""
    try:
        subprocess.run("git status", shell=True, check=True, capture_output=True)
        print("✅ Git repository found")
        return True
    except subprocess.CalledProcessError:
        print("❌ Not in a git repository")
        return False

def main():
    """Main deployment function"""
    print("🚀 Starting Heroku Deployment for QBO Sankey Dashboard")
    print("=" * 60)
    
    # Check prerequisites
    if not check_heroku_cli():
        return False
    
    if not check_git_repo():
        print("Initializing git repository...")
        if not run_command("git init", "Initialize git repository"):
            return False
        
        if not run_command("git add .", "Add all files to git"):
            return False
        
        if not run_command('git commit -m "Initial commit for Heroku deployment"', "Initial commit"):
            return False
    
    # Check if Heroku app already exists
    try:
        subprocess.run("heroku apps:info", shell=True, check=True, capture_output=True)
        print("✅ Heroku app already exists")
        app_name = None
    except subprocess.CalledProcessError:
        print("📱 Creating new Heroku app...")
        app_name = "qbo-sankey-dashboard"
        if not run_command(f"heroku create {app_name}", f"Create Heroku app '{app_name}'"):
            return False
    
    # Set environment variables
    print("🔧 Setting environment variables...")
    env_vars = [
        "DEBUG=False",
        "FLASK_ENV=production"
    ]
    
    for env_var in env_vars:
        if not run_command(f"heroku config:set {env_var}", f"Set {env_var}"):
            return False
    
    # Deploy to Heroku
    print("🚀 Deploying to Heroku...")
    if not run_command("git push heroku master", "Deploy to Heroku"):
        return False
    
    # Get app URL
    try:
        result = subprocess.run("heroku apps:info --json", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            import json
            app_info = json.loads(result.stdout)
            app_url = f"https://{app_info['app']['name']}.herokuapp.com"
            print(f"🌐 Your app is available at: {app_url}")
            print(f"🔗 OAuth redirect URI: {app_url}/callback")
        else:
            print("⚠️  Could not get app URL automatically")
    except Exception as e:
        print(f"⚠️  Could not get app URL: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Deployment completed!")
    print("\n📋 Next steps:")
    print("1. Update your Intuit Developer Console with the redirect URI")
    print("2. Test the OAuth flow with your production app")
    print("3. Verify all functionality works in production")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
