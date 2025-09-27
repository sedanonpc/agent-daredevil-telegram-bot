#!/usr/bin/env python3
"""
Simple Health Server for Railway Deployment
==========================================
A minimal FastAPI server that provides health checks and basic functionality
without requiring complex bot initialization. This ensures the service starts
even if environment variables are missing.
"""

import os
import sys
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agent Daredevil Health Server",
    description="Simple health check server for Railway deployment",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agent Daredevil Health Server",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    try:
        # Check environment variables
        env_status = {
            "OPENAI_API_KEY": "✅" if os.getenv('OPENAI_API_KEY') else "❌",
            "TELEGRAM_API_ID": "✅" if os.getenv('TELEGRAM_API_ID') else "❌",
            "TELEGRAM_API_HASH": "✅" if os.getenv('TELEGRAM_API_HASH') else "❌",
            "TELEGRAM_PHONE_NUMBER": "✅" if os.getenv('TELEGRAM_PHONE_NUMBER') else "❌",
        }
        
        return {
            "status": "healthy",
            "service": "agent-daredevil-health",
            "timestamp": datetime.now().isoformat(),
            "environment": env_status,
            "port": os.getenv('PORT', '8000')
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/status")
async def status():
    """Detailed status endpoint."""
    return {
        "service": "Agent Daredevil",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "python_version": sys.version,
            "port": os.getenv('PORT', '8000'),
            "railway_environment": os.getenv('RAILWAY_ENVIRONMENT', 'unknown')
        }
    }

def main():
    """Main function to run the server."""
    try:
        logger.info("🚀 Starting Agent Daredevil Health Server...")
        
        # Get port from environment (Railway sets this)
        port = int(os.environ.get("PORT", "8000"))
        
        logger.info(f"🌐 Starting server on port {port}")
        logger.info("📊 Health check available at /health")
        logger.info("📈 Status available at /status")
        
        # Run the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Error starting server: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
