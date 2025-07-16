# 🤖 Multi-LLM Provider Guide

The Agent Daredevil Telegram bot now supports multiple LLM providers! You can easily switch between OpenAI GPT, Google Gemini, and Vertex AI models.

## 🚀 Supported Providers

### 1. **OpenAI (GPT Models)**
- **Models**: GPT-4, GPT-3.5-turbo, etc.
- **Best for**: General conversations, coding, analysis
- **API**: Direct OpenAI API
- **Cost**: Pay-per-token

### 2. **Google AI (Gemini Models)**
- **Models**: Gemini 2.5 Flash, Gemini 1.5 Pro, Gemini 1.5 Flash
- **Best for**: Multimodal tasks, long context, reasoning
- **API**: Direct Google AI API
- **Cost**: Free tier available, then pay-per-token

### 3. **Vertex AI (Gemini via OpenAI-compatible API)**
- **Models**: Gemini 2.0 Flash, Gemini 1.5 Pro
- **Best for**: Enterprise use, Google Cloud integration
- **API**: Google Cloud Vertex AI
- **Cost**: Google Cloud pricing

## ⚙️ Setup Instructions

### 1. Install Dependencies

First, install the new Gemini dependencies:

```bash
pip install -r requirements.txt
```

This installs:
- `google-generativeai` - Direct Google AI API
- `google-auth`, `google-cloud-aiplatform` - Vertex AI support

### 2. Configure Environment Variables

Add your provider configurations to `.env`:

```env
# ===========================================
# LLM Provider Configuration
# ===========================================

# Choose your provider: openai, gemini, or vertex_ai
LLM_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4

# Google AI (Gemini) Configuration
GOOGLE_AI_API_KEY=your-google-ai-key-here
GEMINI_MODEL=gemini-2.5-flash

# Vertex AI Configuration
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_AI_MODEL=google/gemini-2.0-flash-001
# Optional: Path to service account JSON
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

### 3. Get API Keys

#### **OpenAI Setup**
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add to `.env`: `OPENAI_API_KEY=sk-...`

#### **Google AI (Gemini) Setup**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to `.env`: `GOOGLE_AI_API_KEY=...`

#### **Vertex AI Setup**
1. Create a [Google Cloud Project](https://console.cloud.google.com/)
2. Enable the Vertex AI API
3. Set up authentication:
   - **Option A**: Use `gcloud auth application-default login`
   - **Option B**: Create a service account and download JSON key
4. Add to `.env`: `GOOGLE_CLOUD_PROJECT_ID=your-project-id`

## 🎮 Usage Examples

### Basic Usage

Simply set the `LLM_PROVIDER` in your `.env` file:

```bash
# Use OpenAI GPT-4
LLM_PROVIDER=openai

# Use Google Gemini
LLM_PROVIDER=gemini

# Use Vertex AI Gemini
LLM_PROVIDER=vertex_ai
```

Then run your bot normally:

```bash
python telegram_bot_rag.py
```

### Testing Providers

Use the test script to compare providers:

```bash
python test_all_providers.py
```

This will:
- Test all configured providers
- Compare responses side-by-side
- Allow interactive testing

### Checking Current Provider

To check which provider and model is currently being used:

```bash
python check_llm_provider.py
```

This will display:
- Current provider setting
- Configured model name
- Actual model being used

### Programmatic Usage

```python
from llm_provider import get_llm_provider, LLMProviderFactory

# Use configured provider
provider = get_llm_provider()

# Or specify provider directly
openai_provider = LLMProviderFactory.create_provider('openai')
gemini_provider = LLMProviderFactory.create_provider('gemini')
vertex_provider = LLMProviderFactory.create_provider('vertex_ai')

# Generate response
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
]

response = await provider.generate_response(
    messages=messages,
    max_tokens=100,
    temperature=0.7
)

# Streaming
async for chunk in provider.generate_stream(messages):
    print(chunk, end='')
```

## 🔧 Advanced Configuration

### Model Selection

Each provider supports different models:

```env
# OpenAI Models
OPENAI_MODEL=gpt-4                    # Most capable
OPENAI_MODEL=gpt-3.5-turbo           # Faster, cheaper

# Gemini Models  
GEMINI_MODEL=gemini-2.5-flash        # Newest, fastest model
GEMINI_MODEL=gemini-1.5-pro          # Most capable
GEMINI_MODEL=gemini-1.5-flash        # Faster, cheaper

# Vertex AI Models
VERTEX_AI_MODEL=google/gemini-2.0-flash-001
VERTEX_AI_MODEL=google/gemini-1.5-pro-001
```

### Provider-Specific Features

#### **OpenAI**
- ✅ Function calling
- ✅ JSON mode
- ✅ Streaming
- ✅ Vision (GPT-4V)

#### **Gemini**
- ✅ Long context (1M+ tokens)
- ✅ Multimodal (text, images, video, audio)
- ✅ Streaming
- ✅ Function calling
- ✅ JSON mode

#### **Vertex AI**
- ✅ Enterprise features
- ✅ Google Cloud integration
- ✅ Same models as Google AI
- ✅ OpenAI-compatible API

### RAG System Compatibility

The RAG system continues to use OpenAI embeddings regardless of your LLM provider choice, since:
- OpenAI embeddings are high-quality and widely supported
- Gemini doesn't have a direct embeddings API yet
- This ensures consistency across providers

To use RAG with any provider, you still need an OpenAI API key for embeddings:

```env
LLM_PROVIDER=gemini                # Use Gemini for chat
OPENAI_API_KEY=sk-...             # Still needed for embeddings
GOOGLE_AI_API_KEY=...             # For Gemini chat
USE_RAG=True                      # Enable RAG system
```

## 🛠️ Troubleshooting

### Common Issues

#### **Gemini API Errors**
```
google.api_core.exceptions.PermissionDenied: 403 User location is not supported
```
**Solution**: Gemini API may not be available in all regions. Try using a VPN or Vertex AI instead.

#### **Vertex AI Authentication**
```
google.auth.exceptions.DefaultCredentialsError
```
**Solution**: 
- Run `gcloud auth application-default login`
- Or set `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON path

#### **Rate Limiting**
```
429 Rate limit exceeded
```
**Solution**: Each provider has different rate limits. Consider:
- Using a different provider
- Implementing request throttling
- Upgrading your API plan

### Provider Comparison

| Feature | OpenAI | Gemini | Vertex AI |
|---------|---------|---------|-----------|
| **Setup Complexity** | Easy | Easy | Medium |
| **Free Tier** | Limited | Yes | GCP Credits |
| **Context Length** | 128K | 2M+ | 2M+ |
| **Multimodal** | Images | Images, Video, Audio | Images, Video, Audio |
| **Streaming** | ✅ | ✅ | ✅ |
| **Function Calling** | ✅ | ✅ | ✅ |
| **Enterprise Features** | Paid | Limited | ✅ |

### Performance Tips

1. **For Speed**: Use `gemini-2.5-flash` or `gpt-3.5-turbo`
2. **For Quality**: Use `gemini-1.5-pro` or `gpt-4`
3. **For Long Context**: Use Gemini models (2M+ tokens)
4. **For Vision**: Any provider supports images
5. **For Enterprise**: Use Vertex AI

## 🔄 Switching Providers

You can switch providers anytime by changing the `.env` file:

```bash
# Before
LLM_PROVIDER=openai

# After
LLM_PROVIDER=gemini
```

Then restart your bot. No code changes needed!

## 📊 Cost Comparison

Approximate costs (as of 2024):

### **OpenAI**
- GPT-4: $30/1M input tokens, $60/1M output tokens
- GPT-3.5-turbo: $1/1M input tokens, $2/1M output tokens

### **Google AI (Gemini)**
- Free tier: 15 requests/minute
- Gemini 2.5 Flash: $0.35/1M input tokens, $1.05/1M output tokens
- Gemini 1.5 Pro: $3.50/1M input tokens, $10.50/1M output tokens
- Gemini 1.5 Flash: $0.35/1M input tokens, $1.05/1M output tokens

### **Vertex AI**
- Similar to Google AI pricing
- Additional Google Cloud charges may apply

## 🎯 Best Practices

1. **Start with Gemini**: Free tier is generous for testing
2. **Use OpenAI for production**: Most stable and mature
3. **Consider Vertex AI for enterprise**: Better SLAs and support
4. **Mix providers**: Use different ones for different tasks
5. **Monitor usage**: Set up billing alerts

## 🚀 Next Steps

1. **Test the integration**: Run `python test_all_providers.py`
2. **Update your .env**: Add the new provider configurations
3. **Start your bot**: Use `python telegram_bot_rag.py`
4. **Experiment**: Try different providers for different use cases

## 📞 Support

If you encounter issues:
1. Check the provider's status page
2. Verify your API keys and quotas
3. Review the logs for detailed error messages
4. Try switching to a different provider temporarily

Happy chatting with your multi-LLM powered bot! 🤖✨ 