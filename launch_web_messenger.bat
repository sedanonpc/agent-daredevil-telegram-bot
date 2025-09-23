@echo off
echo Starting Agent Daredevil Web Messenger Server...
echo.
echo Make sure you have:
echo 1. Python installed
echo 2. Dependencies installed (pip install -r requirements.txt)
echo 3. Environment variables set in .env file
echo.
echo Server will start on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
pause
python launch_web_messenger.py
