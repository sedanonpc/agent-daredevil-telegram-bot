"""
Test script for Multi-Domain RAG System
Demonstrates domain detection, routing, and domain-specific God Commands
"""

import os
from dotenv import load_dotenv
from multi_domain_rag import MultiDomainRAG
from rag_manager import add_god_command

# Load environment variables
load_dotenv()

CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

def safe_print(message=""):
    """Safely print Unicode messages, handling encoding errors"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace emojis with text equivalents for console output
        safe_message = str(message)
        safe_message = safe_message.replace('🏀', '[NBA]')
        safe_message = safe_message.replace('🏎️', '[F1]')
        safe_message = safe_message.replace('⚡', '[GOD]')
        safe_message = safe_message.replace('🔄', '[MULTI]')
        safe_message = safe_message.replace('🏆', '[RAG]')
        safe_message = safe_message.replace('🎯', '[GEN]')
        safe_message = safe_message.replace('🤖', '[AI]')
        safe_message = safe_message.replace('🧪', '[TEST]')
        safe_message = safe_message.replace('🔍', '[SEARCH]')
        safe_message = safe_message.replace('📊', '[STATS]')
        safe_message = safe_message.replace('📝', '[PROMPT]')
        safe_message = safe_message.replace('❌', '[FAIL]')
        safe_message = safe_message.replace('✅', '[PASS]')
        safe_message = safe_message.replace('🚀', '[LAUNCH]')
        try:
            print(safe_message)
        except UnicodeEncodeError:
            # Last resort: encode to ASCII and ignore errors
            print(safe_message.encode('ascii', 'ignore').decode('ascii'))

def test_domain_detection():
    """Test the domain detection functionality"""
    safe_print("🧪 Testing Domain Detection")
    safe_print("=" * 50)
    
    # Initialize multi-domain RAG
    multi_rag = MultiDomainRAG(CHROMA_DB_PATH, OPENAI_API_KEY)
    
    # Test queries for different domains
    test_queries = [
        "How did the Lakers perform in the last game?",
        "What's the current NBA playoff standings?",
        "Who won the Formula 1 race in Monaco?",
        "When is the next F1 qualifying session?",
        "Compare LeBron James and Lewis Hamilton's career achievements",
        "What's the weather like today?",
        "Tell me about basketball strategy in F1 racing circuits"
    ]
    
    for query in test_queries:
        safe_print(f"\n🔍 Query: {query}")
        detection = multi_rag.detect_domain(query)
        
        if detection['primary_domain']:
            domain_config = multi_rag.domains[detection['primary_domain']]
            safe_print(f"   Primary Domain: {domain_config.name} {domain_config.emoji}")
            safe_print(f"   Keywords matched: {detection['scores'][detection['primary_domain']]['matched_keywords']}")
            
            if detection['is_multi_domain']:
                safe_print(f"   🔄 Multi-domain query detected!")
                safe_print(f"   Secondary domains: {[multi_rag.domains[d].name for d in detection['secondary_domains']]}")
        else:
            safe_print(f"   ❌ No specific domain detected")
    
    safe_print("\n" + "=" * 50)

def test_search_functionality():
    """Test domain-specific search functionality"""
    safe_print("🔍 Testing Domain-Specific Search")
    safe_print("=" * 50)
    
    # Initialize multi-domain RAG
    multi_rag = MultiDomainRAG(CHROMA_DB_PATH, OPENAI_API_KEY)
    
    # Get domain stats
    stats = multi_rag.get_domain_stats()
    safe_print(f"📊 Knowledge Base Stats:")
    safe_print(f"   Total chunks: {stats.get('total_chunks', 0)}")
    safe_print(f"   NBA data: {stats.get('domain_distribution', {}).get('nba', 0)}")
    safe_print(f"   F1 data: {stats.get('domain_distribution', {}).get('f1', 0)}")
    safe_print(f"   General data: {stats.get('domain_distribution', {}).get('general', 0)}")
    
    # Test search for each domain
    test_searches = [
        ("nba", "Lakers team performance"),
        ("f1", "Ferrari racing strategy"),
        ("nba", "basketball playoffs"),
        ("f1", "Formula 1 championship")
    ]
    
    for domain, query in test_searches:
        safe_print(f"\n🔍 Searching {domain.upper()} domain for: {query}")
        results = multi_rag.search_domain_specific(query, domain, k=3)
        
        if results:
            safe_print(f"   Found {len(results)} results:")
            for i, (doc, score) in enumerate(results, 1):
                safe_print(f"   {i}. {doc.metadata.get('source', 'Unknown')} (score: {score:.3f})")
        else:
            safe_print(f"   No results found")
    
    safe_print("\n" + "=" * 50)

def add_sample_god_commands():
    """Add sample domain-specific God Commands"""
    safe_print("⚡ Adding Sample Domain-Specific God Commands")
    safe_print("=" * 50)
    
    # NBA analyst God Commands
    nba_commands = [
        {
            "command": "When discussing NBA topics, always respond as an expert basketball analyst with deep knowledge of player statistics, team strategies, and league history. Use basketball terminology and provide context about current season performance.",
            "description": "NBA domain analyst mode - expert basketball analysis",
            "priority": 15
        },
        {
            "command": "For NBA queries, prioritize current season data and recent game performance. Always mention relevant statistics like points, rebounds, assists, and shooting percentages when discussing players.",
            "description": "NBA data prioritization and statistics focus",
            "priority": 12
        },
        {
            "command": "When discussing NBA teams, always consider their current playoff position, recent trades, and injury reports. Provide strategic analysis of their playing style and key matchups.",
            "description": "NBA team analysis with strategic context",
            "priority": 10
        }
    ]
    
    # F1 racing God Commands
    f1_commands = [
        {
            "command": "When discussing Formula 1 topics, respond as a knowledgeable F1 racing expert with expertise in technical regulations, driver performance, and constructor strategies. Use racing terminology and provide context about championship standings.",
            "description": "F1 domain analyst mode - expert racing analysis",
            "priority": 15
        },
        {
            "command": "For F1 queries, prioritize current season data, qualifying results, and race performance. Always mention relevant metrics like lap times, pit stop strategies, and championship points when discussing drivers or teams.",
            "description": "F1 data prioritization and racing metrics focus",
            "priority": 12
        },
        {
            "command": "When discussing F1 constructors, always consider their current championship position, recent car developments, and strategic decisions. Provide technical analysis of their car performance and upgrade packages.",
            "description": "F1 constructor analysis with technical context",
            "priority": 10
        }
    ]
    
    # Add NBA God Commands
    safe_print("🏀 Adding NBA God Commands:")
    for i, cmd in enumerate(nba_commands, 1):
        success, source_id = add_god_command(
            f"NBA_ANALYST_{i:02d}: {cmd['command']}", 
            cmd['description'], 
            cmd['priority']
        )
        if success:
            safe_print(f"   ✅ Added: {source_id}")
        else:
            safe_print(f"   ❌ Failed to add NBA command {i}")
    
    # Add F1 God Commands
    safe_print("\n🏎️ Adding F1 God Commands:")
    for i, cmd in enumerate(f1_commands, 1):
        success, source_id = add_god_command(
            f"F1_ANALYST_{i:02d}: {cmd['command']}", 
            cmd['description'], 
            cmd['priority']
        )
        if success:
            safe_print(f"   ✅ Added: {source_id}")
        else:
            safe_print(f"   ❌ Failed to add F1 command {i}")
    
    safe_print("\n" + "=" * 50)

def test_prompt_generation():
    """Test compartmentalized prompt generation"""
    safe_print("📝 Testing Compartmentalized Prompt Generation")
    safe_print("=" * 50)
    
    # Initialize multi-domain RAG
    multi_rag = MultiDomainRAG(CHROMA_DB_PATH, OPENAI_API_KEY)
    
    # Test queries
    test_queries = [
        "How did the Lakers perform last night?",
        "What's Ferrari's strategy for the next F1 race?",
        "Compare basketball and racing as sports entertainment"
    ]
    
    for query in test_queries:
        safe_print(f"\n🔍 Query: {query}")
        
        # Process the query
        processing_result = multi_rag.process_query(query, k=3)
        
        # Generate prompt
        if processing_result['search_results']:
            prompt = multi_rag.create_compartmentalized_prompt(
                query,
                processing_result['domain_detection'],
                processing_result['search_results']
            )
            
            safe_print(f"📝 Generated prompt preview:")
            safe_print(f"   Domain: {processing_result['domain_detection']['primary_domain']}")
            safe_print(f"   Multi-domain: {processing_result['domain_detection']['is_multi_domain']}")
            safe_print(f"   Results: {processing_result['total_results']}")
            safe_print(f"   Prompt length: {len(prompt)} characters")
        else:
            safe_print(f"   No search results found for this query")
    
    safe_print("\n" + "=" * 50)

def main():
    """Run all tests"""
    safe_print("🚀 Multi-Domain RAG System Testing")
    safe_print("=" * 60)
    
    try:
        # Test 1: Domain Detection
        test_domain_detection()
        safe_print()
        
        # Test 2: Add Sample God Commands
        add_sample_god_commands()
        safe_print()
        
        # Test 3: Search Functionality
        test_search_functionality()
        safe_print()
        
        # Test 4: Prompt Generation
        test_prompt_generation()
        
        safe_print("✅ All tests completed successfully!")
        
    except Exception as e:
        safe_print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 