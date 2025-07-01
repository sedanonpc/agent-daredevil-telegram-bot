#!/usr/bin/env python3
"""
Agent Daredevil Bot Setup Script
Helps users get started with the Telegram bot quickly
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def print_banner():
    """Print setup banner"""
    print("🤖" + "="*60 + "🤖")
    print("  🔥 AGENT DAREDEVIL - TELEGRAM BOT SETUP 🔥")
    print("🤖" + "="*60 + "🤖")
    print()

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher required!")
        print(f"   Current version: {sys.version}")
        print("   Please upgrade Python and try again.")
        return False
    print(f"✅ Python {sys.version.split()[0]} - Compatible")
    return True

def check_pip():
    """Check if pip is available"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        print("✅ pip - Available")
        return True
    except subprocess.CalledProcessError:
        print("❌ pip not found!")
        print("   Please install pip and try again.")
        return False

def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_env_file():
    """Create .env file from template"""
    env_path = Path(".env")
    template_path = Path("env.example")
    
    if env_path.exists():
        print("⚠️  .env file already exists")
        response = input("   Do you want to overwrite it? (y/N): ").strip().lower()
        if response != 'y':
            print("   Keeping existing .env file")
            return True
    
    if template_path.exists():
        shutil.copy(template_path, env_path)
        print("✅ Created .env file from template")
        print("📝 Please edit .env with your credentials:")
        print("   - Get Telegram API from: https://my.telegram.org/apps")
        print("   - Get OpenAI API from: https://platform.openai.com/api-keys")
        return True
    else:
        print("❌ env.example template not found!")
        return False

def check_credentials():
    """Check if .env file has been configured"""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    missing = []
    if 'your_api_id_here' in content:
        missing.append("TELEGRAM_API_ID")
    if 'your_api_hash_here' in content:
        missing.append("TELEGRAM_API_HASH")
    if '+1234567890' in content:
        missing.append("TELEGRAM_PHONE_NUMBER")
    if 'sk-your-openai-api-key-here' in content:
        missing.append("OPENAI_API_KEY")
    
    if missing:
        print("⚠️  Please configure the following in .env:")
        for item in missing:
            print(f"   - {item}")
        return False
    
    print("✅ .env file configured")
    return True

def run_initial_test():
    """Run a quick test to verify setup"""
    print("\n🧪 Running initial test...")
    try:
        # Test imports
        import telethon
        import openai
        import streamlit
        import chromadb
        print("✅ All required modules can be imported")
        
        # Test environment loading
        from dotenv import load_dotenv
        load_dotenv()
        
        if os.getenv('TELEGRAM_API_ID'):
            print("✅ Environment variables loaded")
        else:
            print("⚠️  Environment variables not found")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def show_next_steps():
    """Show what to do next"""
    print("\n🎯 NEXT STEPS:")
    print("="*50)
    print("1. 🔐 Configure your .env file with API credentials")
    print("2. 🤖 Run basic bot:        python telegram_bot.py")
    print("3. 🧠 Run advanced bot:     python telegram_bot_rag.py")
    print("4. 🌐 Run knowledge base:   streamlit run rag_manager.py")
    print("5. 🚀 Run everything:       python launcher.py")
    print()
    print("📚 Documentation: https://github.com/your-username/agent-daredevil-telegram-bot")
    print("🐛 Issues: Report bugs on GitHub Issues")
    print()

def main():
    """Main setup function"""
    print_banner()
    
    # System checks
    print("🔍 Checking system requirements...")
    if not check_python_version():
        sys.exit(1)
    
    if not check_pip():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup environment
    print("\n⚙️  Setting up environment...")
    if not create_env_file():
        sys.exit(1)
    
    # Run tests
    if not run_initial_test():
        print("⚠️  Some tests failed, but you can still proceed")
    
    # Final instructions
    print("\n🎉 SETUP COMPLETE!")
    print("="*50)
    
    if check_credentials():
        print("✅ Ready to run! Your bot is configured.")
    else:
        print("📝 Almost ready! Please configure your .env file.")
    
    show_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user.")
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        print("Please check the logs and try again.")
        sys.exit(1) 