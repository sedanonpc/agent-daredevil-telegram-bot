#!/usr/bin/env python3
"""
Gemini API Installation Script
==============================
This script helps install and configure Gemini API support for Agent Daredevil.

Author: Agent Daredevil
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Colors for output formatting
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(message, color=Colors.ENDC):
    """Print message with color."""
    print(f"{color}{message}{Colors.ENDC}")

def run_command(cmd, description):
    """Run a command and return success status."""
    try:
        print_colored(f"📦 {description}...", Colors.OKCYAN)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print_colored(f"✅ {description} completed successfully", Colors.OKGREEN)
            return True
        else:
            print_colored(f"❌ {description} failed", Colors.FAIL)
            print_colored(f"Error: {result.stderr}", Colors.FAIL)
            return False
    except Exception as e:
        print_colored(f"❌ Error running command: {e}", Colors.FAIL)
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print_colored(f"✅ Python {version.major}.{version.minor}.{version.micro} detected", Colors.OKGREEN)
        return True
    else:
        print_colored(f"❌ Python {version.major}.{version.minor}.{version.micro} detected. Need Python 3.8+", Colors.FAIL)
        return False

def install_dependencies():
    """Install Gemini API dependencies."""
    print_colored("\n🔧 Installing Gemini API Dependencies", Colors.HEADER)
    print_colored("=" * 50, Colors.HEADER)
    
    dependencies = [
        "google-generativeai>=0.8.0",
        "google-auth>=2.23.0", 
        "google-auth-oauthlib>=1.0.0",
        "google-auth-httplib2>=0.1.0",
        "google-cloud-aiplatform>=1.38.0"
    ]
    
    # Install each dependency
    for dep in dependencies:
        success = run_command(f"pip install {dep}", f"Installing {dep}")
        if not success:
            return False
    
    return True

def setup_env_file():
    """Help user setup .env file with Gemini configuration."""
    print_colored("\n⚙️ Environment Configuration", Colors.HEADER)
    print_colored("=" * 50, Colors.HEADER)
    
    env_path = Path(".env")
    env_example_path = Path("env.example")
    
    # Check if .env exists
    if not env_path.exists():
        if env_example_path.exists():
            print_colored("📝 Creating .env file from template...", Colors.OKCYAN)
            shutil.copy(env_example_path, env_path)
            print_colored("✅ .env file created", Colors.OKGREEN)
        else:
            print_colored("❌ env.example not found. Please create .env manually", Colors.FAIL)
            return False
    
    # Check current LLM provider setting
    with open(env_path, 'r') as f:
        content = f.read()
    
    current_provider = "openai"  # default
    if "LLM_PROVIDER=" in content:
        for line in content.split('\n'):
            if line.startswith('LLM_PROVIDER='):
                current_provider = line.split('=')[1].strip()
                break
    
    print_colored(f"Current LLM provider: {current_provider}", Colors.OKBLUE)
    
    # Ask user what they want to do
    print_colored("\nWhat would you like to do?", Colors.OKBLUE)
    print_colored("1. Keep current settings", Colors.ENDC)
    print_colored("2. Switch to Gemini (Google AI)", Colors.ENDC)
    print_colored("3. Switch to Vertex AI", Colors.ENDC)
    print_colored("4. Show API key setup instructions", Colors.ENDC)
    
    try:
        choice = input(f"\n{Colors.OKCYAN}Enter your choice (1-4): {Colors.ENDC}").strip()
        
        if choice == "1":
            print_colored("👍 Keeping current settings", Colors.OKGREEN)
        elif choice == "2":
            setup_gemini_provider()
        elif choice == "3":
            setup_vertex_ai_provider()
        elif choice == "4":
            show_api_setup_instructions()
        else:
            print_colored("Invalid choice. Keeping current settings.", Colors.WARNING)
    except KeyboardInterrupt:
        print_colored("\n🛑 Setup cancelled by user", Colors.WARNING)
        return False
    
    return True

def setup_gemini_provider():
    """Setup Google AI (Gemini) provider."""
    print_colored("\n🤖 Setting up Google AI (Gemini)", Colors.HEADER)
    
    # Ask for API key
    api_key = input(f"{Colors.OKCYAN}Enter your Google AI API key (or press Enter to skip): {Colors.ENDC}").strip()
    
    # Update .env file
    env_path = Path(".env")
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update lines
    new_lines = []
    for line in lines:
        if line.startswith('LLM_PROVIDER='):
            new_lines.append('LLM_PROVIDER=gemini\n')
        elif line.startswith('GOOGLE_AI_API_KEY=') and api_key:
            new_lines.append(f'GOOGLE_AI_API_KEY={api_key}\n')
        else:
            new_lines.append(line)
    
    # Write back to file
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print_colored("✅ Gemini provider configured", Colors.OKGREEN)
    
    if not api_key:
        print_colored("\n📋 To complete setup, add your Google AI API key:", Colors.WARNING)
        print_colored("1. Visit: https://makersuite.google.com/app/apikey", Colors.ENDC)
        print_colored("2. Create an API key", Colors.ENDC)
        print_colored("3. Add to .env: GOOGLE_AI_API_KEY=your_key_here", Colors.ENDC)

def setup_vertex_ai_provider():
    """Setup Vertex AI provider."""
    print_colored("\n☁️ Setting up Vertex AI", Colors.HEADER)
    
    # Ask for project ID
    project_id = input(f"{Colors.OKCYAN}Enter your Google Cloud Project ID (or press Enter to skip): {Colors.ENDC}").strip()
    
    # Update .env file
    env_path = Path(".env")
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update lines
    new_lines = []
    for line in lines:
        if line.startswith('LLM_PROVIDER='):
            new_lines.append('LLM_PROVIDER=vertex_ai\n')
        elif line.startswith('GOOGLE_CLOUD_PROJECT_ID=') and project_id:
            new_lines.append(f'GOOGLE_CLOUD_PROJECT_ID={project_id}\n')
        else:
            new_lines.append(line)
    
    # Write back to file
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print_colored("✅ Vertex AI provider configured", Colors.OKGREEN)
    
    if not project_id:
        print_colored("\n📋 To complete setup:", Colors.WARNING)
        print_colored("1. Create GCP project: https://console.cloud.google.com/", Colors.ENDC)
        print_colored("2. Enable Vertex AI API", Colors.ENDC)
        print_colored("3. Set up authentication: gcloud auth application-default login", Colors.ENDC)
        print_colored("4. Add to .env: GOOGLE_CLOUD_PROJECT_ID=your_project_id", Colors.ENDC)

def show_api_setup_instructions():
    """Show detailed API setup instructions."""
    print_colored("\n📋 API Setup Instructions", Colors.HEADER)
    print_colored("=" * 60, Colors.HEADER)
    
    print_colored("\n🔑 OpenAI Setup:", Colors.OKGREEN)
    print_colored("1. Visit: https://platform.openai.com/api-keys", Colors.ENDC)
    print_colored("2. Create a new API key", Colors.ENDC)
    print_colored("3. Add to .env: OPENAI_API_KEY=sk-your-key-here", Colors.ENDC)
    print_colored("4. Set provider: LLM_PROVIDER=openai", Colors.ENDC)
    
    print_colored("\n🤖 Google AI (Gemini) Setup:", Colors.OKGREEN)
    print_colored("1. Visit: https://makersuite.google.com/app/apikey", Colors.ENDC)
    print_colored("2. Create a new API key", Colors.ENDC)
    print_colored("3. Add to .env: GOOGLE_AI_API_KEY=your-key-here", Colors.ENDC)
    print_colored("4. Set provider: LLM_PROVIDER=gemini", Colors.ENDC)
    
    print_colored("\n☁️ Vertex AI Setup:", Colors.OKGREEN)
    print_colored("1. Create GCP project: https://console.cloud.google.com/", Colors.ENDC)
    print_colored("2. Enable Vertex AI API", Colors.ENDC)
    print_colored("3. Set up authentication:", Colors.ENDC)
    print_colored("   Option A: gcloud auth application-default login", Colors.ENDC)
    print_colored("   Option B: Service account JSON key", Colors.ENDC)
    print_colored("4. Add to .env: GOOGLE_CLOUD_PROJECT_ID=your-project-id", Colors.ENDC)
    print_colored("5. Set provider: LLM_PROVIDER=vertex_ai", Colors.ENDC)

def test_installation():
    """Test if the installation works."""
    print_colored("\n🧪 Testing Installation", Colors.HEADER)
    print_colored("=" * 30, Colors.HEADER)
    
    try:
        # Test imports
        print_colored("📦 Testing imports...", Colors.OKCYAN)
        
        import google.generativeai as genai
        print_colored("✅ google-generativeai imported successfully", Colors.OKGREEN)
        
        from google.auth import default
        print_colored("✅ google-auth imported successfully", Colors.OKGREEN)
        
        # Test LLM provider
        print_colored("🤖 Testing LLM provider...", Colors.OKCYAN)
        
        try:
            from llm_provider import LLMProviderFactory
            print_colored("✅ LLM provider system available", Colors.OKGREEN)
            
            # Check configured providers
            from dotenv import load_dotenv
            load_dotenv()
            
            available_providers = []
            if os.getenv('OPENAI_API_KEY'):
                available_providers.append('openai')
            if os.getenv('GOOGLE_AI_API_KEY'):
                available_providers.append('gemini')
            if os.getenv('GOOGLE_CLOUD_PROJECT_ID'):
                available_providers.append('vertex_ai')
            
            if available_providers:
                print_colored(f"✅ Available providers: {', '.join(available_providers)}", Colors.OKGREEN)
            else:
                print_colored("⚠️ No providers configured. Please add API keys to .env", Colors.WARNING)
                
        except ImportError as e:
            print_colored(f"❌ LLM provider system not found: {e}", Colors.FAIL)
            print_colored("Make sure llm_provider.py is in the current directory", Colors.WARNING)
            
        return True
        
    except ImportError as e:
        print_colored(f"❌ Import test failed: {e}", Colors.FAIL)
        return False

def main():
    """Main installation function."""
    print_colored("🤖 Agent Daredevil - Gemini API Setup", Colors.HEADER)
    print_colored("=" * 50, Colors.HEADER)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print_colored("\n❌ Installation failed. Please check the errors above.", Colors.FAIL)
        sys.exit(1)
    
    # Setup environment
    if not setup_env_file():
        print_colored("\n⚠️ Environment setup incomplete. You may need to configure manually.", Colors.WARNING)
    
    # Test installation
    test_installation()
    
    # Final instructions
    print_colored("\n🎉 Installation Complete!", Colors.OKGREEN)
    print_colored("=" * 30, Colors.OKGREEN)
    
    print_colored("\n📚 Next Steps:", Colors.OKBLUE)
    print_colored("1. Configure your API keys in .env file", Colors.ENDC)
    print_colored("2. Test providers: python test_all_providers.py", Colors.ENDC)
    print_colored("3. Start your bot: python telegram_bot_rag.py", Colors.ENDC)
    print_colored("4. Read the guide: LLM_PROVIDER_GUIDE.md", Colors.ENDC)
    
    print_colored("\n💡 Tips:", Colors.OKCYAN)
    print_colored("- Switch providers anytime by changing LLM_PROVIDER in .env", Colors.ENDC)
    print_colored("- Gemini has a generous free tier for testing", Colors.ENDC)
    print_colored("- Use different providers for different tasks", Colors.ENDC)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n👋 Installation cancelled by user", Colors.WARNING)
    except Exception as e:
        print_colored(f"\n❌ Unexpected error: {e}", Colors.FAIL) 