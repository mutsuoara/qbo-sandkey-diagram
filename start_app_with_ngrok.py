#!/usr/bin/env python3
"""
Start the QBO Sankey Dashboard with ngrok URL properly configured
"""

import os
import subprocess
import sys

def main():
    # Set the ngrok URL
    ngrok_url = "https://2bda5df12b82.ngrok-free.app"
    os.environ['NGROK_URL'] = ngrok_url
    
    print("🚀 Starting QBO Sankey Dashboard with ngrok...")
    print(f"✅ NGROK_URL set to: {ngrok_url}")
    print("=" * 60)
    
    # Start the app
    try:
        subprocess.run([sys.executable, 'app.py'], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
