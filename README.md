# 🤖 Agent Daredevil - Telegram Bot with RAG

A sophisticated Telegram bot powered by OpenAI and Retrieval-Augmented Generation (RAG) capabilities. Agent Daredevil can chat naturally, search knowledge bases, crawl websites, and maintain character consistency.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Telegram](https://img.shields.io/badge/telegram-bot-blue.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-brightgreen.svg)

## ✨ Features

### 🧠 **Core Intelligence**
- **OpenAI Integration**: Powered by GPT-4 for natural conversations
- **RAG System**: Knowledge base retrieval using ChromaDB vector store
- **Character Consistency**: Maintains Agent Daredevil persona across conversations
- **Context Awareness**: Real-time date/time and NBA season tracking

### 🌐 **Knowledge Management**
- **Web Crawler**: Automated NBA statistics and website crawling
- **Document Upload**: PDF and text file processing
- **URL Processing**: Extract content from web pages
- **Vector Search**: Semantic search across knowledge base

### 🎮 **Advanced Features**
- **God Commands**: Override responses with specific instructions
- **Streamlit Interface**: Web-based knowledge base management
- **Session Management**: Persistent Telegram sessions
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

# OpenAI API (get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 4. **Run the Bot**

**Basic Bot (No RAG):**
```bash
python telegram_bot.py
```

**Advanced Bot (With RAG):**
```bash
python telegram_bot_rag.py
```

**Knowledge Base Manager:**
```bash
streamlit run rag_manager.py
```

## 📁 Project Structure

```
📁 agent-daredevil-telegram-bot/
├── 🤖 **Core Bot Files**
│   ├── telegram_bot.py              # Basic bot without RAG
│   ├── telegram_bot_rag.py          # Advanced bot with RAG
│   └── cryptodevil.character.json   # Character personality
│
├── 🧠 **Knowledge & Data**
│   ├── rag_manager.py               # Streamlit knowledge manager
│   ├── basketball_reference_crawler.py  # NBA data crawler
│   └── crawler_config.py            # Crawler configuration
│
├── 🏃 **Launcher Scripts**
│   ├── launcher.py                  # Multi-option launcher
│   ├── run_crawler.py              # Crawler runner
│   ├── run.bat                     # Windows batch script
│   └── run.sh                      # Unix shell script
│
├── 🧪 **Testing & Utils**
│   ├── test_*.py                   # Various test files
│   └── install.py                  # Installation helper
│
└── 📋 **Configuration**
    ├── requirements.txt            # Python dependencies
    ├── env.example                # Environment template
    ├── .gitignore                 # Git ignore rules
    └── README.md                  # This file
```

## 🎯 Usage Guide

### **Basic Telegram Bot**
- Simple OpenAI-powered chat bot
- No knowledge base or RAG features
- Good for testing and basic conversations

### **RAG-Enabled Bot**
- Full knowledge base integration
- Web crawling and document processing
- Advanced context awareness
- Character personality maintenance

### **Knowledge Base Manager**
- Web interface at `http://localhost:8501`
- Upload documents and URLs
- Search knowledge base
- Manage God Commands
- View statistics

## ⚙️ Configuration

### **Character Customization**
Edit `cryptodevil.character.json` to modify:
- Personality traits
- Response style
- Background story
- Behavioral guidelines

### **RAG Settings**
In `telegram_bot_rag.py`:
```python
USE_RAG = True  # Enable/disable RAG
CHROMA_DB_PATH = "./chroma_db"  # Vector store location
```

### **Crawler Configuration**
In `crawler_config.py`:
```python
CRAWL_DELAY = 4.0  # Delay between requests
MAX_PAGES = 100    # Maximum pages to crawl
THREADS = 2        # Concurrent threads
```

## 🛠️ Development

### **Adding New Features**
1. Create feature branch: `git checkout -b feature-name`
2. Implement changes
3. Add tests in `test_*` files
4. Update documentation
5. Submit pull request

### **Testing**
```bash
# Run specific tests
python test_crawler.py
python test_enhanced_crawler.py

# Run with different configurations
python test_conservative_crawler.py
python test_rate_limit_safe.py
```

### **Logging**
Logs are saved to:
- `crawler.log` - Web crawler logs
- `basketball_crawler.log` - NBA data logs

## 🔧 Troubleshooting

### **Common Issues**

**"Database is locked" Error:**
```bash
# Stop all running processes
# Delete session files
rm *.session*
```

**"Missing credentials" Error:**
- Check `.env` file exists
- Verify all required variables are set
- Ensure API keys are valid

**RAG Not Working:**
- Check ChromaDB installation
- Verify knowledge base has content
- Review logs for vector store errors

### **Getting Help**

1. **Check Logs**: Review `.log` files for errors
2. **Verify Setup**: Ensure all environment variables are correct
3. **Test Components**: Run individual test files
4. **Issue Tracker**: Report bugs on GitHub Issues

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram API library
- [OpenAI](https://openai.com/) - GPT-4 API
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Streamlit](https://streamlit.io/) - Web interface framework
- [LangChain](https://langchain.com/) - RAG framework

## 📞 Support

For support, join our Telegram group or open an issue on GitHub.

---

**Made with ❤️ by the Agent Daredevil Team** 