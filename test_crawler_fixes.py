#!/usr/bin/env python3
"""
Test script to verify Basketball-Reference crawler fixes
"""

import time
from basketball_reference_crawler import BasketballReferenceCrawler, CrawlConfig

def test_crawler_fixes():
    """Test the fixed crawler with enhanced error handling"""
    
    print("🔧 Testing Basketball-Reference Crawler Fixes")
    print("=" * 50)
    
    # Ultra-safe configuration
    config = CrawlConfig(
        max_pages=3,  # Very limited for testing
        delay_between_requests=6.0,  # 6 seconds = 10 pages/minute max
        max_concurrent_threads=1,  # Single thread
        timeout=10,  # 10 second timeout to prevent hanging
        max_retries=2,  # Reduced retries
        retry_delay_base=10.0,
        rate_limit_delay=60.0,  # 1 minute delay if rate limited (reduced from 10 minutes)
    )
    
    print(f"📋 Configuration:")
    print(f"  • Max pages: {config.max_pages}")
    print(f"  • Delay: {config.delay_between_requests}s")
    print(f"  • Timeout: {config.timeout}s")
    print(f"  • Rate limit delay: {config.rate_limit_delay}s")
    print()
    
    # Progress and log callbacks
    def progress_callback(stats):
        print(f"📊 Progress: {stats.get('pages_crawled', 0)} crawled, "
              f"{stats.get('queue_size', 0)} in queue, "
              f"{stats.get('errors', 0)} errors")
    
    def log_callback(message, level):
        timestamp = time.strftime("%H:%M:%S")
        level_emoji = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }.get(level, 'ℹ️')
        print(f"[{timestamp}] {level_emoji} {message}")
    
    # Initialize crawler
    try:
        crawler = BasketballReferenceCrawler(
            config=config,
            progress_callback=progress_callback,
            log_callback=log_callback
        )
        print("✅ Crawler initialized successfully")
    except Exception as e:
        print(f"❌ Crawler initialization failed: {e}")
        return False
    
    # Test URLs
    test_urls = [
        "https://www.basketball-reference.com/leagues/NBA_2024.html",
        "https://www.basketball-reference.com/leagues/NBA_2023.html",
    ]
    
    print(f"🌱 Starting test crawl with {len(test_urls)} URLs...")
    print("⏱️ Expected duration: ~30-60 seconds")
    print()
    
    try:
        start_time = time.time()
        result = crawler.start_crawl(test_urls)
        end_time = time.time()
        
        print()
        print("🎯 Test Results:")
        print("=" * 30)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Pages crawled: {result.get('pages_crawled', 0)}")
        print(f"Pages archived: {result.get('pages_archived', 0)}")
        print(f"Data chunks: {result.get('chunks_added', 0)}")
        print(f"Errors: {result.get('errors', 0)}")
        print(f"Duration: {end_time - start_time:.1f} seconds")
        
        # Check success
        if result.get('status') == 'completed':
            print("✅ SUCCESS: Crawler completed without hanging!")
            return True
        elif result.get('status') == 'stopped':
            print("⚠️ STOPPED: Crawler was stopped (may be due to rate limiting)")
            return True  # Still consider this a success since it didn't hang
        else:
            print("❌ FAILED: Crawler did not complete properly")
            return False
            
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        return False
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_crawler_fixes()
    exit(0 if success else 1) 