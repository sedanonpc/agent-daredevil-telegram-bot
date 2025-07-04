#!/bin/bash
# Agent Daredevil - Linux/Mac Service Launcher

echo ""
echo "🎯 Agent Daredevil - Linux/Mac Service Launcher"
echo "==============================================="
echo "🤖 Starting Telegram RAG Bot with Memory & Knowledge Management"
echo "==============================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python is not installed or not in PATH"
        echo "Please install Python 3.8+ and make sure it's accessible"
        echo ""
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "❌ Python 3.8+ is required, found version $PYTHON_VERSION"
    echo "Please upgrade your Python installation"
    echo ""
    exit 1
fi

# Check if launcher script exists
if [ ! -f "launch_daredevil.py" ]; then
    echo "❌ launch_daredevil.py not found"
    echo "Please make sure you're running this from the correct directory"
    echo ""
    exit 1
fi

# Make sure the script has execution permissions
chmod +x launch_daredevil.py

# Launch the Python service manager
echo "🚀 Launching Agent Daredevil services..."
echo ""
$PYTHON_CMD launch_daredevil.py

echo ""
echo "👋 Agent Daredevil services have stopped"
echo "Thanks for using Agent Daredevil! 🎯" 