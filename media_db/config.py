"""
Configuration for Media Database System
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Database configuration
MEDIA_DB_PATH = os.environ.get(
    'MEDIA_DB_PATH',
    str(BASE_DIR / 'instance' / 'media_database.db')
)
MEDIA_DB_URI = f'sqlite:///{MEDIA_DB_PATH}'

# Scraper configuration
OILLOCO_BASE_URL = 'https://oillocotv.biz'
OILLOCO_SERIES_LIST_URL = f'{OILLOCO_BASE_URL}/lista-completa-serie/'
OILLOCO_CATEGORY_URL = f'{OILLOCO_BASE_URL}/category/serie-tv/'

# User agent for requests
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Scraper settings
SCRAPER_DELAY_MIN = 2  # Minimum delay between requests (seconds)
SCRAPER_DELAY_MAX = 5  # Maximum delay between requests (seconds)
SCRAPER_TIMEOUT = 30   # Request timeout (seconds)
USE_SELENIUM = True    # Use Selenium for bot protection bypass

# Selenium settings
SELENIUM_HEADLESS = True
SELENIUM_CHROME_DRIVER_PATH = None  # Auto-detect if None
SELENIUM_PAGE_LOAD_TIMEOUT = 30

# Personal library settings
LIBRARY_PATHS = []  # User can configure multiple library paths
SUPPORTED_VIDEO_EXTENSIONS = [
    '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv',
    '.webm', '.m4v', '.mpg', '.mpeg', '.m2v', '.3gp'
]

# Episode matching settings
MATCH_THRESHOLD = 0.8  # Similarity threshold for fuzzy matching
EXTRACT_PATTERNS = [
    # Standard patterns for extracting show name, season, episode
    r'(.+?)[\.\s]S(\d+)E(\d+)',  # Show.Name.S01E01
    r'(.+?)[\.\s](\d+)x(\d+)',    # Show.Name.1x01
    r'(.+?)[\.\s]Season[\.\s](\d+)[\.\s]Episode[\.\s](\d+)',  # Show Name Season 1 Episode 1
]

# Logging configuration
LOG_LEVEL = os.environ.get('MEDIA_DB_LOG_LEVEL', 'INFO')
LOG_FILE = str(BASE_DIR / 'logs' / 'media_db.log')
