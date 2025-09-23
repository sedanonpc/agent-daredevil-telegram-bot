#!/usr/bin/env python3
"""
Voice Processor Module for Telegram Bot
======================================
This module handles voice note processing using OpenAI Whisper for speech-to-text
and ElevenLabs for text-to-speech.

Author: Agent Daredevil
"""

import os
import tempfile
import asyncio
import logging
from pathlib import Path
from typing import Optional, Union, BinaryIO, Dict, Any
import io

# For environment variables
from dotenv import load_dotenv

# For API calls
import requests
import openai
from elevenlabs.client import ElevenLabs
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeVideo

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceProcessor:
    """
    Handles voice note processing for the Telegram bot.
    Provides speech-to-text and text-to-speech functionality.
    """
    
    def __init__(self):
        """Initialize the VoiceProcessor with API clients."""
        # OpenAI client for Whisper
        self.openai_client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # ElevenLabs client for TTS
        self.elevenlabs_client = ElevenLabs(
            api_key=os.getenv('ELEVENLABS_API_KEY')
        )
        
        # Configuration
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'zYcjlYFOd3taleS0gkk3')
        self.model = os.getenv('ELEVENLABS_MODEL', 'eleven_monolingual_v1')
        self.stability = float(os.getenv('ELEVENLABS_STABILITY', '0.5'))
        self.similarity_boost = float(os.getenv('ELEVENLABS_SIMILARITY_BOOST', '0.5'))
        self.use_voice_features = os.getenv('USE_VOICE_FEATURES', 'True').lower() == 'true'
        
        # Test ElevenLabs permissions
        self.elevenlabs_working = self._test_elevenlabs_permissions()
        
        logger.info(f"VoiceProcessor initialized with voice_id: {self.voice_id}")
        if not self.elevenlabs_working:
            logger.warning("ElevenLabs API has permission issues - voice features will be limited")
    
    def _test_elevenlabs_permissions(self) -> bool:
        """Test if ElevenLabs API has proper permissions for TTS."""
        try:
            # Test TTS conversion directly instead of checking voices list
            # This is more reliable since some API keys don't have voices_read permission
            test_audio = self.elevenlabs_client.text_to_speech.convert(
                text="test",
                voice_id=self.voice_id,
                model_id=self.model,
                output_format="mp3_44100_128"
            )
            return True
        except Exception as e:
            logger.error(f"ElevenLabs TTS test failed: {e}")
            return False
    
    async def is_voice_message(self, message) -> bool:
        """
        Check if a message contains a voice note.
        
        Args:
            message: Telegram message object
            
        Returns:
            bool: True if message contains voice note, False otherwise
        """
        if not message.media:
            return False
            
        # Check for voice messages
        if hasattr(message.media, 'document'):
            document = message.media.document
            if document and document.attributes:
                for attr in document.attributes:
                    if isinstance(attr, DocumentAttributeAudio):
                        # Voice messages have voice=True attribute
                        return getattr(attr, 'voice', False)
        
        return False
    
    async def download_voice_note(self, client: TelegramClient, message) -> Optional[bytes]:
        """
        Download voice note from Telegram message.
        
        Args:
            client: Telegram client
            message: Message containing voice note
            
        Returns:
            bytes: Voice note audio data or None if failed
        """
        try:
            if not await self.is_voice_message(message):
                logger.warning("Message does not contain a voice note")
                return None
            
            # Download the voice note
            voice_data = await client.download_media(message, file=bytes)
            logger.info(f"Downloaded voice note: {len(voice_data)} bytes")
            return voice_data
            
        except Exception as e:
            logger.error(f"Error downloading voice note: {e}")
            return None
    
    async def speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """
        Convert speech to text using OpenAI Whisper.
        
        Args:
            audio_data: Audio data in bytes
            
        Returns:
            str: Transcribed text or None if failed
        """
        try:
            if not self.use_voice_features:
                logger.info("Voice features disabled")
                return None
            
            # Create a temporary file for the audio data
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Use OpenAI Whisper API for transcription
                with open(temp_file_path, 'rb') as audio_file:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                
                logger.info(f"Transcription successful: {transcript[:100]}...")
                return transcript.strip()
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Error in speech-to-text conversion: {e}")
            return None
    
    def estimate_speech_duration(self, text: str) -> float:
        """
        Estimate speech duration in seconds based on text length.
        
        Args:
            text: Text to estimate duration for
            
        Returns:
            float: Estimated duration in seconds
        """
        # Average speech rate: ~150 words per minute = 2.5 words per second
        # Average characters per word: ~5 (including spaces)
        # So ~12.5 characters per second
        words = len(text.split())
        estimated_seconds = words / 2.5
        return estimated_seconds

    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech using ElevenLabs.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            bytes: Audio data or None if failed
        """
        try:
            if not self.use_voice_features:
                logger.info("Voice features disabled")
                return None
            
            if not self.elevenlabs_working:
                logger.warning("ElevenLabs API not working due to permissions - skipping TTS")
                return None
            
            if not text or len(text.strip()) == 0:
                logger.warning("Empty text provided for TTS")
                return None
            
            # Estimate speech duration and limit to 20 seconds
            estimated_duration = self.estimate_speech_duration(text)
            max_characters = 350  # ~20 seconds at average speech rate
            
            if len(text) > max_characters or estimated_duration > 20:
                # Truncate text to fit within 20 seconds
                truncated_text = text[:max_characters]
                # Try to end at a sentence boundary
                last_period = truncated_text.rfind('.')
                last_exclamation = truncated_text.rfind('!')
                last_question = truncated_text.rfind('?')
                
                last_sentence_end = max(last_period, last_exclamation, last_question)
                if last_sentence_end > max_characters * 0.7:  # If we can find a good sentence break
                    text = truncated_text[:last_sentence_end + 1]
                else:
                    text = truncated_text + "..."
                
                logger.info(f"Text truncated for TTS - estimated duration was {estimated_duration:.1f}s, truncated to ~{self.estimate_speech_duration(text):.1f}s")
            
            # Generate speech using ElevenLabs
            audio = self.elevenlabs_client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model,
                output_format="mp3_44100_128"
            )
            
            # Convert audio to bytes if it's not already
            if hasattr(audio, '__iter__') and not isinstance(audio, bytes):
                audio_bytes = b''.join(audio)
            else:
                audio_bytes = audio
            logger.info(f"TTS successful: {len(audio_bytes)} bytes, estimated duration: {self.estimate_speech_duration(text):.1f}s")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Error in text-to-speech conversion: {e}")
            return None
    
    async def is_reply_to_bot(self, client: TelegramClient, message) -> bool:
        """
        Check if the message is a reply to the bot's message.
        
        Args:
            client: Telegram client
            message: Message to check
            
        Returns:
            bool: True if message is a reply to bot, False otherwise
        """
        try:
            if not message.reply_to_msg_id:
                return False
            
            # Get the replied-to message
            replied_message = await client.get_messages(message.chat_id, ids=message.reply_to_msg_id)
            
            if not replied_message:
                return False
            
            # Check if the replied message is from the bot (self)
            me = await client.get_me()
            is_bot_reply = replied_message.sender_id == me.id
            
            if is_bot_reply:
                logger.info(f"Voice message is a reply to bot's message (ID: {message.reply_to_msg_id})")
            
            return is_bot_reply
            
        except Exception as e:
            logger.error(f"Error checking if message is reply to bot: {e}")
            return False

    async def process_voice_message(self, client: TelegramClient, message, rag_manager, is_group: bool = False) -> Optional[str]:
        """
        Process a voice message: download, transcribe, generate response, and convert to speech.
        
        Args:
            client: Telegram client
            message: Voice message
            rag_manager: RAG manager for generating responses
            is_group: Whether this message is from a group chat
            
        Returns:
            str: Transcribed text or None if failed
        """
        try:
            # Download voice note
            voice_data = await self.download_voice_note(client, message)
            if not voice_data:
                return None
            
            # Convert speech to text
            transcribed_text = await self.speech_to_text(voice_data)
            if not transcribed_text:
                await client.send_message(
                    message.chat_id,
                    "Sorry, I couldn't understand the voice message. Please try again or send a text message."
                )
                return None
            
            logger.info(f"Voice message transcribed: {transcribed_text}")
            
            # For group chats, check if bot should respond
            if is_group:
                # Check if this is a reply to the bot's message
                is_reply_to_bot = await self.is_reply_to_bot(client, message)
                
                if is_reply_to_bot:
                    logger.info("Voice message is a reply to bot - responding automatically")
                    should_respond = True
                else:
                    # Check for trigger keywords as before
                    should_respond = rag_manager._should_respond_to_group_message(transcribed_text)
                    if not should_respond:
                        logger.info("Group voice message doesn't contain trigger keywords and is not a reply to bot, ignoring")
                        return transcribed_text  # Return transcription but don't respond
            else:
                should_respond = True
            
            # Only generate response if we should respond
            if not should_respond:
                return transcribed_text
            
            # Generate response using RAG
            response_text = await rag_manager.generate_response(transcribed_text, message.sender_id)
            
            # Check if response would exceed 20 seconds when spoken
            estimated_duration = self.estimate_speech_duration(response_text)
            
            if estimated_duration > 20:
                # Response too long for voice - send as text instead
                logger.info(f"Response too long for voice ({estimated_duration:.1f}s > 20s) - sending as text")
                await client.send_message(
                    message.chat_id,
                    f"🎤 I heard: \"{transcribed_text}\"\n\n📝 {response_text}"
                )
            else:
                # Convert response to speech
                response_audio = await self.text_to_speech(response_text)
                
                if response_audio:
                    # Send ONLY voice response for voice messages
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
                        temp_audio.write(response_audio)
                        temp_audio_path = temp_audio.name
                    
                    try:
                        await client.send_file(
                            message.chat_id,
                            temp_audio_path,
                            voice_note=True
                            # No caption - pure voice response only
                        )
                    finally:
                        os.unlink(temp_audio_path)
                else:
                    # Fallback to text response if TTS fails
                    await client.send_message(
                        message.chat_id,
                        f"🎤 I heard: \"{transcribed_text}\"\n\n📝 {response_text}\n\n(Voice response failed, sending text instead)"
                    )
            
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Error processing voice message: {e}")
            await client.send_message(
                message.chat_id,
                "Sorry, there was an error processing your voice message. Please try again."
            )
            return None
    
    def is_enabled(self) -> bool:
        """Check if voice features are enabled."""
        return (self.use_voice_features and 
                bool(os.getenv('ELEVENLABS_API_KEY')) and 
                bool(os.getenv('OPENAI_API_KEY')) and
                self.elevenlabs_working)

# Global instance
voice_processor = VoiceProcessor()
