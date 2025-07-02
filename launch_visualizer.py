#!/usr/bin/env python3
"""
RAG Knowledge Base Visualizer Launcher
=====================================

Simple launcher script for the RAG Knowledge Visualizer.
This script will check dependencies and launch the Streamlit app.
"""

import sys
import subprocess
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        "streamlit",
        "streamlit_echarts", 
        "pyecharts",
        "networkx",
        "chromadb",
        "langchain",
        "pandas",
        "numpy"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies():
    """Install missing dependencies"""
    print("🔧 Installing required dependencies...")
    
    # Check if requirements_visualizer.txt exists
    req_file = Path("requirements_visualizer.txt")
    if req_file.exists():
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements_visualizer.txt"
        ])
    else:
        # Fallback to individual installations
        essential_packages = [
            "streamlit>=1.28.0",
            "streamlit-echarts>=0.4.0",
            "pyecharts>=1.9.1",
            "networkx>=3.1",
            "chromadb>=0.4.15",
            "langchain>=0.0.330",
            "pandas>=2.1.3",
            "numpy>=1.25.2"
        ]
        
        for package in essential_packages:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def launch_visualizer():
    """Launch the RAG Knowledge Visualizer"""
    print("🚀 Launching RAG Knowledge Visualizer...")
    
    # Check if the visualizer file exists
    visualizer_file = Path("rag_knowledge_visualizer.py")
    if not visualizer_file.exists():
        print("❌ Error: rag_knowledge_visualizer.py not found!")
        print("Please make sure you're running this script from the correct directory.")
        return False
    
    # Launch with Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "rag_knowledge_visualizer.py",
            "--server.headless", "false",
            "--browser.gatherUsageStats", "false"
        ])
        return True
    except KeyboardInterrupt:
        print("\n👋 Visualizer stopped by user")
        return True
    except Exception as e:
        print(f"❌ Error launching visualizer: {e}")
        return False

def main():
    """Main launcher function"""
    print("🕸️ RAG Knowledge Base Visualizer Launcher")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("rag_manager.py").exists():
        print("❌ Error: rag_manager.py not found!")
        print("Please run this script from the same directory as your RAG manager.")
        sys.exit(1)
    
    # Check dependencies
    print("🔍 Checking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print(f"⚠️  Missing dependencies: {', '.join(missing)}")
        
        response = input("\nWould you like to install missing dependencies? (y/n): ").lower()
        if response in ['y', 'yes']:
            try:
                install_dependencies()
                print("✅ Dependencies installed successfully!")
            except Exception as e:
                print(f"❌ Error installing dependencies: {e}")
                print("\nPlease install manually using:")
                print("pip install -r requirements_visualizer.txt")
                sys.exit(1)
        else:
            print("❌ Cannot proceed without required dependencies.")
            print("\nTo install manually:")
            print("pip install -r requirements_visualizer.txt")
            sys.exit(1)
    else:
        print("✅ All dependencies are installed!")
    
    # Launch the visualizer
    print("\n🌟 Starting the RAG Knowledge Visualizer...")
    print("📱 The app will open in your default browser")
    print("🔗 Default URL: http://localhost:8501")
    print("\n📝 Usage Tips:")
    print("   • Click nodes to see details")
    print("   • Drag nodes to rearrange the network")
    print("   • Use sidebar controls to adjust layout")
    print("   • Switch between tabs for different views")
    print("\n⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    success = launch_visualizer()
    
    if not success:
        print("\n❌ Failed to launch visualizer.")
        print("\nTry running manually with:")
        print("streamlit run rag_knowledge_visualizer.py")

if __name__ == "__main__":
    main() 