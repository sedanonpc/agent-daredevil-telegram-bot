# 🤖 Agent Daredevil Telegram Bot

A sophisticated Telegram bot powered by multiple LLM providers (OpenAI, Google Gemini, Vertex AI) with Retrieval-Augmented Generation (RAG) capabilities. Agent Daredevil can chat naturally, search knowledge bases, crawl websites, and maintain character consistency.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Telegram](https://img.shields.io/badge/telegram-bot-blue.svg)
![LLM](https://img.shields.io/badge/LLM-Multi--Provider-brightgreen.svg)

## ✨ Features

### 🧠 **Core Intelligence**
- **Multi-LLM Support**: Switch between OpenAI GPT-4, Google Gemini, and Vertex AI
- **Concise Responses**: All responses limited to 3-5 sentences for clarity and focus
- **RAG System**: Knowledge base retrieval using ChromaDB vector store
- **Character Consistency**: Maintains Agent Daredevil persona across conversations

### 🌐 **Knowledge Management**
- **Web Crawler**: Automated NBA statistics and website crawling
- **Document Upload**: PDF and text file processing
- **URL Processing**: Extract content from web pages
- **Vector Search**: Semantic search across knowledge base

### 🎮 **Advanced Features**
- **God Commands**: Override responses with specific instructions
- **Voice Processing**: Handle voice messages with speech-to-text and text-to-speech
- **Session Memory**: Persistent Telegram sessions
- **Error Handling**: Robust error recovery and logging

## 🚀 Quick Start

### 1. **Clone Repository**
```bash
git clone https://github.com/your-username/agent-daredevil-telegram-bot.git
cd agent-daredevil-telegram-bot
```

### 2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3. **Setup Environment Variables**
```bash
# Copy the environment template
cp env.example .env

# Edit .env with your credentials
nano .env
```

**Required Environment Variables:**
```env
# Telegram API (get from https://my.telegram.org/apps)
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE_NUMBER=+1234567890

# LLM Provider Configuration
LLM_PROVIDER=gemini  # Choose: openai, gemini, or vertex_ai

# OpenAI API (get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4

# Google AI (Gemini) Configuration
GOOGLE_AI_API_KEY=your-google-ai-key-here
GEMINI_MODEL=gemini-2.5-flash

# Vertex AI Configuration (if using)
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

### 4. **Run the Bot**

**Advanced Bot (With RAG):**
```bash
python telegram_bot_rag.py
```

## 🔄 LLM Provider Management

### Checking Current Provider

To check which LLM provider and model is currently being used:

```bash
python check_llm_provider.py
```

This will display:
- Current provider setting (from .env)
- Configured model name
- Actual model being used

### Switching to Gemini 2.5 Flash

To quickly switch to Gemini 2.5 Flash:

```bash
python switch_to_gemini25.py
```

This script will update your .env file to use Gemini as the provider and set the model to gemini-2.5-flash.

### Testing LLM Providers

The comprehensive test script supports multiple testing modes:

```bash
# Test all available providers
python test_all_providers.py

# Test a specific provider
python test_all_providers.py --provider gemini

# Quick test of current provider
python test_all_providers.py --simple

# Test Gemini 2.5 Flash specifically
python test_all_providers.py --gemini25
```

## 📝 Concise Responses

The bot generates concise responses limited to 3-5 sentences. This ensures responses are focused and to the point.

### Response Length Guidelines

All responses follow these guidelines:
- Standard responses: 3-5 sentences
- Data-heavy responses: Up to 6 sentences with data summary in the last sentence
- Small talk: 3 sentences maximum

For more details, see the [Response Length Guide](./RESPONSE_LENGTH_GUIDE.md).

## 🔧 Provider Comparison

| Provider | Speed | Cost | Features | Best For |
|----------|-------|------|----------|----------|
| OpenAI GPT-4 | Medium | High | Most mature | Complex reasoning |
| Gemini 2.5 Flash | Fast | Low | Newest model | General use, best value |
| Gemini 1.5 Pro | Medium | Medium | Long context | Complex tasks |
| Vertex AI | Medium | Medium | Enterprise features | Business use |

For more details, see the comprehensive [LLM Provider Guide](./LLM_PROVIDER_GUIDE.md).

## 🛠️ Project Structure

```
📁 agent-daredevil-telegram-bot/
├── 🤖 Core Bot Files
│   ├── telegram_bot_rag.py         # Main bot with RAG
│   ├── llm_provider.py             # LLM provider abstraction
│   └── session_memory.py           # Session memory management
│
├── 🧠 Knowledge & Data
│   ├── voice_processor.py          # Voice message handling
│   └── cryptodevil.character.json  # Character personality
│
├── 🔧 Utility Scripts
│   ├── check_llm_provider.py       # Check current provider
│   ├── switch_to_gemini25.py       # Switch to Gemini 2.5
│   └── test_all_providers.py       # Comprehensive test script
│
└── 📋 Documentation
    ├── README.md                   # This file
    ├── LLM_PROVIDER_GUIDE.md       # Provider documentation
    ├── RESPONSE_LENGTH_GUIDE.md    # Response length documentation
    ├── GEMINI_25_SETUP.md          # Gemini 2.5 setup guide
    └── env.example                 # Environment template
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram API library
- [OpenAI](https://openai.com/) - GPT-4 API
- [Google AI](https://ai.google.dev/) - Gemini API
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [LangChain](https://langchain.com/) - RAG framework 