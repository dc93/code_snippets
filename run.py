import os
import sys
from app import create_app, db
from app.models import User, Snippet, Tag
from flask_migrate import upgrade
from dotenv import load_dotenv
from app.static_middleware import StaticFileMiddleware

# Load environment variables
load_dotenv()

# Get config from environment
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

# Apply static file middleware for production
if not app.debug and not app.testing:
    app.wsgi_app = StaticFileMiddleware(
        app.wsgi_app,
        static_folder=os.path.join(os.path.dirname(__file__), 'app', 'static'),
        cache_timeout=int(os.environ.get('STATIC_CACHE_TIMEOUT', 86400))
    )

# Create database tables if needed
with app.app_context():
    """Initialize database and create tables if not exists."""
    db.create_all()

# Shell context processor
@app.shell_context_processor
def make_shell_context():
    """Add database models to shell context."""
    return {
        'db': db,
        'User': User,
        'Snippet': Snippet,
        'Tag': Tag
    }

# Performance monitoring in debug mode
if app.debug:
    @app.after_request
    def after_request(response):
        """Log all requests in debug mode."""
        from flask import request, g
        import time

        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            app.logger.debug(f"{request.method} {request.path} {response.status_code} - {elapsed:.4f}s")

        return response

    @app.before_request
    def before_request():
        """Start timing requests in debug mode."""
        import time
        from flask import g
        g.start_time = time.time()

if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # If running with gunicorn (production)
    if 'gunicorn' in sys.modules:
        # Apply additional production optimizations
        app.config['PROPAGATE_EXCEPTIONS'] = False

        # Ensure proper proxy settings
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        app.config['PROXY_FIX'] = True
    else:
        # Development server
        app.run(host=host, port=port, debug=debug)