# 🚀 Railway Deployment Walkthrough - Agent Daredevil

## Overview

This walkthrough covers deploying your Agent Daredevil Telegram Bot to Railway using Docker containers. We'll switch from the current native Python deployment to a containerized deployment for better production reliability.

## 🏗️ Current vs New Architecture

### Current Setup (Native Railway)
```
Railway Platform
├── Python Runtime (Railway managed)
├── telegram_bot_rag.py (Main bot)
├── RAG Manager (Streamlit - Optional)
├── Knowledge Visualizer (Streamlit - Optional)
└── Web Messenger (FastAPI - Optional)
```

### New Setup (Docker on Railway)
```
Railway Platform
├── Docker Container
│   ├── Python 3.11-slim base
│   ├── telegram_bot_rag.py (Main bot)
│   ├── All dependencies pre-installed
│   ├── Non-root user (daredevil)
│   ├── Health checks enabled
│   └── Optimized for production
├── Persistent Volumes (Data)
└── Environment Variables (Secrets)
```

## 🎯 Services That Will Be Running

### Primary Service: Telegram Bot
- **Container**: `agent-daredevil-bot`
- **Main Process**: `python telegram_bot_rag.py`
- **Ports**: Internal only (no external exposure needed)
- **Features**:
  - Telegram message handling
  - Voice note processing
  - RAG knowledge retrieval
  - Session memory management
  - Character personality system

### Supporting Services (Optional)
These can be deployed separately if needed:

#### 1. RAG Manager Web Interface
- **Purpose**: Knowledge base management
- **Technology**: Streamlit
- **Port**: 8501 (if deployed)
- **Access**: Web interface for managing knowledge

#### 2. Knowledge Visualizer
- **Purpose**: Interactive knowledge visualization
- **Technology**: Streamlit
- **Port**: 8502 (if deployed)
- **Access**: Web interface for exploring knowledge

#### 3. Web Messenger Server
- **Purpose**: REST API and WebSocket for web clients
- **Technology**: FastAPI
- **Port**: 8080 (if deployed)
- **Access**: API endpoints for web integration

## 📋 Step-by-Step Deployment Process

### Step 1: Pre-Deployment Verification

```bash
# Verify your environment
railway-deploy.bat check

# Or manually check:
# 1. Ensure .env file exists with all required variables
# 2. Verify Dockerfile and railway.docker.json exist
# 3. Check git repository is connected to Railway
```

**Required Environment Variables:**
```bash
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=+1234567890
OPENAI_API_KEY=your_openai_key
GOOGLE_AI_API_KEY=your_google_ai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
LLM_PROVIDER=gemini
USE_RAG=True
USE_MEMORY=True
USE_VOICE_FEATURES=True
```

### Step 2: Switch to Docker Configuration

```bash
# Automated way
railway-deploy.bat

# Manual way
copy railway.docker.json railway.json
git add railway.json Dockerfile .dockerignore
git commit -m "Deploy with Docker configuration for production"
git push origin main
```

### Step 3: Railway Build Process

When you push to Railway, here's what happens:

#### Build Phase (2-3 minutes)
```
1. Railway detects Dockerfile
2. Downloads Python 3.11-slim base image
3. Installs system dependencies (ffmpeg, curl, etc.)
4. Copies application code
5. Installs Python dependencies from requirements.txt
6. Creates non-root user 'daredevil'
7. Sets up health checks
8. Creates final optimized image
```

#### Deploy Phase (1-2 minutes)
```
1. Railway starts container from built image
2. Sets environment variables from Railway dashboard
3. Runs health checks
4. Starts telegram_bot_rag.py process
5. Waits for Telegram connection
6. Marks deployment as successful
```

### Step 4: Service Initialization

The bot will initialize in this order:

```
1. Load environment configuration
2. Initialize LLM provider (Gemini 1.5 Flash)
3. Initialize Telegram client
4. Setup RAG system (ChromaDB)
5. Load character personality
6. Initialize session memory
7. Test voice processor (ElevenLabs + Whisper)
8. Setup event handlers
9. Connect to Telegram
10. Start listening for messages
```

## 🔍 What You'll See During Deployment

### Railway Dashboard Monitoring

#### Build Logs
```
Building Docker image...
Step 1/10 : FROM python:3.11-slim as builder
Step 2/10 : ENV PYTHONUNBUFFERED=1
...
Step 10/10 : CMD ["python", "telegram_bot_rag.py"]
Successfully built abc123def456
```

#### Deployment Logs
```
Starting container...
Loading environment variables...
INFO:voice_processor:VoiceProcessor initialized with voice_id: zYcjlYFOd3taleS0gkk3
INFO:llm_provider:Gemini provider initialized with model: gemini-1.5-flash
INFO:telegram_bot_rag:AgentDaredevilBot initialized. Voice features: enabled
INFO:telegram_bot_rag:Starting Agent Daredevil Telegram Bot...
INFO:telegram_bot_rag:✅ Bot started successfully! Logged in as: YourBotName
INFO:telegram_bot_rag:🎤 Voice processing enabled
INFO:telegram_bot_rag:🧠 RAG system enabled
INFO:telegram_bot_rag:💾 Session memory enabled
INFO:telegram_bot_rag:🚀 Agent Daredevil is ready to chat!
```

### Health Check Status
```
✅ Container Health: Healthy
✅ Application Health: Running
✅ Telegram Connection: Connected
✅ LLM Provider: Gemini 1.5 Flash
✅ Voice Features: Enabled
✅ RAG System: Active
✅ Memory System: Active
```

## 🎛️ Railway Dashboard Features

### Service Overview
- **Status**: Running/Stopped
- **Health**: Healthy/Unhealthy
- **Uptime**: 99.9% target
- **Memory Usage**: < 1GB
- **CPU Usage**: Optimized

### Logs & Monitoring
- **Real-time Logs**: See bot activity live
- **Error Tracking**: Automatic error detection
- **Performance Metrics**: Response times, memory usage
- **Restart History**: Track container restarts

### Environment Management
- **Secrets**: Secure API key storage
- **Variables**: Configuration management
- **Updates**: Easy environment updates

## 🔧 Service Configuration Details

### Container Specifications
```yaml
Base Image: python:3.11-slim
Memory Limit: 1GB
Memory Reservation: 512MB
CPU: Railway managed
Storage: Persistent volumes for data
Network: Internal only (Telegram API access)
```

### Process Management
```yaml
Main Process: python telegram_bot_rag.py
User: daredevil (non-root)
Working Directory: /app
Health Check: Every 30 seconds
Restart Policy: ON_FAILURE (10 retries)
```

### Data Persistence
```yaml
Session Files: Railway persistent volumes
ChromaDB: /app/chroma_db (persistent)
Memory DB: /app/memory.db (persistent)
Voice Files: /app/temp_voice_files (temporary)
Logs: Railway managed logging
```

## 🚨 Troubleshooting Common Issues

### Issue 1: Build Fails
**Symptoms**: Docker build fails
**Solutions**:
```bash
# Check Dockerfile syntax
docker build -t test . --no-cache

# Verify all files are present
ls -la Dockerfile railway.docker.json
```

### Issue 2: Bot Won't Start
**Symptoms**: Container starts but bot doesn't connect
**Solutions**:
```bash
# Check environment variables in Railway dashboard
# Verify Telegram credentials
# Check logs for specific error messages
```

### Issue 3: Voice Features Not Working
**Symptoms**: Text works but voice fails
**Solutions**:
```bash
# Verify ElevenLabs API key
# Check OpenAI API key for Whisper
# Review voice processor logs
```

### Issue 4: High Memory Usage
**Symptoms**: Container hits memory limits
**Solutions**:
```bash
# Monitor memory usage in Railway dashboard
# Check for memory leaks in logs
# Consider optimizing session storage
```

## 📊 Post-Deployment Verification

### Test Checklist
```bash
# 1. Send text message to bot
# Expected: Bot responds with text

# 2. Send voice message to bot  
# Expected: Bot responds with voice (if enabled)

# 3. Test group chat functionality
# Expected: Bot responds when mentioned

# 4. Test RAG functionality
# Expected: Bot uses knowledge base for responses

# 5. Test session memory
# Expected: Bot remembers conversation context
```

### Performance Monitoring
```bash
# Key metrics to watch:
- Response time: < 5 seconds
- Memory usage: < 800MB
- Error rate: < 1%
- Uptime: > 99.9%
```

## 🔄 Rollback Procedure

If deployment fails or issues occur:

### Quick Rollback
```bash
# Switch back to native Railway setup
copy railway.native.json railway.json
git add railway.json
git commit -m "Rollback to native Railway deployment"
git push origin main
```

### Emergency Stop
```bash
# Use Railway dashboard to:
# 1. Stop the current deployment
# 2. Revert to previous working version
# 3. Investigate issues
# 4. Fix and redeploy
```

## 🎯 Expected Timeline

```
Total Deployment Time: 5-10 minutes
├── Build Phase: 2-3 minutes
├── Deploy Phase: 1-2 minutes  
├── Initialization: 1-2 minutes
└── Health Checks: 1 minute
```

## ✅ Success Indicators

You'll know the deployment is successful when you see:

1. **Railway Dashboard**: Container status "Running" and "Healthy"
2. **Bot Logs**: "🚀 Agent Daredevil is ready to chat!"
3. **Telegram**: Bot responds to test messages
4. **Voice**: Voice messages work (if enabled)
5. **Memory**: Stable memory usage < 1GB
6. **Uptime**: No unexpected restarts

---

## 🚀 Ready to Deploy!

Your Agent Daredevil bot is production-ready with:
- ✅ **Telegram Bot**: Full message handling
- ✅ **LLM Processing**: Gemini 1.5 Flash
- ✅ **Voice Features**: STT + TTS
- ✅ **RAG System**: Knowledge retrieval
- ✅ **Session Memory**: Conversation context
- ✅ **Docker Container**: Production optimized
- ✅ **Railway Integration**: Seamless deployment

**Run `railway-deploy.bat` to start deployment!** 🎯
