"""
Flask application factory for Media Automation Dashboard
"""
from flask import Flask
from pathlib import Path
import logging

from ..config import DASHBOARD_PORT, DASHBOARD_HOST, DASHBOARD_DEBUG

logger = logging.getLogger(__name__)


def create_app(config=None):
    """
    Create and configure the Flask application.

    Args:
        config: Optional configuration dictionary

    Returns:
        Flask application instance
    """
    # Create Flask app
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )

    # Configure app
    app.config['SECRET_KEY'] = 'media-automation-secret-key-change-in-production'
    app.config['JSON_SORT_KEYS'] = False

    if config:
        app.config.update(config)

    # Configure logging
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Register blueprints
    from .routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Register template filters
    register_template_filters(app)

    logger.info("Media Automation Dashboard created")

    return app


def register_template_filters(app):
    """Register custom Jinja2 template filters."""

    @app.template_filter('filesize')
    def filesize_filter(size_bytes):
        """Format file size in human-readable format."""
        if size_bytes is None:
            return 'N/A'

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    @app.template_filter('duration')
    def duration_filter(seconds):
        """Format duration in human-readable format."""
        if seconds is None:
            return 'N/A'

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    @app.template_filter('status_badge')
    def status_badge_filter(status):
        """Get Bootstrap badge class for status."""
        status_map = {
            'wanted': 'secondary',
            'searching': 'info',
            'queued': 'primary',
            'downloading': 'warning',
            'downloaded': 'success',
            'completed': 'success',
            'failed': 'danger',
            'ignored': 'dark'
        }
        return status_map.get(status.lower(), 'secondary')


def run_dashboard(host=None, port=None, debug=None):
    """
    Run the dashboard server.

    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Debug mode
    """
    app = create_app()

    host = host or DASHBOARD_HOST
    port = port or DASHBOARD_PORT
    debug = debug if debug is not None else DASHBOARD_DEBUG

    logger.info(f"Starting Media Automation Dashboard on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
