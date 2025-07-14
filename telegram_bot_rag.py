#!/usr/bin/env python3
"""
Advanced Telegram Bot with RAG and Voice Processing
=================================================
This bot integrates:
- OpenAI GPT for conversations
- ChromaDB RAG for knowledge retrieval
- Voice note processing (speech-to-text and text-to-speech)
- Character personality from JSON file
- Session memory management

Author: Agent Daredevil
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import traceback

# Environment and encoding setup
from dotenv import load_dotenv
load_dotenv()

# Fix Windows console encoding issues
if sys.platform.startswith('win'):
    try:
        os.system('chcp 65001 >nul 2>&1')
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Core imports
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeAudio
import openai
from openai import OpenAI

# RAG and knowledge imports
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# Voice processing
from voice_processor import voice_processor

# Session memory
from session_memory import SessionMemoryManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot_rag.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgentDaredevilBot:
    """
    Advanced Telegram bot with RAG, voice processing, and character consistency.
    """
    
    def __init__(self):
        """Initialize the bot with all necessary components."""
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=self.config['openai_api_key'])
        
        # Initialize Telegram client
        self.client = TelegramClient(
            'daredevil_session',
            self.config['telegram_api_id'],
            self.config['telegram_api_hash']
        )
        
        # Initialize RAG system
        self.embeddings = None
        self.vectorstore = None
        self._init_rag_system()
        
        # Load character personality
        self.character = self._load_character()
        
        # Initialize session memory
        self.session_memory = SessionMemoryManager(
            db_path=self.config.get('memory_db_path', './memory.db'),
            session_timeout_hours=self.config.get('session_timeout_hours', 24),
            max_session_messages=self.config.get('max_session_messages', 50)
        )
        
        # Voice processing enabled check
        self.voice_enabled = voice_processor.is_enabled()
        
        logger.info(f"AgentDaredevilBot initialized. Voice features: {'enabled' if self.voice_enabled else 'disabled'}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {
            'telegram_api_id': int(os.getenv('TELEGRAM_API_ID', 0)),
            'telegram_api_hash': os.getenv('TELEGRAM_API_HASH', ''),
            'telegram_phone_number': os.getenv('TELEGRAM_PHONE_NUMBER', ''),
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'chroma_db_path': os.getenv('CHROMA_DB_PATH', './chroma_db'),
            'character_card_path': os.getenv('CHARACTER_CARD_PATH', './cryptodevil.character.json'),
            'use_rag': os.getenv('USE_RAG', 'True').lower() == 'true',
            'use_memory': os.getenv('USE_MEMORY', 'True').lower() == 'true',
            'memory_db_path': os.getenv('MEMORY_DB_PATH', './memory.db'),
            'session_timeout_hours': int(os.getenv('SESSION_TIMEOUT_HOURS', 24)),
            'max_session_messages': int(os.getenv('MAX_SESSION_MESSAGES', 50)),
            'debug': os.getenv('DEBUG', 'False').lower() == 'true'
        }
        
        # Validate required configuration
        missing = []
        if not config['telegram_api_id']:
            missing.append('TELEGRAM_API_ID')
        if not config['telegram_api_hash']:
            missing.append('TELEGRAM_API_HASH')
        if not config['telegram_phone_number']:
            missing.append('TELEGRAM_PHONE_NUMBER')
        if not config['openai_api_key']:
            missing.append('OPENAI_API_KEY')
        
        if missing:
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return config
    
    def _init_rag_system(self):
        """Initialize the RAG system with ChromaDB."""
        if not self.config['use_rag']:
            logger.info("RAG system disabled")
            return
        
        try:
            # Initialize embeddings
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.config['openai_api_key']
            )
            
            # Initialize vectorstore
            self.vectorstore = Chroma(
                collection_name="telegram_bot_knowledge",
                embedding_function=self.embeddings,
                persist_directory=self.config['chroma_db_path']
            )
            
            logger.info("RAG system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            self.vectorstore = None
    
    def _load_character(self) -> Dict[str, Any]:
        """Load character personality from JSON file."""
        try:
            character_path = self.config['character_card_path']
            if os.path.exists(character_path):
                with open(character_path, 'r', encoding='utf-8') as f:
                    character = json.load(f)
                logger.info(f"Character loaded: {character.get('name', 'Unknown')}")
                return character
            else:
                logger.warning(f"Character file not found: {character_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading character: {e}")
            return {}
    
    def _create_system_prompt(self, user_id: str) -> str:
        """Create system prompt with character and context."""
        base_prompt = "You are Agent Daredevil, a helpful AI assistant."
        
        # Add character personality if available
        if self.character:
            if 'system' in self.character:
                base_prompt = self.character['system']
            
            # Add bio
            if 'bio' in self.character and self.character['bio']:
                bio_text = " | ".join(self.character['bio'])
                base_prompt += f"\n\nBACKGROUND: {bio_text}"
            
            # Add personality traits
            if 'adjectives' in self.character and self.character['adjectives']:
                traits = ", ".join(self.character['adjectives'])
                base_prompt += f"\n\nPERSONALITY: {traits}"
        
        # Add current context
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        base_prompt += f"\n\nCURRENT TIME: {current_time}"
        base_prompt += "\n\nREMEMBER: You are chatting on Telegram. Keep responses conversational and engaging."
        
        return base_prompt
    
    async def search_knowledge_base(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant information."""
        if not self.vectorstore:
            return []
        
        try:
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            knowledge_items = []
            for doc, score in results:
                knowledge_items.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': score
                })
            
            logger.info(f"Found {len(knowledge_items)} knowledge items for query: {query[:50]}...")
            return knowledge_items
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    def _analyze_question_type(self, message_text: str) -> Dict[str, Any]:
        """Analyze the message to determine appropriate response length and style."""
        message_lower = message_text.lower()
        
        # Data/statistical/analytical keywords
        analytical_keywords = [
            'statistics', 'data', 'analysis', 'numbers', 'percentage', 'calculate', 'compare',
            'research', 'study', 'report', 'findings', 'results', 'metrics', 'performance',
            'trends', 'breakdown', 'detailed', 'explain how', 'why does', 'what causes',
            'basketball', 'nba', 'stats', 'season', 'player', 'team', 'game', 'score'
        ]
        
        # Small talk/greeting keywords
        small_talk_keywords = [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
            'how are you', 'whats up', "what's up", 'thanks', 'thank you', 'bye',
            'goodbye', 'see you', 'nice', 'cool', 'awesome', 'great', 'ok', 'okay'
        ]
        
        # Check for analytical content
        is_analytical = any(keyword in message_lower for keyword in analytical_keywords)
        
        # Check for small talk
        is_small_talk = any(keyword in message_lower for keyword in small_talk_keywords)
        
        # Question indicators
        is_question = any(message_text.strip().startswith(q) for q in ['?', 'what', 'how', 'why', 'when', 'where', 'who'])
        is_question = is_question or '?' in message_text
        
        # Determine response type
        if is_analytical or (is_question and not is_small_talk):
            return {
                'type': 'analytical',
                'max_tokens': 400,
                'temperature': 0.3,
                'length_instruction': 'Be thorough but concise. Provide specific details and data when available.'
            }
        elif is_small_talk:
            return {
                'type': 'small_talk',
                'max_tokens': 100,
                'temperature': 0.7,
                'length_instruction': 'Keep it very brief and conversational. 1-2 sentences maximum.'
            }
        else:
            return {
                'type': 'general',
                'max_tokens': 200,
                'temperature': 0.5,
                'length_instruction': 'Be helpful but concise. Keep responses focused and to the point.'
            }
    
    async def _is_reply_to_bot(self, message) -> bool:
        """
        Check if the message is a reply to the bot's message.
        
        Args:
            message: Message to check
            
        Returns:
            bool: True if message is a reply to bot, False otherwise
        """
        try:
            if not message.reply_to_msg_id:
                return False
            
            # Get the replied-to message
            replied_message = await self.client.get_messages(message.chat_id, ids=message.reply_to_msg_id)
            
            if not replied_message:
                return False
            
            # Check if the replied message is from the bot (self)
            me = await self.client.get_me()
            is_bot_reply = replied_message.sender_id == me.id
            
            if is_bot_reply:
                logger.info(f"Message is a reply to bot's message (ID: {message.reply_to_msg_id})")
            
            return is_bot_reply
            
        except Exception as e:
            logger.error(f"Error checking if message is reply to bot: {e}")
            return False

    def _should_respond_to_group_message(self, message_text: str) -> bool:
        """Check if the bot should respond to a message in a group chat."""
        if not message_text:
            return False
        
        # Keywords that trigger bot response in groups
        trigger_keywords = [
            'agent daredevil',
            'daredevil', 
            'devil'
        ]
        
        text_lower = message_text.lower()
        
        # Check if any trigger keyword is mentioned
        for keyword in trigger_keywords:
            if keyword in text_lower:
                logger.info(f"Group trigger detected: '{keyword}' in message")
                return True
        
        return False

    async def generate_response(self, message_text: str, user_id: str) -> str:
        """Generate response using OpenAI with RAG context and intelligent length control."""
        try:
            # Analyze question type for appropriate response length
            question_analysis = self._analyze_question_type(message_text)
            
            # Get session context
            session_context = ""
            if self.config['use_memory']:
                session_context = self.session_memory.get_context_for_llm(int(user_id))
            
            # Search knowledge base (only for analytical questions or when relevant)
            knowledge_context = ""
            if self.config['use_rag'] and self.vectorstore and question_analysis['type'] != 'small_talk':
                knowledge_items = await self.search_knowledge_base(message_text)
                if knowledge_items:
                    knowledge_context = "\n\nRELEVANT KNOWLEDGE:\n"
                    for i, item in enumerate(knowledge_items[:3], 1):
                        knowledge_context += f"{i}. {item['content'][:300]}...\n"
            
            # Create system prompt with length guidance
            system_prompt = self._create_system_prompt(user_id)
            system_prompt += f"\n\nRESPONSE STYLE: {question_analysis['length_instruction']}"
            
            # Add contexts
            if session_context:
                system_prompt += f"\n\nRECENT CONVERSATION CONTEXT:\n{session_context}"
            
            if knowledge_context:
                system_prompt += knowledge_context
            
            # Generate response with appropriate parameters
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message_text}
                ],
                max_tokens=question_analysis['max_tokens'],
                temperature=question_analysis['temperature']
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Store in session memory
            if self.config['use_memory']:
                self.session_memory.add_message(int(user_id), "user", message_text)
                self.session_memory.add_message(int(user_id), "assistant", ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, but I'm experiencing some technical difficulties. Please try again."
    
    async def setup_handlers(self):
        """Setup Telegram event handlers."""
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Handle /start command."""
            welcome_msg = "🤖 Hello! I'm Agent Daredevil, your advanced AI assistant!\n\n"
            welcome_msg += "💬 Send me text messages and I'll respond with knowledge from my database\n"
            
            if self.voice_enabled:
                welcome_msg += "🎤 Send voice notes and I'll transcribe them and respond with voice!\n"
            
            welcome_msg += "🧠 I have access to various knowledge sources and can help with many topics.\n\n"
            welcome_msg += "Type anything to get started!"
            
            await event.respond(welcome_msg)
        
        @self.client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            """Handle /help command."""
            help_msg = "🆘 **Agent Daredevil Help**\n\n"
            help_msg += "**Commands:**\n"
            help_msg += "• `/start` - Welcome message\n"
            help_msg += "• `/help` - This help message\n"
            help_msg += "• `/stats` - Knowledge base statistics\n"
            help_msg += "• `/memory` - Session memory info\n\n"
            help_msg += "**Features:**\n"
            help_msg += "• 💬 Natural conversation with AI\n"
            help_msg += "• 🧠 Knowledge base search\n"
            help_msg += "• 💾 Session memory\n"
            
            if self.voice_enabled:
                help_msg += "• 🎤 Voice note processing\n"
                help_msg += "• 🔊 Voice responses\n"
            
            await event.respond(help_msg)
        
        @self.client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            """Handle /stats command."""
            try:
                if not self.vectorstore:
                    await event.respond("❌ Knowledge base not available")
                    return
                
                # Get collection stats
                client = chromadb.PersistentClient(path=self.config['chroma_db_path'])
                collection = client.get_collection("telegram_bot_knowledge")
                count = collection.count()
                
                stats_msg = f"📊 **Knowledge Base Stats**\n\n"
                stats_msg += f"📄 Total chunks: {count}\n"
                stats_msg += f"🔍 RAG enabled: {'✅' if self.config['use_rag'] else '❌'}\n"
                stats_msg += f"💾 Memory enabled: {'✅' if self.config['use_memory'] else '❌'}\n"
                stats_msg += f"🎤 Voice enabled: {'✅' if self.voice_enabled else '❌'}\n"
                
                await event.respond(stats_msg)
                
            except Exception as e:
                await event.respond(f"❌ Error getting stats: {str(e)}")
        
        @self.client.on(events.NewMessage(pattern='/memory'))
        async def memory_handler(event):
            """Handle /memory command."""
            try:
                if not self.config['use_memory']:
                    await event.respond("❌ Session memory is disabled")
                    return
                
                user_id = event.sender_id
                session = self.session_memory.get_or_create_session(user_id)
                stats = self.session_memory.get_stats()
                
                memory_msg = f"💾 **Session Memory Info**\n\n"
                memory_msg += f"📝 Messages in session: {session.message_count}\n"
                memory_msg += f"⏰ Session started: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                memory_msg += f"🕐 Last activity: {session.last_activity.strftime('%Y-%m-%d %H:%M:%S')}\n"
                memory_msg += f"👥 Total active users: {stats['unique_users']}\n"
                
                await event.respond(memory_msg)
                
            except Exception as e:
                await event.respond(f"❌ Error getting memory info: {str(e)}")
        
        @self.client.on(events.NewMessage)
        async def message_handler(event):
            """Handle all incoming messages."""
            
            # Debug logging for all messages
            chat_info = f"Chat ID: {event.chat_id}, Is Group: {event.is_group}, Is Channel: {event.is_channel}"
            logger.info(f"Received message - {chat_info}")
            
            # Skip commands (already handled above)
            if event.raw_text and event.raw_text.startswith('/'):
                logger.info("Skipping command message")
                return
            
            # Skip messages from broadcast channels (but allow supergroups)
            # Supergroups have both is_group=True and is_channel=True
            # Broadcast channels have is_channel=True but is_group=False
            if event.is_channel and not event.is_group:
                logger.info("Skipping broadcast channel message")
                return
            
            # Skip messages from self
            if event.sender_id == (await self.client.get_me()).id:
                logger.info("Skipping message from self")
                return
            
            user_id = str(event.sender_id)
            
            try:
                # Check if it's a voice message
                if self.voice_enabled and await voice_processor.is_voice_message(event.message):
                    is_group = event.is_group
                    chat_type = "group" if is_group else "private"
                    logger.info(f"Processing voice message from user {user_id} in {chat_type} chat")
                    
                    # Show typing indicator
                    async with self.client.action(event.chat_id, 'typing'):
                        # Process voice message (this handles transcription, response generation, and TTS)
                        transcribed_text = await voice_processor.process_voice_message(
                            self.client, event.message, self, is_group=is_group
                        )
                    
                    if transcribed_text:
                        logger.info(f"Voice message processed successfully: {transcribed_text[:50]}...")
                    
                    return
                
                # Handle text messages
                if event.raw_text:
                    message_text = event.raw_text.strip()
                    is_group = event.is_group
                    chat_type = "group" if is_group else "private"
                    logger.info(f"Processing text message from user {user_id} in {chat_type} chat: {message_text[:50]}...")
                    
                    # For group chats, check if bot should respond to text messages
                    if is_group:
                        # Check if this is a reply to the bot's message
                        is_reply_to_bot = await self._is_reply_to_bot(event.message)
                        
                        if is_reply_to_bot:
                            logger.info("Text message is a reply to bot - responding automatically")
                            should_respond = True
                        else:
                            # Check for trigger keywords as before
                            should_respond = self._should_respond_to_group_message(message_text)
                            if not should_respond:
                                logger.info("Group text message doesn't contain trigger keywords and is not a reply to bot, ignoring")
                                return
                    else:
                        should_respond = True
                    
                    # Show typing indicator
                    async with self.client.action(event.chat_id, 'typing'):
                        # Generate response
                        response = await self.generate_response(message_text, user_id)
                        
                        # Send response
                        await event.respond(response)
                    
                    logger.info(f"Response sent to user {user_id} in {chat_type} chat")
                
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                logger.error(traceback.format_exc())
                await event.respond("Sorry, I encountered an error processing your message. Please try again.")
    
    async def start(self):
        """Start the bot."""
        try:
            logger.info("Starting Agent Daredevil Telegram Bot...")
            
            # Setup event handlers
            await self.setup_handlers()
            
            # Start the client
            await self.client.start(phone=self.config['telegram_phone_number'])
            
            # Get bot info
            me = await self.client.get_me()
            logger.info(f"✅ Bot started successfully! Logged in as: {me.first_name}")
            
            if self.voice_enabled:
                logger.info("🎤 Voice processing enabled")
            
            if self.config['use_rag']:
                logger.info("🧠 RAG system enabled")
            
            if self.config['use_memory']:
                logger.info("💾 Session memory enabled")
            
            logger.info("🚀 Agent Daredevil is ready to chat!")
            
            # Debug: List all dialogs (chats) the bot is part of
            try:
                logger.info("📋 Checking dialogs (chats) the bot is part of...")
                dialogs = await self.client.get_dialogs(limit=50)
                group_count = 0
                for dialog in dialogs:
                    if dialog.is_group:
                        group_count += 1
                        logger.info(f"📱 Group: {dialog.title} (ID: {dialog.id})")
                    elif dialog.is_user:
                        logger.info(f"👤 User: {dialog.title} (ID: {dialog.id})")
                logger.info(f"📊 Total groups: {group_count}")
            except Exception as e:
                logger.error(f"Error listing dialogs: {e}")
            
            # Keep running
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            logger.error(traceback.format_exc())
            raise

async def main():
    """Main function to run the bot."""
    try:
        bot = AgentDaredevilBot()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    asyncio.run(main())
