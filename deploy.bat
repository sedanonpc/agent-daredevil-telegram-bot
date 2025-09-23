@echo off
REM ===========================================
REM Agent Daredevil - Deployment Script (Windows)
REM ===========================================

setlocal enabledelayedexpansion

REM Colors (limited support in Windows cmd)
set "INFO=[INFO]"
set "SUCCESS=[SUCCESS]"
set "WARNING=[WARNING]"
set "ERROR=[ERROR]"

REM Function to check if command exists
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% Git is not installed or not in PATH
    exit /b 1
)

REM Function to check environment
:check_environment
echo %INFO% Checking environment...

if not exist ".env" (
    echo %WARNING% .env file not found. Please copy env.example to .env and configure it.
    exit /b 1
)

REM Load environment variables (basic check)
findstr /C:"TELEGRAM_API_ID" .env >nul
if %errorlevel% neq 0 (
    echo %ERROR% TELEGRAM_API_ID not found in .env file
    exit /b 1
)

findstr /C:"TELEGRAM_API_HASH" .env >nul
if %errorlevel% neq 0 (
    echo %ERROR% TELEGRAM_API_HASH not found in .env file
    exit /b 1
)

findstr /C:"TELEGRAM_PHONE_NUMBER" .env >nul
if %errorlevel% neq 0 (
    echo %ERROR% TELEGRAM_PHONE_NUMBER not found in .env file
    exit /b 1
)

findstr /C:"OPENAI_API_KEY" .env >nul
if %errorlevel% neq 0 (
    echo %ERROR% OPENAI_API_KEY not found in .env file
    exit /b 1
)

echo %SUCCESS% Environment check passed
goto :eof

REM Function to deploy with current Railway setup
:deploy_railway_native
echo %INFO% Deploying with Railway native setup...

REM Create native railway.json
(
echo {
echo   "$schema": "https://railway.com/railway.schema.json",
echo   "build": {
echo     "builder": "RAILPACK"
echo   },
echo   "deploy": {
echo     "startCommand": "python telegram_bot_rag.py",
echo     "runtime": "V2",
echo     "numReplicas": 1,
echo     "sleepApplication": false,
echo     "useLegacyStacker": false,
echo     "multiRegionConfig": {
echo       "us-east4-eqdc4a": {
echo         "numReplicas": 1
echo       }
echo     },
echo     "restartPolicyType": "ON_FAILURE",
echo     "restartPolicyMaxRetries": 10
echo   }
echo }
) > railway.json

echo %SUCCESS% Railway native configuration ready
echo %INFO% Push to your Railway-connected repository to deploy
goto :eof

REM Function to deploy with Docker
:deploy_railway_docker
echo %INFO% Deploying with Docker on Railway...

if not exist "Dockerfile" (
    echo %ERROR% Dockerfile not found. Please ensure Dockerfile exists.
    exit /b 1
)

copy railway.docker.json railway.json >nul
echo %SUCCESS% Docker configuration ready
echo %INFO% Push to your Railway-connected repository to deploy
goto :eof

REM Function to deploy locally with Docker
:deploy_local_docker
echo %INFO% Deploying locally with Docker Compose...

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% Docker is not installed or not in PATH
    exit /b 1
)

where docker-compose >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% Docker Compose is not installed or not in PATH
    exit /b 1
)

if not exist "docker-compose.yml" (
    echo %ERROR% docker-compose.yml not found.
    exit /b 1
)

REM Create data directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "temp_voice_files" mkdir temp_voice_files

echo %INFO% Building Docker images...
docker-compose build
if %errorlevel% neq 0 (
    echo %ERROR% Failed to build Docker images
    exit /b 1
)

echo %INFO% Starting services...
docker-compose up -d
if %errorlevel% neq 0 (
    echo %ERROR% Failed to start services
    exit /b 1
)

echo %SUCCESS% Services started successfully!
echo %INFO% View logs with: docker-compose logs -f telegram-bot
echo %INFO% Stop services with: docker-compose down
goto :eof

REM Function to deploy with web interfaces
:deploy_local_with_web
echo %INFO% Deploying locally with web interfaces...

docker-compose --profile web-interfaces up -d
if %errorlevel% neq 0 (
    echo %ERROR% Failed to start services with web interfaces
    exit /b 1
)

echo %SUCCESS% All services started successfully!
echo %INFO% Telegram Bot: Running
echo %INFO% RAG Manager: http://localhost:8501
echo %INFO% Knowledge Visualizer: http://localhost:8502
echo %INFO% Web Messenger: http://localhost:8080
goto :eof

REM Function to show help
:show_help
echo Agent Daredevil Deployment Script (Windows)
echo.
echo Usage: %0 [OPTION]
echo.
echo Options:
echo   railway-native    Deploy with Railway's native Python setup
echo   railway-docker    Deploy with Docker on Railway
echo   local-docker      Deploy locally with Docker Compose
echo   local-web         Deploy locally with web interfaces
echo   check             Check environment configuration
echo   help              Show this help message
echo.
echo Examples:
echo   %0 check              # Check environment
echo   %0 railway-native     # Deploy to Railway (native)
echo   %0 railway-docker     # Deploy to Railway (Docker)
echo   %0 local-docker       # Deploy locally (bot only)
echo   %0 local-web          # Deploy locally (with web UIs)
goto :eof

REM Main script logic
if "%1"=="" goto :show_help
if "%1"=="help" goto :show_help
if "%1"=="--help" goto :show_help
if "%1"=="-h" goto :show_help

if "%1"=="check" (
    call :check_environment
    goto :eof
)

if "%1"=="railway-native" (
    call :check_environment
    call :deploy_railway_native
    goto :eof
)

if "%1"=="railway-docker" (
    call :check_environment
    call :deploy_railway_docker
    goto :eof
)

if "%1"=="local-docker" (
    call :check_environment
    call :deploy_local_docker
    goto :eof
)

if "%1"=="local-web" (
    call :check_environment
    call :deploy_local_with_web
    goto :eof
)

echo %ERROR% Unknown option: %1
call :show_help
exit /b 1
