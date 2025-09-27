#!/usr/bin/env python3
"""
Test Gemini API Connection
========================
Quick test to verify Gemini API is working with the new API key and model.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test Gemini API connection and model availability."""
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
        
        # Test model availability
        model_name = "gemini-2.5-flash"
        print(f"🧪 Testing model: {model_name}")
        
        # Initialize the model
        model = genai.GenerativeModel(model_name)
        
        # Test a simple generation
        print("📝 Testing simple generation...")
        response = model.generate_content("Hello! Please respond with just 'Agent Daredevil is ready!'")
        
        print(f"✅ Response received: {response.text}")
        print("🎉 Gemini API is working correctly!")
        return True
        
    except ImportError:
        print("❌ google-generativeai package not installed")
        print("Run: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ Error testing Gemini API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Gemini API Connection")
    print("=" * 40)
    
    success = test_gemini_api()
    
    if success:
        print("\n✅ Gemini API test PASSED - Ready for deployment!")
        sys.exit(0)
    else:
        print("\n❌ Gemini API test FAILED - Fix issues before deployment")
        sys.exit(1)
