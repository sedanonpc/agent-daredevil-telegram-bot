#!/usr/bin/env python3
"""
Agent Daredevil Installation Helper
==================================
This script helps set up the Agent Daredevil Telegram bot by:
1. Installing required dependencies
2. Creating and configuring the .env file
3. Testing LLM provider connections
4. Providing next steps

Usage:
    python install.py
"""

import os
import sys
import subprocess
import shutil
import asyncio
from pathlib import Path

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color):
    """Print colored text to terminal."""
    print(f"{color}{text}{Colors.ENDC}")

def print_header(text):
    """Print a formatted header."""
    print("\n")
    print_colored("=" * 60, Colors.HEADER)
    print_colored(f" {text}", Colors.HEADER)
    print_colored("=" * 60, Colors.HEADER)

def run_command(command, explanation=None):
    """Run a shell command and return success status."""
    if explanation:
        print_colored(f"\n{explanation}", Colors.BLUE)
    
    print_colored(f"$ {command}", Colors.CYAN)
    
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_colored(result.stdout, Colors.ENDC)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"Error: {e}", Colors.RED)
        print_colored(e.stderr, Colors.RED)
        return False

def install_dependencies():
    """Install required Python dependencies."""
    print_header("Installing Dependencies")
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print_colored("requirements.txt not found!", Colors.RED)
        return False
    
    # Install dependencies
    success = run_command("pip install -r requirements.txt", 
                         "Installing required packages...")
    
    if success:
        print_colored("\n✅ Dependencies installed successfully!", Colors.GREEN)
    else:
        print_colored("\n❌ Failed to install dependencies.", Colors.RED)
    
    return success

def setup_env_file():
    """Set up the .env configuration file."""
    print_header("Setting Up Environment Configuration")
    
    env_path = Path(".env")
    env_example_path = Path("env.example")
    
    # Check if .env already exists
    if env_path.exists():
        print_colored(".env file already exists.", Colors.YELLOW)
        overwrite = input("Overwrite existing .env file? (y/n): ").lower() == 'y'
        if not overwrite:
            print_colored("Keeping existing .env file.", Colors.BLUE)
            return True
    
    # Check if env.example exists
    if not env_example_path.exists():
        print_colored("env.example not found! Cannot create .env file.", Colors.RED)
        return False
    
    # Copy env.example to .env
    shutil.copy(env_example_path, env_path)
    print_colored("Created .env file from template.", Colors.GREEN)
    
    # Ask for configuration values
    print_colored("\nLet's configure your .env file:", Colors.BLUE)
    
    # Telegram configuration
    print_colored("\nTelegram Configuration:", Colors.CYAN)
    print_colored("Get these values from https://my.telegram.org/apps", Colors.YELLOW)
    telegram_api_id = input("Telegram API ID: ").strip()
    telegram_api_hash = input("Telegram API Hash: ").strip()
    telegram_phone = input("Telegram Phone Number (with country code, e.g. +1234567890): ").strip()
    
    # LLM Provider selection
    print_colored("\nLLM Provider Selection:", Colors.CYAN)
    print_colored("1. OpenAI (GPT-4)", Colors.ENDC)
    print_colored("2. Google Gemini (Recommended: gemini-2.5-flash)", Colors.ENDC)
    print_colored("3. Vertex AI (Google Cloud)", Colors.ENDC)
    
    provider_choice = input("Choose provider (1-3, default: 2): ").strip() or "2"
    
    if provider_choice == "1":
        provider = "openai"
        print_colored("\nOpenAI Configuration:", Colors.CYAN)
        print_colored("Get your API key from https://platform.openai.com/api-keys", Colors.YELLOW)
        openai_api_key = input("OpenAI API Key: ").strip()
        openai_model = input("OpenAI Model (default: gpt-4): ").strip() or "gpt-4"
    elif provider_choice == "2":
        provider = "gemini"
        print_colored("\nGoogle Gemini Configuration:", Colors.CYAN)
        print_colored("Get your API key from https://makersuite.google.com/app/apikey", Colors.YELLOW)
        google_api_key = input("Google AI API Key: ").strip()
        gemini_model = input("Gemini Model (default: gemini-2.5-flash): ").strip() or "gemini-2.5-flash"
    elif provider_choice == "3":
        provider = "vertex_ai"
        print_colored("\nVertex AI Configuration:", Colors.CYAN)
        print_colored("Get these from Google Cloud Console", Colors.YELLOW)
        project_id = input("Google Cloud Project ID: ").strip()
        location = input("Google Cloud Location (default: us-central1): ").strip() or "us-central1"
        vertex_model = input("Vertex AI Model (default: google/gemini-2.0-flash-001): ").strip() or "google/gemini-2.0-flash-001"
    else:
        print_colored("Invalid choice. Defaulting to Gemini.", Colors.YELLOW)
        provider = "gemini"
    
    # Update .env file
    with open(env_path, "r") as f:
        env_content = f.readlines()
    
    new_env_content = []
    for line in env_content:
        if line.startswith("TELEGRAM_API_ID="):
            new_env_content.append(f"TELEGRAM_API_ID={telegram_api_id}\n")
        elif line.startswith("TELEGRAM_API_HASH="):
            new_env_content.append(f"TELEGRAM_API_HASH={telegram_api_hash}\n")
        elif line.startswith("TELEGRAM_PHONE_NUMBER="):
            new_env_content.append(f"TELEGRAM_PHONE_NUMBER={telegram_phone}\n")
        elif line.startswith("LLM_PROVIDER="):
            new_env_content.append(f"LLM_PROVIDER={provider}\n")
        elif provider == "openai" and line.startswith("OPENAI_API_KEY="):
            new_env_content.append(f"OPENAI_API_KEY={openai_api_key}\n")
        elif provider == "openai" and line.startswith("OPENAI_MODEL="):
            new_env_content.append(f"OPENAI_MODEL={openai_model}\n")
        elif provider == "gemini" and line.startswith("GOOGLE_AI_API_KEY="):
            new_env_content.append(f"GOOGLE_AI_API_KEY={google_api_key}\n")
        elif provider == "gemini" and line.startswith("GEMINI_MODEL="):
            new_env_content.append(f"GEMINI_MODEL={gemini_model}\n")
        elif provider == "vertex_ai" and line.startswith("GOOGLE_CLOUD_PROJECT_ID="):
            new_env_content.append(f"GOOGLE_CLOUD_PROJECT_ID={project_id}\n")
        elif provider == "vertex_ai" and line.startswith("GOOGLE_CLOUD_LOCATION="):
            new_env_content.append(f"GOOGLE_CLOUD_LOCATION={location}\n")
        elif provider == "vertex_ai" and line.startswith("VERTEX_AI_MODEL="):
            new_env_content.append(f"VERTEX_AI_MODEL={vertex_model}\n")
        else:
            new_env_content.append(line)
    
    with open(env_path, "w") as f:
        f.writelines(new_env_content)
    
    print_colored("\n✅ .env file configured successfully!", Colors.GREEN)
    return True

async def test_llm_provider():
    """Test the configured LLM provider."""
    print_header("Testing LLM Provider")
    
    try:
        # Import here to ensure dependencies are installed first
        from dotenv import load_dotenv
        load_dotenv()
        
        from llm_provider import get_llm_provider
        
        print_colored("Initializing LLM provider...", Colors.BLUE)
        provider = get_llm_provider()
        print_colored(f"✅ Provider initialized: {provider.get_model_name()}", Colors.GREEN)
        
        print_colored("\nTesting with a simple query...", Colors.BLUE)
        response = await provider.generate_response(
            messages=[{"role": "user", "content": "Hello, please respond with a short greeting."}],
            max_tokens=100,
            temperature=0.7
        )
        
        print_colored("\nResponse:", Colors.GREEN)
        print_colored(response, Colors.ENDC)
        
        print_colored("\n✅ LLM provider test successful!", Colors.GREEN)
        return True
        
    except Exception as e:
        print_colored(f"\n❌ Error testing LLM provider: {e}", Colors.RED)
        return False

def show_next_steps():
    """Show next steps to the user."""
    print_header("Next Steps")
    
    print_colored("1. Run the bot:", Colors.CYAN)
    print_colored("   python telegram_bot_rag.py", Colors.YELLOW)
    
    print_colored("\n2. Test the LLM provider:", Colors.CYAN)
    print_colored("   python test_all_providers.py --simple", Colors.YELLOW)
    
    print_colored("\n3. Run comprehensive tests:", Colors.CYAN)
    print_colored("   python test_all_providers.py", Colors.YELLOW)
    
    print_colored("\n4. Switch to Gemini 2.5 Flash:", Colors.CYAN)
    print_colored("   python switch_to_gemini25.py", Colors.YELLOW)
    
    print_colored("\n5. Check current provider:", Colors.CYAN)
    print_colored("   python check_llm_provider.py", Colors.YELLOW)
    
    print_colored("\nFor more information, see:", Colors.CYAN)
    print_colored("- README.md - General overview", Colors.YELLOW)
    print_colored("- LLM_PROVIDER_GUIDE.md - LLM provider documentation", Colors.YELLOW)
    print_colored("- RESPONSE_LENGTH_GUIDE.md - Response length limitation details", Colors.YELLOW)

async def main():
    """Main installation process."""
    print_colored("\n🤖 Agent Daredevil Telegram Bot - Installation Helper", Colors.HEADER)
    print_colored("=" * 60, Colors.HEADER)
    
    # Step 1: Install dependencies
    if not install_dependencies():
        print_colored("\n❌ Installation failed at dependency installation step.", Colors.RED)
        return
    
    # Step 2: Set up .env file
    if not setup_env_file():
        print_colored("\n❌ Installation failed at environment configuration step.", Colors.RED)
        return
    
    # Step 3: Test LLM provider
    if not await test_llm_provider():
        print_colored("\n⚠️ LLM provider test failed. Check your configuration.", Colors.YELLOW)
        print_colored("You can still proceed, but the bot may not work correctly.", Colors.YELLOW)
    
    # Step 4: Show next steps
    show_next_steps()
    
    print_colored("\n✅ Installation completed successfully!", Colors.GREEN)
    print_colored("You're now ready to run Agent Daredevil Telegram Bot.", Colors.GREEN)

if __name__ == "__main__":
    asyncio.run(main()) 