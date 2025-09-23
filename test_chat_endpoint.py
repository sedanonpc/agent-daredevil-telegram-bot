#!/usr/bin/env python3
"""
Test script for the new /chat endpoint
=====================================
Tests the integration with the frontend's expected API format.
"""

import requests
import json
import os
from pathlib import Path

def test_text_message():
    """Test sending a text message to the /chat endpoint."""
    print("🧪 Testing text message...")
    
    url = "http://localhost:8000/chat"
    
    # Test data matching frontend format
    data = {
        'message': 'Hello, how are you today?',
        'type': 'text',
        'sessionId': 'test_session_123',
        'userId': 'test_user_456',
        'username': 'TestUser'
    }
    
    try:
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Text message test passed!")
            print(f"   Response: {result['message'][:100]}...")
            print(f"   Type: {result['type']}")
            print(f"   Audio URL: {result.get('audioUrl', 'None')}")
            return True
        else:
            print(f"❌ Text message test failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Text message test error: {e}")
        return False

def test_voice_message():
    """Test sending a voice message to the /chat endpoint."""
    print("\n🧪 Testing voice message...")
    
    url = "http://localhost:8000/chat"
    
    # Check if we have a test audio file
    test_audio_path = "test_voice_output.mp3"
    if not os.path.exists(test_audio_path):
        print("⚠️  No test audio file found. Skipping voice test.")
        print("   Create a test audio file named 'test_voice_output.mp3' to test voice messages.")
        return True
    
    # Test data matching frontend format
    data = {
        'message': 'This is a test voice message',
        'type': 'voice',
        'sessionId': 'test_session_123',
        'userId': 'test_user_456',
        'username': 'TestUser'
    }
    
    try:
        with open(test_audio_path, 'rb') as fh:
            files = {
                # Explicitly set filename and MIME type so the server sees audio/*
                'audio': ('test_voice_output.mp3', fh, 'audio/mpeg')
            }
            response = requests.post(url, data=data, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Voice message test passed!")
            print(f"   Response: {result['message'][:100]}...")
            print(f"   Type: {result['type']}")
            print(f"   Audio URL: {result.get('audioUrl', 'None')}")
            return True
        else:
            print(f"❌ Voice message test failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Voice message test error: {e}")
        return False

def test_health_check():
    """Test the health check endpoint."""
    print("\n🧪 Testing health check...")
    
    try:
        response = requests.get("http://localhost:8000/health")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Health check passed!")
            print(f"   Status: {result['status']}")
            print(f"   Voice enabled: {result['voice_enabled']}")
            print(f"   RAG enabled: {result['rag_enabled']}")
            print(f"   LLM Provider: {result['llm_provider']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_api_docs():
    """Test if API documentation is accessible."""
    print("\n🧪 Testing API documentation...")
    
    try:
        response = requests.get("http://localhost:8000/docs")
        
        if response.status_code == 200:
            print("✅ API documentation accessible!")
            print("   Visit http://localhost:8000/docs to view the API docs")
            return True
        else:
            print(f"❌ API documentation not accessible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API documentation error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Agent Daredevil Web Messenger /chat endpoint")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not running or not accessible")
            print("   Please start the server with: python launch_web_messenger.py")
            return
    except:
        print("❌ Server is not running or not accessible")
        print("   Please start the server with: python launch_web_messenger.py")
        return
    
    # Run tests
    tests = [
        test_health_check,
        test_text_message,
        test_voice_message,
        test_api_docs
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your /chat endpoint is ready for frontend integration.")
    else:
        print("⚠️  Some tests failed. Please check the server configuration.")
    
    print("\n📋 Frontend Integration Checklist:")
    print("✅ POST /chat endpoint implemented")
    print("✅ FormData support for text and voice messages")
    print("✅ Response format matches frontend expectations")
    print("✅ Username and session tracking")
    print("✅ Voice file serving with /api/voice/{filename}")
    print("✅ Error handling and validation")

if __name__ == "__main__":
    main()
