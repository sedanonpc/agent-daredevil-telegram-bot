#!/usr/bin/env python3
"""
Session Authentication Helper for Agent Daredevil Bot
====================================================
This script helps authenticate your Telegram session locally before deploying to Railway.
Run this script locally to ensure your session file is properly authenticated.

Usage:
    python authenticate_session.py
"""

import os
import asyncio
import logging
from telethon import TelegramClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def authenticate_session():
    """Authenticate Telegram session locally"""
    try:
        # Get credentials from environment
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        phone_number = os.getenv('TELEGRAM_PHONE_NUMBER')
        session_name = os.getenv('TELEGRAM_SESSION_NAME', 'daredevil_session')
        
        if not all([api_id, api_hash, phone_number]):
            logger.error("❌ Missing required environment variables:")
            logger.error("   - TELEGRAM_API_ID")
            logger.error("   - TELEGRAM_API_HASH") 
            logger.error("   - TELEGRAM_PHONE_NUMBER")
            return False
        
        logger.info("🔐 Starting Telegram session authentication...")
        logger.info(f"📱 Phone: {phone_number}")
        logger.info(f"📄 Session file: {session_name}.session")
        
        # Create client
        client = TelegramClient(session_name, int(api_id), api_hash)
        
        # Start client (this will prompt for authentication if needed)
        await client.start(phone=phone_number)
        
        # Get user info to verify authentication
        me = await client.get_me()
        logger.info(f"✅ Authentication successful!")
        logger.info(f"👤 Logged in as: {me.first_name} {me.last_name or ''}")
        logger.info(f"🆔 User ID: {me.id}")
        
        # Test connection
        await client.get_dialogs(limit=1)
        logger.info("🌐 Connection test successful!")
        
        # Disconnect
        await client.disconnect()
        logger.info("📄 Session file saved and ready for deployment!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        return False

async def main():
    """Main function"""
    print("🚀 Agent Daredevil - Session Authentication Helper")
    print("=" * 50)
    
    success = await authenticate_session()
    
    if success:
        print("\n🎉 Session authentication completed successfully!")
        print("📦 You can now deploy to Railway with confidence.")
        print("💡 The session file will be used for authentication in Docker.")
    else:
        print("\n❌ Session authentication failed!")
        print("💡 Please check your environment variables and try again.")
        print("💡 Make sure you have a valid .env file with Telegram credentials.")

if __name__ == "__main__":
    asyncio.run(main())
