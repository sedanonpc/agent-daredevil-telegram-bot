import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from openai import OpenAI
import asyncio
import sys

# Load environment variables from .env file
load_dotenv()

# Fix Windows console encoding issues
if sys.platform.startswith('win'):
    try:
        # Try to set UTF-8 encoding for Windows console
        os.system('chcp 65001 >nul 2>&1')
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Safe print function that handles encoding issues
def safe_print(message):
    """Print function that handles Unicode encoding issues on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback to ASCII-safe version
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)

# Telegram API credentials from environment variables
API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
PHONE_NUMBER = os.getenv('TELEGRAM_PHONE_NUMBER', '')

# OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

def check_credentials():
    """Check if credentials are properly set"""
    missing = []
    
    if API_ID == 'YOUR_API_ID' or not API_ID:
        missing.append("API_ID")
    
    if API_HASH == 'YOUR_API_HASH' or not API_HASH:
        missing.append("API_HASH")
    
    if PHONE_NUMBER == 'YOUR_PHONE_NUMBER' or not PHONE_NUMBER:
        missing.append("PHONE_NUMBER")
    
    if OPENAI_API_KEY == 'YOUR_OPENAI_API_KEY' or not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    
    if missing:
        safe_print("❌ Missing credentials! Please update the following in telegram_bot.py:")
        for cred in missing:
            safe_print(f"   - {cred}")
        safe_print("\n📋 Setup Instructions:")
        safe_print("1. Get Telegram API credentials from: https://my.telegram.org/apps")
        safe_print("2. Get OpenAI API key from: https://platform.openai.com/api-keys")
        safe_print("3. Update the credentials in telegram_bot.py")
        safe_print("4. Run the script again")
        return False
    
    return True

# Create the Telegram client (only if credentials are set)
if check_credentials():
    # Initialize OpenAI client
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Convert API_ID to integer if it's a string
    try:
        api_id = int(API_ID)
    except ValueError:
        safe_print("❌ API_ID must be a number!")
        sys.exit(1)
    
    client = TelegramClient('session_name', api_id, API_HASH)

    @client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        """Handle /start command"""
        await event.respond('Hello! I am your Telegram bot with OpenAI integration. Send me any message and I\'ll respond using AI!')

    @client.on(events.NewMessage)
    async def message_handler(event):
        """Handle all incoming messages"""
        # Skip messages that start with /start (already handled above)
        if event.raw_text.startswith('/start'):
            return
        
        # Skip messages from other bots or channels
        if event.is_channel or event.is_group:
            return
        
        # Skip messages from yourself to avoid loops
        if event.is_private and event.sender_id == (await client.get_me()).id:
            return
        
        # Get the message text
        message_text = event.raw_text
        
        safe_print(f"📨 Received message: {message_text}")
        
        try:
            # Send typing indicator
            async with client.action(event.chat_id, 'typing'):
                # Send message to OpenAI using new API
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant responding to messages on Telegram."},
                        {"role": "user", "content": message_text}
                    ],
                    max_tokens=1000
                )
                
                # Get the AI response
                ai_response = response.choices[0].message.content
                
                safe_print(f"🤖 AI Response: {ai_response}")
                
                # Send the response back to Telegram
                await event.respond(ai_response)
                
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            safe_print(f"❌ Error: {error_msg}")
            await event.respond(error_msg)

    async def main():
        """Main function to start the client"""
        safe_print("🚀 Starting Telegram client...")
        
        try:
            # Start the client
            await client.start(phone=PHONE_NUMBER)
            
            safe_print("✅ Client started! You are now connected.")
            safe_print("💬 Send messages to your account to test the OpenAI integration.")
            safe_print("🛑 Press Ctrl+C to stop the bot.")
            
            # Keep the client running
            await client.run_until_disconnected()
            
        except Exception as e:
            safe_print(f"❌ Error starting client: {e}")
            safe_print("Make sure your credentials are correct and try again.")

    if __name__ == '__main__':
        try:
            # Run the main function
            asyncio.run(main())
        except KeyboardInterrupt:
            safe_print("\n👋 Bot stopped by user.")
        except Exception as e:
            safe_print(f"❌ Unexpected error: {e}")
else:
    safe_print("\n🔧 Please update your credentials and run the script again.") 