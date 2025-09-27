@echo off
REM ===========================================
REM Agent Daredevil - API-Only Deployment Script
REM ===========================================
REM Optimized for frontend TTS and backend text-only processing

setlocal enabledelayedexpansion

REM Color codes for output
set INFO=[32m[INFO][0m
set SUCCESS=[32m[SUCCESS][0m
set WARNING=[33m[WARNING][0m
set ERROR=[31m[ERROR][0m

echo %INFO% Agent Daredevil API-Only Deployment
echo %INFO% ====================================
echo.

REM Check if we're in the right branch
git branch --show-current | findstr "v2.0_oracle_v1_API_only" >nul
if %errorlevel% neq 0 (
    echo %ERROR% Not on v2.0_oracle_v1_API_only branch
    echo %INFO% Please run: git checkout v2.0_oracle_v1_API_only
    exit /b 1
)

echo %SUCCESS% On correct branch: v2.0_oracle_v1_API_only

REM Check environment file
if not exist "env.api-only.example" (
    echo %ERROR% env.api-only.example not found
    exit /b 1
)

if not exist ".env" (
    echo %WARNING% .env file not found, copying from example
    copy "env.api-only.example" ".env"
    echo %INFO% Please edit .env with your API keys
    pause
)

echo %INFO% Environment configuration checked

REM Check required files
if not exist "railway.json" (
    echo %ERROR% railway.json not found
    exit /b 1
)

if not exist "Dockerfile" (
    echo %ERROR% Dockerfile not found
    exit /b 1
)

echo %SUCCESS% All required files present

REM Check Railway CLI
railway --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% Railway CLI not found
    echo %INFO% Install with: npm install -g @railway/cli
    exit /b 1
)

echo %SUCCESS% Railway CLI available

REM Check if logged in to Railway
railway whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo %WARNING% Not logged in to Railway
    echo %INFO% Logging in...
    railway login
    if %errorlevel% neq 0 (
        echo %ERROR% Failed to login to Railway
        exit /b 1
    )
)

echo %SUCCESS% Railway authentication confirmed

REM Show deployment configuration
echo.
echo %INFO% Deployment Configuration:
echo %INFO% =========================
echo %INFO% Branch: v2.0_oracle_v1_API_only
echo %INFO% Service: Web Messenger (API-Only)
echo %INFO% Voice Processing: Disabled (Frontend TTS)
echo %INFO% RAG System: Enabled
echo %INFO% Memory System: Enabled
echo %INFO% LLM Provider: Gemini 1.5 Flash
echo.

REM Confirm deployment
set /p confirm="Deploy to Railway? (y/N): "
if /i not "%confirm%"=="y" (
    echo %INFO% Deployment cancelled
    exit /b 0
)

echo.
echo %INFO% Starting deployment...

REM Deploy to Railway
railway up --detach
if %errorlevel% neq 0 (
    echo %ERROR% Deployment failed
    exit /b 1
)

echo.
echo %SUCCESS% Deployment successful!
echo.
echo %INFO% API-Only Deployment Summary:
echo %INFO% ============================
echo %INFO% Service: Web Messenger Server
echo %INFO% Endpoints: /chat, /health, /api/stats
echo %INFO% Voice: Frontend TTS (browser SpeechSynthesis)
echo %INFO% Backend: Text-only responses
echo %INFO% Optimization: Reduced bandwidth, faster responses
echo.
echo %INFO% Frontend Integration:
echo %INFO% ====================
echo %INFO% 1. Include frontend-tts-helper.js in your frontend
echo %INFO% 2. Call speakText() with API responses
echo %INFO% 3. No audio file handling needed
echo.
echo %INFO% Test your deployment:
echo %INFO% curl https://your-railway-url.up.railway.app/health
echo.

pause
