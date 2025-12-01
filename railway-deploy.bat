@echo off
REM ===========================================
REM Railway Docker Deployment Script
REM ===========================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   AGENT DAREDEVIL - RAILWAY DEPLOYMENT
echo ========================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo Please copy env.example to .env and configure your environment variables.
    pause
    exit /b 1
)

REM Check required environment variables
echo [INFO] Checking environment configuration...

findstr /C:"TELEGRAM_API_ID" .env >nul
if %errorlevel% neq 0 (
    echo [ERROR] TELEGRAM_API_ID not found in .env file
    pause
    exit /b 1
)

findstr /C:"TELEGRAM_API_HASH" .env >nul
if %errorlevel% neq 0 (
    echo [ERROR] TELEGRAM_API_HASH not found in .env file
    pause
    exit /b 1
)

findstr /C:"OPENAI_API_KEY" .env >nul
if %errorlevel% neq 0 (
    echo [ERROR] OPENAI_API_KEY not found in .env file
    pause
    exit /b 1
)

echo [SUCCESS] Environment configuration verified

REM Check if Dockerfile exists
if not exist "Dockerfile" (
    echo [ERROR] Dockerfile not found!
    echo Please ensure Dockerfile exists in the current directory.
    pause
    exit /b 1
)

echo [INFO] Docker configuration files verified

REM Verify railway.json exists
if not exist "railway.json" (
    echo [ERROR] railway.json not found!
    echo Please ensure railway.json exists in the current directory.
    pause
    exit /b 1
)

echo [SUCCESS] Railway configuration verified

REM Check if git is available
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH
    echo Please install Git to deploy to Railway.
    pause
    exit /b 1
)

REM Check git status
echo [INFO] Checking git status...
git status >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Not in a git repository or git repository not initialized
    echo Please initialize a git repository and connect it to Railway.
    pause
    exit /b 1
)

REM Add all files to git
echo [INFO] Adding files to git...
git add .

REM Check if there are changes to commit
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo [WARNING] No changes to commit
    echo Your repository is already up to date.
) else (
    echo [INFO] Committing changes...
    git commit -m "Deploy with Docker configuration for production"
    
    echo [INFO] Pushing to Railway...
    git push origin main
    
    if %errorlevel% equ 0 (
        echo.
        echo [SUCCESS] Deployment initiated successfully!
        echo.
        echo [INFO] Railway will now:
        echo   - Build your Docker image
        echo   - Deploy your application
        echo   - Start your Telegram bot
        echo.
        echo [INFO] Monitor your deployment at: https://railway.app
        echo.
    ) else (
        echo [ERROR] Failed to push to Railway
        echo Please check your git configuration and Railway connection.
    )
)

echo.
echo [INFO] Deployment process completed
echo Press any key to exit...
pause >nul
