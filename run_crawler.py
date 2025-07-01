#!/usr/bin/env python3
"""
Basketball-Reference Web Crawler - Standalone Runner
Systematically crawl and archive NBA data from Basketball-Reference.com
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

from basketball_reference_crawler import (
    BasketballReferenceCrawler,
    CrawlConfig,
    get_basketball_reference_seed_urls,
    run_sample_crawl
)

# Import configuration presets
try:
    from crawler_config import get_config_by_speed, get_recommended_config
    HAS_CONFIG_PRESETS = True
except ImportError:
    HAS_CONFIG_PRESETS = False

def main():
    parser = argparse.ArgumentParser(
        description="Basketball-Reference Web Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test crawl (super safe settings)
  python run_crawler.py --test

  # Use preset configurations (recommended)
  python run_crawler.py --config super_safe --max-pages 500     # 15 pages/min max
  python run_crawler.py --config ultra_safe --max-pages 100     # 4 pages/min max
  python run_crawler.py --config conservative --max-pages 200   # 7.5 pages/min max

  # Comprehensive crawl with super safe settings (RECOMMENDED)
  python run_crawler.py --comprehensive --max-pages 1000

  # Recent seasons only with custom settings
  python run_crawler.py --recent-seasons --max-pages 200 --delay 4.0

  # Resume previous crawl
  python run_crawler.py --resume

  # Show statistics only
  python run_crawler.py --stats

IMPORTANT: Basketball-Reference.com has a strict 20 pages/minute rate limit!
- Default settings use 4s delays (15 pages/min max) to stay safely under the limit
- Exceeding the limit results in 1-hour IP bans
- ALWAYS use single thread (--threads 1) for rate limiting
- For fastest safe crawling, use --config super_safe
        """
    )
    
    # Crawl modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--test', 
        action='store_true',
        help='Run a quick test crawl with ultra-conservative settings (10 pages)'
    )
    mode_group.add_argument(
        '--comprehensive', 
        action='store_true',
        help='Run comprehensive crawl with full seed URL set'
    )
    mode_group.add_argument(
        '--recent-seasons', 
        action='store_true',
        help='Focus on recent NBA seasons only'
    )
    mode_group.add_argument(
        '--resume', 
        action='store_true',
        help='Resume previous crawl from saved state'
    )
    mode_group.add_argument(
        '--stats', 
        action='store_true',
        help='Show crawl statistics and exit'
    )
    
    # Configuration presets
    if HAS_CONFIG_PRESETS:
        parser.add_argument(
            '--config', 
            choices=['ultra_safe', 'super_safe', 'conservative', 'moderate', 'aggressive', 'test'],
            default='super_safe',
            help='Use predefined configuration preset (default: super_safe - stays under 20 pages/min)'
        )
    
    # Configuration options
    parser.add_argument(
        '--max-pages', 
        type=int, 
        default=500,
        help='Maximum number of pages to crawl (default: 500)'
    )
    parser.add_argument(
        '--delay', 
        type=float, 
        default=4.0,  # Updated to 4.0 seconds to stay under 20 pages/minute
        help='Delay between requests in seconds (default: 4.0 - stays under 20 pages/min limit)'
    )
    parser.add_argument(
        '--threads', 
        type=int, 
        default=1,  # Keep at 1 for safety
        help='Number of concurrent threads (default: 1 - REQUIRED for rate limiting)'
    )
    parser.add_argument(
        '--no-robots', 
        action='store_true',
        help='Ignore robots.txt (not recommended)'
    )
    
    # Custom seed URLs
    parser.add_argument(
        '--seed-file', 
        type=str,
        help='File containing custom seed URLs (one per line)'
    )
    parser.add_argument(
        '--seed-urls', 
        nargs='+',
        help='Custom seed URLs as command line arguments'
    )
    
    # Output options
    parser.add_argument(
        '--output', 
        type=str,
        help='Save crawl results to JSON file'
    )
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Handle stats mode
    if args.stats:
        show_statistics()
        return
    
    # Handle test mode
    if args.test:
        print("🧪 Running test crawl...")
        crawler = run_sample_crawl()
        stats = crawler.get_crawl_statistics()
        print_results(stats, args.output)
        return
    
    # Determine seed URLs
    seed_urls = []
    
    if args.seed_file:
        try:
            with open(args.seed_file, 'r') as f:
                seed_urls = [line.strip() for line in f if line.strip()]
            print(f"📁 Loaded {len(seed_urls)} seed URLs from {args.seed_file}")
        except Exception as e:
            print(f"❌ Error loading seed file: {e}")
            sys.exit(1)
    
    elif args.seed_urls:
        seed_urls = args.seed_urls
        print(f"🔗 Using {len(seed_urls)} custom seed URLs")
    
    elif args.comprehensive:
        seed_urls = get_basketball_reference_seed_urls()
        print(f"🎯 Using comprehensive seed URL set ({len(seed_urls)} URLs)")
    
    elif args.recent_seasons:
        current_year = datetime.now().year
        seed_urls = [
            f"https://www.basketball-reference.com/leagues/NBA_{year}.html" 
            for year in range(current_year - 3, current_year + 1)
        ]
        seed_urls.extend([
            f"https://www.basketball-reference.com/leagues/NBA_{year}_per_game.html" 
            for year in range(current_year - 3, current_year + 1)
        ])
        print(f"📅 Using recent seasons seed URLs ({len(seed_urls)} URLs)")
    
    else:
        # Default to comprehensive
        seed_urls = get_basketball_reference_seed_urls()
        print(f"🎯 Using default comprehensive seed URL set ({len(seed_urls)} URLs)")
    
    # Create crawler configuration
    if HAS_CONFIG_PRESETS and hasattr(args, 'config') and args.config:
        # Use predefined configuration preset
        config = get_config_by_speed(args.config)
        
        # Override with command line arguments if provided
        if args.max_pages != 500:  # Only override if user explicitly set it
            config.max_pages = args.max_pages
        if args.delay != 4.0:  # Only override if user explicitly set it
            config.delay_between_requests = args.delay
        if args.threads != 1:  # Only override if user explicitly set it
            config.max_concurrent_threads = args.threads
        if args.no_robots:
            config.respect_robots_txt = False
            
        print(f"⚙️ Using '{args.config}' configuration preset with overrides:")
    else:
        # Create custom configuration from command line arguments
        config = CrawlConfig(
            max_pages=args.max_pages,
            delay_between_requests=args.delay,
            max_concurrent_threads=args.threads,
            respect_robots_txt=not args.no_robots,
            rate_limit_delay=120.0,  # Add conservative rate limit handling
            retry_delay_base=15.0    # Add conservative retry delays
        )
        
        print(f"⚙️ Using custom configuration:")
    
    print(f"   Max Pages: {config.max_pages}")
    print(f"   Delay: {config.delay_between_requests}s")
    print(f"   Threads: {config.max_concurrent_threads}")
    print(f"   Respect robots.txt: {config.respect_robots_txt}")
    print(f"   Rate limit delay: {config.rate_limit_delay}s")
    print(f"   Retry base delay: {config.retry_delay_base}s")
    print()
    
    # Warning for aggressive settings
    if config.delay_between_requests < 5.0 or config.max_concurrent_threads > 1:
        print("⚠️  WARNING: You're using aggressive settings that may trigger rate limiting!")
        print("   Consider using --config conservative or ultra_safe for safer crawling.")
        print()
    
    # Initialize and run crawler
    try:
        crawler = BasketballReferenceCrawler(config)
        
        if args.resume:
            print("🔄 Resuming previous crawl...")
            # Resume functionality would load existing state
            stats = crawler.start_crawl()
        else:
            print("🚀 Starting new crawl...")
            stats = crawler.start_crawl(seed_urls)
        
        print("\n✅ Crawl completed!")
        print_results(stats, args.output)
        
    except KeyboardInterrupt:
        print("\n⏹️ Crawl interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Crawl failed: {e}")
        sys.exit(1)

def show_statistics():
    """Show comprehensive crawler statistics"""
    try:
        # Initialize crawler to access statistics
        crawler = BasketballReferenceCrawler()
        stats = crawler.get_crawl_statistics()
        
        print("📊 Basketball-Reference Crawler Statistics")
        print("=" * 50)
        
        # Current session
        if stats['current_session']['start_time']:
            print("\n🔄 Current Session:")
            session = stats['current_session']
            print(f"   Pages Crawled: {session['pages_crawled']}")
            print(f"   Pages Archived: {session['pages_archived']}")
            print(f"   Data Chunks Added: {session['data_chunks_added']}")
            print(f"   Errors: {session['errors']}")
            if session['start_time']:
                print(f"   Started: {session['start_time']}")
        
        # URL status counts
        if stats['url_status_counts']:
            print("\n📈 URL Status Breakdown:")
            for status, count in stats['url_status_counts'].items():
                print(f"   {status.title()}: {count:,}")
        
        # Queue information
        print(f"\n📋 Queue Status:")
        print(f"   URLs Discovered: {stats['total_discovered']:,}")
        print(f"   URLs Processed: {stats['total_processed']:,}")
        print(f"   URLs in Queue: {stats['queue_size']:,}")
        
        # Recent activity
        if stats['recent_activity_24h'] > 0:
            print(f"\n📅 Recent Activity (24h): {stats['recent_activity_24h']:,} URLs processed")
        
        # Top categories
        if stats['top_categories']:
            print("\n🏆 Top Archived Categories:")
            for category, chunk_count in stats['top_categories']:
                print(f"   {category}: {chunk_count:,} chunks")
        
    except Exception as e:
        print(f"❌ Error loading statistics: {e}")

def print_results(stats, output_file=None):
    """Print crawl results and optionally save to file"""
    print("\n📊 Crawl Results:")
    print("=" * 30)
    print(f"Pages Crawled: {stats.get('pages_crawled', 0):,}")
    print(f"Pages Archived: {stats.get('pages_archived', 0):,}")
    print(f"Data Chunks Added: {stats.get('data_chunks_added', 0):,}")
    print(f"Errors: {stats.get('errors', 0):,}")
    
    if stats.get('start_time') and stats.get('end_time'):
        start = datetime.fromisoformat(stats['start_time'])
        end = datetime.fromisoformat(stats['end_time'])
        duration = end - start
        print(f"Duration: {duration}")
        
        if stats.get('pages_crawled', 0) > 0:
            pages_per_minute = stats['pages_crawled'] / (duration.total_seconds() / 60)
            print(f"Rate: {pages_per_minute:.1f} pages/minute")
    
    # Save to file if requested
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {output_file}")
        except Exception as e:
            print(f"\n❌ Error saving results: {e}")

if __name__ == "__main__":
    main() 