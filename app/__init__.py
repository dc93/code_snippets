from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
import logging
from logging.handlers import RotatingFileHandler
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()
cache = Cache()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def create_app(config_name='default'):
    """Application factory function."""
    from config import config

    # Create and configure the app
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions with app
    db.init_app(app)

    # Ensure instance directory exists and is writable
    if not os.path.exists(app.instance_path):
        try:
            os.makedirs(app.instance_path, mode=0o775)
        except Exception as e:
            app.logger.warning(f"Could not create instance directory: {str(e)}")

    # Check database readability/writability instead of trying to modify permissions
    db_path = os.path.join(app.instance_path, 'snippets.db')
    if os.path.exists(db_path):
        if not os.access(db_path, os.R_OK | os.W_OK):
            app.logger.warning(f"Database file is not readable/writable: {db_path}")

    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Configure CSRF error handler
    from flask_wtf.csrf import CSRFError
    from flask import render_template

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        app.logger.warning(f"CSRF Error: {str(e)}")
        return render_template('errors/400.html', error="CSRF validation failed. Please try again."), 400

    # Configure login settings
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'

    # Initialize mail
    try:
        from flask_mail import Mail
        mail = Mail(app)
        # Update the mail instance in utils module to ensure it's properly initialized
        from app.utils import set_mail_instance
        set_mail_instance(mail)
        app.logger.info("Flask-Mail initialized successfully")
    except ImportError:
        app.logger.warning("Flask-Mail not installed, email functionality will be disabled")
    except Exception as e:
        app.logger.warning(f"Failed to initialize Flask-Mail: {str(e)}")

    # Register blueprints
    from app.routes import main, auth, snippets
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(snippets)

    # Configure security
    from app.security import configure_security
    configure_security(app)

    # Register error handlers
    from app.error_handlers import register_error_handlers
    register_error_handlers(app)

    # Configure performance optimizations
    from app.performance import configure_performance
    configure_performance(app)

    # Initialize extreme debugging system
    if app.config.get('ENABLE_EXTREME_LOGGING', False) or app.debug:
        try:
            # Initialize extreme debugging and comprehensive logging
            from app.extreme_debugging_plan import init_extreme_debugging
            app = init_extreme_debugging(app)
            app.logger.info("Extreme debugging and comprehensive logging system initialized")
            
            # Configure database logging
            from app.extreme_debug_implementation import DatabaseLogger
            DatabaseLogger.setup(db, app)
            app.logger.info("Database extreme logging configured")
            
            # Set up request context logging
            from app.extreme_debug_implementation import log_request_context
            log_request_context(app)
            app.logger.info("Request context extreme logging configured")
            
            # Register examples blueprint if in debug mode
            if app.debug:
                try:
                    from app.extreme_logging_examples import examples_bp
                    app.register_blueprint(examples_bp, url_prefix='/debug/examples')
                    app.logger.info("Extreme logging examples blueprint registered")
                except Exception as e:
                    app.logger.error(f"Failed to register examples blueprint: {str(e)}")
        except Exception as e:
            app.logger.error(f"Failed to initialize extreme debugging system: {str(e)}", exc_info=True)
            
            # Fall back to standard logging configuration
            app.logger.warning("Falling back to standard logging configuration")
            configure_standard_logging(app)
    else:
        # Configure standard logging
        configure_standard_logging(app)

    return app

def configure_standard_logging(app):
    """Configure standard logging for the application."""
    # Ensure log directory exists
    log_dir = os.path.dirname(app.config.get('LOG_FILE', 'logs/code_snippets.log'))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Set up the file logger with more detailed format
    file_handler = RotatingFileHandler(
        app.config.get('LOG_FILE', 'logs/code_snippets.log'),
        maxBytes=app.config.get('LOG_MAX_BYTES', 10240),
        backupCount=app.config.get('LOG_BACKUP_COUNT', 10)
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))

    # Get log level from config
    log_level_name = app.config.get('LOG_LEVEL', 'DEBUG')
    log_level = getattr(logging, log_level_name.upper())

    file_handler.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(log_level)

    # Create a dedicated debug logger for detailed debugging
    debug_handler = RotatingFileHandler(
        os.path.join(log_dir, 'debug.log'),
        maxBytes=app.config.get('LOG_MAX_BYTES', 10240),
        backupCount=5
    )
    debug_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: [%(module)s:%(funcName)s:%(lineno)d] %(message)s'
    ))
    debug_handler.setLevel(logging.DEBUG)

    # Only add debug handler if we're not in production or explicitly asked for debug
    if app.debug or log_level_name.upper() == 'DEBUG':
        app.logger.addHandler(debug_handler)

    # Log application startup with version info
    app.logger.info('CodeSnippets startup - Debug logging enabled')