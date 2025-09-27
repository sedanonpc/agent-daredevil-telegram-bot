#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import sys
sys.path.append(".")
from telegram_bot_rag import AgentDaredevilBot

async def test_character_rag():
    print("Testing Agent Daredevil character and RAG integration...")
    
    try:
        # Initialize the bot
        bot = AgentDaredevilBot()
        
        # Test messages that should trigger character personality
        test_messages = [
            "Hello, who are you?",
            "What's your take on Bitcoin?",
            "Tell me about the Lakers",
            "What do you think about Web3 gaming?"
        ]
        
        for message in test_messages:
            print(f"\n🧪 Testing: '{message}'")
            
            try:
                response = await bot.generate_response(message, "test_user_123")
                print(f"🤖 Response: {response}")
                
                # Check if response contains character elements
                character_indicators = ["Agent Daredevil", "Web3", "NBA", "esports", "gaming", "crypto"]
                has_character = any(indicator.lower() in response.lower() for indicator in character_indicators)
                
                if has_character:
                    print("✅ Character personality detected")
                else:
                    print("⚠️  Character personality not clearly visible")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"Failed to initialize bot: {e}")

if __name__ == "__main__":
    asyncio.run(test_character_rag())
