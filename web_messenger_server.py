#!/usr/bin/env python3
"""
Web Messenger Server for Agent Daredevil
=======================================
FastAPI-based web server that provides REST API and WebSocket endpoints
for connecting frontend messenger apps to the Agent Daredevil chatbot.

Features:
- REST API for text messages
- WebSocket for real-time communication
- Voice message processing with file upload
- Message type detection (text vs voice)
- Integration with existing bot logic

Author: Agent Daredevil
"""

import os
import sys
import asyncio
import logging
import json
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
import traceback
from datetime import datetime

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

# FastAPI and WebSocket imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

# Core bot imports (reuse existing logic)
from llm_provider import get_llm_provider, LLMProvider
from voice_processor import voice_processor
from session_memory import SessionMemoryManager
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('web_messenger.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Pydantic models for API
class TextMessage(BaseModel):
    message: str
    user_id: str
    session_id: Optional[str] = None

class VoiceMessage(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    transcription: Optional[str] = None

class WebSocketMessage(BaseModel):
    type: str  # "text" or "voice"
    content: str
    user_id: str
    session_id: Optional[str] = None

class BotResponse(BaseModel):
    message: str
    message_type: str  # "text" or "voice"
    user_id: str
    session_id: str
    timestamp: str

# New models for frontend integration
class ChatRequest(BaseModel):
    message: str
    type: str  # "text" or "voice"
    sessionId: str
    userId: str
    username: str

class ChatResponse(BaseModel):
    message: str
    type: str  # "text" or "voice"
    audioUrl: Optional[str] = None

class WebMessengerBot:
    """
    Web-based messenger bot that reuses the existing Agent Daredevil logic.
    Provides REST API and WebSocket endpoints for frontend connections.
    """
    
    def __init__(self):
        """Initialize the web messenger bot."""
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize LLM provider
        try:
            self.llm_provider = get_llm_provider()
            logger.info(f"LLM Provider initialized: {self.llm_provider.get_model_name()}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            raise
        
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
        
        # User session tracking (username support)
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Voice processing enabled check
        self.voice_enabled = voice_processor.is_enabled()
        
        # WebSocket connection manager
        self.active_connections: Dict[str, WebSocket] = {}
        
        logger.info(f"WebMessengerBot initialized. Voice features: {'enabled' if self.voice_enabled else 'disabled'}")
    
    def _normalize_user_id(self, user_id: str) -> int:
        """Convert any user_id (numeric or string) to a stable integer for session memory.
        Tries direct int conversion; falls back to a deterministic SHA-256 based hash.
        """
        try:
            return int(str(user_id))
        except Exception:
            import hashlib
            digest = hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()
            # Use first 12 hex chars to fit into 32-bit-ish range but keep low collision risk
            return int(digest[:12], 16)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {
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
        
        # Check provider-specific requirements
        provider = config['llm_provider']
        if provider == 'openai' and not os.getenv('OPENAI_API_KEY'):
            raise ValueError('OPENAI_API_KEY required for OpenAI provider')
        elif provider == 'gemini' and not os.getenv('GOOGLE_AI_API_KEY'):
            raise ValueError('GOOGLE_AI_API_KEY required for Gemini provider')
        elif provider == 'vertex_ai' and not os.getenv('GOOGLE_CLOUD_PROJECT_ID'):
            raise ValueError('GOOGLE_CLOUD_PROJECT_ID required for Vertex AI provider')
        
        return config
    
    def _init_rag_system(self):
        """Initialize the RAG system with ChromaDB."""
        if not self.config['use_rag']:
            logger.info("RAG system disabled")
            return
        
        try:
            # For embeddings, we'll use OpenAI embeddings regardless of the main LLM provider
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
                collection_name="web_messenger_knowledge",
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
    
    async def generate_response(self, message_text: str, user_id: str, is_voice: bool = False) -> str:
        """Generate response using the configured LLM provider with RAG context."""
        try:
            normalized_user_id = self._normalize_user_id(user_id)
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
                    self.session_memory.add_message(normalized_user_id, "user", message_text)
                    self.session_memory.add_message(normalized_user_id, "assistant", response)
                
                return f"⚡ {response}"
            
            # Regular processing
            # Analyze question type for appropriate response length
            question_analysis = self._analyze_question_type(message_text)
            
            # For voice messages, optimize for shorter responses
            if is_voice:
                question_analysis['max_tokens'] = min(question_analysis['max_tokens'], 150)
                question_analysis['length_instruction'] = 'Keep response very concise for voice (2-3 short sentences max)'
            
            # Get session context
            session_context = ""
            if self.config['use_memory']:
                session_context = self.session_memory.get_context_for_llm(normalized_user_id)
            
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
                self.session_memory.add_message(normalized_user_id, "user", message_text)
                self.session_memory.add_message(normalized_user_id, "assistant", response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Sorry, our servers are a bit loaded right now, try again later [6656]"
    
    async def process_voice_message(self, audio_data: bytes, user_id: str) -> tuple[Optional[str], Optional[str]]:
        """
        Process voice message: transcribe and generate response.
        
        Returns:
            tuple: (transcribed_text, response_text) or (None, None) if failed
        """
        try:
            # Convert speech to text
            transcribed_text = await voice_processor.speech_to_text(audio_data)
            if not transcribed_text:
                return None, "Sorry, I couldn't understand the voice message. Please try again or send a text message."
            
            logger.info(f"Voice message transcribed: {transcribed_text}")
            
            # Generate response optimized for voice
            response_text = await self.generate_response(transcribed_text, user_id, is_voice=True)
            
            return transcribed_text, response_text
            
        except Exception as e:
            logger.error(f"Error processing voice message: {e}")
            return None, "Sorry, there was an error processing your voice message. Please try again."
    
    async def connect_websocket(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection and manage it."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user {user_id}")
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                message_type = message_data.get('type', 'text')
                content = message_data.get('content', '')
                session_id = message_data.get('session_id', str(uuid.uuid4()))
                
                logger.info(f"Received {message_type} message from user {user_id}: {content[:50]}...")
                
                if message_type == 'text':
                    # Process text message
                    response = await self.generate_response(content, user_id)
                    
                    # Send response back
                    response_data = {
                        'type': 'text',
                        'content': response,
                        'user_id': user_id,
                        'session_id': session_id,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    await websocket.send_text(json.dumps(response_data))
                
                elif message_type == 'voice':
                    # For voice messages via WebSocket, we expect the client to send audio data
                    # This is a simplified implementation - in practice, you'd handle binary data
                    logger.warning("Voice messages via WebSocket not fully implemented - use REST API instead")
                    
                    response_data = {
                        'type': 'error',
                        'content': 'Voice messages via WebSocket not supported - use REST API',
                        'user_id': user_id,
                        'session_id': session_id,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    await websocket.send_text(json.dumps(response_data))
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket connection for user {user_id}: {e}")
        finally:
            if user_id in self.active_connections:
                del self.active_connections[user_id]

# Initialize FastAPI app
app = FastAPI(title="Agent Daredevil Web Messenger", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize bot
bot = WebMessengerBot()

# Serve static files (for the test frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Root endpoint - serve the test frontend."""
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "voice_enabled": bot.voice_enabled,
        "rag_enabled": bot.config['use_rag'],
        "memory_enabled": bot.config['use_memory'],
        "llm_provider": bot.llm_provider.get_model_name()
    }

@app.post("/chat")
async def chat_endpoint(
    message: str = Form(...),
    type: str = Form(...),
    sessionId: str = Form(...),
    userId: str = Form(...),
    username: str = Form(...),
    audio: Optional[UploadFile] = File(None)
):
    """
    Main chat endpoint that matches frontend requirements.
    Handles both text and voice messages with FormData.
    """
    try:
        logger.info(f"Processing {type} message from user {username} ({userId}): {message[:50]}...")
        
        # Track user session with username
        if userId not in bot.user_sessions:
            bot.user_sessions[userId] = {
                'username': username,
                'session_id': sessionId,
                'created_at': datetime.now()
            }
        else:
            # Update username if changed
            bot.user_sessions[userId]['username'] = username
            bot.user_sessions[userId]['session_id'] = sessionId
        
        # Validate message type
        if type not in ['text', 'voice']:
            raise HTTPException(status_code=400, detail="Type must be 'text' or 'voice'")
        
        # For voice messages, process audio if provided
        if type == 'voice':
            if not audio:
                raise HTTPException(status_code=400, detail="Audio file required for voice messages")
            
            # Validate audio file
            if not audio.content_type or not audio.content_type.startswith('audio/'):
                raise HTTPException(status_code=400, detail="File must be an audio file")
            
            # Read audio data
            audio_data = await audio.read()
            
            # Process voice message
            transcribed_text, response_text = await bot.process_voice_message(audio_data, userId)
            
            if not transcribed_text:
                raise HTTPException(status_code=400, detail="Could not transcribe voice message")
            
            # Generate voice response if possible
            voice_audio = None
            if response_text and bot.voice_enabled:
                voice_audio = await voice_processor.text_to_speech(response_text)
            
            # Prepare response
            response_data = {
                "message": response_text,
                "type": "voice",
                "audioUrl": None
            }
            
            # If we have voice audio, save it and provide URL
            if voice_audio:
                import tempfile
                import os
                
                # Create a unique filename
                audio_filename = f"voice_response_{userId}_{uuid.uuid4().hex[:8]}.mp3"
                audio_path = os.path.join("temp_voice_files", audio_filename)
                
                # Ensure directory exists
                os.makedirs("temp_voice_files", exist_ok=True)
                
                # Save audio file
                with open(audio_path, 'wb') as f:
                    f.write(voice_audio)
                
                # Provide URL for the audio file
                response_data["audioUrl"] = f"/api/voice/{audio_filename}"
            
            return response_data
        
        else:  # text message
            # Generate text response (userId may be non-numeric; backend will normalize)
            response_text = await bot.generate_response(message, userId)
            
            return {
                "message": response_text,
                "type": "text",
                "audioUrl": None
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/message/text")
async def send_text_message(message: TextMessage):
    """Send a text message and get a text response."""
    try:
        logger.info(f"Processing text message from user {message.user_id}: {message.message[:50]}...")
        
        # Generate response
        response = await bot.generate_response(message.message, message.user_id)
        
        return BotResponse(
            message=response,
            message_type="text",
            user_id=message.user_id,
            session_id=message.session_id or str(uuid.uuid4()),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing text message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/message/voice")
async def send_voice_message(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: Optional[str] = Form(None)
):
    """Send a voice message and get both transcription and response."""
    try:
        if not bot.voice_enabled:
            raise HTTPException(status_code=400, detail="Voice features are disabled")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        logger.info(f"Processing voice message from user {user_id}")
        
        # Read audio data
        audio_data = await file.read()
        
        # Process voice message
        transcribed_text, response_text = await bot.process_voice_message(audio_data, user_id)
        
        if not transcribed_text:
            raise HTTPException(status_code=400, detail="Could not transcribe voice message")
        
        # Generate voice response if possible
        voice_audio = None
        if response_text and bot.voice_enabled:
            voice_audio = await voice_processor.text_to_speech(response_text)
        
        # Prepare response
        response_data = {
            "transcription": transcribed_text,
            "text_response": response_text,
            "voice_response_available": voice_audio is not None,
            "user_id": user_id,
            "session_id": session_id or str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
        
        # If we have voice audio, save it temporarily and return the path
        if voice_audio:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(voice_audio)
                temp_file_path = temp_file.name
            
            response_data["voice_file_path"] = temp_file_path
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/voice/{filename}")
async def get_voice_file(filename: str):
    """Serve generated voice files."""
    try:
        # Security: Only allow files from temp_voice_files directory
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        file_path = os.path.join("temp_voice_files", filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Voice file not found")
        
        return FileResponse(file_path, media_type="audio/mpeg")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving voice file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time communication."""
    await bot.connect_websocket(websocket, user_id)

@app.get("/api/stats")
async def get_stats():
    """Get bot statistics."""
    try:
        stats = {
            "voice_enabled": bot.voice_enabled,
            "rag_enabled": bot.config['use_rag'],
            "memory_enabled": bot.config['use_memory'],
            "llm_provider": bot.llm_provider.get_model_name(),
            "active_connections": len(bot.active_connections)
        }
        
        if bot.config['use_rag'] and bot.vectorstore:
            try:
                client = chromadb.PersistentClient(path=bot.config['chroma_db_path'])
                collection = client.get_collection("web_messenger_knowledge")
                stats["knowledge_base_chunks"] = collection.count()
            except:
                stats["knowledge_base_chunks"] = 0
        
        if bot.config['use_memory']:
            memory_stats = bot.session_memory.get_stats()
            stats.update(memory_stats)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "web_messenger_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
