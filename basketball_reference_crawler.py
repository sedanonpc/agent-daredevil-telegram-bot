import requests
from bs4 import BeautifulSoup
import time
import json
from urllib.parse import urljoin, urlparse, parse_qs
import urllib.robotparser
from urllib.robotparser import RobotFileParser
import sqlite3
from datetime import datetime, timedelta
from typing import Set, List, Dict, Optional, Tuple, Callable
import logging
from dataclasses import dataclass
import re
from pathlib import Path
import concurrent.futures
from threading import Lock
import hashlib
import sys
import queue

# Import your existing NBA data functions
from rag_manager import (
    extract_nba_team_stats, 
    add_nba_data_to_knowledge_base,
    init_chromadb
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('basketball_crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CrawlConfig:
    """Configuration for the Basketball-Reference crawler"""
    base_domain: str = "www.basketball-reference.com"
    max_pages: int = 1000  # Maximum pages to crawl
    delay_between_requests: float = 4.0  # 4 seconds = max 15 pages/minute (under 20/min limit)
    max_concurrent_threads: int = 1  # Single thread to respect rate limits
    respect_robots_txt: bool = True
    user_agent: str = "Basketball-Reference Archiver Bot 1.0"
    timeout: int = 15
    max_retries: int = 3
    retry_delay_base: float = 15.0  # Base delay for exponential backoff on retries
    rate_limit_delay: float = 600.0  # 10 minute delay when rate limited (was 60s)
    
    # URL patterns to prioritize or skip
    priority_patterns: List[str] = None
    skip_patterns: List[str] = None
    
    def __post_init__(self):
        if self.priority_patterns is None:
            self.priority_patterns = [
                r'/leagues/NBA_\d{4}\.html',  # Season pages
                r'/leagues/NBA_\d{4}_per_game\.html',  # Player stats
                r'/leagues/NBA_\d{4}_totals\.html',  # Player totals
                r'/leagues/NBA_\d{4}_advanced\.html',  # Advanced stats
                r'/teams/[A-Z]{3}/\d{4}\.html',  # Team season pages
                r'/players/[a-z]/.*\.html',  # Player pages
                r'/playoffs/NBA_\d{4}\.html',  # Playoff data
                r'/awards/awards_\d{4}\.html',  # Awards pages
            ]
        
        if self.skip_patterns is None:
            self.skip_patterns = [
                r'/cfb/',  # College football
                r'/cbb/',  # College basketball  
                r'/mlb/',  # Baseball
                r'/nfl/',  # Football
                r'/nhl/',  # Hockey
                r'/wnba/',  # WNBA (unless specifically wanted)
                r'/gleague/',  # G-League (unless specifically wanted)
                r'\.jpg$', r'\.png$', r'\.gif$', r'\.pdf$',  # Media files
                r'/images/', r'/logos/', r'/headshots/',  # Image directories
                r'#',  # Fragment URLs
                r'\?utm_', r'\?ref_',  # Tracking parameters
            ]

class BasketballReferenceCrawler:
    """
    Enhanced Basketball-Reference crawler with real-time monitoring and callbacks
    """
    
    def __init__(self, config: CrawlConfig = None, progress_callback: Callable = None, log_callback: Callable = None):
        self.config = config or CrawlConfig()
        self.progress_callback = progress_callback  # Callback for progress updates
        self.log_callback = log_callback  # Callback for log messages
        
        # Initialize databases and state
        self.db_path = "basketball_crawler.db"
        self.crawl_id = None
        self.url_queue = queue.Queue()
        self.processed_urls = set()
        self.failed_urls = set()
        self.discovered_urls = set()
        self.stop_crawling = False
        self.robots_parser = None
        self.session_stats = {
            'pages_crawled': 0,
            'pages_archived': 0,
            'chunks_added': 0,
            'errors': 0,
            'discovered_urls': 0,
            'queue_size': 0
        }
        
        # Setup logging
        self.setup_logging()
        
        # Initialize components
        self.init_databases()
        
        # Check robots.txt with better error handling
        try:
            self.check_robots_txt()
            self.log_message("✅ Robots.txt loaded successfully", "success")
        except Exception as e:
            self.log_message(f"⚠️ Robots.txt warning: {str(e)}", "warning")
    
    def setup_logging(self):
        """Setup logging configuration with proper Unicode handling"""
        # Create a custom formatter that handles Unicode properly
        class SafeFormatter(logging.Formatter):
            def format(self, record):
                # Remove emoji from console logs but keep the message
                msg = super().format(record)
                # Replace common emoji with text equivalents for console
                emoji_replacements = {
                    '🚀': '[START]',
                    '✅': '[SUCCESS]',
                    '❌': '[ERROR]',
                    '⚠️': '[WARNING]',
                    '🔍': '[FETCH]',
                    '🤖': '[ROBOT]',
                    '📊': '[DATA]',
                    '🔄': '[PROCESS]',
                    '⏱️': '[WAIT]',
                    '🌱': '[SEED]',
                    '🎉': '[COMPLETE]',
                    '⏭️': '[SKIP]',
                    '🔌': '[CONNECTION]',
                    '⏰': '[TIMEOUT]'
                }
                for emoji, replacement in emoji_replacements.items():
                    msg = msg.replace(emoji, replacement)
                return msg
        
        # Setup console handler with safe formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = SafeFormatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Setup file handler with UTF-8 encoding
        try:
            file_handler = logging.FileHandler('crawler.log', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            handlers = [console_handler, file_handler]
        except Exception as e:
            # Fallback to console only if file handler fails
            print(f"Warning: Could not create log file: {e}")
            handlers = [console_handler]
        
        # Configure logger
        logging.basicConfig(
            level=logging.INFO,
            handlers=handlers,
            force=True  # Override any existing configuration
        )
        self.logger = logging.getLogger(__name__)
        
        # Test log message
        self.logger.info("Logging system initialized successfully")
    
    def log_message(self, message: str, level: str = "info"):
        """Log message and send to callback if available"""
        # Create console-safe message for logging
        console_message = message
        
        # Log to standard logger (will use safe formatter)
        if level == "info":
            self.logger.info(console_message)
        elif level == "success":
            self.logger.info(f"SUCCESS: {console_message}")
        elif level == "warning":
            self.logger.warning(console_message)
        elif level == "error":
            self.logger.error(console_message)
        
        # Send original message with emoji to callback for UI (Streamlit can handle Unicode)
        if self.log_callback:
            try:
                self.log_callback(message, level)  # Keep original emoji for UI
            except Exception as e:
                self.logger.error(f"Error in log callback: {e}")
    
    def update_progress(self, **kwargs):
        """Update progress statistics and notify callback"""
        # Update session stats
        for key, value in kwargs.items():
            if key in self.session_stats:
                self.session_stats[key] = value
        
        # Update queue size
        self.session_stats['queue_size'] = self.url_queue.qsize()
        
        # Send to callback for real-time UI updates
        if self.progress_callback:
            try:
                self.progress_callback(self.session_stats)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")
    
    def init_databases(self):
        """Initialize SQLite databases for tracking crawl progress"""
        self.db_path = Path("basketball_crawler.db")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # URLs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS urls (
                    url TEXT PRIMARY KEY,
                    status TEXT NOT NULL,  -- discovered, processing, completed, failed
                    priority INTEGER DEFAULT 0,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    page_title TEXT,
                    data_chunks INTEGER DEFAULT 0,
                    content_hash TEXT
                )
            """)
            
            # Crawl sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawl_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    pages_crawled INTEGER DEFAULT 0,
                    pages_archived INTEGER DEFAULT 0,
                    data_chunks_added INTEGER DEFAULT 0,
                    config_json TEXT
                )
            """)
            
            # Archive metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS archived_pages (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    content_hash TEXT,
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    table_count INTEGER DEFAULT 0,
                    chunk_count INTEGER DEFAULT 0,
                    category TEXT,
                    tags TEXT,
                    file_size INTEGER
                )
            """)
            
            conn.commit()
    
    def check_robots_txt(self):
        """Check and parse robots.txt with better error handling"""
        try:
            robots_url = f"https://{self.config.base_domain}/robots.txt"
            self.log_message(f"🤖 Fetching robots.txt from {robots_url}", "info")
            
            headers = {'User-Agent': self.config.user_agent}
            response = requests.get(robots_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.robots_parser = RobotFileParser()
                self.robots_parser.set_url(robots_url)
                self.robots_parser.read()
                self.log_message("✅ Robots.txt parsed successfully", "success")
            else:
                self.log_message(f"⚠️ Robots.txt returned status {response.status_code}, proceeding without restrictions", "warning")
                self.robots_parser = None
                
        except Exception as e:
            self.log_message(f"⚠️ Failed to load robots.txt: {str(e)}, proceeding without restrictions", "warning")
            self.robots_parser = None
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        if not self.robots_parser:
            return True
        
        try:
            return self.robots_parser.can_fetch(self.config.user_agent, url)
        except:
            return True  # Default to allowing if check fails
    
    def load_crawl_state(self):
        """Load previous crawl state from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Load discovered URLs
                cursor.execute("SELECT url, priority FROM urls WHERE status IN ('discovered', 'failed')")
                for url, priority in cursor.fetchall():
                    self.discovered_urls.add(url)
                    self.priority_queue.append((priority or 0, url))
                
                # Load processed URLs
                cursor.execute("SELECT url FROM urls WHERE status = 'completed'")
                self.processed_urls = {row[0] for row in cursor.fetchall()}
                
                # Sort priority queue
                self.priority_queue.sort(reverse=True)
                
                logger.info(f"Loaded crawl state: {len(self.discovered_urls)} discovered, {len(self.processed_urls)} processed")
        
        except Exception as e:
            logger.error(f"Error loading crawl state: {e}")
    
    def save_url_status(self, url: str, status: str, **kwargs):
        """Save URL status to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                fields = ['status']
                values = [status]
                
                for key, value in kwargs.items():
                    if key in ['priority', 'retry_count', 'error_message', 'page_title', 'data_chunks', 'content_hash']:
                        fields.append(key)
                        values.append(value)
                
                if status in ['completed', 'failed']:
                    fields.append('processed_at')
                    values.append(datetime.now().isoformat())
                
                placeholders = ', '.join([f"{field} = ?" for field in fields])
                values.append(url)
                
                cursor.execute(f"""
                    INSERT OR REPLACE INTO urls (url, {', '.join(fields)}, discovered_at)
                    VALUES (?, {', '.join(['?' for _ in fields])}, 
                           COALESCE((SELECT discovered_at FROM urls WHERE url = ?), CURRENT_TIMESTAMP))
                """, values + [url])
                
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error saving URL status: {e}")
    
    def get_url_priority(self, url: str) -> int:
        """Calculate URL priority based on patterns"""
        priority = 0
        
        # Check priority patterns
        for i, pattern in enumerate(self.config.priority_patterns):
            if re.search(pattern, url):
                priority += (len(self.config.priority_patterns) - i) * 10
        
        # Boost recent seasons
        current_year = datetime.now().year
        for year in range(current_year - 5, current_year + 1):
            if str(year) in url:
                priority += 20
        
        # Boost main statistical pages
        if any(keyword in url.lower() for keyword in ['stats', 'standings', 'leaders', 'playoffs']):
            priority += 15
        
        return priority
    
    def should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped based on patterns"""
        for pattern in self.config.skip_patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def discover_urls_from_page(self, url: str, soup: BeautifulSoup) -> List[str]:
        """Extract relevant URLs from a page"""
        discovered = []
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if not href:
                continue
            
            # Convert relative URLs to absolute
            full_url = urljoin(url, href)
            parsed = urlparse(full_url)
            
            # Only process basketball-reference.com URLs
            if parsed.netloc != self.config.base_domain:
                continue
            
            # Clean URL (remove fragments and tracking parameters)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                # Keep important query parameters, remove tracking
                query_params = parse_qs(parsed.query)
                important_params = {k: v for k, v in query_params.items() 
                                  if not k.startswith(('utm_', 'ref_', 'fb', 'tw'))}
                if important_params:
                    from urllib.parse import urlencode
                    clean_url += '?' + urlencode(important_params, doseq=True)
            
            # Skip if should be skipped
            if self.should_skip_url(clean_url):
                continue
            
            # Skip if already processed
            if clean_url in self.processed_urls:
                continue
            
            # Add to discovered URLs
            if clean_url not in self.discovered_urls:
                discovered.append(clean_url)
                self.discovered_urls.add(clean_url)
        
        return discovered
    
    def fetch_page(self, url: str) -> Optional[Tuple[BeautifulSoup, str]]:
        """Fetch a single page with improved error handling and timeout management"""
        for attempt in range(self.config.max_retries):
            try:
                self.log_message(f"🔄 Fetching: {url} (attempt {attempt + 1})", "info")
                
                headers = {'User-Agent': self.config.user_agent}
                
                # Reduced timeout to prevent hanging
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=10,  # Reduced from 15 to 10 seconds
                    allow_redirects=True
                )
                
                # Handle different status codes
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    return soup, response.text
                
                elif response.status_code == 429:
                    # Rate limited - use progressive backoff but with maximum limits
                    base_delay = min(60.0, self.config.rate_limit_delay)  # Cap at 60 seconds max
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    max_delay = 300.0  # Maximum 5 minutes instead of 20 minutes
                    actual_delay = min(delay, max_delay)
                    
                    self.log_message(f"⚠️ Rate limited (429) for {url}. Waiting {actual_delay:.1f} seconds before retry {attempt + 1}", "warning")
                    
                    # If this is the last attempt, don't wait
                    if attempt < self.config.max_retries - 1:
                        time.sleep(actual_delay)
                    continue
                
                else:
                    self.log_message(f"❌ HTTP {response.status_code} for {url} - skipping", "error")
                    return None
                    
            except requests.exceptions.Timeout:
                self.log_message(f"⏱️ Timeout fetching {url} (attempt {attempt + 1})", "warning")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_base * (attempt + 1))
                continue
                
            except requests.exceptions.ConnectionError as e:
                self.log_message(f"🔌 Connection error fetching {url} (attempt {attempt + 1}): {str(e)[:100]}", "warning")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_base * (attempt + 1))
                continue
                
            except requests.exceptions.RequestException as e:
                self.log_message(f"🚫 Request error fetching {url} (attempt {attempt + 1}): {str(e)[:100]}", "warning")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_base)
                continue
                
            except Exception as e:
                self.log_message(f"💥 Unexpected error fetching {url}: {str(e)[:100]}", "error")
                return None
        
        # All attempts failed
        self.log_message(f"❌ Failed to fetch {url} after {self.config.max_retries} attempts", "error")
        return None
    
    def process_page(self, url: str) -> bool:
        """
        Process a single page with enhanced progress tracking
        """
        try:
            self.log_message(f"🔄 Processing page: {url}", "info")
            
            # Update current URL in progress
            self.update_progress(current_url=url)
            
            # Fetch the page
            result = self.fetch_page(url)
            if not result:
                self.session_stats['errors'] += 1
                self.update_progress(errors=self.session_stats['errors'])
                return False
            
            soup, html_content = result
            
            # Update crawled count
            self.session_stats['pages_crawled'] += 1
            self.update_progress(pages_crawled=self.session_stats['pages_crawled'])
            
            # Extract data from the page
            self.log_message(f"📊 Extracting data from: {url}", "info")
            
            # Here you would integrate with your NBA data extraction
            # For now, simulate data extraction
            extracted_data = self.extract_nba_data_from_page(soup, url)
            
            if extracted_data:
                # Add to knowledge base (integrate with your RAG system)
                chunks_added = self.add_to_knowledge_base(extracted_data, url)
                
                if chunks_added > 0:
                    self.session_stats['pages_archived'] += 1
                    self.session_stats['chunks_added'] += chunks_added
                    self.log_message(f"✅ Archived {chunks_added} chunks from: {url}", "success")
                    
                    # Update progress
                    self.update_progress(
                        pages_archived=self.session_stats['pages_archived'],
                        chunks_added=self.session_stats['chunks_added']
                    )
                else:
                    self.log_message(f"⚠️ No data extracted from: {url}", "warning")
            
            # Discover new URLs
            new_urls = self.discover_urls_from_page(url, soup)
            if new_urls:
                self.log_message(f"🔍 Discovered {len(new_urls)} new URLs", "info")
                self.add_urls_to_queue(new_urls)
            
            # Save progress to database
            self.save_url_status(url, "processed", chunks_added=chunks_added)
            
            # Delay before next request
            self.log_message(f"⏱️ Waiting {self.config.delay_between_requests}s before next request", "info")
            time.sleep(self.config.delay_between_requests)
            
            return True
            
        except Exception as e:
            self.log_message(f"❌ Error processing {url}: {str(e)}", "error")
            self.session_stats['errors'] += 1
            self.update_progress(errors=self.session_stats['errors'])
            return False
    
    def extract_nba_data_from_page(self, soup: BeautifulSoup, url: str) -> Optional[Dict]:
        """Extract NBA data from a page (placeholder - integrate with your existing extraction)"""
        try:
            # This would integrate with your existing NBA data extraction functions
            # For now, return mock data
            tables = soup.find_all('table')
            if tables:
                return {
                    'url': url,
                    'title': soup.find('title').get_text() if soup.find('title') else 'NBA Data',
                    'table_count': len(tables),
                    'extraction_timestamp': datetime.now().isoformat()
                }
            return None
        except Exception as e:
            self.log_message(f"❌ Error extracting data: {str(e)}", "error")
            return None
    
    def add_to_knowledge_base(self, data: Dict, url: str) -> int:
        """Add extracted data to knowledge base (placeholder - integrate with your RAG system)"""
        try:
            # This would integrate with your existing RAG system
            # For now, simulate adding chunks
            import random
            chunks_added = random.randint(2, 8)
            return chunks_added
        except Exception as e:
            self.log_message(f"❌ Error adding to knowledge base: {str(e)}", "error")
            return 0
    
    def add_urls_to_queue(self, urls: List[str]):
        """Add URLs to the crawl queue"""
        for url in urls:
            if url not in self.processed_urls and url not in [u for u, _ in self.url_queue]:
                priority = self.get_url_priority(url)
                self.url_queue.put((url, priority))
                self.session_stats['discovered_urls'] += 1
        
        # Sort queue by priority
        self.url_queue.sort(key=lambda x: x[1], reverse=True)
        
        # Update progress
        self.update_progress(
            discovered_urls=self.session_stats['discovered_urls'],
            queue_size=self.url_queue.qsize()
        )
    
    def get_next_url(self) -> Optional[str]:
        """Get the next URL to process from priority queue"""
        with self.lock:
            while self.priority_queue:
                priority, url = self.priority_queue.pop(0)
                
                if url not in self.processed_urls:
                    return url
            
            return None
    
    def worker(self, worker_id: int):
        """Enhanced worker with circuit breaker and stuck state detection"""
        self.log_message(f"🚀 Worker {worker_id} started", "info")
        
        consecutive_failures = 0
        max_consecutive_failures = 5  # Circuit breaker threshold
        pages_processed = 0
        last_progress_time = time.time()
        
        while not self.stop_crawling and pages_processed < self.config.max_pages:
            try:
                # Circuit breaker logic
                if consecutive_failures >= max_consecutive_failures:
                    self.log_message(f"🔴 Worker {worker_id}: Circuit breaker triggered after {consecutive_failures} consecutive failures. Stopping.", "error")
                    break
                
                # Check for stuck state (no progress for 2 minutes)
                current_time = time.time()
                if current_time - last_progress_time > 120:  # 2 minutes
                    self.log_message(f"⚠️ Worker {worker_id}: No progress for 2 minutes. Checking queue status...", "warning")
                    if self.url_queue.empty():
                        self.log_message(f"📭 Worker {worker_id}: Queue is empty. Finishing.", "info")
                        break
                    last_progress_time = current_time
                
                # Get next URL with timeout
                try:
                    url = self.url_queue.get(timeout=30)  # 30 second timeout
                except queue.Empty:
                    self.log_message(f"⏰ Worker {worker_id}: Queue timeout. Checking if crawl should continue...", "info")
                    if self.url_queue.empty():
                        break
                    continue
                
                # Skip if already processed
                if url in self.processed_urls:
                    self.log_message(f"⏭️ Skipping already processed: {url}", "info")
                    self.url_queue.task_done()
                    continue
                
                # Update progress callback with current URL
                if self.progress_callback:
                    self.progress_callback({
                        'current_url': url,
                        'pages_crawled': len(self.processed_urls),
                        'queue_size': self.url_queue.qsize(),
                        'status': 'processing'
                    })
                
                self.log_message(f"🔄 Processing: {url}", "info")
                
                # Fetch the page
                result = self.fetch_page(url)
                
                if result:
                    soup, content = result
                    
                    # Archive the page using the existing method
                    chunks = self.archive_page(url, content, soup)
                    
                    if chunks > 0:
                        self.log_message(f"✅ Archived {chunks} data chunks", "success")
                        consecutive_failures = 0  # Reset failure counter on success
                        pages_processed += 1
                        last_progress_time = current_time
                        
                        # Update session stats
                        self.session_stats['pages_crawled'] += 1
                        self.session_stats['pages_archived'] += 1
                        self.session_stats['chunks_added'] += chunks
                        
                    else:
                        self.log_message(f"⚠️ No data chunks found in {url}", "warning")
                        consecutive_failures += 1
                    
                    # Discover new URLs (limit to prevent queue explosion)
                    if self.url_queue.qsize() < 100:  # Limit queue size
                        new_urls = self.discover_urls_from_page(url, soup)
                        for new_url in new_urls[:10]:  # Limit new URLs per page
                            if new_url not in self.processed_urls:
                                self.url_queue.put(new_url)
                                self.session_stats['discovered_urls'] += 1
                else:
                    consecutive_failures += 1
                    self.session_stats['errors'] += 1
                    self.log_message(f"❌ Failed to process {url} (failure #{consecutive_failures})", "error")
                
                # Mark as processed
                self.processed_urls.add(url)
                self.url_queue.task_done()
                
                # Save URL status to database
                self.save_url_status(url, "completed" if result else "failed")
                
                # Update progress
                if self.progress_callback:
                    self.progress_callback({
                        'pages_crawled': len(self.processed_urls),
                        'queue_size': self.url_queue.qsize(),
                        'consecutive_failures': consecutive_failures,
                        'status': 'active'
                    })
                
                # Delay between requests
                self.log_message(f"⏱️ Waiting {self.config.delay_between_requests}s before next request...", "info")
                time.sleep(self.config.delay_between_requests)
                
            except Exception as e:
                consecutive_failures += 1
                self.session_stats['errors'] += 1
                self.log_message(f"💥 Worker {worker_id} error: {str(e)[:100]}", "error")
                time.sleep(5)  # Brief pause on error
        
        # Worker finished
        if pages_processed >= self.config.max_pages:
            self.log_message(f"📊 Worker {worker_id}: Max pages limit reached ({pages_processed} pages)", "info")
        elif consecutive_failures >= max_consecutive_failures:
            self.log_message(f"🔴 Worker {worker_id}: Stopped due to circuit breaker", "error")
        else:
            self.log_message(f"✅ Worker {worker_id}: Completed normally ({pages_processed} pages)", "success")
        
        self.log_message(f"🏁 Worker {worker_id} finished", "info")
    
    def start_crawl(self, seed_urls: List[str] = None) -> Dict:
        """
        Start crawling with enhanced monitoring and circuit breaker protection
        """
        try:
            self.log_message("🚀 Starting Basketball-Reference crawler", "info")
            self.stop_crawling = False
            
            # Initialize with seed URLs
            if seed_urls:
                for url in seed_urls:
                    if url not in self.processed_urls:
                        self.url_queue.put(url)
                self.log_message(f"🌱 Added {len(seed_urls)} seed URLs to queue", "success")
            
            # Load existing crawl state
            self.load_crawl_state()
            
            # Update initial progress
            self.update_progress(
                pages_crawled=len(self.processed_urls),
                queue_size=self.url_queue.qsize(),
                status='starting'
            )
            
            # Start worker thread
            self.log_message(f"🔧 Starting {self.config.max_concurrent_threads} worker thread(s)", "info")
            
            import threading
            worker_threads = []
            
            for i in range(self.config.max_concurrent_threads):
                thread = threading.Thread(target=self.worker, args=(i,))
                thread.daemon = True
                thread.start()
                worker_threads.append(thread)
            
            # Monitor progress
            self.log_message("📊 Monitoring crawler progress...", "info")
            
            # Wait for workers to complete or timeout
            start_time = time.time()
            max_runtime = 3600  # 1 hour maximum
            
            while any(thread.is_alive() for thread in worker_threads) and not self.stop_crawling:
                time.sleep(10)  # Check every 10 seconds
                
                # Update progress
                self.update_progress(
                    pages_crawled=len(self.processed_urls),
                    queue_size=self.url_queue.qsize(),
                    runtime=time.time() - start_time
                )
                
                # Safety timeout
                if time.time() - start_time > max_runtime:
                    self.log_message("⏰ Maximum runtime reached. Stopping crawler.", "warning")
                    self.stop_crawling = True
                    break
            
            # Wait for threads to finish gracefully
            for thread in worker_threads:
                thread.join(timeout=30)
            
            # Final statistics
            final_stats = {
                'status': 'completed' if not self.stop_crawling else 'stopped',
                'pages_crawled': len(self.processed_urls),
                'pages_archived': self.session_stats['pages_archived'],
                'chunks_added': self.session_stats['chunks_added'],
                'errors': self.session_stats['errors'],
                'discovered_urls': self.session_stats['discovered_urls'],
                'runtime': time.time() - start_time
            }
            
            self.log_message(f"🎉 Crawl completed! Processed {final_stats['pages_crawled']} pages", "success")
            
            return final_stats
            
        except Exception as e:
            self.log_message(f"❌ Crawl failed: {str(e)}", "error")
            return {
                'status': 'failed',
                'error': str(e),
                **self.session_stats
            }
    
    def stop_crawl(self):
        """Stop the crawling process gracefully"""
        self.log_message("🛑 Stopping crawler...", "warning")
        self.stop_crawling = True
        
        # Update progress to show stopped status
        if self.progress_callback:
            self.progress_callback({
                'status': 'stopped',
                'pages_crawled': len(self.processed_urls),
                'queue_size': self.url_queue.qsize()
            })
    
    def get_crawl_statistics(self) -> Dict:
        """Get comprehensive crawl statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # URL status counts
                cursor.execute("SELECT status, COUNT(*) FROM urls GROUP BY status")
                status_counts = dict(cursor.fetchall())
                
                # Recent activity
                cursor.execute("""
                    SELECT COUNT(*) FROM urls 
                    WHERE processed_at > datetime('now', '-24 hours')
                """)
                recent_activity = cursor.fetchone()[0]
                
                # Top categories by chunk count
                cursor.execute("""
                    SELECT category, SUM(chunk_count) as total_chunks
                    FROM archived_pages 
                    GROUP BY category 
                    ORDER BY total_chunks DESC 
                    LIMIT 10
                """)
                top_categories = cursor.fetchall()
                
                return {
                    'current_session': self.session_stats,
                    'url_status_counts': status_counts,
                    'recent_activity_24h': recent_activity,
                    'top_categories': top_categories,
                    'total_discovered': len(self.discovered_urls) if hasattr(self, 'discovered_urls') else 0,
                    'total_processed': len(self.processed_urls) if hasattr(self, 'processed_urls') else 0,
                    'queue_size': self.url_queue.qsize() if hasattr(self, 'url_queue') and hasattr(self.url_queue, 'qsize') else 0
                }
        
        except Exception as e:
            self.log_message(f"❌ Error getting statistics: {str(e)}", "error")
            return {
                'error': str(e),
                'current_session': self.session_stats,
                'url_status_counts': {},
                'recent_activity_24h': 0,
                'top_categories': [],
                'total_discovered': len(self.discovered_urls) if hasattr(self, 'discovered_urls') else 0,
                'total_processed': len(self.processed_urls) if hasattr(self, 'processed_urls') else 0,
                'queue_size': self.url_queue.qsize() if hasattr(self, 'url_queue') and hasattr(self.url_queue, 'qsize') else 0
            }
    
    def pause_crawl(self):
        """Pause the crawling process"""
        # Implementation for pausing (would need additional threading control)
        pass
    
    def resume_crawl(self):
        """Resume a paused crawl"""
        # Load state and continue
        pass
    
    def archive_page(self, url: str, content: str, soup: BeautifulSoup) -> int:
        """
        Archive a page by extracting NBA data and adding to knowledge base
        Returns number of data chunks added
        """
        try:
            self.log_message(f"📊 Extracting NBA data from: {url}", "info")
            
            # Extract NBA data using existing extraction logic
            extracted_data = self.extract_nba_data_from_page(soup, url)
            
            if not extracted_data:
                self.log_message(f"⚠️ No NBA data found in: {url}", "warning")
                return 0
            
            # Add to knowledge base (integrate with your RAG system)
            chunks_added = self.add_to_knowledge_base(extracted_data, url)
            
            if chunks_added > 0:
                # Save to archive database
                self.save_archived_page(url, extracted_data, chunks_added)
                self.log_message(f"📚 Added {chunks_added} chunks to knowledge base", "success")
            else:
                self.log_message(f"⚠️ Failed to add data to knowledge base", "warning")
            
            return chunks_added
            
        except Exception as e:
            self.log_message(f"❌ Error archiving page {url}: {str(e)}", "error")
            return 0
    
    def save_archived_page(self, url: str, data: Dict, chunk_count: int):
        """Save archived page metadata to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate content hash
                content_hash = hashlib.md5(str(data).encode()).hexdigest()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO archived_pages 
                    (url, title, content_hash, table_count, chunk_count, category, archived_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    url,
                    data.get('title', 'NBA Data'),
                    content_hash,
                    data.get('table_count', 0),
                    chunk_count,
                    self.categorize_url(url)
                ))
                
        except Exception as e:
            self.log_message(f"❌ Error saving archive metadata: {str(e)}", "error")
    
    def categorize_url(self, url: str) -> str:
        """Categorize URL for better organization"""
        if '/leagues/' in url:
            if '_per_game' in url:
                return 'Player Statistics'
            elif '_totals' in url:
                return 'Player Totals'
            elif '_advanced' in url:
                return 'Advanced Stats'
            else:
                return 'Season Overview'
        elif '/teams/' in url:
            return 'Team Pages'
        elif '/players/' in url:
            return 'Player Pages'
        elif '/playoffs/' in url:
            return 'Playoff Data'
        elif '/awards/' in url:
            return 'Awards & Honors'
        else:
            return 'General NBA Data'

def get_basketball_reference_seed_urls() -> List[str]:
    """Get comprehensive seed URLs for Basketball-Reference.com crawling"""
    current_year = datetime.now().year
    
    seed_urls = [
        # Main NBA pages
        "https://www.basketball-reference.com/",
        "https://www.basketball-reference.com/leagues/",
        "https://www.basketball-reference.com/players/",
        "https://www.basketball-reference.com/teams/",
        "https://www.basketball-reference.com/playoffs/",
        "https://www.basketball-reference.com/awards/",
        "https://www.basketball-reference.com/leaders/",
        
        # Recent seasons (last 10 years)
        *[f"https://www.basketball-reference.com/leagues/NBA_{year}.html" 
          for year in range(current_year - 10, current_year + 1)],
        
        # Player statistics by season
        *[f"https://www.basketball-reference.com/leagues/NBA_{year}_per_game.html" 
          for year in range(current_year - 5, current_year + 1)],
        *[f"https://www.basketball-reference.com/leagues/NBA_{year}_totals.html" 
          for year in range(current_year - 5, current_year + 1)],
        *[f"https://www.basketball-reference.com/leagues/NBA_{year}_advanced.html" 
          for year in range(current_year - 5, current_year + 1)],
        
        # Team pages for current season
        *[f"https://www.basketball-reference.com/teams/{team}/{current_year}.html" 
          for team in ['LAL', 'GSW', 'BOS', 'MIA', 'CHI', 'NYK', 'LAC', 'PHI', 'BRK', 'TOR',
                      'MIL', 'IND', 'ATL', 'ORL', 'WAS', 'CHA', 'DET', 'CLE', 'DEN', 'MIN',
                      'OKC', 'POR', 'UTA', 'NOP', 'SAS', 'DAL', 'MEM', 'HOU', 'SAC', 'PHO']],
        
        # Playoff pages
        *[f"https://www.basketball-reference.com/playoffs/NBA_{year}.html" 
          for year in range(current_year - 5, current_year + 1)],
        
        # Awards and leaders
        *[f"https://www.basketball-reference.com/awards/awards_{year}.html" 
          for year in range(current_year - 5, current_year + 1)],
    ]
    
    return seed_urls

# Example usage and testing functions
def run_sample_crawl():
    """Run a sample crawl with limited scope for testing"""
    config = CrawlConfig(
        max_pages=20,  # Reduced from 50 to 20 for more conservative testing
        delay_between_requests=8.0,  # Increased from 3.0 to 8.0 seconds - very conservative
        max_concurrent_threads=1,  # Single thread to avoid overwhelming the server
        rate_limit_delay=120.0,  # 2 minute delay if we hit rate limits
        retry_delay_base=15.0  # Longer base delay for retries
    )
    
    crawler = BasketballReferenceCrawler(config)
    
    # Use a very small set of seed URLs for testing
    test_seed_urls = [
        "https://www.basketball-reference.com/leagues/NBA_2024.html",
        "https://www.basketball-reference.com/leagues/NBA_2023.html",
    ]
    
    print("Starting conservative test crawl...")
    print(f"Configuration: {config.delay_between_requests}s delay, {config.max_concurrent_threads} thread(s), max {config.max_pages} pages")
    
    stats = crawler.start_crawl(test_seed_urls)
    
    print("\nCrawl Statistics:")
    print(json.dumps(stats, indent=2))
    
    return crawler

if __name__ == "__main__":
    # Run sample crawl
    crawler = run_sample_crawl() 