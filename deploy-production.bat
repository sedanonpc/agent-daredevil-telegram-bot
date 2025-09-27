@echo off
REM ===========================================
REM Agent Daredevil - Production Deployment Script (Windows)
REM ===========================================
REM Automated deployment script for Railway production environment

echo 🎯 Agent Daredevil - Production Deployment
echo ==========================================

REM Check if required tools are installed
echo [INFO] Checking dependencies...

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

where railway >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Railway CLI is not installed. Please install it first:
    echo npm install -g @railway/cli
    exit /b 1
)

echo [SUCCESS] All dependencies are installed

REM Check if .env file exists
echo [INFO] Checking environment configuration...

if not exist .env (
    echo [ERROR] .env file not found. Please create one based on env.example
    exit /b 1
)

echo [SUCCESS] Environment configuration found

REM Build Docker image locally for testing
echo [INFO] Building Docker image locally...

docker build -t agent-daredevil:latest .
if %errorlevel% neq 0 (
    echo [ERROR] Failed to build Docker image
    exit /b 1
)

echo [SUCCESS] Docker image built successfully

REM Test Docker container locally
echo [INFO] Testing Docker container locally...

REM Start container in background
docker run -d --name agent-daredevil-test --env-file .env -p 8000:8000 agent-daredevil:latest
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start test container
    exit /b 1
)

REM Wait for container to start
timeout /t 10 /nobreak >nul

REM Test health endpoint
curl -f http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Container health check failed
    docker logs agent-daredevil-test
    docker stop agent-daredevil-test
    docker rm agent-daredevil-test
    exit /b 1
)

echo [SUCCESS] Container health check passed

REM Clean up test container
docker stop agent-daredevil-test
docker rm agent-daredevil-test

echo [SUCCESS] Local Docker test completed successfully

REM Deploy to Railway
echo [INFO] Deploying to Railway...

railway whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Not logged in to Railway. Please run: railway login
    exit /b 1
)

railway up --detach
if %errorlevel% neq 0 (
    echo [ERROR] Failed to deploy to Railway
    exit /b 1
)

echo [SUCCESS] Deployment to Railway completed successfully

REM Verify deployment
echo [INFO] Verifying deployment...

for /f "tokens=*" %%i in ('railway domain') do set service_url=%%i

if "%service_url%"=="" (
    echo [WARNING] Could not get service URL from Railway
    goto :end
)

echo [INFO] Service URL: https://%service_url%

REM Test health endpoint
curl -f "https://%service_url%/health" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Health check failed, but deployment may still be starting up
    echo [INFO] Check Railway dashboard for deployment status
) else (
    echo [SUCCESS] Production deployment health check passed
    echo [SUCCESS] 🎯 Agent Daredevil is now live at: https://%service_url%
)

:end
echo.
echo [SUCCESS] 🎯 Production deployment completed successfully!
echo.
echo Next steps:
echo 1. Monitor the deployment in Railway dashboard
echo 2. Check logs: railway logs
echo 3. Test the web interface and Telegram bot
echo 4. Set up monitoring and alerts
echo.
pause
