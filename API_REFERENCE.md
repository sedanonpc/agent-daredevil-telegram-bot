# Agent Daredevil - API Reference

**Version**: 1.0.0  
**Last Updated**: 2024

---

## Table of Contents

1. [Overview](#overview)
2. [Web Messenger API](#web-messenger-api)
3. [Python API](#python-api)
4. [Error Handling](#error-handling)
5. [Rate Limits](#rate-limits)
6. [Authentication](#authentication)

---

## 1. Overview

Agent Daredevil provides two main API interfaces:

1. **Web Messenger API**: REST and WebSocket endpoints for web frontends
2. **Python API**: Internal Python modules for programmatic access

---

## 2. Web Messenger API

### Base URL

- **Development**: `http://localhost:8000`
- **Production**: Configured via environment

### Endpoints

#### POST /chat

Main chat endpoint supporting both text and voice messages.

**Request** (multipart/form-data):
```
message: string (required)
type: "text" | "voice" (required)
sessionId: string (required)
userId: string (required)
username: string (required)
audio: file (optional, required for voice type)
```

**Response**:
```json
{
  "message": "string",
  "type": "text" | "voice",
  "audioUrl": "string | null"
}
```

**Example** (Text):
```bash
curl -X POST http://localhost:8000/chat \
  -F "message=Hello, how are you?" \
  -F "type=text" \
  -F "sessionId=session123" \
  -F "userId=user456" \
  -F "username=testuser"
```

**Example** (Voice):
```bash
curl -X POST http://localhost:8000/chat \
  -F "message=Transcribed text" \
  -F "type=voice" \
  -F "sessionId=session123" \
  -F "userId=user456" \
  -F "username=testuser" \
  -F "audio=@voice_message.mp3"
```

**Status Codes**:
- `200`: Success
- `400`: Bad request (missing fields, invalid type)
- `500`: Server error

---

#### POST /api/message/text

Send a text message and receive a text response.

**Request** (JSON):
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
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/message/text \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the weather today?",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

---

#### POST /api/message/voice

Send a voice message and receive transcription + response.

**Request** (multipart/form-data):
```
file: audio file (required)
user_id: string (required)
session_id: string (optional)
```

**Response**:
```json
{
  "transcription": "string",
  "text_response": "string",
  "voice_response_available": boolean,
  "user_id": "string",
  "session_id": "string",
  "timestamp": "2024-01-01T12:00:00Z",
  "voice_file_path": "string (optional)"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/message/voice \
  -F "file=@voice_message.mp3" \
  -F "user_id=user123" \
  -F "session_id=session456"
```

**Status Codes**:
- `200`: Success
- `400`: Bad request (no file, invalid file type, voice disabled)
- `500`: Server error

---

#### GET /api/voice/{filename}

Retrieve a generated voice file.

**Parameters**:
- `filename`: Voice file filename (from previous response)

**Response**: Audio file (MP3)

**Example**:
```bash
curl http://localhost:8000/api/voice/voice_response_user123_abc123.mp3 \
  --output response.mp3
```

**Status Codes**:
- `200`: Success
- `400`: Invalid filename
- `404`: File not found

---

#### WebSocket /ws/{user_id}

Real-time bidirectional communication.

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/user123');
```

**Send Message** (JSON):
```json
{
  "type": "text" | "voice",
  "content": "string",
  "user_id": "string",
  "session_id": "string (optional)"
}
```

**Receive Message** (JSON):
```json
{
  "type": "text" | "voice" | "error",
  "content": "string",
  "user_id": "string",
  "session_id": "string",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Example** (JavaScript):
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/user123');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'text',
    content: 'Hello!',
    user_id: 'user123',
    session_id: 'session456'
  }));
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log('Response:', response.content);
};
```

**Note**: Voice messages via WebSocket not fully implemented. Use REST API for voice.

---

#### GET /health

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "voice_enabled": boolean,
  "rag_enabled": boolean,
  "memory_enabled": boolean,
  "llm_provider": "string"
}
```

**Example**:
```bash
curl http://localhost:8000/health
```

---

#### GET /api/stats

Get bot statistics.

**Response**:
```json
{
  "voice_enabled": boolean,
  "rag_enabled": boolean,
  "memory_enabled": boolean,
  "llm_provider": "string",
  "active_connections": integer,
  "knowledge_base_chunks": integer,
  "total_sessions": integer,
  "total_messages": integer
}
```

**Example**:
```bash
curl http://localhost:8000/api/stats
```

---

#### GET /

Serve the test frontend (if available).

**Response**: HTML page

---

## 3. Python API

### 3.1 LLM Provider API

**Module**: `llm_provider`

**Get Provider**:
```python
from llm_provider import get_llm_provider

provider = get_llm_provider()
```

**Generate Response**:
```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
]

response = await provider.generate_response(
    messages=messages,
    max_tokens=500,
    temperature=0.7
)
```

**Stream Response**:
```python
async for chunk in provider.generate_stream(messages):
    print(chunk, end='', flush=True)
```

**Get Model Name**:
```python
model_name = provider.get_model_name()
```

---

### 3.2 Session Memory API

**Module**: `session_memory`

**Initialize**:
```python
from session_memory import SessionMemoryManager

memory = SessionMemoryManager(
    db_path='./memory.db',
    session_timeout_hours=24,
    max_session_messages=50
)
```

**Add Message**:
```python
memory.add_message(
    user_id=12345,
    role="user",
    content="Hello!"
)
```

**Get Context**:
```python
context = memory.get_context_for_llm(user_id=12345)
```

**Get or Create Session**:
```python
session = memory.get_or_create_session(user_id=12345)
```

**Get Stats**:
```python
stats = memory.get_stats()
```

---

### 3.3 Voice Processor API

**Module**: `voice_processor`

**Initialize**:
```python
from voice_processor import voice_processor

# Already initialized as singleton
```

**Check if Enabled**:
```python
if voice_processor.is_enabled():
    # Voice features available
```

**Speech to Text**:
```python
with open('audio.mp3', 'rb') as f:
    audio_data = f.read()

text = await voice_processor.speech_to_text(audio_data)
```

**Text to Speech**:
```python
audio_bytes = await voice_processor.text_to_speech("Hello world!")
with open('output.mp3', 'wb') as f:
    f.write(audio_bytes)
```

**Process Voice Message** (Telegram):
```python
transcribed = await voice_processor.process_voice_message(event)
```

---

### 3.4 RAG System API

**Module**: `rag_manager`, `multi_domain_rag`

**Search Knowledge Base**:
```python
from telegram_bot_rag import AgentDaredevilBot

bot = AgentDaredevilBot()
results = await bot.search_knowledge_base("query", k=3)
```

**Add Document** (via RAG Manager UI):
```python
# Use Streamlit UI: streamlit run rag_manager.py
# Or programmatically via ChromaDB client
```

---

### 3.5 Bot Engine API

**Module**: `telegram_bot_rag`

**Initialize Bot**:
```python
from telegram_bot_rag import AgentDaredevilBot

bot = AgentDaredevilBot()
```

**Generate Response**:
```python
response = await bot.generate_response(
    message_text="Hello!",
    user_id=12345,
    is_voice=False
)
```

**Check God Command**:
```python
is_god, instruction = bot._is_god_command("⚡GOD: Say hello")
```

---

## 4. Error Handling

### 4.1 HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request parameters |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error occurred |

### 4.2 Error Response Format

```json
{
  "detail": "Error message description"
}
```

**Example**:
```json
{
  "detail": "Audio file required for voice messages"
}
```

### 4.3 Common Errors

**Missing Required Field**:
```json
{
  "detail": "Field 'message' is required"
}
```

**Invalid File Type**:
```json
{
  "detail": "File must be an audio file"
}
```

**Voice Features Disabled**:
```json
{
  "detail": "Voice features are disabled"
}
```

**Transcription Failed**:
```json
{
  "detail": "Could not transcribe voice message"
}
```

---

## 5. Rate Limits

### 5.1 Current Limits

**No explicit rate limiting implemented** (recommended for production)

**Recommended Limits**:
- Per user: 10 messages/minute
- Per IP: 100 requests/minute
- WebSocket: 1 connection per user

### 5.2 Provider Rate Limits

**OpenAI**:
- Tier-dependent limits
- Check: https://platform.openai.com/docs/guides/rate-limits

**Google Gemini**:
- Project-dependent limits
- Check: Google Cloud Console

**ElevenLabs**:
- Tier-dependent limits
- Check: ElevenLabs dashboard

---

## 6. Authentication

### 6.1 Web API Authentication

**Current**: None (public endpoints)

**Recommended**: API key authentication

**Example Implementation**:
```python
# Add to FastAPI endpoints
from fastapi import Header

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv('API_KEY'):
        raise HTTPException(status_code=401, detail="Invalid API key")
```

### 6.2 Telegram Authentication

**Handled by Telethon**:
- API ID/Hash validation
- Phone number verification
- Session token management

### 6.3 Environment Variables

All API keys stored in environment variables:
- `OPENAI_API_KEY`
- `GOOGLE_AI_API_KEY`
- `ELEVENLABS_API_KEY`
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`

---

## Appendix: Code Examples

### Complete Python Example

```python
import asyncio
from llm_provider import get_llm_provider
from session_memory import SessionMemoryManager
from voice_processor import voice_processor

async def main():
    # Initialize components
    llm = get_llm_provider()
    memory = SessionMemoryManager()
    
    user_id = 12345
    message = "What is the weather today?"
    
    # Add user message
    memory.add_message(user_id, "user", message)
    
    # Get context
    context = memory.get_context_for_llm(user_id)
    
    # Prepare messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": context + "\n\nUser: " + message}
    ]
    
    # Generate response
    response = await llm.generate_response(messages)
    
    # Store response
    memory.add_message(user_id, "assistant", response)
    
    print(f"Response: {response}")

asyncio.run(main())
```

### Complete REST API Example

```python
import requests

# Text message
response = requests.post(
    'http://localhost:8000/chat',
    data={
        'message': 'Hello!',
        'type': 'text',
        'sessionId': 'session123',
        'userId': 'user456',
        'username': 'testuser'
    }
)
print(response.json())

# Voice message
with open('voice.mp3', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/chat',
        data={
            'message': 'Transcribed text',
            'type': 'voice',
            'sessionId': 'session123',
            'userId': 'user456',
            'username': 'testuser'
        },
        files={'audio': f}
    )
print(response.json())
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2024

