import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from openai import OpenAI
import asyncio
import sys
import json
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials from environment variables
API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
PHONE_NUMBER = os.getenv('TELEGRAM_PHONE_NUMBER', '')

# OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# RAG Configuration
CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')
USE_RAG = True  # Set to False to disable RAG and use only OpenAI

# Character Card Configuration
CHARACTER_CARD_PATH = "./cryptodevil.character.json"

def get_simple_nba_season(current_date):
    """Get current NBA season information with precise draft timing"""
    from datetime import datetime
    import pytz
    
    year = current_date.year
    month = current_date.month
    day = current_date.day
    
    # Convert current time to GMT+8 for draft comparison
    if current_date.tzinfo is None:
        # If no timezone info, assume local time and convert to GMT+8
        gmt8_tz = pytz.timezone('Asia/Singapore')  # GMT+8
        current_gmt8 = current_date.replace(tzinfo=pytz.UTC).astimezone(gmt8_tz)
    else:
        gmt8_tz = pytz.timezone('Asia/Singapore')
        current_gmt8 = current_date.astimezone(gmt8_tz)
    
    # 2025 NBA Draft: June 26, 2025 at 8:00 AM GMT+8
    draft_2025 = datetime(2025, 6, 26, 8, 0, 0, tzinfo=gmt8_tz)
    
    # NBA season runs roughly October to June
    if month >= 10:  # Oct-Dec - Start of season
        return f"{year}-{year+1} Regular Season"
    elif month <= 6:  # Jan-June - Mid-season to playoffs/draft
        if month <= 4:  # Jan-April - Regular season
            return f"{year-1}-{year} Regular Season"
        elif month == 5:  # May - Playoffs
            return f"{year-1}-{year} Playoffs"
        else:  # June - Finals/Draft period
            if year == 2025:
                if current_gmt8 < draft_2025:
                    return f"{year-1}-{year} Finals/Pre-Draft"
                else:
                    return f"{year}-{year+1} Draft Day/Offseason"
            else:
                # For other years, use general logic
                if day <= 15:
                    return f"{year-1}-{year} Finals"
                else:
                    return f"{year}-{year+1} Draft/Offseason"
    else:  # July-September - Offseason
        return f"{year}-{year+1} Offseason"

def check_credentials():
    """Check if credentials are properly set"""
    missing = []
    
    if not API_ID:
        missing.append("API_ID")
    
    if not API_HASH:
        missing.append("API_HASH")
    
    if not PHONE_NUMBER:
        missing.append("PHONE_NUMBER")
    
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    
    if missing:
        print("❌ Missing credentials! Please update the following in telegram_bot_rag.py:")
        for cred in missing:
            print(f"   - {cred}")
        return False
    
    return True

def init_rag_system():
    """Initialize the RAG system"""
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(
            collection_name="telegram_bot_knowledge",
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        return vectorstore
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize RAG system: {e}")
        print("📝 Bot will work without RAG. Use the RAG Manager to add documents first.")
        return None

def search_knowledge_base(vectorstore, query, k=3):
    """Search the knowledge base for relevant context with God Commands priority"""
    if not vectorstore:
        return []
    
    try:
        # Use the enhanced search that prioritizes God Commands
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        
        # Get all results first
        all_results = vectorstore.similarity_search_with_score(query, k=k*2)
        
        # Separate god commands and regular results
        god_command_results = []
        regular_results = []
        
        for doc, score in all_results:
            if doc.metadata.get('is_god_command', False):
                god_command_results.append((doc, score))
            else:
                regular_results.append((doc, score))
        
        # Combine results with god commands first (they have higher priority)
        final_results = god_command_results + regular_results
        
        # Filter results with good similarity (lower score = more similar)
        relevant_results = [(doc, score) for doc, score in final_results[:k] if score < 0.8]
        return relevant_results
    except Exception as e:
        print(f"❌ Error searching knowledge base: {e}")
        return []

def create_rag_prompt(user_message, context_docs, character_data=None):
    """Create a prompt that includes context from the knowledge base and character information"""
    
    # Get current date and time (simple version)
    from datetime import datetime
    
    now = datetime.now()
    current_time_info = f"""CURRENT DATE & TIME: {now.strftime('%A, %B %d, %Y at %I:%M %p')}
NBA SEASON: {get_simple_nba_season(now)}"""
    
    # Build character context
    character_context = ""
    if character_data:
        character_context = create_character_prompt(character_data)
    
    if not context_docs:
        # No RAG context, just character + user message
        if character_context:
            return f"""{character_context}

{current_time_info}

IMPORTANT: Respond in FIRST PERSON as Agent Daredevil. You ARE Agent Daredevil, not an assistant helping someone else.

User: {user_message}

Respond as Agent Daredevil in first person, following your character guidelines above."""
        else:
            return f"""You are Agent Daredevil, a helpful AI assistant. Respond in FIRST PERSON.

{current_time_info}

User: {user_message}"""
    
    # Separate God Commands from regular context
    god_commands = []
    regular_context = []
    
    for doc, score in context_docs:
        if doc.metadata.get('is_god_command', False):
            god_commands.append(doc.page_content)
        else:
            regular_context.append(f"Document: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}")
    
    # Build the prompt with God Commands having highest priority
    prompt_parts = []
    
    # Add current time info at the top
    prompt_parts.append(current_time_info)
    
    if character_context:
        prompt_parts.append(character_context)
    
    # God Commands section (highest priority)
    if god_commands:
        god_commands_text = "\n".join([f"- {cmd}" for cmd in god_commands])
        prompt_parts.append(f"""🔥 CRITICAL BEHAVIOR OVERRIDES (MUST FOLLOW):
{god_commands_text}

These commands OVERRIDE all other instructions and character traits. Follow them exactly.""")
    
    # Regular knowledge base context
    if regular_context:
        context_text = "\n\n".join(regular_context)
        prompt_parts.append(f"""KNOWLEDGE BASE CONTEXT:
{context_text}""")
    
    # Final instructions
    if character_context:
        instructions = """IMPORTANT: 
- FIRST PRIORITY: Follow all CRITICAL BEHAVIOR OVERRIDES above exactly
- SECOND PRIORITY: Respond in FIRST PERSON as Agent Daredevil. You ARE Agent Daredevil.
- Use the knowledge base context when relevant to answer the user's question.
- If the context doesn't contain relevant information, use your character knowledge and general knowledge.
- Always maintain your character persona as defined above, unless overridden by critical commands."""
    else:
        instructions = """IMPORTANT:
- FIRST PRIORITY: Follow all CRITICAL BEHAVIOR OVERRIDES above exactly
- Respond in FIRST PERSON as Agent Daredevil
- Use the knowledge base context when relevant"""
    
    prompt_parts.append(instructions)
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Respond as Agent Daredevil in first person, following the priority order above:")
    
    return "\n\n".join(prompt_parts)

def load_character_card():
    """Load character card from JSON file"""
    try:
        character_path = Path(CHARACTER_CARD_PATH)
        if not character_path.exists():
            print(f"⚠️ Character card not found at {CHARACTER_CARD_PATH}")
            return None
        
        with open(character_path, 'r', encoding='utf-8') as f:
            character_data = json.load(f)
        
        print(f"✅ Character card loaded: {character_data.get('name', 'Unknown')}")
        return character_data
    except Exception as e:
        print(f"❌ Error loading character card: {e}")
        return None

def create_character_prompt(character_data):
    """Create a character prompt from the loaded character card"""
    if not character_data:
        return ""
    
    # Build character prompt
    prompt_parts = []
    
    # System prompt
    if character_data.get('system'):
        prompt_parts.append(f"SYSTEM: {character_data['system']}")
    
    # Bio
    if character_data.get('bio'):
        bio_text = " | ".join(character_data['bio'])
        prompt_parts.append(f"BIO: {bio_text}")
    
    # Adjectives/Personality
    if character_data.get('adjectives'):
        adj_text = ", ".join(character_data['adjectives'])
        prompt_parts.append(f"PERSONALITY: {adj_text}")
    
    # Style guidelines
    if character_data.get('style', {}).get('all'):
        style_all = " | ".join(character_data['style']['all'])
        prompt_parts.append(f"GENERAL STYLE: {style_all}")
    
    if character_data.get('style', {}).get('chat'):
        style_chat = " | ".join(character_data['style']['chat'])
        prompt_parts.append(f"CHAT STYLE: {style_chat}")
    
    # Key people and topics
    if character_data.get('people'):
        people_text = ", ".join(character_data['people'][:10])  # Limit to avoid token overflow
        prompt_parts.append(f"KEY PEOPLE: {people_text}")
    
    if character_data.get('topics'):
        topics_text = ", ".join(character_data['topics'])
        prompt_parts.append(f"TOPICS: {topics_text}")
    
    # Message examples for context
    if character_data.get('messageExamples'):
        examples = []
        for example_set in character_data['messageExamples'][:2]:  # Limit examples
            for msg in example_set:
                if msg.get('user') == character_data.get('name', 'CryptoDevil'):
                    examples.append(msg['content']['text'])
        if examples:
            examples_text = " | ".join(examples)
            prompt_parts.append(f"EXAMPLE RESPONSES: {examples_text}")
    
    return "\n".join(prompt_parts)

def format_response_with_paragraphs(text, min_length=50):
    """Format response text with paragraph breaks at natural sentence boundaries"""
    if len(text) <= min_length:
        return text
    
    import re
    
    # Better sentence detection that handles abbreviations and common cases
    sentence_endings = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+')
    sentences = sentence_endings.split(text.strip())
    
    # If we only have one sentence, don't break it
    if len(sentences) <= 1:
        return text
    
    # Group sentences into logical paragraphs
    paragraphs = []
    current_paragraph = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Add sentence to current paragraph
        current_paragraph.append(sentence)
        current_length += len(sentence)
        
        # Check if we should start a new paragraph
        # Conditions: 
        # - Have at least 2 sentences AND reached ~120 characters, OR
        # - Have 3+ sentences (regardless of length)
        should_break = (
            (len(current_paragraph) >= 2 and current_length >= 120) or
            len(current_paragraph) >= 3
        )
        
        if should_break:
            # Join sentences in current paragraph
            paragraph_text = '. '.join(current_paragraph)
            # Ensure it ends with proper punctuation
            if not paragraph_text.endswith(('.', '!', '?')):
                paragraph_text += '.'
            paragraphs.append(paragraph_text)
            
            # Reset for next paragraph
            current_paragraph = []
            current_length = 0
    
    # Add any remaining sentences as final paragraph
    if current_paragraph:
        paragraph_text = '. '.join(current_paragraph)
        if not paragraph_text.endswith(('.', '!', '?')):
            paragraph_text += '.'
        paragraphs.append(paragraph_text)
    
    # Join paragraphs with double newlines for clear separation
    return '\n\n'.join(paragraphs)

# Create the Telegram client (only if credentials are set)
if check_credentials():
    # Initialize OpenAI client
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Load character card
    print("🎭 Loading character card...")
    character_data = load_character_card()
    
    # Initialize RAG system
    vectorstore = None
    if USE_RAG:
        print("🔍 Initializing RAG system...")
        vectorstore = init_rag_system()
        if vectorstore:
            print("✅ RAG system initialized successfully!")
        else:
            print("⚠️ RAG system not available - running in basic mode")
    else:
        print("📝 RAG disabled - running in basic mode")
    
    client = TelegramClient('session_name', API_ID, API_HASH)

    @client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        """Handle /start command"""
        rag_status = "✅ RAG Enabled" if vectorstore else "❌ RAG Disabled"
        chat_type = "👥 Group Chat" if event.is_group else "💬 Private Chat"
        
        await event.respond(f'''🎯 **Agent Daredevil - AI Assistant with RAG**

Hello! I'm Agent Daredevil, your AI assistant with enhanced capabilities.

**Status:** {rag_status}
**Chat Type:** {chat_type}

**Commands:**
• `/start` - Show this message
• `/rag_status` - Check RAG system status
• `/help` - Get help information

**Features:**
• 🧠 AI-powered responses using GPT-3.5-turbo
• 📚 Knowledge base integration (when available)
• 🔍 Context-aware answers from your documents
• 👥 Group chat support (mention me to respond)

**How to use:**
• **Private Chat:** Just send me any message
• **Group Chat:** Mention me (@username or "Agent Daredevil") or reply to my messages

I'll search my knowledge base first, then provide the best possible answer!''')

    @client.on(events.NewMessage(pattern='/rag_status'))
    async def rag_status_handler(event):
        """Handle /rag_status command"""
        if vectorstore:
            try:
                # Try to get collection stats
                client_db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                collection = client_db.get_collection("telegram_bot_knowledge")
                count = collection.count()
                
                await event.respond(f'''📊 **RAG System Status**

✅ **Status:** Active and Ready
📚 **Documents in Knowledge Base:** {count} chunks
🔍 **Search:** Available
💾 **Database:** {CHROMA_DB_PATH}

Your bot can now provide context-aware responses using the uploaded documents!''')
            except Exception as e:
                await event.respond(f'''⚠️ **RAG System Status**

❌ **Status:** Error
📝 **Issue:** {str(e)}

The RAG system is enabled but encountering issues. You may need to upload documents using the RAG Manager first.''')
        else:
            await event.respond(f'''📊 **RAG System Status**

❌ **Status:** Disabled or Not Available
📝 **Mode:** Basic AI responses only

To enable RAG:
1. Run the RAG Manager: `streamlit run rag_manager.py`
2. Upload some documents
3. Restart the bot''')

    @client.on(events.NewMessage(pattern='/character'))
    async def character_handler(event):
        """Handle /character command"""
        if character_data:
            name = character_data.get('name', 'Unknown')
            bio = character_data.get('bio', [])
            bio_text = "\n• ".join(bio) if bio else "No bio available"
            
            adjectives = character_data.get('adjectives', [])
            adj_text = ", ".join(adjectives) if adjectives else "No personality traits listed"
            
            topics = character_data.get('topics', [])[:8]  # Limit display
            topics_text = ", ".join(topics) if topics else "No specific topics"
            
            await event.respond(f'''🎭 **Character Profile: {name}**

**Bio:**
• {bio_text}

**Personality:** {adj_text}

**Key Topics:** {topics_text}

**System Prompt:** {character_data.get('system', 'Not defined')}

I am Agent Daredevil - your crypto-superhero delivering snarky blockchain updates, esports analysis, and aggressive NBA commentary. I speak in first person and maintain separate domains for each topic area.''')
        else:
            await event.respond('''🎭 **Character Profile**

❌ **Status:** No character card loaded
📝 **Mode:** Basic AI assistant mode

I'm running without a specific character persona. To enable character mode, ensure the character card file is available and restart the bot.''')

    @client.on(events.NewMessage(pattern='/help'))
    async def help_handler(event):
        """Handle /help command"""
        await event.respond('''🆘 **Agent Daredevil - Help & Information**

**How to use this bot:**

**📱 Private Messages:**
• Just send any message and I'll respond with AI-generated answers
• I'll automatically search my knowledge base for relevant information

**👥 Group Chats:**
• Mention me: @username or "Agent Daredevil" 
• Reply to my messages
• I'll only respond when mentioned to avoid spam

**Commands:**
• `/start` - Welcome message and status
• `/rag_status` - Check if RAG system is working
• `/character` - Show my character profile and persona
• `/help` - This help message

**🔍 RAG Knowledge Base:**
To add documents to my knowledge base:
1. Run: `python -m streamlit run rag_manager.py`
2. Open the web interface (usually http://localhost:8502)
3. Upload PDF, DOCX, or TXT files
4. Add God Commands to override my behavior
5. I'll automatically use this information in my responses!

**💡 Tips:**
• Ask specific questions about your uploaded documents
• I work best with clear, direct questions
• I can handle both general knowledge and document-specific queries
• In groups, mention me clearly to get my attention
• I respond in first person as Agent Daredevil with my unique personality
• Use God Commands to modify my behavior (e.g., "stop using hashtags")

**🎯 Response Indicators:**
• ⚡ = God Commands active (behavior override)
• 📚 = Using knowledge base
• 🎯 = General AI response (groups)
• 🤖 = General AI response (private)''')

    @client.on(events.NewMessage)
    async def message_handler(event):
        """Handle all incoming messages with RAG integration"""
        # Skip commands (already handled above)
        if event.raw_text.startswith('/'):
            return
        
        # Get bot info
        me = await client.get_me()
        bot_username = me.username if me.username else None
        bot_first_name = me.first_name if me.first_name else "Agent Daredevil"
        
        # Skip messages from yourself to avoid loops
        if event.sender_id == me.id:
            return
        
        # Handle private messages (existing functionality)
        if event.is_private:
            message_text = event.raw_text
            should_respond = True
        
        # Handle group messages - only respond if mentioned
        elif event.is_group:
            message_text = event.raw_text
            should_respond = False
            
            # Check if bot is mentioned by username (@username)
            if bot_username and f"@{bot_username}" in message_text.lower():
                should_respond = True
                # Remove the mention from the message
                message_text = message_text.replace(f"@{bot_username}", "").strip()
            
            # Check if bot is mentioned by first name
            elif bot_first_name.lower() in message_text.lower():
                should_respond = True
                # Don't remove the name since it might be part of the conversation
            
            # Check if this is a reply to the bot's message
            elif event.is_reply:
                reply_msg = await event.get_reply_message()
                if reply_msg and reply_msg.sender_id == me.id:
                    should_respond = True
            
            # Don't respond if not mentioned
            if not should_respond:
                return
        
        # Skip channel messages
        elif event.is_channel:
            return
        
        # Skip if no valid message text
        if not message_text or not message_text.strip():
            return
        
        print(f"📨 Received message: {message_text}")
        if event.is_group:
            print(f"👥 Group: {event.chat.title if hasattr(event.chat, 'title') else 'Unknown'}")
        
        try:
            # Send typing indicator
            async with client.action(event.chat_id, 'typing'):
                context_docs = []
                
                # Search knowledge base if RAG is available
                if vectorstore and USE_RAG:
                    print(f"🔍 Searching knowledge base for: {message_text}")
                    context_docs = search_knowledge_base(vectorstore, message_text, k=3)
                    
                    if context_docs:
                        print(f"📚 Found {len(context_docs)} relevant documents")
                        # Check if any are God Commands
                        god_commands_found = []
                        regular_docs_found = []
                        
                        for doc, score in context_docs:
                            source = doc.metadata.get('source', 'Unknown')
                            if doc.metadata.get('is_god_command', False):
                                god_commands_found.append((source, score))
                                print(f"   ⚡ GOD COMMAND: {source} (similarity: {score:.3f})")
                            else:
                                regular_docs_found.append((source, score))
                                print(f"   - {source} (similarity: {score:.3f})")
                        
                        if god_commands_found:
                            print(f"🔥 {len(god_commands_found)} God Commands will override behavior!")
                    else:
                        print("📝 No relevant documents found in knowledge base")
                
                # Create prompt with or without context
                if context_docs:
                    prompt = create_rag_prompt(message_text, context_docs, character_data)
                    
                    # Check if God Commands are present
                    has_god_commands = any(doc.metadata.get('is_god_command', False) for doc, score in context_docs)
                    
                    if has_god_commands:
                        response_prefix = "⚡ " if event.is_group else "⚡ "
                    else:
                        response_prefix = "🏆" if event.is_group else "🏆 "
                else:
                    prompt = create_rag_prompt(message_text, [], character_data)
                    response_prefix = "🎯 " if event.is_group else "🤖 "
                
                # Get AI response
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.7
                )
                
                # Get the AI response
                ai_response = response.choices[0].message.content
                
                # Format response with paragraphs if longer than 50 characters
                formatted_response = format_response_with_paragraphs(ai_response, min_length=50)
                
                print(f"🤖 AI Response: {formatted_response}")
                
                # Send the response back to Telegram with prefix
                full_response = f"{response_prefix}{formatted_response}"
                await event.respond(full_response)
                
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            print(f"❌ Error: {error_msg}")
            await event.respond(error_msg)

    async def main():
        """Main function to start the client"""
        print("🚀 Starting Agent Daredevil - Telegram RAG Bot...")
        
        try:
            # Start the client
            await client.start(phone=PHONE_NUMBER)
            
            # Get bot info
            me = await client.get_me()
            bot_name = me.first_name if me.first_name else "Agent Daredevil"
            bot_username = f"@{me.username}" if me.username else "no username"
            
            print("✅ Client started! You are now connected.")
            print(f"🎯 Bot Name: {bot_name}")
            print(f"👤 Username: {bot_username}")
            print("💬 Ready for private messages and group mentions!")
            print("🛑 Press Ctrl+C to stop the bot.")
            
            if character_data:
                print(f"🎭 Character: {character_data.get('name', 'Unknown')} persona loaded")
            else:
                print("⚠️ No character card loaded - using basic persona")
            
            if vectorstore:
                print("📚 RAG system is active - bot will use knowledge base for responses")
            else:
                print("📝 RAG system not available - bot will use general knowledge only")
            
            print("\n📋 Usage:")
            print("  • Private chats: Send any message")
            print(f"  • Group chats: Mention '{bot_name}' or {bot_username}")
            print("  • Group chats: Reply to bot messages")
            
            # Keep the client running
            await client.run_until_disconnected()
            
        except Exception as e:
            print(f"❌ Error starting client: {e}")
            print("Make sure your credentials are correct and try again.")

    if __name__ == '__main__':
        try:
            # Run the main function
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n👋 Bot stopped by user.")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
else:
    print("\n🔧 Please update your credentials and run the script again.")