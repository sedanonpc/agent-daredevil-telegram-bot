#!/usr/bin/env python3
"""
Switch to Gemini 2.5 Flash
=========================
This script updates your .env file to use Gemini 2.5 Flash as the LLM provider.

Usage:
    python switch_to_gemini25.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv

def update_env_file():
    """Update .env file to use Gemini 2.5 Flash."""
    # Load current environment
    load_dotenv()
    
    # Check if .env file exists
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found. Creating one from env.example...")
        
        # Try to copy from env.example
        if Path("env.example").exists():
            with open("env.example", "r") as example_file:
                content = example_file.read()
            
            with open(".env", "w") as env_file:
                env_file.write(content)
            
            print("✅ Created .env file from env.example")
        else:
            print("❌ env.example not found. Creating a minimal .env file...")
            with open(".env", "w") as env_file:
                env_file.write("LLM_PROVIDER=gemini\nGEMINI_MODEL=gemini-2.5-flash\n")
            
            print("✅ Created minimal .env file")
    
    # Read current .env file
    with open(".env", "r") as file:
        lines = file.readlines()
    
    # Track what we've updated
    provider_updated = False
    model_updated = False
    
    # Update lines
    new_lines = []
    for line in lines:
        if line.strip().startswith("LLM_PROVIDER="):
            new_lines.append("LLM_PROVIDER=gemini\n")
            provider_updated = True
        elif line.strip().startswith("GEMINI_MODEL="):
            new_lines.append("GEMINI_MODEL=gemini-2.5-flash\n")
            model_updated = True
        else:
            new_lines.append(line)
    
    # Add settings if they weren't in the file
    if not provider_updated:
        new_lines.append("LLM_PROVIDER=gemini\n")
    if not model_updated:
        new_lines.append("GEMINI_MODEL=gemini-2.5-flash\n")
    
    # Write updated content back to .env
    with open(".env", "w") as file:
        file.writelines(new_lines)
    
    print("✅ .env file updated successfully!")
    print("🤖 Now using Gemini 2.5 Flash as the LLM provider")
    
    # Check if Google AI API key is set
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        print("\n⚠️ Warning: GOOGLE_AI_API_KEY is not set in your .env file")
        print("You need to add your Google AI API key to use Gemini:")
        print("1. Get an API key from: https://makersuite.google.com/app/apikey")
        print("2. Add it to your .env file: GOOGLE_AI_API_KEY=your_key_here")

if __name__ == "__main__":
    print("🔄 Switching to Gemini 2.5 Flash...")
    update_env_file()
    print("\n✅ Done! Restart your bot for changes to take effect.") 