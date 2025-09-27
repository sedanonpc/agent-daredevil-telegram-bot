#!/usr/bin/env python3
"""
List Available Gemini Models
===========================
List all available Gemini models to find the correct model name.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def list_gemini_models():
    """List all available Gemini models."""
    try:
        import google.generativeai as genai
        
        # Get API key
        api_key = os.getenv('GOOGLE_AI_API_KEY')
        if not api_key:
            print("❌ GOOGLE_AI_API_KEY not found in environment")
            return False
        
        print(f"✅ API Key found: {api_key[:10]}...")
        
        # Configure the API
        genai.configure(api_key=api_key)
        
        # List available models
        print("🔍 Fetching available models...")
        models = genai.list_models()
        
        print("\n📋 Available Gemini Models:")
        print("=" * 50)
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                print(f"✅ {model.name}")
                print(f"   Display Name: {model.display_name}")
                print(f"   Description: {model.description}")
                print()
        
        return True
        
    except ImportError:
        print("❌ google-generativeai package not installed")
        print("Run: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Listing Available Gemini Models")
    print("=" * 40)
    
    success = list_gemini_models()
    
    if not success:
        print("\n❌ Failed to list models")
        exit(1)
