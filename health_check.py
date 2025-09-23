#!/usr/bin/env python3
"""
Simple health check script for Railway deployment
Checks if the Telegram bot dependencies are available
"""

import sys
import os

def check_dependencies():
    """Check if all required dependencies are available"""
    try:
        import telegram_bot_rag
        import telethon
        import openai
        from llm_provider import get_llm_provider
        from voice_processor import voice_processor
        
        print("✅ All dependencies imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        'TELEGRAM_API_ID',
        'TELEGRAM_API_HASH', 
        'TELEGRAM_PHONE_NUMBER'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ Environment variables configured")
    return True

def main():
    """Main health check function"""
    print("🔍 Running health check...")
    
    deps_ok = check_dependencies()
    env_ok = check_environment()
    
    if deps_ok and env_ok:
        print("✅ Health check passed")
        sys.exit(0)
    else:
        print("❌ Health check failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
