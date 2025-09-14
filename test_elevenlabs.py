#!/usr/bin/env python3
"""
Test ElevenLabs TTS functionality
"""

import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

def test_elevenlabs():
    load_dotenv()
    
    api_key = os.getenv('ELEVENLABS_API_KEY')
    voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'zYcjlYFOd3taleS0gkk3')
    
    print("🔊 Testing ElevenLabs TTS")
    print("=" * 40)
    print(f"API Key: {'Found' if api_key else 'Missing'}")
    print(f"Voice ID: {voice_id}")
    
    if not api_key:
        print("❌ No ElevenLabs API key found")
        return
    
    try:
        # Test client initialization
        client = ElevenLabs(api_key=api_key)
        print("✅ ElevenLabs client initialized")
        
        # Test permissions by getting voices
        try:
            voices = client.voices.get_all()
            print(f"✅ Permissions OK - Found {len(voices.voices)} voices")
        except Exception as e:
            print(f"❌ Permissions issue: {e}")
            return
        
        # Test TTS conversion
        try:
            print("🎤 Testing TTS conversion...")
            audio = client.text_to_speech.convert(
                text="Hello, this is a test of ElevenLabs text to speech.",
                voice_id=voice_id,
                model_id="eleven_monolingual_v1",
                output_format="mp3_44100_128"
            )
            
            # Convert to bytes
            if hasattr(audio, '__iter__') and not isinstance(audio, bytes):
                audio_bytes = b''.join(audio)
            else:
                audio_bytes = audio
                
            print(f"✅ TTS successful: {len(audio_bytes)} bytes generated")
            
            # Save test file
            with open('test_voice_output.mp3', 'wb') as f:
                f.write(audio_bytes)
            print("✅ Test audio saved as 'test_voice_output.mp3'")
            
        except Exception as e:
            print(f"❌ TTS conversion failed: {e}")
            
    except Exception as e:
        print(f"❌ ElevenLabs client error: {e}")

if __name__ == "__main__":
    test_elevenlabs()
