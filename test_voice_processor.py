#!/usr/bin/env python3
"""
Test script for voice processing functionality
============================================
This script tests the voice processor module to ensure ElevenLabs
and OpenAI Whisper integration works correctly.
"""

import os
import asyncio
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test if voice processor can be imported
try:
    from voice_processor import voice_processor
    print("✅ Voice processor imported successfully")
except ImportError as e:
    print(f"❌ Failed to import voice processor: {e}")
    exit(1)

async def test_text_to_speech():
    """Test text-to-speech functionality."""
    print("\n🔊 Testing Text-to-Speech...")
    
    test_text = "Hello! This is Agent Daredevil testing the voice processing system."
    
    try:
        # Test TTS
        audio_data = await voice_processor.text_to_speech(test_text)
        
        if audio_data:
            print(f"✅ TTS successful! Generated {len(audio_data)} bytes of audio")
            
            # Save test audio file
            with open("test_voice_output.mp3", "wb") as f:
                f.write(audio_data)
            print("💾 Test audio saved as 'test_voice_output.mp3'")
            
            return True
        else:
            print("❌ TTS failed - no audio data returned")
            return False
            
    except Exception as e:
        print(f"❌ TTS error: {e}")
        return False

def test_configuration():
    """Test if all required configuration is present."""
    print("\n⚙️ Testing Configuration...")
    
    required_vars = [
        'ELEVENLABS_API_KEY',
        'OPENAI_API_KEY'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("\n📋 Setup Instructions:")
        print("1. Copy env.example to .env")
        print("2. Add your API keys to the .env file")
        print("3. Run this test again")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def test_voice_processor_init():
    """Test voice processor initialization."""
    print("\n🎤 Testing Voice Processor Initialization...")
    
    try:
        # Check if voice processor is enabled
        if voice_processor.is_enabled():
            print("✅ Voice processor is enabled and ready")
            print(f"🔧 Voice ID: {voice_processor.voice_id}")
            print(f"🔧 Model: {voice_processor.model}")
            return True
        else:
            print("❌ Voice processor is disabled or missing API keys")
            return False
            
    except Exception as e:
        print(f"❌ Voice processor initialization error: {e}")
        return False

async def main():
    """Run all tests."""
    print("🧪 Starting Voice Processor Tests")
    print("=" * 50)
    
    # Test 1: Configuration
    config_ok = test_configuration()
    
    # Test 2: Voice processor initialization
    init_ok = test_voice_processor_init()
    
    # Test 3: Text-to-speech (only if previous tests pass)
    tts_ok = False
    if config_ok and init_ok:
        tts_ok = await test_text_to_speech()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"⚙️  Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"🎤 Initialization: {'✅ PASS' if init_ok else '❌ FAIL'}")
    print(f"🔊 Text-to-Speech: {'✅ PASS' if tts_ok else '❌ FAIL'}")
    
    if config_ok and init_ok and tts_ok:
        print("\n🎉 All tests passed! Voice processing is ready to use.")
        print("\n📝 Next steps:")
        print("1. Update your .env file with Telegram credentials")
        print("2. Run: python telegram_bot_rag.py")
        print("3. Send voice notes to test full functionality")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        
        if not config_ok:
            print("\n🔧 To fix configuration issues:")
            print("1. Copy env.example to .env")
            print("2. Add your API keys to the .env file")
        
        if not init_ok:
            print("\n🔧 To fix initialization issues:")
            print("1. Verify your ElevenLabs API key is correct")
            print("2. Check your internet connection")
            print("3. Ensure elevenlabs package is installed: pip install elevenlabs")

if __name__ == '__main__':
    asyncio.run(main()) 