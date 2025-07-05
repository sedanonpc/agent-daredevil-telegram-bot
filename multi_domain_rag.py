"""
Multi-Domain RAG System for Agent Daredevil
Handles NBA and Formula 1 data with domain-aware routing and compartmentalized responses
"""

import os
import re
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb

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
        try:
            print(safe_message)
        except UnicodeEncodeError:
            # Last resort: encode to ASCII and ignore errors
            print(safe_message.encode('ascii', 'ignore').decode('ascii'))

# Domain definitions
@dataclass
class DomainConfig:
    name: str
    keywords: List[str]
    source_types: List[str]
    god_command_prefixes: List[str]
    color_scheme: str
    emoji: str
    priority_boost: float = 1.0

class MultiDomainRAG:
    """Multi-domain RAG system with compartmentalized reasoning"""
    
    def __init__(self, chroma_db_path: str, openai_api_key: str):
        self.chroma_db_path = chroma_db_path
        self.openai_api_key = openai_api_key
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        
        # Conversation context tracking
        self.conversation_contexts = {}  # user_id -> current_domain
        self.MIN_SWITCH_CONFIDENCE = 0.8  # Higher threshold for switching domains
        
        # Define domain configurations
        self.domains = {
            'nba': DomainConfig(
                name="NBA Basketball",
                keywords=[
                    'nba', 'basketball', 'lakers', 'warriors', 'celtics', 'heat', 'bulls', 'knicks',
                    'playoff', 'finals', 'championship', 'draft', 'trade', 'player', 'coach', 'team',
                    'lebron', 'curry', 'jordan', 'kobe', 'shaq', 'magic', 'bird', 'duncan',
                    'luka', 'doncic', 'dončić', 'giannis', 'antetokounmpo', 'tatum', 'booker', 'embiid',
                    'jokic', 'morant', 'ja', 'anthony', 'davis', 'kawhi', 'leonard', 'harden', 'durant',
                    'westbrook', 'paul', 'george', 'butler', 'lillard', 'adebayo', 'siakam', 'towns',
                    'points', 'assists', 'rebounds', 'stats', 'mvp', 'rookie', 'veteran',
                    'season', 'game', 'match', 'conference', 'eastern', 'western', 'division',
                    'arena', 'court', 'basketball', 'hoops', 'ball', 'dunk', 'shot', 'three-pointer'
                ],
                source_types=['nba_data'],
                god_command_prefixes=['NBA_ANALYST', 'BASKETBALL'],
                color_scheme='#FFA500',  # Orange
                emoji='🏀',
                priority_boost=1.2
            ),
            'f1': DomainConfig(
                name="Formula 1 Racing",
                keywords=[
                    'f1', 'formula1', 'formula 1', 'racing', 'ferrari', 'mercedes', 'redbull', 'red bull',
                    'mclaren', 'aston martin', 'alpine', 'williams', 'haas', 'alphatauri', 'alfa romeo',
                    'verstappen', 'hamilton', 'leclerc', 'russell', 'norris', 'piastri', 'alonso',
                    'vettel', 'sainz', 'perez', 'gasly', 'ocon', 'stroll', 'bottas', 'zhou',
                    'monaco', 'silverstone', 'monza', 'spa', 'suzuka', 'interlagos', 'bahrain',
                    'qualifying', 'pole position', 'fastest lap', 'pit stop', 'drs', 'kers',
                    'championship', 'constructor', 'driver', 'grand prix', 'circuit', 'track',
                    'race', 'lap', 'sector', 'tire', 'tyre', 'strategy', 'podium', 'points'
                ],
                source_types=['f1_data'],
                god_command_prefixes=['F1_ANALYST', 'RACING'],
                color_scheme='#DC143C',  # Ferrari red
                emoji='🏎️',
                priority_boost=1.2
            )
        }
        
        # Initialize vectorstore
        self.vectorstore = None
        self._init_vectorstore()
    
    def _init_vectorstore(self):
        """Initialize the ChromaDB vectorstore"""
        try:
            self.vectorstore = Chroma(
                collection_name="telegram_bot_knowledge",
                embedding_function=self.embeddings,
                persist_directory=self.chroma_db_path
            )
        except Exception as e:
            print(f"[ERR] Failed to initialize vectorstore: {e}")
            self.vectorstore = None
    
    def detect_domain(self, query: str) -> Dict[str, Any]:
        """Detect which domain(s) a query belongs to"""
        query_lower = query.lower()
        domain_scores = {}
        
        for domain_key, domain_config in self.domains.items():
            score = 0
            matched_keywords = []
            
            # Count keyword matches
            for keyword in domain_config.keywords:
                if keyword.lower() in query_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # Apply priority boost
            score *= domain_config.priority_boost
            
            if score > 0:
                domain_scores[domain_key] = {
                    'score': score,
                    'config': domain_config,
                    'matched_keywords': matched_keywords
                }
        
        # Determine primary domain
        if not domain_scores:
            return {
                'primary_domain': None,
                'secondary_domains': [],
                'is_multi_domain': False,
                'scores': {}
            }
        
        # Sort by score
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        primary_domain = sorted_domains[0][0]
        
        # Check if this is a multi-domain query
        is_multi_domain = len(sorted_domains) > 1 and sorted_domains[1][1]['score'] >= sorted_domains[0][1]['score'] * 0.5
        
        secondary_domains = [d[0] for d in sorted_domains[1:] if d[1]['score'] >= sorted_domains[0][1]['score'] * 0.3]
        
        return {
            'primary_domain': primary_domain,
            'secondary_domains': secondary_domains,
            'is_multi_domain': is_multi_domain,
            'scores': domain_scores,
            'detection_details': {
                'total_keywords_matched': sum(len(d['matched_keywords']) for d in domain_scores.values()),
                'strongest_matches': sorted_domains[0][1]['matched_keywords'] if sorted_domains else []
            }
        }
    
    def _is_ambiguous_query(self, query: str) -> bool:
        """Check if query contains ambiguous terms that need context"""
        ambiguous_terms = ['stats', 'performance', 'results', 'standings', 'scores', 'rankings', 'season', 'games', 'matches', 'data', 'numbers', 'info', 'information']
        contextual_terms = ['updates', 'update', 'this', 'that', 'it', 'them', 'they', 'latest', 'recent', 'new', 'what happened', 'how about', 'tell me more']
        query_lower = query.lower().strip()
        
        # Check if query is ONLY ambiguous terms (like just "stats" or "tell me stats")
        query_words = [word for word in query_lower.split() if word not in ['tell', 'me', 'show', 'give', 'about', 'the', 'some', 'any']]
        
        if not query_words:
            return True
        
        # Check for highly contextual queries like "updates", "any updates", "updates on this?"
        for term in contextual_terms:
            if term in query_lower:
                safe_print(f"[CONTEXT] Contextual term detected: '{term}'")
                return True
        
        ambiguous_words = [word for word in query_words if any(term in word for term in ambiguous_terms)]
        
        # If more than 70% of meaningful query words are ambiguous, it's risky
        return len(ambiguous_words) / len(query_words) > 0.7
    
    def _has_explicit_domain_indicators(self, query: str) -> Dict[str, Any]:
        """Check for explicit domain indicators that should override context"""
        query_lower = query.lower().strip()
        
        # Define explicit indicators for each domain
        explicit_indicators = {
            'nba': [
                # Current superstars
                'luka', 'doncic', 'dončić', 'giannis', 'antetokounmpo', 'lebron', 'james',
                'stephen', 'curry', 'steph', 'tatum', 'booker', 'embiid', 'jokic', 'morant',
                'ja morant', 'anthony davis', 'kawhi', 'leonard', 'harden', 'durant', 'kd',
                'westbrook', 'paul george', 'butler', 'lillard', 'damian', 'adebayo',
                # Teams
                'lakers', 'warriors', 'celtics', 'mavericks', 'mavs', 'bucks', 'suns', 'sixers',
                'nuggets', 'grizzlies', 'clippers', 'heat', 'trail blazers', 'blazers',
                # NBA-specific terms
                'nba', 'basketball', 'playoff', 'finals'
            ],
            'f1': [
                # Current drivers
                'verstappen', 'max verstappen', 'hamilton', 'lewis', 'leclerc', 'charles',
                'russell', 'george', 'norris', 'lando', 'piastri', 'oscar', 'alonso', 'fernando',
                'sainz', 'carlos', 'perez', 'sergio', 'gasly', 'pierre', 'ocon', 'esteban',
                # Teams/Constructors
                'ferrari', 'mercedes', 'red bull', 'redbull', 'mclaren', 'aston martin',
                'alpine', 'williams', 'haas', 'alphatauri', 'alfa romeo',
                # F1-specific terms
                'formula 1', 'formula1', 'f1', 'grand prix', 'qualifying', 'pole position'
            ]
        }
        
        # Check for explicit indicators
        for domain, indicators in explicit_indicators.items():
            for indicator in indicators:
                if indicator in query_lower:
                    return {
                        'has_explicit': True,
                        'domain': domain,
                        'indicator': indicator,
                        'confidence': 0.95  # Very high confidence for explicit mentions
                    }
        
        return {'has_explicit': False}
    
    def detect_domain_with_context(self, query: str, user_id: str = "default") -> Dict[str, Any]:
        """Enhanced domain detection with conversation context awareness"""
        
        # Get base detection
        base_detection = self.detect_domain(query)
        
        # Get current conversation context
        current_domain = self.conversation_contexts.get(user_id)
        
        # Check for explicit domain indicators first (highest priority)
        explicit_check = self._has_explicit_domain_indicators(query)
        if explicit_check['has_explicit']:
            explicit_domain = explicit_check['domain']
            safe_print(f"[EXPLICIT] Explicit {explicit_domain.upper()} indicator detected: '{explicit_check['indicator']}'")
            
            # Force switch to explicit domain regardless of context
            self.conversation_contexts[user_id] = explicit_domain
            
            # Ensure proper scores structure
            if explicit_domain not in base_detection.get('scores', {}):
                domain_config = self.domains.get(explicit_domain)
                if domain_config:
                    base_detection.setdefault('scores', {})[explicit_domain] = {
                        'score': explicit_check['confidence'],
                        'config': domain_config,
                        'matched_keywords': [explicit_check['indicator']]
                    }
            
            return {
                **base_detection,
                'primary_domain': explicit_domain,
                'confidence': explicit_check['confidence'],
                'reason': f'Explicit {explicit_domain.upper()} indicator: {explicit_check["indicator"]}',
                'is_context_override': current_domain != explicit_domain,
                'original_detection': base_detection['primary_domain']
            }
        
        # Check if query is ambiguous (only matters if no explicit indicators)
        if self._is_ambiguous_query(query):
            safe_print(f"[CONTEXT] Ambiguous query detected: '{query}'")
            
            # Use conversation context for ambiguous queries
            if current_domain:
                safe_print(f"[CONTEXT] Staying in {current_domain} context for ambiguous query")
                
                # Ensure proper scores structure for the current domain
                if current_domain not in base_detection.get('scores', {}):
                    # Create a minimal score entry for the current domain
                    domain_config = self.domains.get(current_domain)
                    if domain_config:
                        base_detection.setdefault('scores', {})[current_domain] = {
                            'score': 0.5,  # Context-based score
                            'config': domain_config,
                            'matched_keywords': ['context-based']
                        }
                
                return {
                    **base_detection,
                    'primary_domain': current_domain,
                    'confidence': 0.7,
                    'reason': f'Ambiguous query - staying in {current_domain} context',
                    'is_context_override': True,
                    'original_detection': base_detection['primary_domain']
                }
            else:
                safe_print(f"[CONTEXT] No current domain for ambiguous query")
                return {
                    **base_detection,
                    'primary_domain': None,
                    'confidence': 0.3,
                    'reason': 'Ambiguous query with no conversation context',
                    'is_context_override': False,
                    'suggestion': 'Please specify NBA or F1 for more accurate results'
                }
        
        # Check for domain switching resistance
        if current_domain and current_domain != base_detection['primary_domain']:
            # Calculate confidence based on keyword matches
            total_keywords = base_detection.get('detection_details', {}).get('total_keywords_matched', 0)
            confidence = min(0.9, 0.5 + (total_keywords * 0.1))
            
            if confidence < self.MIN_SWITCH_CONFIDENCE:
                safe_print(f"[CONTEXT] Resisting domain switch from {current_domain} to {base_detection['primary_domain']} (confidence: {confidence:.2f})")
                
                # Ensure proper scores structure for the current domain
                if current_domain not in base_detection.get('scores', {}):
                    # Create a minimal score entry for the current domain
                    domain_config = self.domains.get(current_domain)
                    if domain_config:
                        base_detection.setdefault('scores', {})[current_domain] = {
                            'score': confidence,
                            'config': domain_config,
                            'matched_keywords': ['context-override']
                        }
                
                return {
                    **base_detection,
                    'primary_domain': current_domain,
                    'confidence': confidence,
                    'reason': f'Low confidence switch - staying in {current_domain}',
                    'is_context_override': True,
                    'original_detection': base_detection['primary_domain']
                }
        
        # High confidence detection - update context
        if base_detection['primary_domain']:
            self.conversation_contexts[user_id] = base_detection['primary_domain']
            safe_print(f"[CONTEXT] Setting domain context to {base_detection['primary_domain']} for user {user_id}")
        
        return {
            **base_detection,
            'confidence': 0.9,
            'reason': 'Clear domain detection',
            'is_context_override': False
        }
    
    def search_domain_specific(self, query: str, domain: str, k: int = 5) -> List[Tuple[Any, float]]:
        """Search knowledge base filtered by domain"""
        if not self.vectorstore:
            return []
        
        try:
            domain_config = self.domains.get(domain)
            if not domain_config:
                return []
            
            # Get all results first
            all_results = self.vectorstore.similarity_search_with_score(query, k=k*3)
            
            # Filter by domain source types
            domain_results = []
            god_command_results = []
            
            for doc, score in all_results:
                metadata = doc.metadata
                source_type = metadata.get('source_type', 'file')
                is_god_command = metadata.get('is_god_command', False)
                
                # Check if this is a domain-specific god command
                if is_god_command:
                    source = metadata.get('source', '').upper()
                    if any(prefix in source for prefix in domain_config.god_command_prefixes):
                        god_command_results.append((doc, score))
                        continue
                
                # Check if this matches domain source types
                if source_type in domain_config.source_types:
                    domain_results.append((doc, score))
            
            # Combine with god commands first
            final_results = god_command_results + domain_results
            
            # Apply domain-specific scoring boost
            boosted_results = []
            for doc, score in final_results[:k]:
                boosted_score = score / domain_config.priority_boost
                boosted_results.append((doc, boosted_score))
            
            return boosted_results
            
        except Exception as e:
            print(f"[ERR] Error in domain-specific search: {e}")
            return []
    
    def search_cross_domain(self, query: str, domains: List[str], k: int = 5) -> Dict[str, List[Tuple[Any, float]]]:
        """Search across multiple domains"""
        results = {}
        
        for domain in domains:
            domain_results = self.search_domain_specific(query, domain, k=k//len(domains) + 1)
            if domain_results:
                results[domain] = domain_results
        
        return results
    
    def get_domain_god_commands(self, domain: str) -> List[Dict[str, Any]]:
        """Get god commands specific to a domain"""
        if not self.vectorstore:
            return []
        
        try:
            domain_config = self.domains.get(domain)
            if not domain_config:
                return []
            
            # Get all documents
            client = chromadb.PersistentClient(path=self.chroma_db_path)
            collection = client.get_collection("telegram_bot_knowledge")
            results = collection.get()
            
            domain_god_commands = []
            
            for i, metadata in enumerate(results['metadatas']):
                if metadata.get('is_god_command', False):
                    source = metadata.get('source', '').upper()
                    if any(prefix in source for prefix in domain_config.god_command_prefixes):
                        domain_god_commands.append({
                            'id': results['ids'][i],
                            'text': results['documents'][i],
                            'source': metadata.get('source', ''),
                            'description': metadata.get('description', ''),
                            'timestamp': metadata.get('timestamp', ''),
                            'priority': metadata.get('priority', 10),
                            'domain': domain
                        })
            
            # Sort by priority
            domain_god_commands.sort(key=lambda x: -x['priority'])
            
            return domain_god_commands
            
        except Exception as e:
            print(f"[ERR] Error getting domain god commands: {e}")
            return []
    
    def create_compartmentalized_prompt(self, user_message: str, domain_detection: Dict[str, Any], 
                                      search_results: Dict[str, List[Tuple[Any, float]]], 
                                      character_data: Optional[Dict] = None, 
                                      conversation_context: str = "") -> str:
        """Create a compartmentalized prompt based on domain detection"""
        
        # Get current time info
        now = datetime.now()
        current_time_info = f"""CURRENT DATE & TIME: {now.strftime('%A, %B %d, %Y at %I:%M %p')}"""
        
        # Build character context
        character_context = ""
        if character_data:
            character_context = self._create_character_prompt(character_data)
        
        prompt_parts = [current_time_info]
        
        if character_context:
            prompt_parts.append(character_context)
        
        if conversation_context:
            prompt_parts.append(conversation_context)
        
        # Add domain-specific context
        if domain_detection['primary_domain']:
            primary_domain = domain_detection['primary_domain']
            domain_config = self.domains[primary_domain]
            
            # Domain-specific god commands
            domain_god_commands = []
            regular_context = []
            
            if primary_domain in search_results:
                for doc, score in search_results[primary_domain]:
                    if doc.metadata.get('is_god_command', False):
                        domain_god_commands.append(doc.page_content)
                    else:
                        regular_context.append(f"Document: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}")
            
            # Add domain header with safe keyword access
            try:
                keywords = domain_detection['scores'][primary_domain]['matched_keywords']
                keywords_text = ', '.join(keywords) if keywords else 'context-based'
            except (KeyError, TypeError):
                keywords_text = 'context-based'
            
            prompt_parts.append(f"""{domain_config.emoji} DOMAIN DETECTED: {domain_config.name.upper()}
Matched Keywords: {keywords_text}
Domain Priority: {domain_config.priority_boost}x""")
            
            # Add domain-specific god commands
            if domain_god_commands:
                god_commands_text = "\n".join([f"- {cmd}" for cmd in domain_god_commands])
                prompt_parts.append(f"""🔥 {domain_config.name.upper()} DOMAIN BEHAVIOR OVERRIDES:
{god_commands_text}

These domain-specific commands take precedence when discussing {domain_config.name} topics.""")
            
            # Add regular context
            if regular_context:
                context_text = "\n\n".join(regular_context)
                prompt_parts.append(f"""{domain_config.emoji} {domain_config.name.upper()} KNOWLEDGE BASE:
{context_text}""")
        
        # Add multi-domain context if applicable
        if domain_detection['is_multi_domain'] and domain_detection['secondary_domains']:
            prompt_parts.append(f"""🔄 MULTI-DOMAIN QUERY DETECTED:
Primary: {self.domains[domain_detection['primary_domain']].name} {self.domains[domain_detection['primary_domain']].emoji}
Secondary: {', '.join([f"{self.domains[d].name} {self.domains[d].emoji}" for d in domain_detection['secondary_domains']])}

Provide insights from both domains when relevant, but prioritize the primary domain.""")
        
        # Add hallucination prevention guard rails
        if domain_detection['primary_domain']:
            domain_config = self.domains[domain_detection['primary_domain']]
            guard_rails = f"""🛡️ CRITICAL ACCURACY GUIDELINES:
- You are in {domain_config.name} mode - ONLY provide {domain_config.name} information
- Use ONLY the information provided in the knowledge base above
- If you don't have specific {domain_config.name} data, say "I don't have that specific {domain_config.name} information"
- NEVER make up player names, statistics, scores, or facts
- NEVER switch to other sports/domains unless explicitly asked
- When uncertain about data accuracy, say "I'm not certain about this information"
- If context is insufficient, admit knowledge limitations clearly
- Use phrases like "Based on available information..." when appropriate"""
            
            prompt_parts.append(guard_rails)
        else:
            general_guards = """🛡️ ACCURACY GUIDELINES:
- Only use information you're confident about
- If you don't have specific information, say so clearly
- Never fabricate statistics, names, or specific details
- When uncertain, express it clearly"""
            
            prompt_parts.append(general_guards)
        
        # Add instructions
        if domain_detection['primary_domain']:
            domain_config = self.domains[domain_detection['primary_domain']]
            instructions = f"""DOMAIN-SPECIFIC RESPONSE INSTRUCTIONS:
- RESPOND AS {domain_config.name.upper()} ANALYST: Use your expertise in {domain_config.name} 
- DOMAIN PRIORITY: Focus primarily on {domain_config.name} context and knowledge
- COMPARTMENTALIZED REASONING: Keep {domain_config.name} analysis separate from other sports
- CROSS-DOMAIN INSIGHTS: Only mention other domains if directly relevant
- EMOJI USAGE: Use {domain_config.emoji} when discussing {domain_config.name} topics
- FIRST PERSON: Respond as Agent Daredevil, but with {domain_config.name} specialization"""
        else:
            instructions = """GENERAL RESPONSE INSTRUCTIONS:
- No specific domain detected - respond with general knowledge
- Maintain Agent Daredevil persona
- Use relevant emojis for any sports mentioned"""
        
        prompt_parts.append(instructions)
        prompt_parts.append(f"User: {user_message}")
        
        if domain_detection['primary_domain']:
            domain_config = self.domains[domain_detection['primary_domain']]
            prompt_parts.append(f"Respond as Agent Daredevil with {domain_config.name} specialization {domain_config.emoji}:")
        else:
            prompt_parts.append("Respond as Agent Daredevil:")
        
        return "\n\n".join(prompt_parts)
    
    def _create_character_prompt(self, character_data: Dict) -> str:
        """Create character prompt from character data"""
        if not character_data:
            return ""
        
        prompt_parts = []
        
        if character_data.get('system'):
            prompt_parts.append(f"SYSTEM: {character_data['system']}")
        
        if character_data.get('bio'):
            bio_text = " | ".join(character_data['bio'])
            prompt_parts.append(f"BIO: {bio_text}")
        
        if character_data.get('adjectives'):
            adj_text = ", ".join(character_data['adjectives'])
            prompt_parts.append(f"PERSONALITY: {adj_text}")
        
        return "\n".join(prompt_parts)
    
    def process_query(self, query: str, user_id: str = "default", k: int = 5) -> Dict[str, Any]:
        """Process a query with full multi-domain pipeline"""
        
        # Step 1: Enhanced domain detection with context
        domain_detection = self.detect_domain_with_context(query, user_id)
        
        # Step 2: Search based on domain
        search_results = {}
        
        if domain_detection['primary_domain']:
            if domain_detection['is_multi_domain']:
                # Multi-domain search
                all_domains = [domain_detection['primary_domain']] + domain_detection['secondary_domains']
                search_results = self.search_cross_domain(query, all_domains, k=k)
            else:
                # Single domain search
                domain_results = self.search_domain_specific(query, domain_detection['primary_domain'], k=k)
                if domain_results:
                    search_results[domain_detection['primary_domain']] = domain_results
        
        # Step 3: Create processing summary
        processing_summary = {
            'query': query,
            'domain_detection': domain_detection,
            'search_results': search_results,
            'total_results': sum(len(results) for results in search_results.values()),
            'timestamp': datetime.now().isoformat()
        }
        
        return processing_summary
    
    def get_domain_stats(self) -> Dict[str, Any]:
        """Get statistics about domain distribution in the knowledge base"""
        if not self.vectorstore:
            return {}
        
        try:
            client = chromadb.PersistentClient(path=self.chroma_db_path)
            collection = client.get_collection("telegram_bot_knowledge")
            results = collection.get()
            
            stats = {
                'total_chunks': len(results['ids']),
                'domain_distribution': {},
                'god_commands_by_domain': {}
            }
            
            for metadata in results['metadatas']:
                source_type = metadata.get('source_type', 'file')
                is_god_command = metadata.get('is_god_command', False)
                
                # Count by domain
                domain_found = None
                for domain_key, domain_config in self.domains.items():
                    if source_type in domain_config.source_types:
                        domain_found = domain_key
                        break
                    elif is_god_command:
                        source = metadata.get('source', '').upper()
                        if any(prefix in source for prefix in domain_config.god_command_prefixes):
                            domain_found = domain_key
                            break
                
                if domain_found:
                    if domain_found not in stats['domain_distribution']:
                        stats['domain_distribution'][domain_found] = 0
                    stats['domain_distribution'][domain_found] += 1
                    
                    if is_god_command:
                        if domain_found not in stats['god_commands_by_domain']:
                            stats['god_commands_by_domain'][domain_found] = 0
                        stats['god_commands_by_domain'][domain_found] += 1
                else:
                    # General/unclassified
                    if 'general' not in stats['domain_distribution']:
                        stats['domain_distribution']['general'] = 0
                    stats['domain_distribution']['general'] += 1
            
            return stats
            
        except Exception as e:
            print(f"[ERR] Error getting domain stats: {e}")
            return {} 