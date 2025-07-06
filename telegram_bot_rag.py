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
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import requests
from bs4 import BeautifulSoup
import re
import aiohttp
from urllib.parse import quote_plus
import time
import functools

# Memory system imports
try:
    from session_memory import get_memory_manager
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    print("[!] Session memory system not available")

# Multi-domain RAG imports
try:
    from multi_domain_rag import MultiDomainRAG
    MULTI_DOMAIN_AVAILABLE = True
except ImportError:
    MULTI_DOMAIN_AVAILABLE = False
    print("[!] Multi-domain RAG system not available")

# Failsafe Configuration - Hierarchical Timeout System
MAX_RESPONSE_TIME = 45  # Maximum time for entire response generation (seconds)
LLM_TIMEOUT = 30  # OpenAI API timeout (should be less than MAX_RESPONSE_TIME)
WEB_SEARCH_TIMEOUT = 15  # Web search timeout (should be less than LLM_TIMEOUT)
HTTP_REQUEST_TIMEOUT = 10  # Individual HTTP request timeout
MAX_RETRIES = 2  # Maximum retries for failed operations
CIRCUIT_BREAKER_THRESHOLD = 5  # Number of failures before circuit breaker opens
CIRCUIT_BREAKER_TIMEOUT = 300  # Circuit breaker timeout (seconds)

# Circuit breaker state
circuit_breaker_state = {
    'web_search_failures': 0,
    'rag_search_failures': 0,
    'llm_failures': 0,
    'last_failure_time': None,
    'circuit_open': False
}

def circuit_breaker_check(service_name: str) -> bool:
    """Check if circuit breaker allows operation for a service"""
    failures = circuit_breaker_state.get(f'{service_name}_failures', 0)
    
    if failures >= CIRCUIT_BREAKER_THRESHOLD:
        if circuit_breaker_state.get('last_failure_time'):
            time_since_failure = time.time() - circuit_breaker_state['last_failure_time']
            if time_since_failure < CIRCUIT_BREAKER_TIMEOUT:
                circuit_breaker_state['circuit_open'] = True
                return False
            else:
                # Reset circuit breaker after timeout
                circuit_breaker_state[f'{service_name}_failures'] = 0
                circuit_breaker_state['circuit_open'] = False
                return True
    
    return True

def record_failure(service_name: str):
    """Record a failure for circuit breaker tracking"""
    if f'{service_name}_failures' not in circuit_breaker_state:
        circuit_breaker_state[f'{service_name}_failures'] = 0
    circuit_breaker_state[f'{service_name}_failures'] += 1
    circuit_breaker_state['last_failure_time'] = time.time()

def record_success(service_name: str):
    """Record a success for circuit breaker tracking"""
    if f'{service_name}_failures' not in circuit_breaker_state:
        circuit_breaker_state[f'{service_name}_failures'] = 0
    circuit_breaker_state[f'{service_name}_failures'] = max(0, circuit_breaker_state[f'{service_name}_failures'] - 1)

def with_timeout(timeout_seconds: int):
    """Decorator to add timeout to async functions"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
        return wrapper
    return decorator

def validate_assessment_result(assessment: Dict) -> Dict:
    """Validate and sanitize assessment results"""
    if not isinstance(assessment, dict):
        return {
            'confidence': 0.0,
            'recommendation': 'basic_response',
            'reason': 'Invalid assessment format'
        }
    
    # Ensure required fields exist with safe defaults
    assessment.setdefault('confidence', 0.0)
    assessment.setdefault('recommendation', 'basic_response')
    assessment.setdefault('reason', 'No reason provided')
    
    # Validate confidence is a number between 0 and 1
    try:
        confidence = float(assessment['confidence'])
        assessment['confidence'] = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        assessment['confidence'] = 0.0
    
    # Validate recommendation is a valid option
    valid_recommendations = [
        'use_rag_only', 'web_search', 'use_rag_with_web_fallback', 
        'ask_for_clarification', 'basic_response'
    ]
    if assessment['recommendation'] not in valid_recommendations:
        assessment['recommendation'] = 'basic_response'
    
    return assessment

def safe_print(message=""):
    """Print message with Unicode error handling"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace problematic characters with text equivalents
        safe_message = message.replace('🏀', '[NBA]').replace('🏎️', '[F1]').replace('🔄', '[MULTI]').replace('⚡', '[GOD]').replace('🏆', '[RAG]').replace('🤖', '[AI]').replace('🎯', '[BASIC]')
        print(safe_message)

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
USE_MULTI_DOMAIN = os.getenv('USE_MULTI_DOMAIN', 'True').lower() == 'true'  # Enable multi-domain routing

# Character Card Configuration
CHARACTER_CARD_PATH = "./cryptodevil.character.json"

# Memory System Configuration
MEMORY_DB_PATH = os.getenv('MEMORY_DB_PATH', './memory.db')
USE_MEMORY = os.getenv('USE_MEMORY', 'True').lower() == 'true'
MAX_SESSION_MESSAGES = int(os.getenv('MAX_SESSION_MESSAGES', '50'))
SESSION_TIMEOUT_HOURS = int(os.getenv('SESSION_TIMEOUT_HOURS', '24'))

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
        safe_print("[ERR] Missing credentials! Please update the following in telegram_bot_rag.py:")
        for cred in missing:
            safe_print(f"   - {cred}")
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
        safe_print(f"[!] Warning: Could not initialize RAG system: {e}")
        safe_print("[*] Bot will work without RAG. Use the RAG Manager to add documents first.")
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
        safe_print(f"[ERR] Error searching knowledge base: {e}")
        return []

def create_rag_prompt(user_message, context_docs, character_data=None, conversation_context=""):
    """Create a prompt that includes context from the knowledge base, character information, and conversation history"""
    
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
        # No RAG context, just character + user message + memory
        memory_section = f"\n\n{conversation_context}" if conversation_context else ""
        
        if character_context:
            return f"""{character_context}

{current_time_info}{memory_section}

IMPORTANT: Respond in FIRST PERSON as Agent Daredevil. You ARE Agent Daredevil, not an assistant helping someone else.

User: {user_message}

Respond as Agent Daredevil in first person, following your character guidelines above."""
        else:
            return f"""You are Agent Daredevil, a helpful AI assistant. Respond in FIRST PERSON.

{current_time_info}{memory_section}

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
    
    # Add conversation memory context
    if conversation_context:
        prompt_parts.append(conversation_context)
    
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
            safe_print(f"[!] Character card not found at {CHARACTER_CARD_PATH}")
            return None
        
        with open(character_path, 'r', encoding='utf-8') as f:
            character_data = json.load(f)
        
        safe_print(f"[+] Character card loaded: {character_data.get('name', 'Unknown')}")
        return character_data
    except Exception as e:
        safe_print(f"[ERR] Error loading character card: {e}")
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

# Add web search functionality with failsafes
@with_timeout(WEB_SEARCH_TIMEOUT)
async def search_web(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """Search the web for information about a query using multiple methods with failsafes"""
    # Check circuit breaker
    if not circuit_breaker_check('web_search'):
        safe_print("[WEB] Circuit breaker open - skipping web search")
        return []
    
    # Input validation
    if not query or not query.strip():
        safe_print("[WEB] Empty query provided")
        return []
    
    if len(query) > 500:  # Prevent excessively long queries
        query = query[:500]
        safe_print("[WEB] Query truncated to 500 characters")
    
    max_results = max(1, min(max_results, 10))  # Limit results between 1-10
    
    retry_count = 0
    while retry_count <= MAX_RETRIES:
        try:
            safe_print(f"[WEB] Searching web for: {query}")
            
            # Method 1: Try Wikipedia API for general knowledge
            try:
                wikipedia_results = await search_wikipedia(query, max_results=2)
                if wikipedia_results:
                    safe_print(f"[WEB] Found {len(wikipedia_results)} Wikipedia results")
                    record_success('web_search')
                    return wikipedia_results
            except Exception as e:
                safe_print(f"[WEB] Wikipedia search failed: {e}")
            
            # Method 2: Try DuckDuckGo with different approach
            try:
                search_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&pretty=1&no_html=1&skip_disambig=1"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                timeout = aiohttp.ClientTimeout(total=15, connect=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(search_url, headers=headers) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                results = []
                                
                                # Get abstract/summary
                                if data.get('Abstract') and len(data['Abstract']) > 20:
                                    results.append({
                                        'title': data.get('AbstractText', 'Search Result')[:200],
                                        'content': data.get('Abstract')[:500],
                                        'url': data.get('AbstractURL', 'https://duckduckgo.com/')
                                    })
                                
                                # Get related topics
                                if data.get('RelatedTopics'):
                                    for topic in data.get('RelatedTopics', [])[:2]:
                                        if isinstance(topic, dict) and topic.get('Text'):
                                            results.append({
                                                'title': 'Related Information',
                                                'content': topic.get('Text')[:500],
                                                'url': topic.get('FirstURL', 'https://duckduckgo.com/')
                                            })
                                
                                if results:
                                    safe_print(f"[WEB] Found {len(results)} DuckDuckGo results")
                                    record_success('web_search')
                                    return results
                            except Exception as json_error:
                                safe_print(f"[WEB] Failed to parse DuckDuckGo JSON: {json_error}")
                        else:
                            safe_print(f"[WEB] DuckDuckGo returned status {response.status}")
            except Exception as e:
                safe_print(f"[WEB] DuckDuckGo search failed: {e}")
            
            # Method 3: Create a fallback response with search suggestions
            safe_print("[WEB] Creating fallback search response")
            fallback_result = [{
                'title': 'Web Search Suggestion',
                'content': f"I wasn't able to search the web for current information about '{query}'. For the most up-to-date statistics and information, I recommend checking official sources like ESPN.com, NBA.com, Formula1.com, or other sports websites.",
                'url': 'https://www.google.com/search?q=' + quote_plus(query)
            }]
            
            # Don't record success for fallback, but don't record failure either
            return fallback_result
            
        except asyncio.TimeoutError:
            safe_print(f"[WEB] Timeout error for query: {query}")
            if retry_count < MAX_RETRIES:
                retry_count += 1
                safe_print(f"[WEB] Retrying ({retry_count}/{MAX_RETRIES})")
                await asyncio.sleep(2)
                continue
            else:
                record_failure('web_search')
                return []
        except Exception as e:
            safe_print(f"[WEB] Error in web search: {e}")
            if retry_count < MAX_RETRIES:
                retry_count += 1
                safe_print(f"[WEB] Retrying ({retry_count}/{MAX_RETRIES})")
                await asyncio.sleep(1)
                continue
            else:
                record_failure('web_search')
                return []
    
    # If we get here, all retries failed
    record_failure('web_search')
    return []

async def search_wikipedia(query: str, max_results: int = 2) -> List[Dict[str, str]]:
    """Search Wikipedia for information"""
    try:
        # Wikipedia API endpoint
        search_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote_plus(query.replace(' ', '_'))
        
        headers = {
            'User-Agent': 'Agent-Daredevil-Bot/1.0 (https://github.com/example/agent-daredevil)'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=10, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('extract') and len(data['extract']) > 50:
                        result = {
                            'title': data.get('title', 'Wikipedia'),
                            'content': data.get('extract', ''),
                            'url': data.get('content_urls', {}).get('desktop', {}).get('page', f'https://en.wikipedia.org/wiki/{quote_plus(query)}')
                        }
                        
                        # If we have a good result, try to get more from search API
                        results = [result]
                        
                        # Search for related articles
                        try:
                            search_api_url = f"https://en.wikipedia.org/api/rest_v1/page/related/{quote_plus(query.replace(' ', '_'))}"
                            async with session.get(search_api_url, timeout=5, headers=headers) as related_response:
                                if related_response.status == 200:
                                    related_data = await related_response.json()
                                    if related_data.get('pages'):
                                        for page in related_data['pages'][:1]:  # Get 1 related page
                                            if page.get('extract'):
                                                results.append({
                                                    'title': page.get('title', 'Related Wikipedia Article'),
                                                    'content': page.get('extract', ''),
                                                    'url': page.get('content_urls', {}).get('desktop', {}).get('page', 'https://wikipedia.org')
                                                })
                        except:
                            pass  # Related search is optional
                        
                        return results
                elif response.status == 404:
                    # Try search API instead
                    search_api_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={quote_plus(query)}&srlimit=2"
                    
                    async with session.get(search_api_url, timeout=10, headers=headers) as search_response:
                        if search_response.status == 200:
                            search_data = await search_response.json()
                            results = []
                            
                            for item in search_data.get('query', {}).get('search', [])[:max_results]:
                                title = item.get('title', '')
                                snippet = item.get('snippet', '').replace('<span class="searchmatch">', '').replace('</span>', '')
                                
                                if title and snippet:
                                    results.append({
                                        'title': f"Wikipedia: {title}",
                                        'content': snippet,
                                        'url': f"https://en.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}"
                                    })
                            
                            return results
        
        return []
    except Exception as e:
        safe_print(f"[WEB] Wikipedia search error: {e}")
        return []

def _detect_statistical_query(query: str) -> bool:
    """Detect if query asks for specific statistics that might not be available"""
    stat_patterns = [
        # Existing patterns
        r'averaged?\s+\d+[\.\d]*\s*\+?\s*(ppg|rpg|apg|points|rebounds|assists)',
        r'scored?\s+\d+[\.\d]*\s*\+?\s*(points|goals)',
        r'list\s+all\s+.*players?\s+who\s+averaged?',
        r'how\s+many\s+.*games?\s+did\s+.*\s+have',
        r'what\s+was\s+.*\s+average\s+in\s+\d{4}',
        r'stats?\s+for\s+.*\s+in\s+\d{4}',
        r'season\s+stats?\s+for',
        r'career\s+stats?\s+for',
        r'playoff\s+stats?\s+for',
        
        # NEW: General specific data patterns
        r'specific\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'exact\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'precise\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'detailed\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'current\s+(date|data|statistics|stats|numbers|figures|standings|results)',
        r'latest\s+(date|data|statistics|stats|numbers|figures|standings|results)',
        r'recent\s+(date|data|statistics|stats|numbers|figures|standings|results)',
        r'(date|data)\s+points?',
        r'when\s+(did|was|were)\s+.*\s+(happen|occur|take place)',
        r'what\s+(date|time|year|month|day)',
        r'(show|give|tell)\s+me\s+.*\s+(date|data|statistics|stats|numbers)',
        r'how\s+(many|much)\s+.*\s+(points|goals|wins|losses|games)',
        r'which\s+.*\s+(scored|had|achieved|won)\s+.*\s+(points|goals|games)',
        r'(schedule|fixture|calendar)\s+for',
        r'(results|scores|standings)\s+(from|for|of)',
        r'(performance|record)\s+(in|during|for)\s+\d{4}',
        # FIX: Add patterns for "specifics on", "details about", etc.
        r'specifics?\s+on',  # "specifics on engineering upgrades"
        r'details?\s+(about|on)',  # "details about/on upgrades"
        r'information\s+(about|on)',  # "information about upgrades"
        r'what.*specifics',  # "what specifics can you share"
        r'can\s+you\s+(share|tell|provide).*details',  # "can you share details"
        r'breakdown\s+(of|for)',  # "breakdown of upgrades"
        r'analysis\s+(of|for)',  # "analysis of performance"
        
        # NEW: Add patterns for recommendations, betting, predictions
        r'(give|provide|suggest|offer)\s+.*recommendations?',  # "give me recommendations"
        r'recommendations?\s+(for|about|on)',  # "recommendations for betting"
        r'(betting|bet|gambling)\s+(tips|advice|recommendations?|suggestions?)',  # "betting tips"
        r'place\s+(bets?|wagers?)',  # "place bets on the game"
        r'(predictions?|forecast|predict)\s+(for|about|on)',  # "predictions for the race"
        r'who\s+(will|should|might)\s+(win|lose)',  # "who will win the race"
        r'odds\s+(for|on|of)',  # "odds for the game"
        r'tips\s+(for|on|about)',  # "tips for betting"
        r'advice\s+(for|on|about)',  # "advice on the race"
        r'(fantasy|pick.*em)\s+(advice|tips|picks)',  # "fantasy advice"
        
        # NEW: F1/Sports schedule and current event patterns
        r'race\s+(this|next)\s+(sunday|weekend|week)',  # "race this Sunday"
        r'(game|match|race)\s+(today|tomorrow|tonight)',  # "game today"
        r'(what|which)\s+.*\s+(playing|racing)\s+(today|tomorrow|sunday)',  # "what team playing today"
        r'schedule\s+(for|this)\s+(week|weekend|today|tomorrow)',  # "schedule for this week"
        r'(current|upcoming|next)\s+(race|game|match)',  # "current race"
        r'what.*happening\s+(today|tomorrow|sunday|this weekend)',  # "what's happening this Sunday"
        r'think\s+about.*\s+(race|game|match)',  # "think about the race"
    ]
    
    query_lower = query.lower()
    for pattern in stat_patterns:
        if re.search(pattern, query_lower):
            return True
    return False

def _assess_rag_sufficiency(query: str, rag_context: List[Tuple[Any, float]]) -> Dict[str, Any]:
    """Assess if RAG context has sufficient information for the specific query"""
    if not rag_context:
        return {
            'sufficient': False,
            'reason': 'no_rag_results',
            'confidence': 0.0,
            'recommendation': 'web_search'
        }
    
    # Check if this is a statistical/specific data query
    is_statistical = _detect_statistical_query(query)
    
    # NEW: Detect if this is a career total vs. season-specific query
    query_lower = query.lower()
    
    # Career total indicators (no year specified)
    career_indicators = [
        r'how\s+many.*total',
        r'total.*finishes',
        r'total.*wins',
        r'total.*championships',
        r'total.*podiums',
        r'career.*total',
        r'all.*time',
        r'overall.*record',
        r'lifetime.*statistics',
        r'how\s+many.*\bdoes\b.*\bhave\b',  # "how many does Hamilton have" (present tense = career)
        r'how\s+many.*\bhas\b.*\bhad\b',   # "how many has Hamilton had"
        r'how\s+many.*championships.*\bhas\b',  # "how many championships has X won"
        r'what\s+is.*total.*number',  # "what is Hamilton's total number of wins"
        r'total.*race.*wins',  # "total race wins for Fernando Alonso"
    ]
    
    # Season-specific indicators (year mentioned)
    season_indicators = [
        r'\b(19|20)\d{2}\b',  # Any year from 1900-2099
        r'in.*\d{4}',
        r'during.*\d{4}',
        r'that\s+season',
        r'this\s+season',
        r'last\s+season'
    ]
    
    is_career_query = any(re.search(pattern, query_lower) for pattern in career_indicators)
    is_season_query = any(re.search(pattern, query_lower) for pattern in season_indicators)
    
    # Extract key terms from query
    specific_terms = []
    
    # Look for specific data indicators
    data_indicators = ['specific', 'exact', 'precise', 'detailed', 'current', 'latest', 'recent', 'when', 'what date', 'how many', 'which', 'results', 'scores', 'standings', 'schedule', 'performance', 'record']
    for term in data_indicators:
        if term in query_lower:
            specific_terms.append(term)
    
    # Analyze RAG context quality
    total_content_length = sum(len(doc.page_content) for doc, score in rag_context)
    avg_score = sum(score for doc, score in rag_context) / len(rag_context)
    
    # Check if RAG context contains specific data types
    has_dates = any(re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}', doc.page_content) for doc, score in rag_context)
    has_numbers = any(re.search(r'\d+\.?\d*\s*(points|goals|wins|losses|games|%|percent|podiums?|finishes?)', doc.page_content) for doc, score in rag_context)
    has_names = any(re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', doc.page_content) for doc, score in rag_context)
    
    # NEW: Check for career vs. season data coverage
    years_mentioned = set()
    for doc, score in rag_context:
        # Extract years from content
        year_matches = re.findall(r'\b(19|20)\d{2}\b', doc.page_content)
        years_mentioned.update(year_matches)
    
    # For career queries, we need data spanning multiple years or explicit career totals
    if is_career_query and not is_season_query:
        if len(years_mentioned) >= 3:  # Multiple years = likely career data
            career_coverage = True
        elif any(keyword in ' '.join(doc.page_content for doc, score in rag_context).lower() 
                for keyword in ['career', 'total', 'all-time', 'overall', 'lifetime']):
            career_coverage = True
        else:
            career_coverage = False
            
        if not career_coverage:
            return {
                'sufficient': False,
                'reason': 'insufficient_career_data',
                'confidence': 0.2,
                'recommendation': 'web_search',
                'details': f'Career query needs comprehensive data, but only found {len(years_mentioned)} year(s): {list(years_mentioned)}'
            }
    
    # For God Commands, they're usually sufficient unless asking for specific stats
    has_god_commands = any(doc.metadata.get('is_god_command', False) for doc, score in rag_context)
    
    # Assessment logic
    if has_god_commands and not is_statistical:
        return {
            'sufficient': True,
            'reason': 'god_commands_available',
            'confidence': 0.9,
            'recommendation': 'use_rag'
        }
    
    if is_statistical and specific_terms:
        # For statistical queries, we need specific data
        if has_dates and has_numbers:
            # Additional check for career queries
            if is_career_query and not is_season_query and len(years_mentioned) < 2:
                return {
                    'sufficient': False,
                    'reason': 'career_query_needs_comprehensive_data',
                    'confidence': 0.3,
                    'recommendation': 'web_search',
                    'details': f'Career statistical query but only found limited year coverage: {list(years_mentioned)}'
                }
            else:
                return {
                    'sufficient': True,
                    'reason': 'specific_data_available',
                    'confidence': 0.8,
                    'recommendation': 'use_rag'
                }
        elif total_content_length > 500 and avg_score < 0.5:
            # Check if this is sufficient for the query type
            if is_career_query and not is_season_query:
                return {
                    'sufficient': False,
                    'reason': 'career_query_insufficient_scope',
                    'confidence': 0.4,
                    'recommendation': 'web_search'
                }
            else:
                return {
                    'sufficient': True,
                    'reason': 'relevant_context_available',
                    'confidence': 0.6,
                    'recommendation': 'use_rag_with_web_fallback'
                }
        else:
            return {
                'sufficient': False,
                'reason': 'insufficient_specific_data',
                'confidence': 0.3,
                'recommendation': 'web_search'
            }
    
    # General assessment
    if avg_score < 0.6 and total_content_length > 300:
        # Additional career query check
        if is_career_query and not is_season_query and len(years_mentioned) < 2:
            return {
                'sufficient': False,
                'reason': 'career_query_limited_scope',
                'confidence': 0.4,
                'recommendation': 'web_search'
            }
        else:
            return {
                'sufficient': True,
                'reason': 'good_general_context',
                'confidence': 0.7,
                'recommendation': 'use_rag'
            }
    elif avg_score < 0.8 and total_content_length > 100:
        return {
            'sufficient': True,
            'reason': 'moderate_context',
            'confidence': 0.5,
            'recommendation': 'use_rag_with_web_fallback'
        }
    else:
        return {
            'sufficient': False,
            'reason': 'low_relevance_or_content',
            'confidence': 0.2,
            'recommendation': 'web_search'
        }

def _classify_query_type(user_message: str) -> str:
    """Classify the type of query for specific redirect suggestions"""
    query_lower = user_message.lower()
    
    # Current stats patterns
    current_patterns = [
        r'this\s+(season|year)', r'current.*stats', r'how\s+many.*this', 
        r'what.*average.*this', r'standings.*now', r'right\s+now',
        r'so\s+far\s+this', r'currently', r'at\s+the\s+moment'
    ]
    
    # Historical patterns  
    historical_patterns = [
        r'\b(19|20)\d{2}\b', r'in.*\d{4}', r'back\s+in', r'used\s+to',
        r'career.*stats', r'all.*time.*record', r'throughout.*career',
        r'historically', r'over.*years'
    ]
    
    # News patterns
    news_patterns = [
        r'what.*happened', r'latest.*news', r'recently', r'last.*race',
        r'got.*traded', r'signed.*with', r'breaking.*news', r'just.*announced',
        r'yesterday', r'today', r'this.*week'
    ]
    
    # Schedule patterns
    schedule_patterns = [
        r'when.*next', r'schedule.*for', r'what.*time', r'upcoming.*games',
        r'when.*is.*the', r'what.*day', r'tomorrow.*race', r'this.*weekend'
    ]
    
    # Comparison patterns
    comparison_patterns = [
        r'better.*than', r'vs\.?', r'versus', r'compare.*to', r'who.*best',
        r'which.*is.*better', r'stronger.*than', r'faster.*than'
    ]
    
    # Prediction patterns
    prediction_patterns = [
        r'who.*will.*win', r'predict', r'odds.*for', r'chances.*of',
        r'going.*to.*win', r'likely.*to', r'think.*will'
    ]
    
    # Check patterns and return classification
    if any(re.search(p, query_lower) for p in current_patterns):
        return 'current_stats'
    elif any(re.search(p, query_lower) for p in historical_patterns):
        return 'historical_stats'
    elif any(re.search(p, query_lower) for p in news_patterns):
        return 'news_events'
    elif any(re.search(p, query_lower) for p in schedule_patterns):
        return 'schedule'
    elif any(re.search(p, query_lower) for p in comparison_patterns):
        return 'comparison'
    elif any(re.search(p, query_lower) for p in prediction_patterns):
        return 'prediction'
    else:
        return 'general'

def _detect_sport_domain(user_message: str) -> str:
    """Detect if query is F1, NBA, or general sports"""
    query_lower = user_message.lower()
    
    f1_keywords = [
        'f1', 'formula', 'race', 'driver', 'hamilton', 'verstappen', 'mercedes', 'ferrari',
        'red bull', 'mclaren', 'aston martin', 'pole position', 'championship', 'grand prix',
        'silverstone', 'monaco', 'spa', 'monza', 'qualifying', 'drs', 'pit stop'
    ]
    nba_keywords = [
        'nba', 'basketball', 'lakers', 'celtics', 'lebron', 'jordan', 'points', 'assists',
        'rebounds', 'mvp', 'playoffs', 'finals', 'warriors', 'nets', 'heat', 'bulls',
        'scoring', 'three-pointer', 'dunk', 'coach', 'trade', 'draft'
    ]
    
    f1_score = sum(1 for keyword in f1_keywords if keyword in query_lower)
    nba_score = sum(1 for keyword in nba_keywords if keyword in query_lower)
    
    if f1_score > nba_score and f1_score > 0:
        return 'f1'
    elif nba_score > 0:
        return 'nba'
    else:
        return 'general'

def _get_current_stats_redirect(sport_domain: str) -> str:
    """Get redirect message for current stats queries"""
    if sport_domain == 'f1':
        return """I don't have access to current season statistics that update in real-time.

For the most up-to-date F1 stats, I'd recommend:
🏎️ **Formula1.com** - Official standings, driver stats, and race results
🏎️ **ESPN F1** - Comprehensive current season analysis  
🏎️ **Team websites** - Mercedes, Red Bull, Ferrari for detailed team stats

Alternatively, I can help you with:
• Historical F1 achievements and records
• How the points system works
• Technical aspects of Formula 1
• Driver backgrounds and career highlights
• Championship history and memorable races

What specific aspect of F1 would you like to explore instead?"""
    elif sport_domain == 'nba':
        return """I don't have access to current season statistics that update in real-time.

For the most up-to-date NBA stats, I'd recommend:
🏀 **NBA.com** - Official stats, standings, and player performance
🏀 **ESPN.com** - Current season analysis and team breakdowns
🏀 **Basketball-Reference.com** - Detailed statistical breakdowns

Alternatively, I can help you with:
• Historical NBA achievements and records  
• How different stats categories work
• Player backgrounds and career highlights
• Championship history and legendary games
• Understanding basketball strategies and rules

What specific aspect of basketball would you like to explore instead?"""
    else:
        return """I don't have access to current season statistics that update in real-time.

For up-to-date sports stats, I'd recommend:
📊 **ESPN.com** - Comprehensive current sports coverage
📊 **Official league websites** - Most accurate current data
📊 **Team websites** - Direct from the source

Alternatively, I can help you with:
• Historical achievements and records
• How different sports work
• General sports knowledge and trivia
• Background information on teams and athletes

What specific aspect would you like to explore instead?"""

def _get_historical_stats_redirect(sport_domain: str) -> str:
    """Get redirect message for historical stats queries"""
    if sport_domain == 'f1':
        return """I have some historical F1 data, but I might not have the exact detailed statistics you're looking for from that specific period.

For comprehensive historical F1 data, try:
📊 **StatsF1.com** - Detailed historical race and championship data
📊 **Formula1.com** - Official historical records and archives
📊 **Racing-Reference.info** - Extensive historical racing statistics

I can help you with:
• Major career achievements and milestones
• Championship victories and memorable races
• Context about what made certain seasons significant
• Comparisons with other great drivers and eras
• Technical evolution of Formula 1

What specific aspect of F1 history interests you most?"""
    elif sport_domain == 'nba':
        return """I have some historical NBA data, but I might not have the exact detailed statistics you're looking for from that specific period.

For precise historical NBA stats, try:
📊 **Basketball-Reference.com** - The gold standard for NBA historical data
📊 **NBA.com** - Official historical records and archives
📊 **ESPN.com** - Historical analysis and context

I can help you with:
• Major career achievements and milestones
• Championship runs and legendary performances
• Context about what made certain seasons special
• Comparisons with other great players and eras
• Evolution of basketball over the decades

What specific aspect of NBA history interests you most?"""
    else:
        return """I have some historical sports data, but I might not have the exact detailed statistics you're looking for from that specific time period.

For comprehensive historical sports data, try:
📊 **Sports-Reference.com** - Detailed historical data across multiple sports
📊 **Official league websites** - Historical archives and records
📊 **ESPN.com** - Historical analysis and context

I can help you with:
• Major achievements and milestones
• Championship moments and legendary performances  
• Context about significant periods in sports
• General sports history and evolution

What specific aspect of sports history interests you most?"""

def _get_news_events_redirect(sport_domain: str) -> str:
    """Get redirect message for news and current events queries"""
    if sport_domain == 'f1':
        return """I don't have access to real-time news or recent events that happened after my last update.

For breaking F1 news and recent developments:
📺 **Formula1.com** - Official race reports and breaking news
📺 **ESPN F1** - Immediate race coverage and analysis
📺 **Motorsport.com** - Comprehensive F1 journalism
📺 **Sky Sports F1** - Live coverage and expert analysis

I can help you with:
• Background context on drivers, teams, and storylines
• Technical explanations of F1 concepts
• Historical context for ongoing narratives
• General information about how F1 works

Is there a specific driver, team, or F1 concept you'd like to know more about?"""
    elif sport_domain == 'nba':
        return """I don't have access to real-time news or recent events that happened after my last update.

For breaking NBA news and recent developments:
📺 **ESPN.com** - Immediate NBA news and analysis
📺 **NBA.com** - Official league announcements  
📺 **The Athletic** - In-depth NBA journalism
📺 **Shams Charania & Adrian Wojnarowski** on Twitter - Breaking news

I can help you with:
• Background context on players, teams, and storylines
• Explaining NBA rules, strategies, and concepts
• Historical context for ongoing narratives
• General information about how the NBA works

Is there a specific player, team, or basketball concept you'd like to know more about?"""
    else:
        return """I don't have access to real-time news or recent events that happened after my last update.

For breaking sports news and recent developments:
📺 **ESPN.com** - Comprehensive sports news coverage
📺 **Official league websites** - Direct announcements
📺 **Sports journalism apps** - Real-time notifications

I can help you with:
• Background context on athletes, teams, and storylines
• Explaining sports rules, strategies, and concepts
• Historical context for ongoing narratives
• General sports knowledge and information

Is there a specific sport, team, or concept you'd like to know more about?"""

def _get_schedule_redirect(sport_domain: str) -> str:
    """Get redirect message for schedule queries"""
    if sport_domain == 'f1':
        return """I don't have access to real-time schedules or current calendar information.

For up-to-date F1 schedules:
📅 **Formula1.com** - Official race calendar with session times
📅 **ESPN F1** - Race schedules with timezone conversions
📅 **F1 Mobile App** - Personalized notifications and reminders
📅 **Your local TV guide** - Broadcasting schedules

I can help you understand:
• How F1 race weekends are typically structured
• What happens during practice, qualifying, and race sessions
• General timing of the F1 season
• Time zone considerations for international races

Would you like to know more about how F1 race weekends work or what typically happens during this time of year?"""
    elif sport_domain == 'nba':
        return """I don't have access to real-time schedules or current calendar information.

For up-to-date NBA schedules:
📅 **NBA.com** - Official game schedules and times
📅 **ESPN.com** - Game schedules with TV information
📅 **NBA Mobile App** - Personalized team notifications
📅 **Your team's official website** - Detailed schedule information

I can help you understand:
• How NBA seasons are typically structured
• What happens during regular season vs playoffs
• General timing of different NBA events
• How scheduling works across time zones

Would you like to know more about how the NBA season format works or what typically happens during this time of year?"""
    else:
        return """I don't have access to real-time schedules or current calendar information.

For up-to-date sports schedules:
📅 **ESPN.com** - Multi-sport schedule coverage
📅 **Official league websites** - Most accurate scheduling
📅 **Sports apps** - Personalized notifications
📅 **Local sports media** - Regional coverage

I can help you understand:
• How different sports seasons are structured
• General timing of championships and playoffs
• How scheduling typically works
• What to expect during different parts of seasons

Would you like to know more about how a particular sport's season works?"""

def _get_comparison_redirect(sport_domain: str) -> str:
    """Get redirect message for comparison queries"""
    if sport_domain == 'f1':
        return """That's a fascinating F1 comparison! I can share some historical context and career highlights, but detailed current performance comparisons need up-to-date data.

For detailed current F1 comparisons:
📊 **Formula1.com** - Official driver and team statistics
📊 **ESPN F1** - Head-to-head analysis tools
📊 **F1 comparison websites** - Side-by-side statistical breakdowns

I can help you explore:
• Historical achievements and career milestones
• Different eras of Formula 1 and how they compare
• What makes each driver's style unique
• The context behind their biggest accomplishments
• Technical differences between teams and cars

What specific aspects would you like me to compare - their careers, driving styles, achievements, or impact on F1?"""
    elif sport_domain == 'nba':
        return """That's a fascinating NBA comparison! I can share some historical context and career highlights, but detailed current performance comparisons need up-to-date stats.

For detailed current NBA comparisons:
📊 **NBA.com** - Official player comparison tools
📊 **ESPN.com** - Head-to-head statistical analysis
📊 **Basketball-Reference.com** - Advanced statistical comparisons

I can help you explore:
• Historical achievements and career milestones
• Different eras of basketball and how they compare
• What makes each player's style unique
• The context behind their biggest accomplishments
• How different positions and roles compare

What specific aspects would you like me to compare - their careers, playing styles, achievements, or impact on basketball?"""
    else:
        return """That's a fascinating comparison! I can share some historical context and career highlights, but detailed current performance comparisons need up-to-date stats.

For detailed current sports comparisons:
📊 **ESPN.com** - Multi-sport comparison tools
📊 **Official league websites** - Statistical breakdowns
📊 **Sports analytics sites** - Advanced comparison metrics

I can help you explore:
• Historical achievements and career milestones
• Different eras and how they compare
• What makes each athlete unique
• The context behind their biggest accomplishments
• How different sports and positions compare

What specific aspects would you like me to compare - their careers, styles, achievements, or impact on their sport?"""

def _get_prediction_redirect(sport_domain: str) -> str:
    """Get redirect message for prediction queries"""
    return """I don't make predictions or provide betting advice, and I don't have access to current odds or expert predictions.

For expert analysis and predictions:
🎯 **ESPN expert predictions** - Professional sports analysts
🎯 **Official sports commentators** - Insider knowledge and analysis  
🎯 **Sports betting sites** - Current odds and predictions (if that's your interest)
🎯 **Sports podcasts and shows** - Expert opinions and discussions

I can help you understand:
• What factors typically influence outcomes in sports
• Historical patterns and trends that matter
• How playoff and championship systems work
• What makes teams or athletes competitive
• The unpredictable nature of sports

Would you like to explore what factors usually determine success in this sport, or learn about how competitions typically unfold?"""

def _get_general_redirect(sport_domain: str) -> str:
    """Get redirect message for general queries"""
    return """I searched my knowledge base and the web, but I couldn't find sufficient specific information to answer your question confidently.

For the most current and detailed information:
🔍 **ESPN.com** - Comprehensive sports coverage
🔍 **Official league/sport websites** - Most accurate information
🔍 **Specialized sports news sources** - Expert analysis

I can help you with:
• General sports knowledge and explanations
• Historical context and background information
• Understanding how different sports work
• Player and team backgrounds
• Rules, strategies, and technical aspects

Could you be more specific about what you're looking for, or would you like me to help with a related topic I might know more about?"""

def _create_smart_clarification_prompt(user_message: str, query_type: str, sport_domain: str) -> str:
    """Create a smart clarification prompt based on query analysis"""
    
    # Get redirect template based on query type
    redirect_functions = {
        'current_stats': _get_current_stats_redirect,
        'historical_stats': _get_historical_stats_redirect,
        'news_events': _get_news_events_redirect,
        'schedule': _get_schedule_redirect,
        'comparison': _get_comparison_redirect,
        'prediction': _get_prediction_redirect,
        'general': _get_general_redirect
    }
    
    redirect_function = redirect_functions.get(query_type, redirect_functions['general'])
    redirect_content = redirect_function(sport_domain)
    
    return f"""You are Agent Daredevil. The user asked: "{user_message}"

{redirect_content}

IMPORTANT INSTRUCTIONS:
- Respond in FIRST PERSON as Agent Daredevil
- Use the suggested redirect content above as your response
- Keep it conversational and maintain your personality
- Be helpful and engaging, not dismissive
- Show genuine interest in helping them find what they need

User: {user_message}
Respond as Agent Daredevil with the smart redirect:"""

def _assess_web_search_confidence(web_results: List[Dict[str, str]], query: str) -> Dict[str, Any]:
    """Assess confidence in web search results"""
    if not web_results:
        return {
            'confident': False,
            'confidence': 0.0,
            'reason': 'no_web_results',
            'recommendation': 'ask_for_clarification'
        }
    
    # Check result quality
    total_content_length = sum(len(result.get('content', '')) for result in web_results)
    valid_urls = sum(1 for result in web_results if result.get('url') and 'http' in result.get('url', ''))
    
    # Look for specific data in results
    query_lower = query.lower()
    has_relevant_content = False
    
    for result in web_results:
        content = result.get('content', '').lower()
        # Check if content seems relevant to query
        query_words = [word for word in query_lower.split() if len(word) > 2]
        matching_words = sum(1 for word in query_words if word in content)
        
        if matching_words > len(query_words) * 0.3:  # 30% of query words found
            has_relevant_content = True
            break
    
    # Confidence assessment
    if total_content_length > 500 and valid_urls > 0 and has_relevant_content:
        return {
            'confident': True,
            'confidence': 0.8,
            'reason': 'good_web_results',
            'recommendation': 'use_web_results'
        }
    elif total_content_length > 200 and has_relevant_content:
        return {
            'confident': True,
            'confidence': 0.6,
            'reason': 'moderate_web_results',
            'recommendation': 'use_web_results'
        }
    elif total_content_length > 100:
        return {
            'confident': True,
            'confidence': 0.4,
            'reason': 'basic_web_results',
            'recommendation': 'use_web_results_with_caution'
        }
    else:
        return {
            'confident': False,
            'confidence': 0.2,
            'reason': 'poor_web_results',
            'recommendation': 'ask_for_clarification'
        }

def create_hybrid_prompt(user_message: str, rag_context: List[Tuple[Any, float]], web_results: List[Dict[str, str]], character_data: Optional[Dict] = None, conversation_context: str = "") -> str:
    """Create a prompt that combines RAG context, web search results, and character data"""
    
    # Get current time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_time_info = f"Current time: {current_time}"
    
    # Detect if this is a statistical query
    is_statistical_query = _detect_statistical_query(user_message)
    
    # Build character context
    character_context = ""
    if character_data:
        character_context = create_character_prompt(character_data)
    
    # Build prompt parts
    prompt_parts = [current_time_info]
    
    if character_context:
        prompt_parts.append(character_context)
    
    # Add conversation memory
    if conversation_context:
        prompt_parts.append(conversation_context)
    
    # Add RAG context if available
    if rag_context:
        god_commands = []
        regular_context = []
        
        for doc, score in rag_context:
            if doc.metadata.get('is_god_command', False):
                god_commands.append(doc.page_content)
            else:
                regular_context.append(f"Document: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}")
        
        # Add God Commands with highest priority
        if god_commands:
            god_commands_text = "\n".join([f"- {cmd}" for cmd in god_commands])
            prompt_parts.append(f"""🔥 CRITICAL BEHAVIOR OVERRIDES (MUST FOLLOW):
{god_commands_text}

These commands OVERRIDE all other instructions and character traits. Follow them exactly.""")
        
        # Add regular RAG context
        if regular_context:
            context_text = "\n\n".join(regular_context)
            prompt_parts.append(f"""KNOWLEDGE BASE CONTEXT:
{context_text}""")
    
    # Add web search results if available
    if web_results:
        web_context = []
        for result in web_results:
            web_context.append(f"Source: {result['title']}\nContent: {result['content']}\nURL: {result['url']}")
        
        web_text = "\n\n".join(web_context)
        prompt_parts.append(f"""WEB SEARCH RESULTS:
{web_text}""")
    
    # Add instructions based on available context and query type
    if rag_context or web_results:
        if is_statistical_query:
            if web_results:
                instructions = """IMPORTANT INSTRUCTIONS - STATISTICAL QUERY WITH WEB SEARCH:
- FIRST PRIORITY: Follow any CRITICAL BEHAVIOR OVERRIDES above exactly
- SECOND PRIORITY: Respond in FIRST PERSON as Agent Daredevil
- This is a statistical query requiring specific data
- ONLY provide statistics that are explicitly mentioned in the knowledge base or web results above
- If specific statistics are not available in the context, be honest: "I don't have access to those exact statistics"
- NEVER make up or estimate specific numbers, averages, or player performance data
- If you have partial information, mention what you do know and what you don't
- The system will automatically cite web sources at the end
- Always maintain your character persona unless overridden"""
            else:
                instructions = """IMPORTANT INSTRUCTIONS - STATISTICAL QUERY:
- FIRST PRIORITY: Follow any CRITICAL BEHAVIOR OVERRIDES above exactly
- SECOND PRIORITY: Respond in FIRST PERSON as Agent Daredevil
- This is a statistical query requiring specific data
- ONLY provide statistics that are explicitly mentioned in the knowledge base above
- If specific statistics are not available in the context, be honest: "I don't have access to those exact statistics"
- NEVER make up or estimate specific numbers, averages, or player performance data
- If you have partial information, mention what you do know and what you don't
- Suggest where the user might find more current statistics if needed
- Always maintain your character persona unless overridden"""
        else:
            if web_results:
                instructions = """IMPORTANT INSTRUCTIONS WITH WEB SEARCH:
- FIRST PRIORITY: Follow any CRITICAL BEHAVIOR OVERRIDES above exactly
- SECOND PRIORITY: Respond in FIRST PERSON as Agent Daredevil
- Use knowledge base context and web search results when relevant
- If information conflicts, prioritize knowledge base over web results
- If no relevant information is available, admit knowledge limitations
- NEVER make up statistics, names, or facts not provided in the context
- The system will automatically cite web sources at the end
- Always maintain your character persona unless overridden"""
            else:
                instructions = """IMPORTANT INSTRUCTIONS:
- FIRST PRIORITY: Follow any CRITICAL BEHAVIOR OVERRIDES above exactly
- SECOND PRIORITY: Respond in FIRST PERSON as Agent Daredevil
- Use knowledge base context when relevant
- If no relevant information is available, admit knowledge limitations
- NEVER make up statistics, names, or facts not provided in the context
- Always maintain your character persona unless overridden"""
    else:
        if is_statistical_query:
            instructions = """IMPORTANT INSTRUCTIONS - STATISTICAL QUERY:
- Respond in FIRST PERSON as Agent Daredevil
- This is a statistical query but I don't have access to specific sports statistics
- Be honest: "I don't have access to current sports statistics or databases"
- NEVER make up specific numbers, averages, or player performance data
- Suggest reliable sources like ESPN.com, NBA.com, Formula1.com, or official team websites
- Offer to help with other basketball/F1-related questions that don't require specific stats"""
        else:
            instructions = """IMPORTANT INSTRUCTIONS:
- Respond in FIRST PERSON as Agent Daredevil
- Use your general knowledge to help the user
- If you don't have specific information about the topic, be honest about limitations
- NEVER make up statistics, names, or facts
- Suggest reliable sources when appropriate
- Suggest the user ask more specific questions if needed"""
    
    prompt_parts.append(instructions)
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Respond as Agent Daredevil in first person:")
    
    return "\n\n".join(prompt_parts)

def create_enhanced_hybrid_prompt(user_message: str, rag_context: List[Tuple[Any, float]], web_results: List[Dict[str, str]], character_data: Optional[Dict] = None, conversation_context: str = "", rag_assessment: Dict = None, web_assessment: Dict = None) -> str:
    """Create an enhanced hybrid prompt that takes into account RAG and web search assessment results"""
    
    # Get current time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_time_info = f"Current time: {current_time}"
    
    # Detect if this is a statistical query
    is_statistical_query = _detect_statistical_query(user_message)
    
    # Build character context
    character_context = ""
    if character_data:
        character_context = create_character_prompt(character_data)
    
    # Build prompt parts
    prompt_parts = [current_time_info]
    
    if character_context:
        prompt_parts.append(character_context)
    
    # Add conversation memory
    if conversation_context:
        prompt_parts.append(conversation_context)
    
    # Add RAG context assessment
    if rag_context and rag_assessment:
        god_commands = []
        regular_context = []
        
        for doc, score in rag_context:
            if doc.metadata.get('is_god_command', False):
                god_commands.append(doc.page_content)
            else:
                regular_context.append(f"Document: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}")
        
        # Add God Commands with highest priority
        if god_commands:
            god_commands_text = "\n".join([f"- {cmd}" for cmd in god_commands])
            prompt_parts.append(f"""🔥 CRITICAL BEHAVIOR OVERRIDES (MUST FOLLOW):
{god_commands_text}

These commands OVERRIDE all other instructions and character traits. Follow them exactly.""")
        
        # Add regular RAG context with assessment info
        if regular_context:
            context_text = "\n\n".join(regular_context)
            rag_confidence_note = f"(RAG Assessment: {rag_assessment['reason']} - Confidence: {rag_assessment['confidence']:.2f})"
            prompt_parts.append(f"""KNOWLEDGE BASE CONTEXT {rag_confidence_note}:
{context_text}""")
    
    # Add web search results with assessment
    if web_results and web_assessment:
        web_context = []
        for result in web_results:
            web_context.append(f"Source: {result['title']}\nContent: {result['content']}\nURL: {result['url']}")
        
        web_text = "\n\n".join(web_context)
        web_confidence_note = f"(Web Assessment: {web_assessment['reason']} - Confidence: {web_assessment['confidence']:.2f})"
        prompt_parts.append(f"""WEB SEARCH RESULTS {web_confidence_note}:
{web_text}""")
    
    # Enhanced instructions based on assessments
    instructions = """IMPORTANT INSTRUCTIONS - ENHANCED HYBRID RESPONSE:
- FIRST PRIORITY: Follow any CRITICAL BEHAVIOR OVERRIDES above exactly
- SECOND PRIORITY: Respond in FIRST PERSON as Agent Daredevil
- I have searched both my knowledge base and the web for your question"""
    
    if rag_assessment and web_assessment:
        if rag_assessment['confidence'] >= 0.7:
            instructions += f"""
- My knowledge base has good information for your question ({rag_assessment['reason']})
- Use the knowledge base information as the primary source"""
        elif web_assessment['confidence'] >= 0.7:
            instructions += f"""
- My knowledge base has limited information, but web search found good results ({web_assessment['reason']})
- Use web search results as the primary source, mention knowledge base limitations"""
        elif rag_assessment['confidence'] >= 0.5 and web_assessment['confidence'] >= 0.5:
            instructions += f"""
- Both my knowledge base and web search have moderate information
- Combine information from both sources, noting any limitations or uncertainties"""
        else:
            instructions += f"""
- Both my knowledge base and web search have limited information
- Be honest about limitations while providing what information is available
- Suggest more specific questions or reliable sources for better information"""
    
    if is_statistical_query:
        instructions += """
- This is a statistical query requiring specific data
- ONLY provide statistics that are explicitly mentioned in the context above
- If specific statistics are not available, be honest about limitations
- NEVER make up or estimate specific numbers, averages, or performance data"""
    
    instructions += """
- Always maintain your character persona unless overridden
- If information conflicts between sources, prioritize knowledge base over web results
- The system will automatically cite web sources at the end"""
    
    prompt_parts.append(instructions)
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Respond as Agent Daredevil in first person:")
    
    return "\n\n".join(prompt_parts)

@with_timeout(MAX_RESPONSE_TIME)
async def get_hybrid_response(user_message: str, event, openai_client, vectorstore, multi_domain_rag, character_data, conversation_context: str = "") -> Dict[str, Any]:
    """Get a hybrid response using RAG + Web Search + LLM with comprehensive failsafes"""
    
    response_data = {
        'content': '',
        'prefix': '🤖 ',
        'sources': [],
        'method': 'basic',
        'error': None,
        'timeout': False
    }
    
    # Input validation
    if not user_message or not user_message.strip():
        response_data['content'] = "I didn't receive a valid message. Please try asking me something!"
        response_data['error'] = "Empty message"
        return response_data
    
    # Prevent excessively long messages
    if len(user_message) > 2000:
        user_message = user_message[:2000]
        safe_print("[HYBRID] Message truncated to 2000 characters")
    
    retry_count = 0
    while retry_count <= MAX_RETRIES:
        try:
            # Step 1: Try RAG first
            rag_context = []
            domain_info = None
            
            # Enhanced contextual query handling
            enhanced_query = user_message
            is_contextual_query = False
            
            # Check if this is a contextual query that needs conversation history
            contextual_indicators = ['updates', 'update', 'this', 'that', 'it', 'them', 'they', 'latest', 'recent', 'new']
            if any(indicator in user_message.lower() for indicator in contextual_indicators):
                is_contextual_query = True
                safe_print(f"[CONTEXT] Detected contextual query: '{user_message}'")
                
                # Try to enhance the query with conversation context
                if conversation_context:
                    # Extract key topics from conversation history
                    conversation_words = conversation_context.lower().split()
                    important_terms = []
                    
                    # Look for NBA/F1 related terms in recent conversation
                    nba_terms = ['nba', 'basketball', 'lakers', 'warriors', 'celtics', 'lebron', 'curry', 'playoffs', 'finals']
                    f1_terms = ['f1', 'formula1', 'ferrari', 'mercedes', 'hamilton', 'verstappen', 'racing', 'grand prix']
                    
                    for term in nba_terms + f1_terms:
                        if term in conversation_words:
                            important_terms.append(term)
                    
                    if important_terms:
                        enhanced_query = f"{user_message} {' '.join(important_terms[:3])}"
                        safe_print(f"[CONTEXT] Enhanced query: '{enhanced_query}'")
            
            # RAG search with circuit breaker protection
            if vectorstore and circuit_breaker_check('rag_search'):
                try:
                    safe_print(f"[HYBRID] Step 1: RAG search for: {enhanced_query}")
                    
                    # Use multi-domain RAG if available
                    if multi_domain_rag:
                        domain_info = multi_domain_rag.detect_domain_with_context(enhanced_query, str(event.sender_id))
                        
                        if domain_info and domain_info.get('primary_domain'):
                            search_results = multi_domain_rag.search_domain_specific(enhanced_query, domain_info['primary_domain'], k=5)
                            if search_results:
                                rag_context = search_results
                                response_data['method'] = 'multi_domain_rag'
                                
                                # Set domain-specific prefix
                                domain_config = multi_domain_rag.domains[domain_info['primary_domain']]
                                response_data['prefix'] = f"{domain_config.emoji} "
                                response_data['sources'].append(f"Domain: {domain_config.name}")
                    
                    # Fallback to standard RAG if multi-domain didn't work
                    if not rag_context:
                        rag_context = search_knowledge_base(vectorstore, enhanced_query, k=5)
                        if rag_context:
                            response_data['method'] = 'standard_rag'
                            response_data['prefix'] = '🏆 '
                            response_data['sources'].append('Knowledge Base')
                    
                    if rag_context:
                        safe_print(f"[HYBRID] RAG found {len(rag_context)} relevant documents")
                        record_success('rag_search')
                        
                        # Check for God Commands
                        has_god_commands = any(doc.metadata.get('is_god_command', False) for doc, score in rag_context)
                        if has_god_commands:
                            response_data['prefix'] = '⚡ '
                            response_data['sources'].append('God Commands')
                    else:
                        safe_print("[HYBRID] No relevant RAG results found")
                        
                except Exception as e:
                    safe_print(f"[HYBRID] RAG search failed: {e}")
                    record_failure('rag_search')
                    response_data['error'] = f"RAG error: {str(e)}"
            elif not circuit_breaker_check('rag_search'):
                safe_print("[HYBRID] RAG search skipped - circuit breaker open")
            
            # Step 2: Assess RAG sufficiency and decide on web search
            try:
                rag_assessment = _assess_rag_sufficiency(user_message, rag_context)
                rag_assessment = validate_assessment_result(rag_assessment)
                safe_print(f"[HYBRID] RAG Assessment: {rag_assessment['reason']} (confidence: {rag_assessment['confidence']:.2f})")
            except Exception as e:
                safe_print(f"[HYBRID] RAG assessment failed: {e}")
                rag_assessment = validate_assessment_result({})
            
            web_results = []
            web_assessment = None
            
            # Only trigger web search if RAG is insufficient
            if rag_assessment['recommendation'] in ['web_search', 'use_rag_with_web_fallback']:
                try:
                    search_query = enhanced_query if is_contextual_query else user_message
                    safe_print(f"[HYBRID] Step 2: Web search triggered - {rag_assessment['reason']}")
                    safe_print(f"[HYBRID] Searching web for: {search_query}")
                    web_results = await search_web(search_query, max_results=3)
                    
                    # Assess web search confidence
                    try:
                        web_assessment = _assess_web_search_confidence(web_results, user_message)
                        web_assessment = validate_assessment_result(web_assessment)
                        safe_print(f"[HYBRID] Web Assessment: {web_assessment['reason']} (confidence: {web_assessment['confidence']:.2f})")
                    except Exception as e:
                        safe_print(f"[HYBRID] Web assessment failed: {e}")
                        web_assessment = validate_assessment_result({})
                    
                    if web_results and web_assessment['confident']:
                        safe_print(f"[HYBRID] Web search found {len(web_results)} confident results")
                        response_data['method'] = 'hybrid_rag_web' if rag_context else 'web_search'
                        response_data['prefix'] = '🌐 ' if not rag_context else f"{response_data['prefix']}🌐 "
                        response_data['sources'].append('Web Search')
                    elif web_results:
                        safe_print(f"[HYBRID] Web search found {len(web_results)} results but low confidence")
                        response_data['method'] = 'hybrid_rag_web_cautious' if rag_context else 'web_search_cautious'
                        response_data['prefix'] = '🔍 ' if not rag_context else f"{response_data['prefix']}🔍 "
                        response_data['sources'].append('Web Search (Low Confidence)')
                    else:
                        safe_print("[HYBRID] No useful web results found")
                        
                except Exception as e:
                    safe_print(f"[HYBRID] Web search failed: {e}")
                    if not response_data['error']:
                        response_data['error'] = f"Web search error: {str(e)}"
            else:
                safe_print(f"[HYBRID] Skipping web search - {rag_assessment['reason']}")
            
            # Step 2.5: Final decision based on both assessments
            should_ask_for_clarification = False
            if not rag_context and not web_results:
                should_ask_for_clarification = True
            elif rag_assessment['recommendation'] == 'web_search' and web_assessment and web_assessment['recommendation'] == 'ask_for_clarification':
                should_ask_for_clarification = True
            elif rag_assessment['confidence'] < 0.3 and web_assessment and web_assessment['confidence'] < 0.3:
                should_ask_for_clarification = True
            
            # Step 3: Create hybrid prompt based on assessments
            try:
                if should_ask_for_clarification:
                    safe_print("[HYBRID] Step 3: Creating smart clarification prompt - insufficient data from both RAG and web")
                    
                    # Analyze the query to provide smart, contextual redirects
                    query_type = _classify_query_type(user_message)
                    sport_domain = _detect_sport_domain(user_message)
                    
                    safe_print(f"[HYBRID] Query classified as: {query_type} in {sport_domain} domain")
                    
                    # Create smart clarification prompt based on query analysis
                    prompt = _create_smart_clarification_prompt(user_message, query_type, sport_domain)
                    
                    response_data['method'] = 'smart_clarification_request'
                    response_data['prefix'] = '❓ '
                    response_data['sources'] = [f'Smart Redirect ({query_type})']
                elif rag_context or web_results:
                    safe_print(f"[HYBRID] Step 3: Creating hybrid prompt with {len(rag_context)} RAG + {len(web_results)} web results")
                    
                    # Enhanced prompt creation with assessment context
                    if rag_assessment['recommendation'] == 'use_rag_with_web_fallback' and web_results:
                        prompt = create_enhanced_hybrid_prompt(user_message, rag_context, web_results, character_data, conversation_context, rag_assessment, web_assessment)
                    else:
                        prompt = create_hybrid_prompt(user_message, rag_context, web_results, character_data, conversation_context)
                else:
                    safe_print("[HYBRID] Step 3: Creating basic prompt (no RAG or web results)")
                    prompt = create_hybrid_prompt(user_message, [], [], character_data, conversation_context)
                    response_data['method'] = 'basic_llm'
                    response_data['prefix'] = '🤖 '
                    response_data['sources'] = ['General Knowledge']
            
            except Exception as e:
                safe_print(f"[HYBRID] Prompt creation failed: {e}")
                response_data['error'] = f"Prompt error: {str(e)}"
                break
            
            # Step 4: Get LLM response with timeout and circuit breaker
            try:
                safe_print("[HYBRID] Step 4: Getting LLM response")
                
                # Check circuit breaker for LLM
                if not circuit_breaker_check('llm'):
                    safe_print("[HYBRID] LLM circuit breaker open - using fallback response")
                    response_data['content'] = "I'm currently experiencing technical difficulties. Please try again in a few minutes."
                    response_data['error'] = "LLM circuit breaker open"
                    response_data['method'] = 'circuit_breaker_fallback'
                    response_data['prefix'] = '⚠️ '
                    break
                
                # Use asyncio.wait_for to add timeout
                async def get_openai_response():
                    return openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1000,
                        temperature=0.7
                    )
                
                response = await asyncio.wait_for(get_openai_response(), timeout=LLM_TIMEOUT)
                ai_response = response.choices[0].message.content
                
                if ai_response:
                    response_data['content'] = ai_response
                    safe_print(f"[HYBRID] LLM response received ({len(ai_response)} chars)")
                    record_success('llm')
                else:
                    raise Exception("Empty response from LLM")
                    
            except asyncio.TimeoutError:
                safe_print("[HYBRID] LLM request timed out")
                record_failure('llm')
                if retry_count < MAX_RETRIES:
                    retry_count += 1
                    safe_print(f"[HYBRID] Retrying LLM ({retry_count}/{MAX_RETRIES})")
                    await asyncio.sleep(2)
                    continue
                else:
                    response_data['content'] = "I apologize, but I'm taking too long to respond. Please try asking your question again."
                    response_data['error'] = "LLM timeout"
                    response_data['timeout'] = True
                    break
                
            except Exception as e:
                safe_print(f"[HYBRID] LLM request failed: {e}")
                record_failure('llm')
                if retry_count < MAX_RETRIES:
                    retry_count += 1
                    safe_print(f"[HYBRID] Retrying LLM ({retry_count}/{MAX_RETRIES})")
                    await asyncio.sleep(1)
                    continue
                else:
                    response_data['content'] = f"I apologize, but I encountered an issue processing your request. Please try again. Error: {str(e)[:100]}"
                    response_data['error'] = f"LLM error: {str(e)}"
                    break
            
            # Step 5: Format and validate response
            try:
                if response_data['content']:
                    response_data['content'] = format_response_with_paragraphs(response_data['content'], min_length=50)
                    
                    # ONLY add source information if web search was actually used
                    if web_results and any('http' in result.get('url', '') for result in web_results):
                        url_citations = []
                        for result in web_results:
                            if result.get('url') and 'http' in result['url'] and not result['url'].endswith('duckduckgo.com/'):
                                url_citations.append(f"• {result['title']}: {result['url']}")
                        
                        if url_citations:
                            response_data['content'] += f"\n\n**Sources:**\n" + "\n".join(url_citations)
                    
                    safe_print(f"[HYBRID] Final response ready ({response_data['method']})")
                    break  # Success - exit retry loop
                else:
                    raise Exception("No content generated")
                    
            except Exception as e:
                safe_print(f"[HYBRID] Response formatting failed: {e}")
                if retry_count < MAX_RETRIES:
                    retry_count += 1
                    safe_print(f"[HYBRID] Retrying formatting ({retry_count}/{MAX_RETRIES})")
                    await asyncio.sleep(1)
                    continue
                else:
                    response_data['content'] = "I apologize, but I had trouble formatting my response. Please try asking your question again."
                    response_data['error'] = f"Formatting error: {str(e)}"
                    break
        
        except asyncio.TimeoutError:
            safe_print("[HYBRID] Overall timeout reached")
            response_data['content'] = "I apologize, but I'm taking too long to process your request. Please try again."
            response_data['error'] = "Overall timeout"
            response_data['timeout'] = True
            break
        
        except Exception as e:
            safe_print(f"[HYBRID] Critical error in hybrid response: {e}")
            if retry_count < MAX_RETRIES:
                retry_count += 1
                safe_print(f"[HYBRID] Retrying entire process ({retry_count}/{MAX_RETRIES})")
                await asyncio.sleep(2)
                continue
            else:
                response_data['content'] = "I apologize, but I encountered a critical error. Please try asking your question again."
                response_data['error'] = f"Critical error: {str(e)}"
                response_data['method'] = 'error_fallback'
                response_data['prefix'] = '⚠️ '
                break
    
    # Final failsafe - ensure we always have content
    if not response_data.get('content'):
        response_data['content'] = "I apologize, but I'm having trouble generating a response right now. Please try again."
        response_data['error'] = "No content generated"
        response_data['method'] = 'ultimate_fallback'
        response_data['prefix'] = '⚠️ '
    
    return response_data

# Create the Telegram client (only if credentials are set)
if check_credentials():
    # Initialize OpenAI client
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Load character card
    safe_print("[*] Loading character card...")
    character_data = load_character_card()
    
    # Initialize RAG system
    vectorstore = None
    multi_domain_rag = None
    
    if USE_RAG:
        safe_print("[*] Initializing RAG system...")
        vectorstore = init_rag_system()
        if vectorstore:
            safe_print("[+] RAG system initialized successfully!")
        else:
            safe_print("[!] RAG system not available - running in basic mode")
        
        # Initialize multi-domain RAG if available
        if USE_MULTI_DOMAIN and MULTI_DOMAIN_AVAILABLE:
            safe_print("[*] Initializing Multi-Domain RAG system...")
            try:
                multi_domain_rag = MultiDomainRAG(CHROMA_DB_PATH, OPENAI_API_KEY)
                safe_print("[+] Multi-Domain RAG system initialized successfully!")
                
                # Get domain stats
                domain_stats = multi_domain_rag.get_domain_stats()
                safe_print(f"[+] Domain distribution: {domain_stats.get('domain_distribution', {})}")
            except Exception as e:
                safe_print(f"[!] Multi-Domain RAG initialization failed: {e}")
                multi_domain_rag = None
            else:
                safe_print("[*] Multi-Domain RAG disabled - using standard RAG")
    else:
        safe_print("[*] RAG disabled - running in basic mode")
    
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
                
                status_message = f'''📊 **RAG System Status**

✅ **Status:** Active and Ready
📚 **Documents in Knowledge Base:** {count} chunks
🔍 **Search:** Available
💾 **Database:** {CHROMA_DB_PATH}'''
                
                # Add multi-domain information if available
                if multi_domain_rag and USE_MULTI_DOMAIN:
                    domain_stats = multi_domain_rag.get_domain_stats()
                    status_message += f'''

🌐 **Multi-Domain System:** Active
🏀 **NBA Data:** {domain_stats.get('domain_distribution', {}).get('nba', 0)} chunks
🏎️ **F1 Data:** {domain_stats.get('domain_distribution', {}).get('f1', 0)} chunks
📊 **General Data:** {domain_stats.get('domain_distribution', {}).get('general', 0)} chunks
⚡ **Domain God Commands:** {sum(domain_stats.get('god_commands_by_domain', {}).values())}'''
                
                status_message += "\n\nYour bot can now provide context-aware responses using the uploaded documents!"
                
                await event.respond(status_message)
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
• 🏀 = NBA Basketball domain detected
• 🏎️ = Formula 1 Racing domain detected
• 🔄 = Multi-domain query (covers multiple sports)
• 📚 = Using knowledge base
• 🎯 = General AI response (groups)
• 🤖 = General AI response (private)''')

    @client.on(events.NewMessage)
    async def message_handler(event):
        """Handle all incoming messages with hybrid RAG + Web Search + LLM system with comprehensive failsafes"""
        # Skip commands (already handled above)
        if event.raw_text.startswith('/'):
            return
        
        # Input validation and safety checks
        try:
            # Get bot info with timeout
            me = await asyncio.wait_for(client.get_me(), timeout=10.0)
            bot_username = me.username if me.username else None
            bot_first_name = me.first_name if me.first_name else "Agent Daredevil"
        except Exception as e:
            safe_print(f"[ERR] Failed to get bot info: {e}")
            return
        
        # Skip messages from yourself to avoid loops
        if event.sender_id == me.id:
            return
        
        # Rate limiting check - prevent too many requests from same user
        current_time = time.time()
        user_id = str(event.sender_id)
        if not hasattr(message_handler, 'user_timestamps'):
            message_handler.user_timestamps = {}
        
        if user_id in message_handler.user_timestamps:
            time_diff = current_time - message_handler.user_timestamps[user_id]
            if time_diff < 2:  # 2 second cooldown per user
                safe_print(f"[RATE] Rate limit hit for user {user_id}")
                return
        
        message_handler.user_timestamps[user_id] = current_time
        
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
                try:
                    reply_msg = await asyncio.wait_for(event.get_reply_message(), timeout=5.0)
                    if reply_msg and reply_msg.sender_id == me.id:
                        should_respond = True
                except Exception as e:
                    safe_print(f"[ERR] Failed to get reply message: {e}")
            
            # Don't respond if not mentioned
            if not should_respond:
                return
        
        # Skip channel messages
        elif event.is_channel:
            return
        
        # Skip if no valid message text
        if not message_text or not message_text.strip():
            return
        
        # Prevent excessively long messages
        if len(message_text) > 2000:
            message_text = message_text[:2000]
            safe_print("[MSG] Message truncated to 2000 characters")
        
        safe_print(f"[MSG] Received message: {message_text}")
        if event.is_group:
            safe_print(f"[GRP] Group: {event.chat.title if hasattr(event.chat, 'title') else 'Unknown'}")
        
        # Main processing with comprehensive error handling
        processing_start_time = time.time()
        max_processing_time = 60  # Maximum 60 seconds for entire processing
        
        try:
            # Send typing indicator with error handling
            typing_action = None
            try:
                typing_action = client.action(event.chat_id, 'typing')
                await typing_action.__aenter__()
            except Exception as e:
                safe_print(f"[ERR] Failed to start typing indicator: {e}")
            
            try:
                # Get memory context if available
                conversation_context = ""
                if MEMORY_AVAILABLE and USE_MEMORY:
                    try:
                        memory_manager = get_memory_manager(MEMORY_DB_PATH, MAX_SESSION_MESSAGES, SESSION_TIMEOUT_HOURS)
                        conversation_context = memory_manager.get_context_for_llm(event.sender_id)
                        if conversation_context:
                            safe_print(f"[MEM] Retrieved conversation context for user {event.sender_id}")
                        else:
                            safe_print(f"[MEM] No previous conversation found for user {event.sender_id}")
                    except Exception as e:
                        safe_print(f"[ERR] Memory system error: {e}")
                
                # Store user message in memory
                if MEMORY_AVAILABLE and USE_MEMORY:
                    try:
                        memory_manager.add_message(event.sender_id, "user", message_text)
                        safe_print(f"[MEM] Stored user message in memory")
                    except Exception as e:
                        safe_print(f"[ERR] Failed to store user message: {e}")
                
                # Check if we're taking too long
                if time.time() - processing_start_time > max_processing_time:
                    raise TimeoutError("Processing time exceeded maximum limit")
                
                # Get hybrid response with overall timeout
                response_data = await asyncio.wait_for(
                    get_hybrid_response(
                        message_text, 
                        event, 
                        openai_client, 
                        vectorstore if USE_RAG else None, 
                        multi_domain_rag if USE_MULTI_DOMAIN else None, 
                        character_data, 
                        conversation_context
                    ),
                    timeout=MAX_RESPONSE_TIME
                )
                
                # Validate response data
                if not response_data or not isinstance(response_data, dict):
                    raise ValueError("Invalid response data received")
                
                if not response_data.get('content'):
                    response_data['content'] = "I apologize, but I'm having trouble generating a response right now. Please try again."
                    response_data['prefix'] = '⚠️ '
                    response_data['method'] = 'validation_fallback'
                
                # Store assistant response in memory
                if MEMORY_AVAILABLE and USE_MEMORY and response_data['content']:
                    try:
                        memory_manager.add_message(event.sender_id, "assistant", response_data['content'])
                        safe_print(f"[MEM] Stored assistant response in memory")
                    except Exception as e:
                        safe_print(f"[ERR] Failed to store assistant response: {e}")
                
                # Send the response back to Telegram with appropriate prefix
                try:
                    full_response = f"{response_data['prefix']}{response_data['content']}"
                    
                    # Validate response length
                    if len(full_response) > 4000:  # Telegram message limit
                        safe_print("[SEND] Response too long, truncating")
                        full_response = full_response[:3950] + "...\n\n[Response truncated due to length]"
                    
                    await event.respond(full_response)
                    safe_print(f"[SENT] Response sent using {response_data.get('method', 'unknown')}")
                    
                except UnicodeEncodeError:
                    # Fallback response without emojis if encoding fails
                    safe_response = f"[AGENT] {response_data['content']}"
                    if len(safe_response) > 4000:
                        safe_response = safe_response[:3950] + "...\n\n[Response truncated]"
                    await event.respond(safe_response)
                    safe_print(f"[SENT] Fallback response sent (encoding issue)")
                
                except Exception as send_error:
                    safe_print(f"[ERR] Failed to send response: {send_error}")
                    # Try to send a basic error message
                    try:
                        await event.respond("I apologize, but I had trouble sending my response. Please try again.")
                    except:
                        safe_print("[ERR] Failed to send error notification")
                
            finally:
                # Clean up typing indicator
                if typing_action:
                    try:
                        await typing_action.__aexit__(None, None, None)
                    except:
                        pass
                
        except asyncio.TimeoutError:
            safe_print("[ERR] Message processing timed out")
            try:
                await event.respond("I apologize, but I'm taking too long to process your request. Please try again.")
            except:
                safe_print("[ERR] Failed to send timeout message")
                
        except Exception as e:
            processing_time = time.time() - processing_start_time
            error_msg = f"Sorry, I encountered an error: {str(e)[:100]}"
            safe_print(f"[ERR] Critical error in message handler (took {processing_time:.2f}s): {error_msg}")
            
            # Try multiple fallback approaches
            try:
                await event.respond(error_msg)
            except:
                try:
                    await event.respond("I apologize, but I encountered a technical issue. Please try again.")
                except:
                    try:
                        await event.respond("Error occurred. Please retry.")
                    except:
                        safe_print("[ERR] All fallback response attempts failed")
        
        finally:
            # Clean up any remaining resources
            processing_time = time.time() - processing_start_time
            if processing_time > 30:  # Log slow responses
                safe_print(f"[PERF] Slow response: {processing_time:.2f}s for message: {message_text[:50]}...")
            
            # Circuit breaker reset logic - reset failures occasionally
            if hasattr(message_handler, 'reset_counter'):
                message_handler.reset_counter += 1
            else:
                message_handler.reset_counter = 1
            
            if message_handler.reset_counter % 10 == 0:  # Every 10 messages
                for service in ['web_search', 'rag_search', 'llm']:
                    if circuit_breaker_state.get(f'{service}_failures', 0) > 0:
                        circuit_breaker_state[f'{service}_failures'] = max(0, circuit_breaker_state[f'{service}_failures'] - 1)
                        safe_print(f"[CIRCUIT] Decreased {service} failure count")

    async def main():
        """Main function to start the client"""
        safe_print("[*] Starting Agent Daredevil - Telegram RAG Bot...")
        
        try:
            # Start the client
            await client.start(phone=PHONE_NUMBER)
            
            # Get bot info
            me = await client.get_me()
            bot_name = me.first_name if me.first_name else "Agent Daredevil"
            bot_username = f"@{me.username}" if me.username else "no username"
            
            safe_print("[+] Client started! You are now connected.")
            safe_print(f"[*] Bot Name: {bot_name}")
            safe_print(f"[*] Username: {bot_username}")
            safe_print("[*] Ready for private messages and group mentions!")
            safe_print("[*] Press Ctrl+C to stop the bot.")
            
            if character_data:
                safe_print(f"[*] Character: {character_data.get('name', 'Unknown')} persona loaded")
            else:
                safe_print("[!] No character card loaded - using basic persona")
            
            if vectorstore:
                safe_print("[+] RAG system is active - bot will use knowledge base for responses")
            else:
                safe_print("[!] RAG system not available - bot will use general knowledge only")
            
            if MEMORY_AVAILABLE and USE_MEMORY:
                safe_print("[+] Memory system is active - bot will remember conversations")
            else:
                safe_print("[!] Memory system not available - conversations won't be remembered")
            
            safe_print("\n[*] Usage:")
            safe_print("  - Private chats: Send any message")
            safe_print(f"  - Group chats: Mention '{bot_name}' or {bot_username}")
            safe_print("  - Group chats: Reply to bot messages")
            
            # Keep the client running
            await client.run_until_disconnected()
            
        except Exception as e:
            safe_print(f"[ERR] Error starting client: {e}")
            safe_print("Make sure your credentials are correct and try again.")

    if __name__ == '__main__':
        try:
            # Run the main function
            asyncio.run(main())
        except KeyboardInterrupt:
            safe_print("\n[*] Bot stopped by user.")
        except Exception as e:
            safe_print(f"[ERR] Unexpected error: {e}")
else:
    safe_print("\n[!] Please update your credentials and run the script again.")