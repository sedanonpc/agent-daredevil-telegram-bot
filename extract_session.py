#!/usr/bin/env python3
"""
Session Data Extractor for Railway Deployment
============================================
This script can output either a compact StringSession (recommended) or the
raw .session as base64 for environments with larger limits.

Usage:
    python extract_session.py
"""

import os
import sqlite3
import base64
from pathlib import Path
from telethon.sessions import StringSession
from telethon import TelegramClient

def extract_string_session():
    """Export compact Telethon StringSession from local session"""
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    if not api_id or not api_hash:
        print("❌ TELEGRAM_API_ID and TELEGRAM_API_HASH needed to export StringSession")
        return None
    try:
        with TelegramClient('daredevil_session', int(api_id), api_hash) as client:
            s = client.session.save()
            if not isinstance(s, str):
                s = StringSession.save(client.session)
            return s
    except Exception as e:
        print(f"❌ Failed to export StringSession: {e}")
        return None

def extract_session_data_b64():
    """Extract session DB as base64 (fallback)"""
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
    print("🚀 Agent Daredevil - Session Exporter")
    print("=" * 40)

    s = extract_string_session()
    if s:
        Path('TELEGRAM_STRING_SESSION.txt').write_text(s, encoding='utf-8')
        print("✅ Wrote TELEGRAM_STRING_SESSION.txt (recommended)")
        print("➡ Use Railway var TELEGRAM_STRING_SESSION with this value")
    else:
        print("⚠️ Falling back to .session base64 export...")
        auth_b64 = extract_session_data_b64()
        if auth_b64:
            Path('TELEGRAM_SESSION_B64.txt').write_text(auth_b64, encoding='utf-8')
            print("✅ Wrote TELEGRAM_SESSION_B64.txt")
            print("➡ Use Railway var TELEGRAM_SESSION_B64 with this value")
        else:
            print("❌ Could not export session data")
