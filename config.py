import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///snippets.db?mode=rw')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Cache configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))

    # Snippet settings
    MAX_SNIPPET_SIZE = int(os.environ.get('MAX_SNIPPET_SIZE', 100000))
    SNIPPETS_PER_PAGE = int(os.environ.get('SNIPPETS_PER_PAGE', 10))

    # Session settings
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('SESSION_DAYS', 14)) * 86400  # days to seconds
    REMEMBER_COOKIE_DURATION = int(os.environ.get('REMEMBER_DAYS', 30)) * 86400  # days to seconds
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', 3600))  # Session inactivity timeout (1 hour)

    # Feature toggles
    ENABLE_REGISTRATION = os.environ.get('ENABLE_REGISTRATION', 'True').lower() == 'true'
    ENABLE_PUBLIC_SNIPPETS = os.environ.get('ENABLE_PUBLIC_SNIPPETS', 'True').lower() == 'true'

    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour in seconds
    SESSION_COOKIE_SECURE = False  # Set to True only in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    BCRYPT_LOG_ROUNDS = int(os.environ.get('BCRYPT_LOG_ROUNDS', 12))

    # Password policy
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL = True

    # Rate limiting
    RATELIMIT_STORAGE_URI = os.environ.get('LIMITER_STORAGE_URI', 'memory://')
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STRATEGY = 'fixed-window'

    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'False').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@codesnippets.com')
    MAIL_MAX_EMAILS = int(os.environ.get('MAIL_MAX_EMAILS', 100))
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'

    # Set to True in development to log emails instead of sending them
    MAIL_DEBUG = os.environ.get('MAIL_DEBUG', 'False').lower() == 'true'

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 1024000))  # 1MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 10))
    LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    
    # Extreme logging configuration
    ENABLE_EXTREME_LOGGING = os.environ.get('ENABLE_EXTREME_LOGGING', 'False').lower() == 'true'
    EXTREME_LOG_DIR = os.environ.get('EXTREME_LOG_DIR', 'logs')
    EXTREME_LOG_MAX_BYTES = int(os.environ.get('EXTREME_LOG_MAX_BYTES', 10485760))  # 10MB
    EXTREME_LOG_BACKUP_COUNT = int(os.environ.get('EXTREME_LOG_BACKUP_COUNT', 20))
    EXTREME_LOG_LEVEL = os.environ.get('EXTREME_LOG_LEVEL', 'DEBUG')
    
    # Sensitive parameters that should never be logged in plain text
    SENSITIVE_PARAM_PATTERNS = [
        'password', 'secret', 'token', 'key', 'auth', 'credential',
        'private', 'security', 'hash', 'salt', 'pin', 'cipher',
        'credit_card', 'ssn', 'social', 'birth', 'phone'
    ]
    
    # Extreme logging feature flags
    LOG_FUNCTION_CALLS = True       # Log all function entry/exit
    LOG_VARIABLE_CHANGES = True     # Log all variable changes
    LOG_DB_OPERATIONS = True        # Log all database operations
    LOG_HTTP_REQUESTS = True        # Log HTTP request details
    LOG_PERFORMANCE = True          # Log performance metrics
    LOG_EXCEPTIONS = True           # Log detailed exception info
    STRUCTURED_LOGGING = True       # Use structured (JSON) logging
    LOG_CODE_BLOCKS = True          # Log execution of code blocks


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

    # In development, log emails instead of sending them
    MAIL_SUPPRESS_SEND = True
    MAIL_DEBUG = True
    
    # Enable extreme logging in development by default
    ENABLE_EXTREME_LOGGING = os.environ.get('ENABLE_EXTREME_LOGGING', 'True').lower() == 'true'


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

    # In production, ensure secure configurations
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Higher security settings for production
    BCRYPT_LOG_ROUNDS = 14  # Increase computational work for password hashing

    # Enforce HTTPS
    PREFERRED_URL_SCHEME = 'https'

    # Stricter rate limiting
    RATELIMIT_DEFAULT = "100 per day"
    RATELIMIT_STORAGE_URI = os.environ.get('LIMITER_STORAGE_URI', 'memory://')

    # SQL query logging disabled
    SQLALCHEMY_ECHO = False
    
    # Configure extreme logging for production
    ENABLE_EXTREME_LOGGING = os.environ.get('ENABLE_EXTREME_LOGGING', 'False').lower() == 'true'
    EXTREME_LOG_LEVEL = os.environ.get('EXTREME_LOG_LEVEL', 'INFO')  # Default to INFO level in production
    
    # In production, be more selective about what is logged to reduce overhead
    LOG_FUNCTION_CALLS = False      # Only log critical functions in production
    LOG_VARIABLE_CHANGES = False    # Don't log all variable changes
    LOG_CODE_BLOCKS = False         # Don't log all code blocks
    STRUCTURED_LOGGING = True       # Always use structured logging in production


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}