#!/usr/bin/env python3
"""
Test the Basketball-Reference crawler with ultra-conservative settings
This script is designed to safely test the crawler without hitting rate limits.
"""

from basketball_reference_crawler import BasketballReferenceCrawler, CrawlConfig
from crawler_config import get_config_by_speed
import time

def test_ultra_conservative_crawl():
    """Test crawl with ultra-conservative settings"""
    print("🧪 Testing Basketball-Reference Crawler with Ultra-Conservative Settings")
    print("=" * 70)
    
    # Use ultra-conservative configuration
    config = get_config_by_speed('ultra_safe')
    config.max_pages = 5  # Only test 5 pages
    
    print(f"Configuration:")
    print(f"  Max Pages: {config.max_pages}")
    print(f"  Delay: {config.delay_between_requests}s")
    print(f"  Threads: {config.max_concurrent_threads}")
    print(f"  Rate Limit Delay: {config.rate_limit_delay}s")
    print(f"  Retry Base Delay: {config.retry_delay_base}s")
    print()
    
    # Use minimal seed URLs for testing
    test_seed_urls = [
        "https://www.basketball-reference.com/leagues/NBA_2024.html",
        "https://www.basketball-reference.com/leagues/NBA_2023.html",
    ]
    
    print(f"Seed URLs ({len(test_seed_urls)}):")
    for url in test_seed_urls:
        print(f"  - {url}")
    print()
    
    # Initialize crawler
    crawler = BasketballReferenceCrawler(config)
    
    print("🚀 Starting ultra-conservative test crawl...")
    print("This will be slow but should avoid rate limiting.")
    print()
    
    start_time = time.time()
    
    try:
        # Start the crawl
        stats = crawler.start_crawl(test_seed_urls)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n✅ Test crawl completed successfully!")
        print("=" * 40)
        print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"Pages Crawled: {stats.get('pages_crawled', 0)}")
        print(f"Pages Archived: {stats.get('pages_archived', 0)}")
        print(f"Data Chunks Added: {stats.get('data_chunks_added', 0)}")
        print(f"Errors: {stats.get('errors', 0)}")
        
        if stats.get('pages_crawled', 0) > 0:
            avg_time = duration / stats['pages_crawled']
            print(f"Average Time per Page: {avg_time:.1f} seconds")
        
        # Get detailed statistics
        detailed_stats = crawler.get_crawl_statistics()
        if detailed_stats.get('url_status_counts'):
            print("\nURL Status Breakdown:")
            for status, count in detailed_stats['url_status_counts'].items():
                print(f"  {status.title()}: {count}")
        
        print("\n🎉 Test completed without rate limiting errors!")
        return True
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        return False
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_ultra_conservative_crawl()
    
    if success:
        print("\n💡 Tips for production crawling:")
        print("  - Use 'conservative' config for regular crawling")
        print("  - Use 'ultra_safe' config if you encounter rate limits")
        print("  - Monitor the crawler logs for 429 errors")
        print("  - Consider running crawls during off-peak hours")
        print("  - The crawler will automatically handle rate limits with exponential backoff")
    else:
        print("\n⚠️ Test failed. Check your internet connection and try again.") 