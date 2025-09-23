# Agent Daredevil Web Messenger

A FastAPI-based web server that provides REST API and WebSocket endpoints for connecting frontend messenger apps to the Agent Daredevil chatbot.

## Features

- **REST API** for text and voice messages
- **WebSocket** for real-time communication
- **Voice Processing** with speech-to-text and text-to-speech
- **Message Type Detection** (text vs voice)
- **Session Memory** management
- **RAG Integration** with ChromaDB
- **Multi-LLM Support** (OpenAI, Gemini, Vertex AI)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file with your API keys:

```env
# Required for all providers
OPENAI_API_KEY=your_openai_api_key_here

# For Gemini
GOOGLE_AI_API_KEY=your_google_ai_api_key_here

# For Vertex AI
GOOGLE_CLOUD_PROJECT_ID=your_project_id_here

# Voice Processing (Optional)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here

# LLM Provider (openai, gemini, vertex_ai)
LLM_PROVIDER=openai

# RAG and Memory
USE_RAG=True
USE_MEMORY=True
CHROMA_DB_PATH=./chroma_db
MEMORY_DB_PATH=./memory.db
```

### 3. Launch the Server

```bash
python launch_web_messenger.py
```

The server will start on `http://localhost:8000`

### 4. Test the Connection

Open your browser and navigate to `http://localhost:8000` to use the test frontend.

## API Endpoints

### Main Chat Endpoint (Frontend Integration)

#### Send Message (Text or Voice)
```http
POST /chat
Content-Type: multipart/form-data

message: "Hello, how are you?"
type: "text" | "voice"
sessionId: "session_123"
userId: "user_456"
username: "JohnDoe"
audio: [audio_file] (required for voice messages)
```

**Response:**
```json
{
    "message": "Hello! I'm doing great, thanks for asking!",
    "type": "text" | "voice",
    "audioUrl": "/api/voice/voice_response_user_456_abc123.mp3" (for voice responses)
}
```

### Legacy REST API

#### Send Text Message
```http
POST /api/message/text
Content-Type: application/json

{
    "message": "Hello, how are you?",
    "user_id": "user123",
    "session_id": "optional_session_id"
}
```

**Response:**
```json
{
    "message": "Hello! I'm doing great, thanks for asking!",
    "message_type": "text",
    "user_id": "user123",
    "session_id": "generated_session_id",
    "timestamp": "2024-01-01T12:00:00"
}
```

#### Send Voice Message
```http
POST /api/message/voice
Content-Type: multipart/form-data

file: [audio_file]
user_id: user123
session_id: optional_session_id
```

**Response:**
```json
{
    "transcription": "Hello, how are you?",
    "text_response": "Hello! I'm doing great, thanks for asking!",
    "voice_response_available": true,
    "voice_file_path": "/tmp/voice_response.mp3",
    "user_id": "user123",
    "session_id": "generated_session_id",
    "timestamp": "2024-01-01T12:00:00"
}
```

#### Get Voice File
```http
GET /api/voice/{file_path}
```

Returns the generated voice response as an MP3 file.

#### Health Check
```http
GET /health
```

#### Get Statistics
```http
GET /api/stats
```

### WebSocket API

Connect to: `ws://localhost:8000/ws/{user_id}`

#### Send Message
```json
{
    "type": "text",
    "content": "Hello, how are you?",
    "user_id": "user123",
    "session_id": "optional_session_id"
}
```

#### Receive Response
```json
{
    "type": "text",
    "content": "Hello! I'm doing great, thanks for asking!",
    "user_id": "user123",
    "session_id": "session_id",
    "timestamp": "2024-01-01T12:00:00"
}
```

## Message Types

### Text Messages
- **Input**: Plain text string
- **Output**: Text response
- **Use Case**: General conversation, questions, commands

### Voice Messages
- **Input**: Audio file (MP3, WAV, OGG, etc.)
- **Processing**: Speech-to-text → LLM response → Text-to-speech
- **Output**: Transcription + text response + voice response
- **Use Case**: Voice conversations, hands-free interaction

## Frontend Integration

### JavaScript Example

```javascript
// Send text message using the main /chat endpoint
async function sendTextMessage(message, userId, username, sessionId) {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('type', 'text');
    formData.append('userId', userId);
    formData.append('username', username);
    formData.append('sessionId', sessionId);
    
    const response = await fetch('/chat', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    return data;
}

// Send voice message using the main /chat endpoint
async function sendVoiceMessage(audioFile, message, userId, username, sessionId) {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('type', 'voice');
    formData.append('userId', userId);
    formData.append('username', username);
    formData.append('sessionId', sessionId);
    formData.append('audio', audioFile);
    
    const response = await fetch('/chat', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    return data;
}

// Legacy API examples (still available)
async function sendTextMessageLegacy(message, userId) {
    const response = await fetch('/api/message/text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            user_id: userId
        })
    });
    
    const data = await response.json();
    return data.message;
}

async function sendVoiceMessageLegacy(audioFile, userId) {
    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('user_id', userId);
    
    const response = await fetch('/api/message/voice', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    return data;
}

// WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws/user123');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data.content);
};

// Send message via WebSocket
ws.send(JSON.stringify({
    type: 'text',
    content: 'Hello!',
    user_id: 'user123'
}));
```

### React Example

```jsx
import React, { useState, useEffect } from 'react';

function ChatComponent() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [ws, setWs] = useState(null);
    
    useEffect(() => {
        const websocket = new WebSocket('ws://localhost:8000/ws/user123');
        
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setMessages(prev => [...prev, {
                content: data.content,
                isUser: false,
                timestamp: data.timestamp
            }]);
        };
        
        setWs(websocket);
        
        return () => websocket.close();
    }, []);
    
    const sendMessage = () => {
        if (ws && input.trim()) {
            ws.send(JSON.stringify({
                type: 'text',
                content: input,
                user_id: 'user123'
            }));
            
            setMessages(prev => [...prev, {
                content: input,
                isUser: true,
                timestamp: new Date().toISOString()
            }]);
            
            setInput('');
        }
    };
    
    return (
        <div>
            <div>
                {messages.map((msg, index) => (
                    <div key={index} className={msg.isUser ? 'user-message' : 'bot-message'}>
                        {msg.content}
                    </div>
                ))}
            </div>
            <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            />
            <button onClick={sendMessage}>Send</button>
        </div>
    );
}
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Yes* | - |
| `GOOGLE_AI_API_KEY` | Google AI API key | Yes* | - |
| `GOOGLE_CLOUD_PROJECT_ID` | Google Cloud project ID | Yes* | - |
| `LLM_PROVIDER` | LLM provider (openai/gemini/vertex_ai) | No | openai |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for TTS | No | - |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice ID | No | zYcjlYFOd3taleS0gkk3 |
| `USE_RAG` | Enable RAG system | No | True |
| `USE_MEMORY` | Enable session memory | No | True |
| `CHROMA_DB_PATH` | ChromaDB storage path | No | ./chroma_db |
| `MEMORY_DB_PATH` | Session memory DB path | No | ./memory.db |

*At least one LLM provider API key is required.

### Character Configuration

The bot uses the character configuration from `cryptodevil.character.json`. You can customize the bot's personality by modifying this file.

## Deployment

### Local Development
```bash
python launch_web_messenger.py
```

### Production with Gunicorn
```bash
pip install gunicorn
gunicorn web_messenger_server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "launch_web_messenger.py"]
```

## Troubleshooting

### Common Issues

1. **Voice features not working**
   - Check if `ELEVENLABS_API_KEY` is set
   - Verify ElevenLabs API permissions
   - Check audio file format (MP3, WAV, OGG supported)

2. **RAG system not working**
   - Ensure `OPENAI_API_KEY` is set (required for embeddings)
   - Check if ChromaDB directory exists and is writable
   - Verify knowledge base has been populated

3. **WebSocket connection issues**
   - Check firewall settings
   - Ensure WebSocket is supported by your proxy/load balancer
   - Verify CORS settings for cross-origin requests

4. **Memory issues**
   - Check database file permissions
   - Monitor disk space usage
   - Adjust `MAX_SESSION_MESSAGES` if needed

### Logs

Check the following log files:
- `web_messenger.log` - Main application logs
- `telegram_bot_rag.log` - Shared bot logic logs

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for interactive API documentation powered by Swagger UI.

## Security Considerations

- **CORS**: Currently set to allow all origins (`*`). In production, specify your frontend domain.
- **Authentication**: No authentication is implemented. Add JWT or session-based auth for production.
- **Rate Limiting**: Consider implementing rate limiting for production use.
- **File Upload**: Voice files are temporarily stored. Implement cleanup mechanisms.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the same terms as the main Agent Daredevil project.
