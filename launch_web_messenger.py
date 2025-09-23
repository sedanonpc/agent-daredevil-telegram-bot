#!/usr/bin/env python3
"""
Launch Web Messenger Server
==========================
Simple launcher script for the Agent Daredevil Web Messenger server.

Usage:
    python launch_web_messenger.py

This will start the FastAPI server on http://localhost:8000
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Launch the web messenger server."""
    try:
        logger.info("🚀 Starting Agent Daredevil Web Messenger Server...")
        
        # Check if required environment variables are set
        required_vars = ['OPENAI_API_KEY']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            logger.error("Please set these variables in your .env file or environment")
            return 1
        
        # Import and run the server
        import uvicorn
        from web_messenger_server import app
        
        logger.info("✅ Environment variables validated")
        logger.info("🌐 Starting server on http://localhost:8000")
        logger.info("📱 Open your browser and navigate to http://localhost:8000 to test the messenger")
        logger.info("🔌 WebSocket endpoint available at ws://localhost:8000/ws/{user_id}")
        logger.info("📚 API documentation available at http://localhost:8000/docs")
        
        # Run the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Error starting server: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
