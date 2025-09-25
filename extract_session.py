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
    """Encode the entire .session file as base64 (fallback)"""
    session_file = "daredevil_session.session"
    if not os.path.exists(session_file):
        print(f"❌ Session file not found: {session_file}")
        return None
    try:
        data = Path(session_file).read_bytes()
        return base64.b64encode(data).decode("utf-8")
    except Exception as e:
        print(f"❌ Error reading session file: {e}")
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
