#!/usr/bin/env python3
"""
Installation and Setup Script for Telegram Bot & RAG Manager
============================================================
This script helps users set up the project dependencies and configuration.
"""

import subprocess
import sys
import os
import json
from pathlib import Path

class Colors:
    """ANSI color codes for console output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def safe_print(message):
    """Print function that handles Unicode encoding issues on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback to ASCII-safe version
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)

def print_banner():
    """Print installation banner"""
    banner = f"""
{Colors.HEADER}{'='*70}
{Colors.BOLD}🛠️  TELEGRAM BOT & RAG MANAGER INSTALLER  🛠️{Colors.ENDC}
{Colors.HEADER}{'='*70}{Colors.ENDC}

{Colors.OKCYAN}This installer will:{Colors.ENDC}
{Colors.OKGREEN}✓{Colors.ENDC} Check Python version compatibility
{Colors.OKGREEN}✓{Colors.ENDC} Install required Python packages
{Colors.OKGREEN}✓{Colors.ENDC} Guide you through credential setup
{Colors.OKGREEN}✓{Colors.ENDC} Verify installation completeness

{Colors.WARNING}📋 Prerequisites:{Colors.ENDC}
- Python 3.8 or higher
- Internet connection for package installation
- Telegram API credentials (we'll help you get these)
- OpenAI API key (we'll help you get this too)

{Colors.HEADER}{'='*70}{Colors.ENDC}
"""
    safe_print(banner)

def check_python_version():
    """Check if Python version is compatible"""
    safe_print(f"{Colors.OKCYAN}🐍 Checking Python version...{Colors.ENDC}")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        safe_print(f"{Colors.FAIL}❌ Python 3.8+ required, found {version.major}.{version.minor}{Colors.ENDC}")
        safe_print(f"{Colors.WARNING}Please upgrade Python and try again.{Colors.ENDC}")
        return False
    
    safe_print(f"{Colors.OKGREEN}✅ Python {version.major}.{version.minor}.{version.micro} is compatible{Colors.ENDC}")
    return True

def install_packages():
    """Install required packages"""
    safe_print(f"\n{Colors.OKCYAN}📦 Installing required packages...{Colors.ENDC}")
    
    try:
        # Check if requirements.txt exists
        if not Path("requirements.txt").exists():
            safe_print(f"{Colors.FAIL}❌ requirements.txt not found{Colors.ENDC}")
            return False
        
        # Install packages
        safe_print(f"{Colors.WARNING}This may take a few minutes...{Colors.ENDC}")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            safe_print(f"{Colors.OKGREEN}✅ All packages installed successfully{Colors.ENDC}")
            return True
        else:
            safe_print(f"{Colors.FAIL}❌ Package installation failed:{Colors.ENDC}")
            safe_print(result.stderr)
            return False
            
    except Exception as e:
        safe_print(f"{Colors.FAIL}❌ Installation error: {e}{Colors.ENDC}")
        return False

def guide_credential_setup():
    """Guide user through credential setup"""
    safe_print(f"\n{Colors.OKCYAN}🔑 Credential Setup Guide{Colors.ENDC}")
    safe_print(f"{Colors.HEADER}{'='*40}{Colors.ENDC}")
    
    # Telegram API Setup
    safe_print(f"\n{Colors.OKBLUE}📱 Telegram API Setup:{Colors.ENDC}")
    safe_print("1. Go to: https://my.telegram.org/apps")
    safe_print("2. Log in with your Telegram account")
    safe_print("3. Create a new application")
    safe_print("4. Note down your API_ID and API_HASH")
    
    # OpenAI API Setup
    safe_print(f"\n{Colors.OKBLUE}🤖 OpenAI API Setup:{Colors.ENDC}")
    safe_print("1. Go to: https://platform.openai.com/api-keys")
    safe_print("2. Create an account or log in")
    safe_print("3. Create a new API key")
    safe_print("4. Note down your API key (starts with 'sk-')")
    
    # Configuration Instructions
    safe_print(f"\n{Colors.WARNING}⚙️  Configuration Instructions:{Colors.ENDC}")
    safe_print("After getting your credentials, update these files:")
    safe_print("")
    safe_print(f"{Colors.OKGREEN}telegram_bot.py:{Colors.ENDC}")
    safe_print("- API_ID = your_api_id  # (number)")
    safe_print("- API_HASH = 'your_api_hash'  # (string)")
    safe_print("- PHONE_NUMBER = '+1234567890'  # (your phone)")
    safe_print("")
    safe_print(f"{Colors.OKGREEN}rag_manager.py:{Colors.ENDC}")
    safe_print("- OPENAI_API_KEY = 'sk-your-key-here'")
    
    return True

def check_configuration():
    """Check if configuration files are properly set up"""
    safe_print(f"\n{Colors.OKCYAN}🔍 Checking configuration...{Colors.ENDC}")
    
    issues = []
    
    # Check telegram_bot.py
    try:
        with open('telegram_bot.py', 'r') as f:
            content = f.read()
            if 'YOUR_API_ID' in content or 'API_ID = 25986520' in content:
                issues.append("telegram_bot.py: API_ID needs to be updated")
            if 'YOUR_API_HASH' in content:
                issues.append("telegram_bot.py: API_HASH needs to be updated")
            if 'YOUR_PHONE_NUMBER' in content:
                issues.append("telegram_bot.py: PHONE_NUMBER needs to be updated")
    except FileNotFoundError:
        issues.append("telegram_bot.py: File not found")
    
    # Check rag_manager.py
    try:
        with open('rag_manager.py', 'r') as f:
            content = f.read()
            if 'YOUR_OPENAI_API_KEY' in content:
                issues.append("rag_manager.py: OPENAI_API_KEY needs to be updated")
    except FileNotFoundError:
        issues.append("rag_manager.py: File not found")
    
    if issues:
        safe_print(f"{Colors.WARNING}⚠️  Configuration issues found:{Colors.ENDC}")
        for issue in issues:
            safe_print(f"   - {issue}")
        safe_print(f"\n{Colors.WARNING}Please update your credentials before running the bot.{Colors.ENDC}")
        return False
    else:
        safe_print(f"{Colors.OKGREEN}✅ Configuration looks good!{Colors.ENDC}")
        return True

def create_example_config():
    """Create example configuration file"""
    safe_print(f"\n{Colors.OKCYAN}📝 Creating example configuration...{Colors.ENDC}")
    
    config_example = {
        "telegram": {
            "api_id": "YOUR_API_ID",
            "api_hash": "YOUR_API_HASH", 
            "phone_number": "YOUR_PHONE_NUMBER"
        },
        "openai": {
            "api_key": "YOUR_OPENAI_API_KEY"
        },
        "setup_instructions": {
            "telegram_api": "https://my.telegram.org/apps",
            "openai_api": "https://platform.openai.com/api-keys"
        }
    }
    
    try:
        with open('config_example.json', 'w') as f:
            json.dump(config_example, f, indent=2)
        safe_print(f"{Colors.OKGREEN}✅ Created config_example.json{Colors.ENDC}")
        return True
    except Exception as e:
        safe_print(f"{Colors.FAIL}❌ Failed to create config example: {e}{Colors.ENDC}")
        return False

def final_instructions():
    """Show final instructions"""
    safe_print(f"\n{Colors.HEADER}🎉 Installation Complete!{Colors.ENDC}")
    safe_print(f"{Colors.HEADER}{'='*40}{Colors.ENDC}")
    
    safe_print(f"\n{Colors.OKGREEN}✅ Next Steps:{Colors.ENDC}")
    safe_print("1. Update your credentials in the configuration files")
    safe_print("2. Run the launcher: python launcher.py")
    safe_print("3. Or use the convenience scripts:")
    safe_print("   - Windows: run.bat")
    safe_print("   - Linux/Mac: ./run.sh")
    
    safe_print(f"\n{Colors.OKCYAN}📚 Documentation:{Colors.ENDC}")
    safe_print("- Full setup guide: README.md")
    safe_print("- Example config: config_example.json")
    
    safe_print(f"\n{Colors.WARNING}💡 Tips:{Colors.ENDC}")
    safe_print("- Keep the launcher console open to monitor both services")
    safe_print("- Access RAG Manager at: http://localhost:8501")
    safe_print("- Use Ctrl+C to stop all services")
    
    safe_print(f"\n{Colors.OKGREEN}🚀 Ready to launch!{Colors.ENDC}")

def main():
    """Main installation function"""
    print_banner()
    
    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Step 2: Install packages
    if not install_packages():
        safe_print(f"\n{Colors.FAIL}❌ Installation failed. Please check the errors above.{Colors.ENDC}")
        sys.exit(1)
    
    # Step 3: Guide credential setup
    guide_credential_setup()
    
    # Step 4: Create example config
    create_example_config()
    
    # Step 5: Check current configuration
    check_configuration()
    
    # Step 6: Final instructions
    final_instructions()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        safe_print(f"\n{Colors.WARNING}Installation cancelled by user.{Colors.ENDC}")
    except Exception as e:
        safe_print(f"\n{Colors.FAIL}❌ Unexpected error: {e}{Colors.ENDC}")
        sys.exit(1) 