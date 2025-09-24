#!/usr/bin/env python3
"""
Advanced Telegram Bot with RAG and Voice Processing
=================================================
This bot integrates:
- Multi-LLM Support (OpenAI GPT, Google Gemini, Vertex AI)
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
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import chromadb
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

# RAG and knowledge imports
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# LLM provider abstraction
from llm_provider import get_llm_provider, LLMProvider

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
    Supports multiple LLM providers: OpenAI, Google Gemini, and Vertex AI.
    """
    
    def __init__(self):
        """Initialize the bot with all necessary components."""
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize LLM provider (OpenAI, Gemini, or Vertex AI)
        try:
            self.llm_provider = get_llm_provider()
            logger.info(f"LLM Provider initialized: {self.llm_provider.get_model_name()}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            raise
        
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
            'llm_provider': os.getenv('LLM_PROVIDER', 'openai').lower(),
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
        
        # Check provider-specific requirements
        provider = config['llm_provider']
        if provider == 'openai' and not os.getenv('OPENAI_API_KEY'):
            missing.append('OPENAI_API_KEY')
        elif provider == 'gemini' and not os.getenv('GOOGLE_AI_API_KEY'):
            missing.append('GOOGLE_AI_API_KEY')
        elif provider == 'vertex_ai' and not os.getenv('GOOGLE_CLOUD_PROJECT_ID'):
            missing.append('GOOGLE_CLOUD_PROJECT_ID')
        
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
            # For embeddings, we'll use OpenAI embeddings regardless of the main LLM provider
            # since Gemini doesn't have a direct embeddings API yet
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                logger.warning("OpenAI API key not found. RAG system requires OpenAI embeddings. Disabling RAG.")
                return
            
            # Initialize embeddings
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=openai_api_key
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
        """Create system prompt based on character and current context."""
        
        # Base system prompt from character
        system_prompt = self.character.get('system', 'You are a helpful AI assistant.')
        
        # Add character bio if available
        bio = self.character.get('bio', [])
        if bio:
            system_prompt += f"\n\nCharacter Bio:\n" + "\n".join(f"- {point}" for point in bio)
        
        # Add current date/time context
        current_time = datetime.now()
        system_prompt += f"\n\nCurrent date and time: {current_time.strftime('%A, %B %d, %Y at %I:%M %p')}"
        
        # Add NBA season context (example of domain-specific context)
        if current_time.month >= 10 or current_time.month <= 4:
            system_prompt += f"\nNote: Currently in NBA regular season (October-April)"
        elif current_time.month >= 5 and current_time.month <= 6:
            system_prompt += f"\nNote: Currently in NBA playoffs season (May-June)"
        else:
            system_prompt += f"\nNote: Currently in NBA off-season"
        
        # Add response length limitation
        system_prompt += "\n\nIMPORTANT: Keep your responses concise, using only 3-5 sentences. Only use up to 6 sentences for data-heavy responses, with the last sentence including a data summary."
        
        return system_prompt

    def _analyze_question_type(self, message_text: str) -> Dict[str, Any]:
        """Analyze the question type to determine appropriate response parameters."""
        message_lower = message_text.lower()
        
        # Quick responses for greetings and small talk
        quick_triggers = ['hi', 'hello', 'hey', 'sup', 'yo', 'what\'s up', 'how are you', 'good morning', 'good night']
        if any(trigger in message_lower for trigger in quick_triggers) and len(message_text) < 50:
            return {
                'type': 'small_talk',
                'max_tokens': 150,
                'temperature': 0.9,
                'length_instruction': 'Keep response brief and friendly (3 sentences max)'
            }
        
        # Analytical questions that might need RAG
        analytical_triggers = ['explain', 'analyze', 'compare', 'stats', 'data', 'performance', 'history', 'tell me about']
        if any(trigger in message_lower for trigger in analytical_triggers):
            return {
                'type': 'analytical',
                'max_tokens': 600,
                'temperature': 0.4,
                'length_instruction': 'Provide concise analysis in 3-5 sentences; include data summary in the last sentence'
            }
        
        # Default case - general conversation
        return {
            'type': 'general',
            'max_tokens': 400,
            'temperature': 0.7,
            'length_instruction': 'Respond in 3-5 concise, informative sentences'
        }

    async def search_knowledge_base(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant information."""
        if not self.vectorstore:
            return []
        
        try:
            # Perform similarity search
            docs = self.vectorstore.similarity_search(query, k=k)
            
            # Format results
            results = []
            for doc in docs:
                results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    def _is_god_command(self, message_text: str) -> tuple[bool, str]:
        """Check if message is a god command and extract the override instruction."""
        message_upper = message_text.upper()
        
        # God command triggers
        god_triggers = [
            '⚡GOD:', 'GOD:', '!GOD', '/GOD', 'OVERRIDE:', '⚡OVERRIDE:',
            'NBA_ANALYST:', 'BASKETBALL:', 'F1_EXPERT:', 'CRYPTO_DEVIL:'
        ]
        
        for trigger in god_triggers:
            if message_upper.startswith(trigger):
                instruction = message_text[len(trigger):].strip()
                return True, instruction
        
        return False, ""

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
        """Generate response using the configured LLM provider with RAG context."""
        try:
            # Check for god commands first
            is_god_command, god_instruction = self._is_god_command(message_text)
            
            if is_god_command:
                # For god commands, use the instruction directly with minimal context
                messages = [
                    {"role": "system", "content": self._create_system_prompt(user_id)},
                    {"role": "user", "content": god_instruction}
                ]
                
                response = await self.llm_provider.generate_response(
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
            
                # Store in session memory
                if self.config['use_memory']:
                    self.session_memory.add_message(int(user_id), "user", message_text)
                    self.session_memory.add_message(int(user_id), "assistant", response)
                
                return f"⚡ {response}"
            
            # Regular processing
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
            
            # Prepare messages for LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_text}
            ]
            
            # Generate response using the configured provider
            response = await self.llm_provider.generate_response(
                messages=messages,
                max_tokens=question_analysis['max_tokens'],
                temperature=question_analysis['temperature']
            )
            
            # Store in session memory
            if self.config['use_memory']:
                self.session_memory.add_message(int(user_id), "user", message_text)
                self.session_memory.add_message(int(user_id), "assistant", response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Sorry, our servers are a bit loaded right now, try again later [6656]"

    async def setup_handlers(self):
        """Setup Telegram event handlers."""
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Handle /start command."""
            provider_info = f"Using {self.llm_provider.get_model_name()}"
            
            welcome_msg = f"🤖 Hello! I'm Agent Daredevil, your advanced AI assistant!\n\n"
            welcome_msg += f"🧠 {provider_info}\n"
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
            
            # Skip messages from Telegram system accounts
            if event.sender_id in [777000, 424000]:  # Telegram system accounts
                logger.info("Skipping Telegram system message")
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
            
            # Start the client with non-interactive authentication
            try:
                await self.client.start(phone=self.config['telegram_phone_number'])
            except Exception as e:
                if "EOF when reading a line" in str(e) or "input" in str(e).lower():
                    logger.error("❌ Authentication failed: No interactive terminal available in Docker")
                    logger.error("💡 Solution: Use Railway's environment variables for authentication")
                    logger.error("💡 Add TELEGRAM_BOT_TOKEN to Railway variables if using bot token")
                    logger.error("💡 Or ensure session file is properly authenticated locally first")
                    
                    # Check if we have a bot token as alternative
                    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                    if bot_token:
                        logger.info("🤖 Bot token found! Switching to bot authentication...")
                        # Create a new client with bot token
                        from telethon import TelegramClient
                        self.client = TelegramClient(
                            'bot_session',
                            self.config['telegram_api_id'],
                            self.config['telegram_api_hash']
                        )
                        await self.client.start(bot_token=bot_token)
                        logger.info("✅ Bot authentication successful!")
                    else:
                        raise Exception("Telegram authentication requires interactive session setup or bot token")
                else:
                    raise e
            
            # Register handlers on the active client (must be after .start())
            await self.setup_handlers()

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
            
            # Debug: List dialogs only for user accounts (bots cannot call get_dialogs)
            try:
                if not me.bot:
                    logger.info("📋 Checking dialogs (chats) the account is part of...")
                    dialogs = await self.client.get_dialogs(limit=50)
                    group_count = 0
                    for dialog in dialogs:
                        if dialog.is_group:
                            group_count += 1
                            logger.info(f"📱 Group: {dialog.title} (ID: {dialog.id})")
                        elif dialog.is_user:
                            logger.info(f"👤 User: {dialog.title} (ID: {dialog.id})")
                    logger.info(f"📊 Total groups: {group_count}")
                else:
                    logger.info("🤖 Running as bot: skipping get_dialogs (restricted for bots)")
            except Exception as e:
                logger.error(f"Dialog check skipped: {e}")
            
            # Keep running
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            logger.error(traceback.format_exc())
            raise

async def main():
    """Main function to run the bot."""
    try:
        # Start health server in background thread for Railway
        import threading
        from health_server import start_health_server
        
        logger.info("🚀 Starting Agent Daredevil Bot...")
        
        # Start health server first
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()
        
        # Give health server a moment to start
        await asyncio.sleep(1)
        logger.info("🏥 Health server started in background")
        
        # Start the main bot
        bot = AgentDaredevilBot()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    asyncio.run(main())
