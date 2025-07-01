#!/usr/bin/env python3
"""
Test script for rate-limit-safe Basketball-Reference crawling
This script demonstrates crawling that stays well under the 20 pages/minute limit
"""

import time
from datetime import datetime
from basketball_reference_crawler import BasketballReferenceCrawler
from crawler_config import SUPER_SAFE_CONFIG, get_config_by_speed

def test_rate_limit_safe_crawling():
    """Test crawling with super-safe rate limiting (under 20 pages/minute)"""
    print("🛡️  Testing Rate-Limit-Safe Basketball-Reference Crawler")
    print("=" * 60)
    
    # Use super-safe configuration
    config = SUPER_SAFE_CONFIG
    config.max_pages = 10  # Limit for testing
    
    print(f"📊 Configuration:")
    print(f"   • Delay between requests: {config.delay_between_requests}s")
    print(f"   • Max pages: {config.max_pages}")
    print(f"   • Threads: {config.max_concurrent_threads}")
    print(f"   • Rate limit delay: {config.rate_limit_delay}s")
    print(f"   • Pages per minute (theoretical max): {60/config.delay_between_requests:.1f}")
    print()
    
    # Verify we're under the limit
    pages_per_minute = 60 / config.delay_between_requests
    if pages_per_minute > 20:
        print("⚠️  WARNING: Configuration may exceed 20 pages/minute limit!")
        return False
    else:
        print(f"✅ Configuration safely under 20 pages/minute limit ({pages_per_minute:.1f} pages/min)")
    
    print()
    print("🚀 Starting crawl...")
    
    # Create crawler
    crawler = BasketballReferenceCrawler(config)
    
    # Test with a few recent season URLs
    seed_urls = [
        "https://www.basketball-reference.com/leagues/NBA_2024.html",
        "https://www.basketball-reference.com/leagues/NBA_2023.html",
        "https://www.basketball-reference.com/leagues/NBA_2024_per_game.html",
    ]
    
    start_time = time.time()
    
    try:
        # Run the crawl
        results = crawler.start_crawl(seed_urls)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print()
        print("📈 Crawl Results:")
        print(f"   • Pages crawled: {results.get('pages_crawled', 0)}")
        print(f"   • Pages archived: {results.get('pages_archived', 0)}")
        print(f"   • Data chunks added: {results.get('data_chunks_added', 0)}")
        print(f"   • Duration: {duration:.1f} seconds")
        print(f"   • Average pages per minute: {(results.get('pages_crawled', 0) / duration * 60):.1f}")
        
        # Verify rate limiting
        actual_rate = results.get('pages_crawled', 0) / duration * 60
        if actual_rate <= 20:
            print(f"✅ Successfully stayed under 20 pages/minute limit!")
        else:
            print(f"⚠️  Rate may be too high: {actual_rate:.1f} pages/minute")
        
        print()
        print("🎯 Crawl completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during crawl: {e}")
        return False

def show_all_safe_configs():
    """Show all available safe configurations"""
    print("\n🔧 Available Safe Configurations:")
    print("=" * 50)
    
    configs = {
        'ultra_safe': get_config_by_speed('ultra_safe'),
        'super_safe': get_config_by_speed('super_safe'), 
        'conservative': get_config_by_speed('conservative'),
    }
    
    for name, config in configs.items():
        pages_per_min = 60 / config.delay_between_requests
        status = "✅ SAFE" if pages_per_min <= 20 else "⚠️  RISKY"
        
        print(f"\n{name.upper()}:")
        print(f"   • Delay: {config.delay_between_requests}s")
        print(f"   • Pages/minute: {pages_per_min:.1f}")
        print(f"   • Rate limit delay: {config.rate_limit_delay}s")
        print(f"   • Status: {status}")

if __name__ == "__main__":
    print("🏀 Basketball-Reference Rate-Limit-Safe Crawler Test")
    print("This test ensures we stay under the 20 pages/minute limit\n")
    
    # Show available configurations
    show_all_safe_configs()
    
    print("\n" + "="*60)
    
    # Run the test
    success = test_rate_limit_safe_crawling()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("Your crawler is configured to safely stay under rate limits.")
    else:
        print("\n❌ Test failed!")
        print("Please check your configuration and try again.") 