"""
Configuration for Media Automation System
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Database
AUTOMATION_DB_PATH = os.environ.get(
    'AUTOMATION_DB_PATH',
    str(BASE_DIR / 'instance' / 'media_automation.db')
)
AUTOMATION_DB_URI = f'sqlite:///{AUTOMATION_DB_PATH}'

# JDownloader Configuration
JDOWNLOADER_EMAIL = os.environ.get('JDOWNLOADER_EMAIL', '')
JDOWNLOADER_PASSWORD = os.environ.get('JDOWNLOADER_PASSWORD', '')
JDOWNLOADER_DEVICE_NAME = os.environ.get('JDOWNLOADER_DEVICE_NAME', '')
JDOWNLOADER_APP_KEY = os.environ.get('JDOWNLOADER_APP_KEY', 'MediaAutomation')

# Source Sites
SOURCES = {
    'oillocotv': {
        'base_url': 'https://oillocotv.biz',
        'enabled': True,
        'priority': 1,
    },
    'crockdown': {
        'base_url': 'https://crockdown.com',
        'enabled': True,
        'priority': 2,
    }
}

# Monitoring
CHECK_INTERVAL_MINUTES = int(os.environ.get('CHECK_INTERVAL_MINUTES', 30))
RSS_CHECK_INTERVAL_MINUTES = int(os.environ.get('RSS_CHECK_INTERVAL_MINUTES', 15))
MAX_EPISODES_PER_CHECK = int(os.environ.get('MAX_EPISODES_PER_CHECK', 50))

# Download Settings
DOWNLOAD_FOLDER = os.environ.get('DOWNLOAD_FOLDER', '/downloads')
PROCESSING_FOLDER = os.environ.get('PROCESSING_FOLDER', '/downloads/processing')

# Library Settings
TV_LIBRARY_PATH = os.environ.get('TV_LIBRARY_PATH', '/media/tv')
LIBRARY_STRUCTURE = os.environ.get('LIBRARY_STRUCTURE', '{show}/{season}/{episode}')
# Supported formats: {show}, {season}, {season_number}, {episode}, {episode_number}, {title}, {quality}

# File Organization
AUTO_ORGANIZE = os.environ.get('AUTO_ORGANIZE', 'True').lower() == 'true'
DELETE_AFTER_ORGANIZE = os.environ.get('DELETE_AFTER_ORGANIZE', 'True').lower() == 'true'
MINIMUM_FILE_SIZE_MB = int(os.environ.get('MINIMUM_FILE_SIZE_MB', 50))

# Quality Preferences
QUALITY_ORDER = [
    '2160p', '1080p', '720p', '480p'
]
PREFERRED_QUALITY = os.environ.get('PREFERRED_QUALITY', '1080p')

# Episode Preferences
DOWNLOAD_SUBTITLED = os.environ.get('DOWNLOAD_SUBTITLED', 'True').lower() == 'true'
LANGUAGE_PREFERENCE = os.environ.get('LANGUAGE_PREFERENCE', 'ITA')  # ITA, ENG, MULTI

# Notifications
ENABLE_NOTIFICATIONS = os.environ.get('ENABLE_NOTIFICATIONS', 'True').lower() == 'true'
NOTIFICATION_METHODS = os.environ.get('NOTIFICATION_METHODS', 'email').split(',')

# Email Notifications
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 25))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False').lower() == 'true'
EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'media@automation.local')
EMAIL_TO = os.environ.get('EMAIL_TO', '').split(',')

# Webhook Notifications (Discord, Slack, etc.)
WEBHOOK_URLS = os.environ.get('WEBHOOK_URLS', '').split(',')

# Web Dashboard
DASHBOARD_PORT = int(os.environ.get('DASHBOARD_PORT', 5001))
DASHBOARD_HOST = os.environ.get('DASHBOARD_HOST', '0.0.0.0')
DASHBOARD_DEBUG = os.environ.get('DASHBOARD_DEBUG', 'False').lower() == 'true'

# Logging
LOG_LEVEL = os.environ.get('AUTOMATION_LOG_LEVEL', 'INFO')
LOG_FILE = str(BASE_DIR / 'logs' / 'automation.log')

# Scraper Settings
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
REQUEST_TIMEOUT = 30
REQUEST_DELAY_MIN = 2
REQUEST_DELAY_MAX = 5
USE_SELENIUM = True
SELENIUM_HEADLESS = True

# Advanced Settings
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get('MAX_CONCURRENT_DOWNLOADS', 3))
RETRY_FAILED_DOWNLOADS = os.environ.get('RETRY_FAILED_DOWNLOADS', 'True').lower() == 'true'
MAX_RETRY_ATTEMPTS = int(os.environ.get('MAX_RETRY_ATTEMPTS', 3))
BACKLOG_SEARCH_ENABLED = os.environ.get('BACKLOG_SEARCH_ENABLED', 'True').lower() == 'true'
BACKLOG_DAYS = int(os.environ.get('BACKLOG_DAYS', 7))
