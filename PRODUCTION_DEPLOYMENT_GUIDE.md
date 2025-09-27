# 🎯 Agent Daredevil - Production Deployment Guide

## Overview

This guide will help you deploy the Agent Daredevil Telegram Bot to Railway using Docker. The deployment includes:

1. **Telegram Bot** - Main bot with RAG, memory, and character features
2. **LLM Services** - Multi-provider support (OpenAI, Gemini, Vertex AI) with voice processing  
3. **Web Endpoints** - FastAPI web messenger server with health checks

## Prerequisites

### Required Tools
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for local testing)
- [Railway CLI](https://docs.railway.app/develop/cli) (`npm install -g @railway/cli`)
- [Git](https://git-scm.com/) (for version control)

### Required Accounts & API Keys
- [Telegram API](https://my.telegram.org/apps) - API ID and Hash
- [OpenAI API](https://platform.openai.com/api-keys) - API Key
- [ElevenLabs](https://elevenlabs.io/) - API Key (for voice features)
- [Railway Account](https://railway.app/) - Free tier available

## Quick Start

### 1. Environment Setup

```bash
# Copy the production environment template
cp env.production.example .env

# Edit .env with your actual API keys and configuration
# Required minimum configuration:
# - TELEGRAM_API_ID
# - TELEGRAM_API_HASH  
# - TELEGRAM_PHONE_NUMBER
# - OPENAI_API_KEY
```

### 2. Local Testing (Optional)

```bash
# Start Docker Desktop first, then:

# Build and test locally
docker build -t agent-daredevil:latest .
docker run -d --name test-bot --env-file .env -p 8000:8000 agent-daredevil:latest

# Test health endpoint
curl http://localhost:8000/health

# Clean up
docker stop test-bot && docker rm test-bot
```

### 3. Deploy to Railway

```bash
# Login to Railway
railway login

# Deploy (automated script)
# Windows:
deploy-production.bat

# Linux/Mac:
./deploy-production.sh

# Or manual deployment:
railway up --detach
```

## Configuration

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `TELEGRAM_API_ID` | ✅ | Telegram API ID | `12345678` |
| `TELEGRAM_API_HASH` | ✅ | Telegram API Hash | `abcdef1234567890` |
| `TELEGRAM_PHONE_NUMBER` | ✅ | Your phone number | `+1234567890` |
| `OPENAI_API_KEY` | ✅ | OpenAI API Key | `sk-...` |
| `LLM_PROVIDER` | ❌ | LLM provider (openai/gemini/vertex_ai) | `openai` |
| `ELEVENLABS_API_KEY` | ❌ | ElevenLabs API Key | `...` |
| `USE_VOICE_FEATURES` | ❌ | Enable voice processing | `True` |
| `USE_RAG` | ❌ | Enable RAG features | `True` |
| `USE_MEMORY` | ❌ | Enable session memory | `True` |

### Railway Configuration

The `railway.json` file is already configured for optimal deployment:

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "python launch_web_messenger.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "healthcheckInterval": 60,
    "healthcheckStartPeriod": 120
  }
}
```

## Service Architecture

### Primary Service: Web Messenger
- **Port**: 8000 (Railway auto-assigned)
- **Health Check**: `/health`
- **Features**: REST API, WebSocket, Voice processing
- **Command**: `python launch_web_messenger.py`

### Optional Services (Development)
- **RAG Manager**: Port 8501 (Streamlit interface)
- **Knowledge Visualizer**: Port 8502 (Streamlit interface)
- **Telegram Bot**: Background service (separate container)

## Docker Configuration

### Multi-Stage Build
- **Stage 1**: Build dependencies in optimized environment
- **Stage 2**: Runtime with minimal dependencies
- **Security**: Non-root user, proper permissions
- **Size**: Optimized for production deployment

### Key Features
- Python 3.11 slim base image
- FFmpeg for voice processing
- ChromaDB for vector storage
- Health checks for Railway
- Proper logging and error handling

## Monitoring & Maintenance

### Health Checks
```bash
# Check service health
curl https://your-app.railway.app/health

# Expected response:
{"status": "healthy", "service": "telegram-bot", "timestamp": "1234567890"}
```

### Logs
```bash
# View Railway logs
railway logs

# View specific service logs
railway logs --service your-service-name
```

### Updates
```bash
# Redeploy with latest changes
railway up --detach

# Or use the deployment script
deploy-production.bat  # Windows
./deploy-production.sh  # Linux/Mac
```

## Troubleshooting

### Common Issues

#### 1. Docker Build Fails
```bash
# Check Docker is running
docker --version

# Clean build cache
docker system prune -a
```

#### 2. Railway Deployment Fails
```bash
# Check Railway login
railway whoami

# Check environment variables
railway variables

# View deployment logs
railway logs
```

#### 3. Health Check Fails
- Verify all required environment variables are set
- Check that the service is binding to the correct port
- Ensure the `/health` endpoint is accessible

#### 4. Telegram Bot Not Responding
- Verify Telegram API credentials
- Check phone number format (+1234567890)
- Ensure session files are properly configured

### Debug Mode
```bash
# Enable debug logging
DEBUG=True LOG_LEVEL=DEBUG railway up --detach
```

## Security Considerations

### Environment Variables
- Never commit `.env` files to version control
- Use Railway's environment variable management
- Rotate API keys regularly

### Container Security
- Non-root user execution
- Minimal base image
- No unnecessary packages
- Proper file permissions

### Network Security
- HTTPS enforced by Railway
- CORS properly configured
- Rate limiting implemented

## Performance Optimization

### Resource Limits
- **Memory**: 2GB limit, 1GB reservation
- **CPU**: 1.0 limit, 0.5 reservation
- **Storage**: Persistent volumes for data

### Caching
- ChromaDB vector cache
- Session memory management
- LLM response caching

### Scaling
- Railway auto-scaling based on traffic
- Horizontal scaling with multiple replicas
- Load balancing across regions

## Cost Optimization

### Railway Pricing
- Free tier: $5 credit monthly
- Pro tier: Pay-as-you-go
- Optimize resource usage

### Tips
- Use appropriate resource limits
- Monitor usage in Railway dashboard
- Implement proper caching
- Optimize Docker image size

## Support & Resources

### Documentation
- [Railway Docs](https://docs.railway.app/)
- [Docker Docs](https://docs.docker.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Community
- [Railway Discord](https://discord.gg/railway)
- [Telegram Bot Community](https://t.me/BotSupport)

### Issues
- Check logs first: `railway logs`
- Verify environment variables
- Test locally with Docker
- Contact support if needed

---

## 🎯 Ready to Deploy?

1. **Set up your environment**: Copy `env.production.example` to `.env` and configure
2. **Test locally** (optional): `docker build -t agent-daredevil:latest .`
3. **Deploy to Railway**: `railway up --detach`
4. **Monitor**: Check Railway dashboard and logs
5. **Test**: Verify health endpoint and bot functionality

Your Agent Daredevil bot will be live and ready to serve users! 🚀