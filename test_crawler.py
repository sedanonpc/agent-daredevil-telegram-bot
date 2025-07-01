#!/usr/bin/env python3
"""
Quick test script for Basketball-Reference Web Crawler
"""

import sys
from basketball_reference_crawler import run_sample_crawl

def main():
    print("🧪 Testing Basketball-Reference Web Crawler")
    print("=" * 50)
    
    try:
        print("🚀 Starting sample crawl (limited scope)...")
        crawler = run_sample_crawl()
        
        print("✅ Sample crawl completed successfully!")
        
        # Get and display statistics
        stats = crawler.get_crawl_statistics()
        
        print("\n📊 Crawl Results:")
        print(f"   Pages Crawled: {stats.get('pages_crawled', 0)}")
        print(f"   Pages Archived: {stats.get('pages_archived', 0)}")
        print(f"   Data Chunks Added: {stats.get('data_chunks_added', 0)}")
        print(f"   Errors: {stats.get('errors', 0)}")
        
        if stats.get('pages_archived', 0) > 0:
            print("\n🎉 Test successful! NBA data has been archived to your RAG memory.")
            print("   You can now search for this data in your Telegram bot or RAG Manager.")
        else:
            print("\n⚠️ Test completed but no data was archived.")
            print("   This might be normal for a very limited test crawl.")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nMake sure you have installed all required dependencies:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 