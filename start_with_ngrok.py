#!/usr/bin/env python3
"""
Script to start the QBO Sankey Dashboard with ngrok for HTTPS OAuth
"""

import subprocess
import sys
import time
import os
import requests
import json

def get_ngrok_url():
    """Get the ngrok public URL"""
    try:
        response = requests.get("http://localhost:4040/api/tunnels")
        if response.status_code == 200:
            data = response.json()
            for tunnel in data.get('tunnels', []):
                if tunnel.get('proto') == 'https':
                    return tunnel.get('public_url')
    except:
        pass
    return None

def main():
    print("🚀 Starting QBO Sankey Dashboard with ngrok...")
    print("=" * 60)
    
    # Check if ngrok is installed
    try:
        subprocess.run(['ngrok', 'version'], check=True, capture_output=True)
        print("✅ ngrok is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ngrok not found!")
        print("Please install ngrok:")
        print("1. Download from: https://ngrok.com/download")
        print("2. Extract ngrok.exe to a folder")
        print("3. Add that folder to your PATH")
        print("4. Run: ngrok authtoken YOUR_TOKEN")
        return
    
    # Start ngrok in background
    print("🌐 Starting ngrok tunnel...")
    ngrok_process = subprocess.Popen(['ngrok', 'http', '8050'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
    
    # Wait for ngrok to start
    print("⏳ Waiting for ngrok to start...")
    time.sleep(3)
    
    # Get ngrok URL
    ngrok_url = get_ngrok_url()
    if not ngrok_url:
        print("❌ Failed to get ngrok URL")
        print("Make sure ngrok is running and accessible at http://localhost:4040")
        return
    
    print(f"✅ ngrok tunnel active: {ngrok_url}")
    
    # Set environment variable for the app
    os.environ['NGROK_URL'] = ngrok_url
    print(f"🔧 Set NGROK_URL={ngrok_url}")
    
    print("\n📋 Next steps:")
    print("1. Update your Intuit Developer Console:")
    print(f"   - Go to: https://developer.intuit.com/")
    print(f"   - Add redirect URI: {ngrok_url}/callback")
    print("2. Start your app with production credentials")
    print("3. Click 'Connect to QuickBooks' to test OAuth")
    
    print("\n🚀 Starting your app...")
    print("=" * 60)
    
    # Start the app
    try:
        subprocess.run([sys.executable, 'app.py'], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        ngrok_process.terminate()
    except Exception as e:
        print(f"❌ Error starting app: {e}")
        ngrok_process.terminate()

if __name__ == "__main__":
    main()
