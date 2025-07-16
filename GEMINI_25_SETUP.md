# Gemini 2.5 Flash Setup Guide

## What We've Done

1. **Updated Configuration**:
   - Modified `env.example` to use `GEMINI_MODEL=gemini-2.5-flash`
   - Updated `llm_provider.py` to support Gemini 2.5 models
   - Updated documentation in `LLM_PROVIDER_GUIDE.md`

2. **Created Utility Scripts**:
   - `check_llm_provider.py` - Shows which provider and model is active
   - `switch_to_gemini25.py` - Quickly switches to Gemini 2.5 Flash
   - `test_all_providers.py --gemini25` - Tests the Gemini 2.5 Flash model

3. **Verified Integration**:
   - Confirmed that the bot can use Gemini 2.5 Flash
   - Tested response generation with the new model

## How to Check Current Provider

Run:
```bash
python check_llm_provider.py
```

This will show:
```
📋 Current LLM provider setting: gemini
📝 Model configured in .env: gemini-2.5-flash
✅ Actual model being used: gemini-2.5-flash
```

## How to Switch to Gemini 2.5 Flash

Run:
```bash
python switch_to_gemini25.py
```

This will update your `.env` file to use Gemini 2.5 Flash.

## Manual Configuration

Edit your `.env` file:
```
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
```

## Notes on Gemini 2.5 Flash

- **Faster**: Optimized for speed and efficiency
- **Cheaper**: Lower cost per token than other models
- **Newer**: Latest model from Google AI
- **Streaming**: There might be some issues with streaming responses

## Troubleshooting

If you encounter issues:

1. **Check API Key**: Make sure your Google AI API key is valid
2. **Update Dependencies**: Run `pip install -r requirements.txt` to ensure you have the latest libraries
3. **Check Logs**: Look for error messages in the console output
4. **Try Fallback**: If Gemini 2.5 Flash doesn't work, try falling back to Gemini 1.5 Pro

For more detailed information, see the [LLM Provider Guide](./LLM_PROVIDER_GUIDE.md). 