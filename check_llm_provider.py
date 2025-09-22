#!/usr/bin/env python3
"""
LLM Provider Checker
===================
Simple utility to check which LLM provider and model is currently being used.

Usage:
    python check_llm_provider.py
"""

import os
from dotenv import load_dotenv
from llm_provider import get_llm_provider

def main():
    """Check and display the current LLM provider and model."""
    # Load environment variables
    load_dotenv()
    
    # Get current provider setting
    provider_type = os.getenv('LLM_PROVIDER', 'openai').lower()
    print(f"📋 Current LLM provider setting: {provider_type}")
    
    # Get model name for each provider type
    if provider_type == 'openai':
        model_name = os.getenv('OPENAI_MODEL', 'gpt-4')
    elif provider_type == 'gemini':
        model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
    elif provider_type == 'vertex_ai':
        model_name = os.getenv('VERTEX_AI_MODEL', 'google/gemini-2.0-flash-001')
    else:
        model_name = "unknown"
    
    print(f"📝 Model configured in .env: {model_name}")
    
    # Get actual provider instance
    try:
        provider = get_llm_provider()
        actual_model = provider.get_model_name()
        print(f"✅ Actual model being used: {actual_model}")
        
        if model_name != actual_model:
            print(f"⚠️ Warning: Configured model ({model_name}) doesn't match actual model ({actual_model})")
            print("   This might indicate the .env setting is being overridden or not applied.")
    except Exception as e:
        print(f"❌ Error initializing provider: {e}")
        print("   Check your API keys and provider configuration.")

if __name__ == "__main__":
    main() 