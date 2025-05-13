"""Error handlers for the application."""
from flask import render_template, request, jsonify, current_app
import logging
import traceback
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors."""
        if request.is_json or request.content_type == 'application/json':
            return jsonify(error=str(error)), 400
        return render_template('errors/400.html', error=error), 400
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors."""
        app.logger.warning(f"Forbidden access attempt: {request.path} - IP: {request.remote_addr}")
        if request.is_json or request.content_type == 'application/json':
            return jsonify(error="You don't have permission to access this resource"), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        if request.is_json or request.content_type == 'application/json':
            return jsonify(error="Resource not found"), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(429)
    def ratelimit_error(error):
        """Handle 429 Too Many Requests errors."""
        app.logger.warning(f"Rate limit exceeded: {request.path} - IP: {request.remote_addr}")
        if request.is_json or request.content_type == 'application/json':
            return jsonify(error="Too many requests, please try again later"), 429
        return render_template('errors/429.html'), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error."""
        # Log the error
        app.logger.error(f"Internal Server Error: {str(error)}")
        app.logger.error(traceback.format_exc())
        
        if request.is_json or request.content_type == 'application/json':
            if current_app.debug:
                return jsonify(error=str(error), traceback=traceback.format_exc()), 500
            return jsonify(error="An unexpected error occurred"), 500
        
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def unhandled_exception(error):
        """Handle unhandled exceptions."""
        # Get detailed request information for debugging
        request_info = {
            'path': request.path,
            'method': request.method,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'referrer': request.referrer
        }

        # Structured logging with request context
        app.logger.error(f"Unhandled Exception: {str(error)}")
        app.logger.error(f"Request info: {request_info}")
        app.logger.error(traceback.format_exc())

        # Add more debug info at debug level
        app.logger.debug(f"Request args: {request.args}")
        app.logger.debug(f"Request form data keys: {list(request.form.keys()) if request.form else 'None'}")

        # Log user info if available
        from flask_login import current_user
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            app.logger.debug(f"User context: {current_user.username} (ID: {current_user.id})")

        if isinstance(error, HTTPException):
            code = error.code
            app.logger.debug(f"HTTP Exception {code}: {error.description}")
        else:
            code = 500

        if request.is_json or request.content_type == 'application/json':
            if current_app.debug:
                return jsonify(error=str(error), traceback=traceback.format_exc()), code
            return jsonify(error="An unexpected error occurred"), code

        if current_app.debug and not isinstance(error, HTTPException):
            # In debug mode, show the traceback for non-HTTP exceptions
            return str(error), code

        # Log template rendering attempt
        app.logger.debug(f"Rendering error template for code {code}")
        return render_template('errors/generic.html', error=error), code

def log_security_event(app, event_type, message, user_id=None, ip=None, severity='WARNING'):
    """Log a security-related event."""
    # Get request information if available
    if not ip and request:
        ip = request.remote_addr
    
    # Format the log message
    log_message = f"SECURITY - {event_type}: {message}"
    if user_id:
        log_message += f" [User: {user_id}]"
    if ip:
        log_message += f" [IP: {ip}]"
    
    # Log with the appropriate severity
    if severity == 'CRITICAL':
        app.logger.critical(log_message)
    elif severity == 'ERROR':
        app.logger.error(log_message)
    elif severity == 'WARNING':
        app.logger.warning(log_message)
    elif severity == 'INFO':
        app.logger.info(log_message)
    else:
        app.logger.warning(log_message)  # Default to warning