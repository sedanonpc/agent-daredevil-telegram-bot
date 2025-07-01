#!/usr/bin/env python3
"""
Enhanced Basketball-Reference Crawler Test
This script tests the improved crawler with better rate limiting and error handling.
"""

import sys
import time
from pathlib import Path
from basketball_reference_crawler import BasketballReferenceCrawler, CrawlConfig

def test_enhanced_crawler():
    """Test the enhanced crawler with ultra-safe settings"""
    
    print("🏀 Enhanced Basketball-Reference Crawler Test")
    print("=" * 50)
    
    # Ultra-safe configuration to avoid rate limits
    config = CrawlConfig(
        max_pages=5,  # Very limited for testing
        delay_between_requests=10.0,  # 10 seconds between requests (6 pages/minute max)
        max_concurrent_threads=1,  # Single thread
        timeout=30,  # 30 second timeout
        max_retries=3,
        retry_delay_base=25.0,  # 25 second base delay for retries
        rate_limit_delay=1200.0,  # 20 minute delay if rate limited
    )
    
    print(f"📋 Configuration:")
    print(f"  • Max pages: {config.max_pages}")
    print(f"  • Delay between requests: {config.delay_between_requests}s")
    print(f"  • Timeout: {config.timeout}s")
    print(f"  • Rate limit delay: {config.rate_limit_delay}s")
    print()
    
    # Progress callback for real-time monitoring
    def progress_callback(stats):
        print(f"📊 Progress: {stats.get('pages_crawled', 0)} crawled, "
              f"{stats.get('pages_archived', 0)} archived, "
              f"{stats.get('errors', 0)} errors, "
              f"Queue: {stats.get('queue_size', 0)}")
    
    # Log callback for detailed logging
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
    crawler = BasketballReferenceCrawler(
        config=config,
        progress_callback=progress_callback,
        log_callback=log_callback
    )
    
    # Test URLs - start with just 2 URLs
    test_urls = [
        "https://www.basketball-reference.com/leagues/NBA_2024.html",
        "https://www.basketball-reference.com/leagues/NBA_2023.html",
    ]
    
    print(f"🌱 Starting crawl with {len(test_urls)} seed URLs...")
    print("🚨 This test uses very conservative settings to avoid rate limits")
    print("⏱️ Expected duration: ~2-3 minutes with 10s delays")
    print()
    
    try:
        # Start the crawl
        start_time = time.time()
        result = crawler.start_crawl(test_urls)
        end_time = time.time()
        
        print()
        print("🎯 Crawl Results:")
        print("=" * 30)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Completion reason: {result.get('completion_reason', 'N/A')}")
        print(f"Pages crawled: {result.get('pages_crawled', 0)}")
        print(f"Pages archived: {result.get('pages_archived', 0)}")
        print(f"Data chunks added: {result.get('chunks_added', 0)}")
        print(f"Errors: {result.get('errors', 0)}")
        print(f"Failed URLs: {result.get('failed_urls', 0)}")
        print(f"Discovered URLs: {result.get('discovered_urls', 0)}")
        print(f"Total duration: {end_time - start_time:.1f} seconds")
        print()
        
        # Check if crawl was successful
        if result.get('status') == 'completed':
            if result.get('pages_archived', 0) > 0:
                print("✅ SUCCESS: Crawler completed successfully and archived data!")
            else:
                print("⚠️ PARTIAL: Crawler completed but no data was archived")
        else:
            print("❌ FAILED: Crawler did not complete successfully")
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        # Show statistics
        stats = crawler.get_crawl_statistics()
        if 'error' not in stats:
            print("\n📈 Detailed Statistics:")
            print(f"  • Current session: {stats.get('current_session', {})}")
            print(f"  • Queue size: {stats.get('queue_size', 0)}")
            print(f"  • Total processed: {stats.get('total_processed', 0)}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Crawl interrupted by user")
    except Exception as e:
        print(f"\n❌ Crawl failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_crawler() 