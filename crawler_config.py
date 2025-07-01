"""
Configuration presets for Basketball-Reference crawler
Adjust these settings based on your needs and to avoid rate limiting.
"""

from basketball_reference_crawler import CrawlConfig

# Ultra-conservative configuration - safest option, very slow
ULTRA_CONSERVATIVE_CONFIG = CrawlConfig(
    max_pages=100,
    delay_between_requests=15.0,  # 15 seconds between requests (4 pages/minute max)
    max_concurrent_threads=1,     # Single thread only
    rate_limit_delay=600.0,       # 10 minute delay if rate limited
    retry_delay_base=60.0,        # 60 second base delay for retries
    max_retries=5
)

# Super safe configuration - stays well under 20 pages/minute limit
SUPER_SAFE_CONFIG = CrawlConfig(
    max_pages=200,
    delay_between_requests=4.0,   # 4 seconds between requests (15 pages/minute max)
    max_concurrent_threads=1,     # Single thread only
    rate_limit_delay=300.0,       # 5 minute delay if rate limited
    retry_delay_base=30.0,        # 30 second base delay for retries
    max_retries=4
)

# Conservative configuration - recommended for most users
CONSERVATIVE_CONFIG = CrawlConfig(
    max_pages=500,
    delay_between_requests=8.0,   # 8 seconds between requests
    max_concurrent_threads=1,     # Single thread only
    rate_limit_delay=180.0,       # 3 minute delay if rate limited
    retry_delay_base=20.0,        # 20 second base delay for retries
    max_retries=4
)

# Moderate configuration - for users who want faster crawling
MODERATE_CONFIG = CrawlConfig(
    max_pages=1000,
    delay_between_requests=5.0,   # 5 seconds between requests (default)
    max_concurrent_threads=1,     # Single thread
    rate_limit_delay=120.0,       # 2 minute delay if rate limited
    retry_delay_base=15.0,        # 15 second base delay for retries
    max_retries=3
)

# Aggressive configuration - use with caution, higher risk of rate limiting
AGGRESSIVE_CONFIG = CrawlConfig(
    max_pages=2000,
    delay_between_requests=3.0,   # 3 seconds between requests
    max_concurrent_threads=2,     # Two threads
    rate_limit_delay=60.0,        # 1 minute delay if rate limited
    retry_delay_base=10.0,        # 10 second base delay for retries
    max_retries=3
)

# Testing configuration - for quick tests
TEST_CONFIG = CrawlConfig(
    max_pages=10,
    delay_between_requests=8.0,   # Conservative for testing
    max_concurrent_threads=1,
    rate_limit_delay=120.0,
    retry_delay_base=15.0,
    max_retries=2
)

def get_recommended_config():
    """Get the recommended configuration for most users"""
    return SUPER_SAFE_CONFIG

def get_config_by_speed(speed_level: str) -> CrawlConfig:
    """
    Get configuration by speed level
    
    Args:
        speed_level: 'ultra_safe', 'super_safe', 'conservative', 'moderate', 'aggressive', or 'test'
    
    Returns:
        CrawlConfig object
    """
    configs = {
        'ultra_safe': ULTRA_CONSERVATIVE_CONFIG,
        'super_safe': SUPER_SAFE_CONFIG,
        'conservative': CONSERVATIVE_CONFIG,
        'moderate': MODERATE_CONFIG,
        'aggressive': AGGRESSIVE_CONFIG,
        'test': TEST_CONFIG
    }
    
    return configs.get(speed_level.lower(), SUPER_SAFE_CONFIG)

# Usage examples:
"""
# Use recommended super-safe settings (stays under 20 pages/minute)
from crawler_config import get_recommended_config
from basketball_reference_crawler import BasketballReferenceCrawler

config = get_recommended_config()  # Uses SUPER_SAFE_CONFIG by default
crawler = BasketballReferenceCrawler(config)

# Or choose by speed level
config = get_config_by_speed('super_safe')    # 15 pages/minute max - RECOMMENDED
config = get_config_by_speed('ultra_safe')    # 4 pages/minute max - Ultra conservative
config = get_config_by_speed('conservative')  # 7.5 pages/minute - Very safe
crawler = BasketballReferenceCrawler(config)

# Custom configuration for staying under 20 pages/minute
custom_config = CrawlConfig(
    max_pages=200,
    delay_between_requests=4.0,   # 4+ seconds = max 15 pages/minute
    max_concurrent_threads=1,     # ALWAYS use 1 thread for rate limiting
    rate_limit_delay=600.0,       # 10 minute delay if rate limited
)
crawler = BasketballReferenceCrawler(custom_config)

# IMPORTANT: Basketball-Reference.com has a 20 pages/minute limit
# - Use 4+ second delays to stay under this limit
# - NEVER use multiple threads
# - Exceeding the limit results in 1-hour IP bans
""" 