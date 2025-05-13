from flask import request, redirect, url_for, g, session, current_app
from functools import wraps
import re
import time
import secrets
from werkzeug.http import parse_date, http_date
from datetime import datetime, timedelta
import ipaddress

def configure_security(app):
    """Configure security features for the Flask application."""
    @app.before_request
    def before_request():
        # Store request start time for performance tracking
        g.start = time.time()
        
        # Force HTTPS in production
        if not app.debug and not app.testing:
            if request.headers.get('X-Forwarded-Proto') == 'http':
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)
        
        # Check for session expiry
        if 'user_id' in session and 'last_active' in session:
            last_active = datetime.fromtimestamp(session['last_active'])
            timeout = timedelta(seconds=app.config.get('SESSION_TIMEOUT', 3600))
            if datetime.utcnow() - last_active > timeout:
                # Session has expired
                session.clear()
        
        # Update last active time
        if 'user_id' in session:
            session['last_active'] = time.time()
        
        # Add CSRF token to session if not present
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)

    @app.after_request
    def add_security_headers(response):
        # Add security headers if not in debug mode
        if not app.debug and not app.testing:
            # Content Security Policy (CSP)
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' https://cdn.jsdelivr.net; "
                "style-src 'self' https://cdn.jsdelivr.net; "
                "img-src 'self' data:; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self';"
            )
            
            # Prevent clickjacking
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            
            # XSS protection
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # MIME type sniffing protection
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
            # Referrer policy
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Feature Policy/Permissions Policy
            response.headers['Permissions-Policy'] = (
                'camera=(), microphone=(), geolocation=(), interest-cohort=()'
            )
            
            # HSTS (HTTP Strict Transport Security)
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            # Set secure cookie policy
            if 'Set-Cookie' in response.headers:
                # Only add Secure flag in production or when using HTTPS
                if request.is_secure or 'X-Forwarded-Proto' in request.headers and request.headers['X-Forwarded-Proto'] == 'https':
                    response.headers['Set-Cookie'] = response.headers['Set-Cookie'] + '; SameSite=Lax; Secure'
                else:
                    # For HTTP in development, don't add Secure flag
                    response.headers['Set-Cookie'] = response.headers['Set-Cookie'] + '; SameSite=Lax'
        
        # For all responses, add performance timing for debugging
        if hasattr(g, 'start'):
            response_time = time.time() - g.start
            response.headers['X-Response-Time'] = f"{response_time:.4f} seconds"
        
        return response

def require_csrf(func_or_request):
    """CSRF token validation.

    Can be used as:
    1. Function: require_csrf(request) -> returns boolean
    2. Decorator: @require_csrf -> decorates a view function

    Args:
        func_or_request: Either a Flask request object or a view function

    Returns:
        Boolean (True if valid) or decorated function
    """
    # When used as a regular function to validate a request
    if hasattr(func_or_request, 'form') and hasattr(func_or_request, 'method'):
        request_obj = func_or_request
        if request_obj.method == 'POST':
            csrf_token = request_obj.form.get('csrf_token')
            return csrf_token and csrf_token == session.get('csrf_token')
        return True  # Non-POST requests don't need CSRF validation

    # When used as a decorator
    @wraps(func_or_request)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            csrf_token = request.form.get('csrf_token')
            if not csrf_token or csrf_token != session.get('csrf_token'):
                return redirect(url_for('main.index'))
        return func_or_request(*args, **kwargs)
    return decorated_function

def is_safe_url(target):
    """Check if a URL is safe to redirect to.

    Args:
        target: The URL to check

    Returns:
        Boolean indicating if the URL is safe to redirect to
    """
    from urllib.parse import urlparse, urljoin, unquote
    from flask import request, current_app

    if not target:
        return False

    # Decode URL before checking to prevent encoding bypass attacks
    target = unquote(target)

    # Check for dangerous schemes early before any parsing
    dangerous_schemes = ['javascript:', 'data:', 'vbscript:', 'file:', 'ftp:', 'mailto:', 'tel:']
    if any(scheme in target.lower() for scheme in dangerous_schemes):
        return False

    # Get host from request or use a default
    host_url = None
    if request:
        host_url = request.host_url

    if not host_url:
        # Fallback if outside request context
        try:
            server_name = current_app.config.get('SERVER_NAME', 'localhost')
            server_protocol = current_app.config.get('PREFERRED_URL_SCHEME', 'https')
            if not server_name.startswith(('http://', 'https://')):
                host_url = f"{server_protocol}://{server_name}/"
            else:
                host_url = server_name if server_name.endswith('/') else server_name + '/'
        except RuntimeError:
            # Fallback if no app context
            host_url = 'https://localhost/'

    # Parse the target URL
    parse_target = urlparse(target)

    # Completely relative URLs with no scheme or netloc (like '/path')
    if not parse_target.netloc and not parse_target.scheme:
        # Construct full URL for checking
        target_url = urljoin(host_url, target)
        parse_target = urlparse(target_url)
    else:
        # Target has scheme or netloc
        target_url = target

    # Parse host URL for comparison
    parse_host = urlparse(host_url)

    # Only allow HTTP or HTTPS URLs
    if parse_target.scheme and parse_target.scheme not in ('http', 'https'):
        return False

    # Domain validation - compare the host netloc with target netloc
    # Also check for non-standard ports which could bypass safeguards
    if parse_target.netloc and parse_target.netloc != parse_host.netloc:
        # For extra security, validate domain structure
        host_domain = parse_host.netloc.split(':')[0] if ':' in parse_host.netloc else parse_host.netloc
        target_domain = parse_target.netloc.split(':')[0] if ':' in parse_target.netloc else parse_target.netloc

        # Additional check: Is the target domain a subdomain of our domain?
        # This is occasionally desired, but can be dangerous if not expected
        is_subdomain = target_domain.endswith('.' + host_domain)

        # By default, reject different domains and subdomains
        # If subdomain redirection is needed, a configuration option should be added
        return False

    # More robust path traversal prevention
    # Normalize path to catch various traversal attempts
    path_segments = parse_target.path.split('/')
    normalized_path = []

    for segment in path_segments:
        if segment == '..':
            if normalized_path:
                normalized_path.pop()  # Go up one level
            else:
                return False  # Trying to go above root - suspicious
        elif segment not in ('', '.'):
            normalized_path.append(segment)

    # Check for other potential issues in the path
    path_str = '/'.join(normalized_path)
    if '\\' in path_str:  # Backslash could be used in path traversal attempts
        return False

    # Check for suspicious encoded characters that might be used to bypass filters
    suspicious_sequences = ['%2e%2e', '%2e.', '.%2e']  # Various encodings of '..'
    if any(seq in target.lower() for seq in suspicious_sequences):
        return False

    # Check URL components like query parameters and fragments for malicious content
    if parse_target.query:
        # Check query parameters for suspicious content
        if any(scheme in parse_target.query.lower() for scheme in dangerous_schemes):
            return False

    if parse_target.fragment:
        # Check fragments for suspicious content
        if any(scheme in parse_target.fragment.lower() for scheme in dangerous_schemes):
            return False

    return True

def validate_ip(ip_str):
    """Validate if a string is a proper IP address."""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def password_meets_requirements(password):
    """Check if a password meets our security requirements."""
    # At least 8 characters
    if len(password) < 8:
        return False
    
    # Check for at least 3 of the 4 requirements:
    has_lowercase = bool(re.search(r'[a-z]', password))
    has_uppercase = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    requirements_met = sum([has_lowercase, has_uppercase, has_digit, has_special])
    return requirements_met >= 3

def sanitize_input(string):
    """Simple function to sanitize user input."""
    if not string:
        return ""
    
    # Remove any HTML tags
    string = re.sub(r'<[^>]*>', '', string)
    
    # Escape special characters
    escape_chars = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
        '\\': '&#x5C;',
    }
    
    for char, replacement in escape_chars.items():
        string = string.replace(char, replacement)
    
    return string