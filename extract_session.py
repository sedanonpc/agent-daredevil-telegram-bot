#!/usr/bin/env python3
"""
Session Data Extractor for Railway Deployment
============================================
This script extracts session data from the local session file and provides
instructions for setting up Railway environment variables.

Usage:
    python extract_session.py
"""

import os
import sqlite3
import base64
from pathlib import Path

def extract_session_data():
    """Extract session data from the session file"""
    session_file = "daredevil_session.session"
    
    if not os.path.exists(session_file):
        print(f"❌ Session file not found: {session_file}")
        return None
    
    try:
        # Connect to the session database
        conn = sqlite3.connect(session_file)
        cursor = conn.cursor()
        
        # Get session data
        cursor.execute("SELECT * FROM sessions LIMIT 1")
        session_data = cursor.fetchone()
        
        if not session_data:
            print("❌ No session data found in the session file")
            return None
        
        # Extract the auth_key (this is what we need for authentication)
        auth_key = session_data[2] if len(session_data) > 2 else None
        
        if auth_key:
            # Convert to base64 for environment variable
            auth_key_b64 = base64.b64encode(auth_key).decode('utf-8')
            
            print("✅ Session data extracted successfully!")
            print("\n🔐 Add these environment variables to Railway:")
            print("=" * 50)
            print(f"TELEGRAM_AUTH_KEY={auth_key_b64}")
            print("=" * 50)
            
            conn.close()
            return auth_key_b64
        else:
            print("❌ Could not extract auth key from session file")
            return None
            
    except Exception as e:
        print(f"❌ Error extracting session data: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Agent Daredevil - Session Data Extractor")
    print("=" * 45)
    
    auth_key = extract_session_data()
    
    if auth_key:
        print("\n📋 Instructions:")
        print("1. Copy the TELEGRAM_AUTH_KEY value above")
        print("2. Go to your Railway project dashboard")
        print("3. Navigate to Variables tab")
        print("4. Add the TELEGRAM_AUTH_KEY variable")
        print("5. Redeploy your application")
        print("\n💡 This allows Railway to authenticate without session files!")
    else:
        print("\n❌ Failed to extract session data")
        print("💡 Make sure you've run the authentication script first")
