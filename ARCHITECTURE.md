# Agent Daredevil - System Architecture Documentation

**Version**: 1.0.0  
**Last Updated**: 2024

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Component Architecture](#component-architecture)
4. [Data Architecture](#data-architecture)
5. [Integration Architecture](#integration-architecture)
6. [Deployment Architecture](#deployment-architecture)
7. [Security Architecture](#security-architecture)
8. [Scalability Architecture](#scalability-architecture)

---

## 1. System Overview

### 1.1 High-Level Architecture

Agent Daredevil follows a **modular, event-driven architecture** with clear separation of concerns:

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

### 1.2 Core Principles

1. **Separation of Concerns**: Each component has a single responsibility
2. **Abstraction**: LLM providers abstracted behind unified interface
3. **Modularity**: Components can be enabled/disabled independently
4. **Extensibility**: Easy to add new providers, features, domains
5. **Stateless Design**: Bot instances are stateless (state in databases)

---

## 2. Architecture Patterns

### 2.1 Design Patterns Used

#### Provider Pattern
**Location**: `llm_provider.py`

**Purpose**: Abstract LLM provider differences

**Implementation**:
```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(...): pass

class OpenAIProvider(LLMProvider): ...
class GeminiProvider(LLMProvider): ...
class VertexAIProvider(LLMProvider): ...
```

**Benefits**:
- Easy to switch providers
- Consistent interface
- Easy to add new providers

#### Repository Pattern
**Location**: `session_memory.py`

**Purpose**: Abstract data access layer

**Implementation**:
```python
class SessionMemoryManager:
    def add_message(...)
    def get_context_for_llm(...)
    def cleanup_old_sessions(...)
```

**Benefits**:
- Database abstraction
- Easy to swap storage backends
- Centralized data access logic

#### Factory Pattern
**Location**: `llm_provider.py` → `get_llm_provider()`

**Purpose**: Create appropriate LLM provider instance

**Implementation**:
```python
def get_llm_provider() -> LLMProvider:
    provider = os.getenv('LLM_PROVIDER')
    if provider == 'openai':
        return OpenAIProvider(...)
    elif provider == 'gemini':
        return GeminiProvider(...)
    ...
```

**Benefits**:
- Centralized instantiation
- Configuration-driven
- Easy to extend

#### Strategy Pattern
**Location**: Response length limiting, question type analysis

**Purpose**: Different strategies for different scenarios

**Implementation**:
```python
def _analyze_question_type(message):
    if is_small_talk(message):
        return SmallTalkStrategy()
    elif is_analytical(message):
        return AnalyticalStrategy()
    else:
        return GeneralStrategy()
```

**Benefits**:
- Flexible response handling
- Easy to add new strategies
- Clean separation

### 2.2 Architectural Styles

#### Event-Driven Architecture
- **Telegram Events**: Telethon event handlers
- **WebSocket Events**: Real-time communication
- **Async Processing**: All I/O operations async

#### Layered Architecture
```
┌─────────────────┐
│  Presentation   │  Telegram API, Web API
├─────────────────┤
│   Application   │  Bot Engine, Response Generation
├─────────────────┤
│     Domain      │  LLM Providers, RAG, Voice
├─────────────────┤
│ Infrastructure  │  Databases, External APIs
└─────────────────┘
```

#### Microservices-Ready
- Components can be split into separate services
- Web API already separate from Telegram bot
- Database access abstracted

---

## 3. Component Architecture

### 3.1 Core Bot Engine

**File**: `telegram_bot_rag.py`

**Responsibilities**:
- Telegram event handling
- Message processing orchestration
- Response generation coordination
- Error handling and recovery

**Key Classes**:
- `AgentDaredevilBot`: Main orchestrator

**Dependencies**:
- LLM Provider
- Session Memory
- RAG System
- Voice Processor

**Interfaces**:
- Telegram API (Telethon)
- User messages (input)
- Bot responses (output)

### 3.2 LLM Provider Layer

**File**: `llm_provider.py`

**Responsibilities**:
- Abstract LLM provider differences
- Provide unified interface
- Handle provider-specific logic
- Response length limiting

**Key Classes**:
- `LLMProvider`: Abstract base
- `OpenAIProvider`: OpenAI implementation
- `GeminiProvider`: Gemini implementation
- `VertexAIProvider`: Vertex AI implementation

**Dependencies**:
- External APIs (OpenAI, Google, Vertex)

**Interfaces**:
- `generate_response()`: Generate text
- `generate_stream()`: Stream text
- `get_model_name()`: Get model info

### 3.3 RAG System

**Files**: `rag_manager.py`, `multi_domain_rag.py`

**Responsibilities**:
- Knowledge base management
- Vector search
- Document embedding
- Domain-specific retrieval

**Key Components**:
- ChromaDB vector database
- LangChain embeddings
- Document chunking
- Similarity search

**Dependencies**:
- ChromaDB
- LangChain
- OpenAI (for embeddings)

**Interfaces**:
- `add_document()`: Add knowledge
- `search_knowledge_base()`: Search knowledge
- `get_domain()`: Domain detection

### 3.4 Session Memory

**File**: `session_memory.py`

**Responsibilities**:
- Conversation history storage
- Session management
- Context retrieval
- Session cleanup

**Key Classes**:
- `SessionMemoryManager`: Main manager
- `Message`: Message model
- `ConversationSession`: Session model

**Dependencies**:
- SQLite3

**Interfaces**:
- `add_message()`: Store message
- `get_context_for_llm()`: Get context
- `get_or_create_session()`: Session management

### 3.5 Voice Processor

**File**: `voice_processor.py`

**Responsibilities**:
- Speech-to-text conversion
- Text-to-speech conversion
- Audio file handling
- Voice feature management

**Key Classes**:
- `VoiceProcessor`: Main processor

**Dependencies**:
- OpenAI Whisper API
- ElevenLabs API

**Interfaces**:
- `speech_to_text()`: Convert audio to text
- `text_to_speech()`: Convert text to audio
- `is_enabled()`: Check availability

### 3.6 Web Messenger Server

**File**: `web_messenger_server.py`

**Responsibilities**:
- REST API endpoints
- WebSocket connections
- File upload handling
- CORS management

**Key Classes**:
- `WebMessengerBot`: Bot instance for web
- `ChatRequest`: Request model
- `ChatResponse`: Response model

**Dependencies**:
- FastAPI
- Core bot components

**Interfaces**:
- REST endpoints: `/chat`, `/api/message/*`
- WebSocket: `/ws/{user_id}`
- Health: `/health`, `/api/stats`

---

## 4. Data Architecture

### 4.1 Data Flow

```
User Message
    ↓
Session Memory (retrieve context)
    ↓
RAG System (retrieve knowledge)
    ↓
LLM Provider (generate response)
    ↓
Response Formatting (length limit, character)
    ↓
User Response
```

### 4.2 Data Storage

#### Session Memory (SQLite)

**Schema**:
```sql
conversation_sessions:
  session_id (TEXT PRIMARY KEY)
  user_id (INTEGER)
  created_at (TIMESTAMP)
  last_activity (TIMESTAMP)
  message_count (INTEGER)
  is_active (BOOLEAN)

messages:
  id (INTEGER PRIMARY KEY)
  session_id (TEXT FOREIGN KEY)
  user_id (INTEGER)
  role (TEXT: "user" | "assistant")
  content (TEXT)
  timestamp (TIMESTAMP)
```

**Indexes**:
- `idx_messages_session`: (session_id, timestamp)
- `idx_messages_user`: (user_id, timestamp)

#### ChromaDB (Vector Database)

**Collections**:
- `nba_data`: NBA Basketball knowledge
- `f1_data`: Formula 1 Racing knowledge
- `general`: General knowledge
- `web_messenger_knowledge`: Web messenger knowledge

**Structure**:
- Documents: Chunked text
- Embeddings: OpenAI embeddings (1536 dimensions)
- Metadata: Domain, source, timestamp

### 4.3 Data Models

#### Message Model
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

#### Session Model
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

#### Character Model
```json
{
  "name": "string",
  "system": "string",
  "bio": ["string"],
  "messageExamples": [[{user, content}]]
}
```

---

## 5. Integration Architecture

### 5.1 External API Integrations

#### Telegram API
- **Library**: Telethon
- **Protocol**: MTProto
- **Authentication**: API ID/Hash + Phone
- **Events**: NewMessage, MessageEdited, etc.

#### OpenAI API
- **Endpoints**: 
  - Chat Completions: `/v1/chat/completions`
  - Whisper: `/v1/audio/transcriptions`
- **Authentication**: Bearer token
- **Rate Limits**: Per-tier limits

#### Google Gemini API
- **Endpoints**: `/v1beta/models/{model}:generateContent`
- **Authentication**: API key
- **Rate Limits**: Per-project limits

#### ElevenLabs API
- **Endpoints**: `/v1/text-to-speech/{voice_id}`
- **Authentication**: API key
- **Rate Limits**: Per-tier limits

### 5.2 Integration Patterns

#### Synchronous API Calls
- LLM provider calls (async)
- Voice processing (async)
- Database operations (sync)

#### Asynchronous Processing
- All I/O operations async
- Event-driven message handling
- WebSocket real-time communication

#### Error Handling
- Retry logic for transient failures
- Fallback mechanisms
- Graceful degradation

---

## 6. Deployment Architecture

### 6.1 Deployment Options

#### Option 1: Railway (Recommended)
```
GitHub Repository
    ↓
Railway Platform
    ↓
Docker Build
    ↓
Container Deployment
    ↓
Running Bot Instance
```

**Configuration**: `railway.json`

#### Option 2: Docker Compose
```
docker-compose.yml
    ↓
Multiple Services:
  - Telegram Bot
  - RAG Manager (Streamlit)
  - Knowledge Visualizer (Streamlit)
  - Web Messenger (FastAPI)
```

**Configuration**: `docker-compose.yml`

#### Option 3: Native Python
```
Systemd Service
    ↓
Python Process
    ↓
Direct Execution
```

**Configuration**: Systemd service file

### 6.2 Container Architecture

**Dockerfile Structure**:
```dockerfile
# Multi-stage build
Stage 1: Builder
  - Install build dependencies
  - Install Python packages

Stage 2: Runtime
  - Copy virtual environment
  - Install runtime dependencies
  - Set up non-root user
  - Configure health checks
```

**Container Features**:
- Non-root user execution
- Health check endpoints
- Volume mounts for persistence
- Environment variable configuration

### 6.3 Scaling Architecture

#### Horizontal Scaling
- Stateless bot instances
- Shared database (ChromaDB, SQLite → PostgreSQL)
- Load balancer (if needed)

#### Vertical Scaling
- Increase container resources
- Optimize database queries
- Cache frequently accessed data

---

## 7. Security Architecture

### 7.1 Authentication & Authorization

#### Telegram Authentication
- API ID/Hash validation
- Phone number verification
- Session token management

#### API Authentication
- API keys in environment variables
- No hardcoded credentials
- Secure key storage

#### User Isolation
- User ID-based session isolation
- No cross-user data access
- Session timeout enforcement

### 7.2 Data Security

#### Encryption
- API keys encrypted at rest (environment)
- HTTPS for API calls
- Secure session storage

#### Input Validation
- Message length limits
- File type validation
- SQL injection prevention (parameterized queries)

#### Output Sanitization
- Response content validation
- Error message sanitization
- No sensitive data in logs

### 7.3 Security Best Practices

- Environment variable configuration
- Non-root container execution
- Minimal container image
- Regular dependency updates
- Security audit logging

---

## 8. Scalability Architecture

### 8.1 Current Scalability

**Limitations**:
- SQLite: Single-writer limitation
- ChromaDB: File-based (can scale)
- Stateless design: Good for horizontal scaling

**Strengths**:
- Async I/O: Handles concurrency well
- Modular design: Easy to scale components
- Provider abstraction: Can optimize per provider

### 8.2 Scaling Strategies

#### Database Scaling
```
Current: SQLite
    ↓
Migration: PostgreSQL
    ↓
Scaling: Read replicas, connection pooling
```

#### Application Scaling
```
Single Instance
    ↓
Multiple Instances (load balanced)
    ↓
Microservices (if needed)
```

#### Caching Strategy
```
No Cache (current)
    ↓
In-Memory Cache (Redis)
    ↓
Distributed Cache (Redis Cluster)
```

### 8.3 Performance Optimization

**Current Optimizations**:
- Async I/O operations
- Database indexing
- Response length limiting
- Connection pooling (if using PostgreSQL)

**Future Optimizations**:
- Response caching
- Database query optimization
- CDN for static assets
- Rate limiting per user

---

## Appendix: Architecture Diagrams

### Component Interaction Diagram

```
[User] → [Telegram API] → [Bot Engine]
                              ↓
                    [Session Memory]
                              ↓
                    [RAG System]
                              ↓
                    [LLM Provider]
                              ↓
                    [Response Formatting]
                              ↓
[User] ← [Telegram API] ← [Bot Engine]
```

### Data Flow Diagram

```
Input: User Message
    ↓
1. Store in Session Memory
    ↓
2. Retrieve Context from Session Memory
    ↓
3. Search Knowledge Base (RAG)
    ↓
4. Combine Context + Knowledge
    ↓
5. Send to LLM Provider
    ↓
6. Format Response (length, character)
    ↓
7. Store Response in Session Memory
    ↓
Output: Formatted Response
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2024

