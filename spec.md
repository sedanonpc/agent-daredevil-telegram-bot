# Agent Daredevil - Technical Specification

**Version:** 1.0.0  
**Last Updated:** 2024  
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [API Specifications](#api-specifications)
5. [Data Models](#data-models)
6. [Integration Points](#integration-points)
7. [Performance Requirements](#performance-requirements)
8. [Security Specifications](#security-specifications)
9. [Deployment Specifications](#deployment-specifications)

---

## 1. Overview

### 1.1 Project Description

Agent Daredevil is a sophisticated Telegram bot that provides AI-powered conversational capabilities with multi-domain knowledge retrieval, voice processing, and character consistency. The system supports multiple LLM providers (OpenAI, Google Gemini, Vertex AI) through a unified abstraction layer.

### 1.2 Key Features

- **Multi-LLM Provider Support**: Seamless switching between OpenAI GPT, Google Gemini, and Vertex AI
- **Retrieval-Augmented Generation (RAG)**: ChromaDB-based vector search for knowledge retrieval
- **Voice Processing**: Speech-to-text (OpenAI Whisper) and text-to-speech (ElevenLabs)
- **Session Memory**: Persistent conversation history with SQLite backend
- **Character Consistency**: JSON-based character personality system
- **Web Messenger API**: FastAPI-based REST and WebSocket endpoints
- **Multi-Domain Support**: NBA Basketball and Formula 1 Racing domain expertise

### 1.3 Technology Stack

- **Language**: Python 3.8+
- **Telegram API**: Telethon 1.40.0+
- **LLM Providers**: OpenAI, Google Gemini, Vertex AI
- **Vector Database**: ChromaDB 0.4.0+
- **RAG Framework**: LangChain 0.1.0+
- **Web Framework**: FastAPI 0.104.0+
- **Database**: SQLite3 (session memory)
- **Voice STT**: OpenAI Whisper API
- **Voice TTS**: ElevenLabs API

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Daredevil System                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐ │
│  │ Telegram Bot │◄────►│ Web Messenger│◄────►│ Frontend │ │
│  │  (Telethon)  │      │   (FastAPI)  │      │   (UI)   │ │
│  └──────┬───────┘      └──────┬───────┘      └──────────┘ │
│         │                      │                            │
│         └──────────┬───────────┘                            │
│                    │                                         │
│         ┌──────────▼───────────┐                            │
│         │   Core Bot Engine    │                            │
│         │  (telegram_bot_rag)  │                            │
│         └──────────┬───────────┘                            │
│                    │                                         │
│    ┌───────────────┼───────────────┐                         │
│    │               │               │                         │
│ ┌──▼──┐      ┌────▼────┐    ┌───▼───┐                      │
│ │ LLM │      │   RAG    │    │ Voice │                      │
│ │Provider│   │  System  │    │Processor│                     │
│ └──┬──┘      └────┬─────┘    └───┬───┘                      │
│    │              │              │                          │
│ ┌──▼──────────────▼──────────────▼──┐                       │
│ │      Session Memory Manager       │                       │
│ │         (SQLite Database)          │                       │
│ └───────────────────────────────────┘                       │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │   ChromaDB    │      │   External  │                     │
│  │  (Vector DB)  │      │    APIs     │                     │
│  └──────────────┘      └──────────────┘                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Component Interaction Flow

1. **Message Reception**: Telegram client receives message → Bot engine processes
2. **Context Retrieval**: Session memory + RAG system retrieve relevant context
3. **LLM Processing**: Provider abstraction layer generates response
4. **Response Formatting**: Response length limitation + character consistency
5. **Delivery**: Response sent via Telegram or Web API

---

## 3. Core Components

### 3.1 Telegram Bot (`telegram_bot_rag.py`)

**Purpose**: Main bot engine handling Telegram interactions

**Key Classes**:
- `AgentDaredevilBot`: Main bot class orchestrating all components

**Key Methods**:
- `_load_config()`: Load configuration from environment
- `_init_rag_system()`: Initialize ChromaDB vector store
- `_load_character()`: Load character personality JSON
- `generate_response()`: Generate AI response with RAG context
- `_is_god_command()`: Detect override commands
- `_analyze_question_type()`: Classify question for response optimization

**Dependencies**:
- `llm_provider.py`
- `session_memory.py`
- `voice_processor.py`
- `rag_manager.py` (optional)

### 3.2 LLM Provider Abstraction (`llm_provider.py`)

**Purpose**: Unified interface for multiple LLM providers

**Key Classes**:
- `LLMProvider`: Abstract base class
- `OpenAIProvider`: OpenAI GPT implementation
- `GeminiProvider`: Google Gemini implementation
- `VertexAIProvider`: Vertex AI implementation

**Key Methods**:
- `generate_response()`: Generate text response
- `generate_stream()`: Generate streaming response
- `get_model_name()`: Get current model identifier
- `limit_response_length()`: Enforce 3-5 sentence limit

**Supported Providers**:
- OpenAI: `gpt-4`, `gpt-3.5-turbo`
- Gemini: `gemini-2.5-flash`, `gemini-1.5-pro`, `gemini-1.5-flash`
- Vertex AI: `google/gemini-2.0-flash-001`

### 3.3 RAG System (`rag_manager.py`, `multi_domain_rag.py`)

**Purpose**: Knowledge retrieval and vector search

**Components**:
- ChromaDB vector database
- LangChain embeddings (OpenAI)
- Multi-domain support (NBA, F1, General)

**Key Features**:
- Semantic search across knowledge base
- Domain-specific collections
- Document chunking and embedding
- Similarity search with configurable k

### 3.4 Session Memory (`session_memory.py`)

**Purpose**: Persistent conversation history

**Database Schema**:
```sql
conversation_sessions:
  - session_id (TEXT PRIMARY KEY)
  - user_id (INTEGER)
  - created_at (TIMESTAMP)
  - last_activity (TIMESTAMP)
  - message_count (INTEGER)
  - is_active (BOOLEAN)

messages:
  - id (INTEGER PRIMARY KEY)
  - session_id (TEXT FOREIGN KEY)
  - user_id (INTEGER)
  - role (TEXT: "user" | "assistant")
  - content (TEXT)
  - timestamp (TIMESTAMP)
```

**Key Methods**:
- `get_or_create_session()`: Get/create user session
- `add_message()`: Store message in history
- `get_context_for_llm()`: Retrieve conversation context
- `cleanup_old_sessions()`: Remove expired sessions

### 3.5 Voice Processor (`voice_processor.py`)

**Purpose**: Speech-to-text and text-to-speech processing

**Components**:
- OpenAI Whisper API (STT)
- ElevenLabs API (TTS)

**Key Methods**:
- `speech_to_text()`: Convert audio to text
- `text_to_speech()`: Convert text to audio
- `is_enabled()`: Check if voice features available
- `process_voice_message()`: Process Telegram voice note

### 3.6 Web Messenger Server (`web_messenger_server.py`)

**Purpose**: REST API and WebSocket server for web frontend

**Endpoints**:
- `POST /chat`: Main chat endpoint (text/voice)
- `POST /api/message/text`: Text message API
- `POST /api/message/voice`: Voice message API
- `GET /api/voice/{filename}`: Serve generated voice files
- `WebSocket /ws/{user_id}`: Real-time WebSocket communication
- `GET /health`: Health check endpoint
- `GET /api/stats`: Bot statistics

**Key Classes**:
- `WebMessengerBot`: Bot instance for web API
- `ChatRequest`: Request model
- `ChatResponse`: Response model

---

## 4. API Specifications

### 4.1 Telegram Bot API

**Platform**: Telegram via Telethon

**Message Format**:
- Text messages: Plain text
- Voice messages: Audio file (OGG Opus)
- Commands: `/start`, `/help` (if implemented)

**Response Format**:
- Text responses: 3-5 sentences (6 for data-heavy)
- Voice responses: MP3 audio file
- Error messages: User-friendly error text

### 4.2 Web Messenger API

#### POST /chat

**Request**:
```json
{
  "message": "string",
  "type": "text" | "voice",
  "sessionId": "string",
  "userId": "string",
  "username": "string",
  "audio": "file" (multipart/form-data, optional)
}
```

**Response**:
```json
{
  "message": "string",
  "type": "text" | "voice",
  "audioUrl": "string | null"
}
```

#### POST /api/message/text

**Request**:
```json
{
  "message": "string",
  "user_id": "string",
  "session_id": "string (optional)"
}
```

**Response**:
```json
{
  "message": "string",
  "message_type": "text",
  "user_id": "string",
  "session_id": "string",
  "timestamp": "ISO 8601 datetime"
}
```

#### WebSocket /ws/{user_id}

**Message Format**:
```json
{
  "type": "text" | "voice",
  "content": "string",
  "user_id": "string",
  "session_id": "string (optional)"
}
```

**Response Format**:
```json
{
  "type": "text" | "voice" | "error",
  "content": "string",
  "user_id": "string",
  "session_id": "string",
  "timestamp": "ISO 8601 datetime"
}
```

---

## 5. Data Models

### 5.1 Character Configuration

**File**: `cryptodevil.character.json`

**Structure**:
```json
{
  "name": "string",
  "system": "string (system prompt)",
  "bio": ["string array"],
  "messageExamples": [[{user, content}]],
  "settings": {
    "voice": {
      "model": "string"
    }
  }
}
```

### 5.2 Session Memory Models

**Message**:
```python
@dataclass
class Message:
    id: Optional[int]
    user_id: int
    role: str  # "user" | "assistant"
    content: str
    timestamp: Optional[datetime]
    session_id: Optional[str]
```

**ConversationSession**:
```python
@dataclass
class ConversationSession:
    session_id: str
    user_id: int
    created_at: datetime
    last_activity: datetime
    message_count: int
    is_active: bool
```

### 5.3 Configuration Model

**Environment Variables** (see `env.example`):
- Telegram: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE_NUMBER`
- LLM: `LLM_PROVIDER`, `OPENAI_API_KEY`, `GOOGLE_AI_API_KEY`
- RAG: `CHROMA_DB_PATH`, `USE_RAG`
- Memory: `MEMORY_DB_PATH`, `USE_MEMORY`, `SESSION_TIMEOUT_HOURS`
- Voice: `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `USE_VOICE_FEATURES`

---

## 6. Integration Points

### 6.1 External APIs

**OpenAI API**:
- Endpoint: `https://api.openai.com/v1/`
- Usage: Chat completions, Whisper transcription
- Authentication: Bearer token (`OPENAI_API_KEY`)

**Google Gemini API**:
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/`
- Usage: Chat completions
- Authentication: API key (`GOOGLE_AI_API_KEY`)

**ElevenLabs API**:
- Endpoint: `https://api.elevenlabs.io/v1/`
- Usage: Text-to-speech conversion
- Authentication: API key (`ELEVENLABS_API_KEY`)

**Telegram API**:
- Library: Telethon
- Authentication: API ID, API Hash, Phone Number

### 6.2 Database Systems

**ChromaDB**:
- Type: Vector database
- Path: `./chroma_db` (configurable)
- Collections: Domain-specific (NBA, F1, General)

**SQLite**:
- Type: Relational database
- Path: `./memory.db` (configurable)
- Tables: `conversation_sessions`, `messages`

---

## 7. Performance Requirements

### 7.1 Response Time

- **Text Response**: < 5 seconds average
- **Voice Transcription**: < 10 seconds
- **Voice Synthesis**: < 15 seconds
- **RAG Search**: < 2 seconds

### 7.2 Throughput

- **Concurrent Users**: Support 100+ concurrent sessions
- **Messages per Second**: Handle 10+ messages/second
- **API Requests**: Support 50+ requests/second

### 7.3 Resource Usage

- **Memory**: < 1GB per instance
- **CPU**: Moderate usage (I/O bound)
- **Storage**: 
  - ChromaDB: ~100MB per 10,000 documents
  - SQLite: ~10MB per 10,000 messages

### 7.4 Scalability

- **Horizontal Scaling**: Stateless design supports multiple instances
- **Database Scaling**: ChromaDB supports sharding
- **Session Management**: SQLite can be migrated to PostgreSQL for scale

---

## 8. Security Specifications

### 8.1 Authentication

- **Telegram**: API ID/Hash + Phone verification
- **OpenAI**: API key (Bearer token)
- **Google**: API key or Service Account
- **ElevenLabs**: API key

### 8.2 Data Protection

- **Session Data**: User-isolated in SQLite
- **API Keys**: Stored in environment variables (never in code)
- **Voice Files**: Temporary storage, auto-cleanup
- **Logs**: No sensitive data in logs

### 8.3 Input Validation

- **Message Length**: Max 4096 characters
- **File Upload**: Audio files only, max 20MB
- **User ID**: Validated and normalized
- **SQL Injection**: Parameterized queries

### 8.4 Rate Limiting

- **Per User**: Configurable message rate limits
- **API Calls**: Respect provider rate limits
- **Web Endpoints**: CORS configured, rate limiting recommended

---

## 9. Deployment Specifications

### 9.1 Environment Requirements

- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, Windows
- **Dependencies**: See `requirements.txt`
- **Storage**: 500MB+ free space

### 9.2 Deployment Options

**Option 1: Railway (Recommended)**
- Platform: Railway.app
- Configuration: `railway.json`
- Dockerfile: Multi-stage build
- Health Check: `/health` endpoint

**Option 2: Docker Compose**
- Configuration: `docker-compose.yml`
- Services: Bot, RAG Manager, Visualizer
- Volumes: Persistent data storage

**Option 3: Native Python**
- Direct execution: `python telegram_bot_rag.py`
- Process management: Systemd/PM2 recommended

### 9.3 Environment Variables

See `env.example` for complete list. Required variables:
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_PHONE_NUMBER`
- `LLM_PROVIDER`
- Provider-specific API keys

### 9.4 Monitoring

- **Logs**: File-based (`telegram_bot_rag.log`)
- **Health Checks**: `/health` endpoint
- **Metrics**: `/api/stats` endpoint
- **Error Tracking**: Structured logging with traceback

---

## 10. Future Enhancements

### 10.1 Planned Features

- Multi-language support
- Advanced analytics dashboard
- Plugin system for extensibility
- Integration with additional LLM providers
- Enhanced voice customization

### 10.2 Technical Debt

- Migrate SQLite to PostgreSQL for production scale
- Implement comprehensive test suite
- Add API rate limiting middleware
- Enhance error recovery mechanisms
- Optimize RAG search performance

---

## Appendix A: File Structure

```
agent-daredevil-telegram-bot/
├── telegram_bot_rag.py          # Main bot engine
├── web_messenger_server.py      # Web API server
├── llm_provider.py              # LLM abstraction layer
├── session_memory.py            # Session management
├── voice_processor.py           # Voice processing
├── rag_manager.py               # RAG system manager
├── multi_domain_rag.py          # Multi-domain RAG
├── basketball_reference_crawler.py # Web crawler
├── cryptodevil.character.json   # Character config
├── requirements.txt             # Dependencies
├── Dockerfile                   # Docker configuration
├── docker-compose.yml           # Docker Compose config
├── railway.json                 # Railway deployment config
└── docs/                        # Documentation
```

---

## Appendix B: Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| 6656 | Server overload | Retry later |
| 1001 | LLM provider error | Check API keys |
| 1002 | RAG system error | Check ChromaDB |
| 1003 | Voice processing error | Check ElevenLabs |
| 1004 | Session memory error | Check SQLite DB |

---

**Document Version**: 1.0.0  
**Last Updated**: 2024  
**Maintained By**: Development Team

