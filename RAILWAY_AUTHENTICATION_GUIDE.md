# 🚀 Railway Authentication Guide - Agent Daredevil

## Overview

This guide explains how to properly authenticate your Agent Daredevil Telegram Bot on Railway platform.

## 🔐 Authentication Options

### Option 1: Bot Token Authentication (Recommended for Production)

**Advantages:**
- ✅ No session files needed
- ✅ More secure
- ✅ Better for production deployments
- ✅ No interactive authentication required

**Setup Steps:**

1. **Create a Telegram Bot:**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Send `/newbot` and follow instructions
   - Get your bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Add to Railway Environment Variables:**
   - Go to your Railway project dashboard
   - Navigate to Variables tab
   - Add: `TELEGRAM_BOT_TOKEN=your_bot_token_here`

3. **Update Bot Configuration:**
   - The bot will automatically detect the token and use bot authentication
   - No session files required

### Option 2: Session File Authentication (For User Accounts)

**Advantages:**
- ✅ Works with your personal Telegram account
- ✅ Full access to Telegram features
- ✅ Can join groups as a user

**Setup Steps:**

1. **Authenticate Locally:**
   ```bash
   python authenticate_session.py
   ```

2. **Force Include Session File:**
   ```bash
   git add -f daredevil_session.session
   git commit -m "Add authenticated session file for Railway"
   git push origin main
   ```

3. **Update .dockerignore:**
   - Comment out `*.session` line in `.dockerignore`

## 🎯 Recommended Approach

For Railway deployment, **use Bot Token authentication** because:

1. **More Secure:** No session files in your repository
2. **Simpler:** Just add one environment variable
3. **Reliable:** No authentication prompts in Docker
4. **Production Ready:** Standard practice for bot deployments

## 🔧 Current Bot Configuration

The bot is configured to:
1. Try user authentication first (session file)
2. Fall back to bot token authentication if available
3. Provide clear error messages if neither works

## 📋 Environment Variables for Railway

Required variables:
```
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=your_phone_number
TELEGRAM_BOT_TOKEN=your_bot_token  # For bot authentication
```

Optional variables:
```
LLM_PROVIDER=gemini
GOOGLE_AI_API_KEY=your_gemini_key
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
```

## 🚀 Deployment Steps

1. **Choose authentication method** (Bot Token recommended)
2. **Set environment variables** in Railway dashboard
3. **Deploy** - Railway will automatically build and deploy
4. **Monitor logs** for successful startup

## 🔍 Troubleshooting

**If authentication fails:**
- Check environment variables are set correctly
- Verify bot token is valid (for bot authentication)
- Ensure session file is authenticated (for user authentication)
- Check Railway logs for specific error messages

**Common Issues:**
- Missing environment variables
- Invalid bot token
- Session file not authenticated
- Network connectivity issues

## 💡 Pro Tips

1. **Use Bot Token for production** - more reliable and secure
2. **Test locally first** with `python authenticate_session.py`
3. **Monitor Railway logs** during deployment
4. **Keep environment variables secure** - never commit them to git
