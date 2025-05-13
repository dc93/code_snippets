"""Performance optimization utilities for the application."""
from flask import request, current_app, make_response
from functools import wraps
import time
import gzip
import io
import hashlib
from werkzeug.http import parse_accept_header
from app import cache

def configure_performance(app):
    """Configure performance optimizations for the Flask application."""

    # Response compression
    @app.after_request
    def compress_response(response):
        """Compress response if client supports it."""
        # Don't compress if response is already compressed or shouldn't be
        if (response.direct_passthrough or
            response.status_code < 200 or
            response.status_code >= 300 or
            'Content-Encoding' in response.headers or
            not response.content_length or
            response.content_length < 500):  # Don't compress small responses
            return response

        # Check if client accepts gzip encoding
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if 'gzip' not in accept_encoding.lower():
            return response

        # Check if content should be compressed based on mime type
        content_type = response.content_type.lower() if response.content_type else ''
        compressible_types = [
            'text/html', 'text/css', 'text/plain', 'text/xml', 'text/javascript',
            'application/json', 'application/javascript', 'application/xml',
            'application/xhtml+xml', 'application/vnd.ms-fontobject',
            'application/x-font-ttf', 'application/x-font-opentype',
            'application/vnd.ms-opentype', 'image/svg+xml'
        ]

        if not any(t in content_type for t in compressible_types):
            return response

        # Dynamically adjust compression level based on response size
        if response.content_length < 5000:  # Small responses - faster compression
            compression_level = 1
        elif response.content_length > 100000:  # Large responses - better compression
            compression_level = 6
        else:  # Medium responses - balanced
            compression_level = 3

        # Compress the response
        compressed_data = io.BytesIO()
        with gzip.GzipFile(fileobj=compressed_data, mode='wb', compresslevel=compression_level) as f:
            f.write(response.get_data())

        # Only use compressed data if it's actually smaller
        compressed_value = compressed_data.getvalue()
        if len(compressed_value) < response.content_length:
            response.set_data(compressed_value)
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Length'] = len(response.get_data())
            response.headers['Vary'] = 'Accept-Encoding'

        return response

    # Performance tracking
    @app.before_request
    def start_timer():
        """Start timer for request."""
        request._start_time = time.time()

    @app.after_request
    def log_performance(response):
        """Log request performance."""
        if hasattr(request, '_start_time'):
            request_duration = time.time() - request._start_time

            # Only log in debug mode or for slow requests to reduce noise
            if current_app.debug:
                app.logger.debug(f'Request to {request.path} took {request_duration:.4f}s')
                response.headers['X-Response-Time'] = f'{request_duration:.4f}s'

            # Log slow requests - threshold depends on request type
            slow_threshold = 1.0  # Default 1 second

            # Adjust threshold based on request type
            if request.path.startswith('/static/'):
                slow_threshold = 0.5  # Static files should be fast
            elif request.method == 'POST':
                slow_threshold = 2.0  # POST requests might take longer

            if request_duration > slow_threshold:
                app.logger.warning(
                    f'Slow request: {request.method} {request.path} '
                    f'took {request_duration:.4f}s (limit: {slow_threshold:.1f}s)'
                )

        return response

    # Cache configuration helper - set frequently used values
    app.config.setdefault('CACHE_DEFAULT_TIMEOUT', 300)

    # Set server-timing header in debug mode for performance analysis
    if app.debug:
        @app.after_request
        def add_server_timing(response):
            if hasattr(request, '_start_time'):
                total_time = (time.time() - request._start_time) * 1000  # ms
                response.headers['Server-Timing'] = f'total;dur={total_time:.0f}'
            return response

    # Return configured app
    return app

def cache_control(max_age=0, public=False, must_revalidate=True, etag_data=None):
    """Decorator to set Cache-Control header for a view with optional ETag support.

    Args:
        max_age: Maximum cache age in seconds
        public: Whether the cache is public (True) or private (False)
        must_revalidate: Whether clients must revalidate stale cache entries
        etag_data: Function that returns data to use for ETag generation

    Returns:
        Decorated view function with cache control headers
    """
    def decorator(view):
        @wraps(view)
        def decorated_function(*args, **kwargs):
            # Check for conditional requests if etag_data provided
            if etag_data:
                data = etag_data(*args, **kwargs)
                etag = etag_for(data)

                # Handle If-None-Match for conditional requests
                if_none_match = request.headers.get('If-None-Match')
                if if_none_match and if_none_match == etag:
                    response = make_response('', 304)  # Not Modified
                    return response

            # Get the regular response
            response = view(*args, **kwargs)

            # Set cache-control headers
            cache_control_value = []
            if public:
                cache_control_value.append('public')
            else:
                cache_control_value.append('private')

            if max_age > 0:
                cache_control_value.append(f'max-age={max_age}')

            if must_revalidate:
                cache_control_value.append('must-revalidate')

            # Set ETag if etag_data provided
            if etag_data and hasattr(response, 'get_data'):
                etag = etag_for(response.get_data())
                response.headers['ETag'] = etag

            response.headers['Cache-Control'] = ', '.join(cache_control_value)
            return response
        return decorated_function
    return decorator

def etag_for(data):
    """Generate ETag for data.

    Args:
        data: The data to generate an ETag for (str, bytes, or an object with __str__)

    Returns:
        String containing the ETag hash
    """
    if data is None:
        return None

    if not isinstance(data, (str, bytes)):
        data = str(data)

    if isinstance(data, str):
        data = data.encode('utf-8')

    return hashlib.sha256(data).hexdigest()

def memoize_with_timeout(timeout=300):
    """Cache function results with a timeout.

    This provides a simpler alternative to the flask-caching decorator
    for functions that don't need the full power of the cache extension.

    Args:
        timeout: Cache timeout in seconds

    Returns:
        Decorated function with memoization
    """
    def decorator(f):
        # Create cache dict for this function
        cache_dict = {}

        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Create cache key from function args and kwargs
            key_parts = [str(arg) for arg in args]
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = f.__name__ + "_" + "_".join(key_parts)

            # Get from cache if available and not expired
            if cache_key in cache_dict:
                result, timestamp = cache_dict[cache_key]
                if time.time() - timestamp < timeout:
                    return result

            # Compute new result and cache it
            result = f(*args, **kwargs)
            cache_dict[cache_key] = (result, time.time())

            # Cleanup old entries (only occasionally)
            if len(cache_dict) > 100:  # arbitrary threshold
                now = time.time()
                expired_keys = [k for k, (_, ts) in cache_dict.items()
                              if now - ts > timeout]
                for key in expired_keys:
                    del cache_dict[key]

            return result
        return decorated_function
    return decorator

def cache_with_key_function(timeout=300, key_prefix='view', unless=None, key_function=None,
                     safe_for_anonymous=True, hash_keys=True, cache_none=False):
    """Enhanced caching decorator with flexible key function.

    This provides an enhanced version of the flask-caching decorator
    with support for custom key functions and improved error handling.

    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache keys
        unless: Function that returns True if caching should be skipped
        key_function: Function to generate a custom cache key
        safe_for_anonymous: Whether to cache for anonymous users (default: True)
        hash_keys: Whether to hash long keys (default: True)
        cache_none: Whether to cache None results (default: False)

    Returns:
        Decorated view function with caching
    """
    def decorator(view):
        @wraps(view)
        def decorated_function(*args, **kwargs):
            # Import in function to avoid circular imports
            from flask import has_request_context, request, current_app

            # Initialize
            cache_key = None
            skip_cache = False

            # Define a safe way to access the current user
            def get_current_user_safely():
                try:
                    # Only attempt to import and use Flask-Login if we're in a request context
                    if has_request_context():
                        from flask_login import current_user
                        return current_user
                    return None
                except (ImportError, RuntimeError):
                    # Handle case where Flask-Login is not installed or app context issues
                    return None

            # Skip the cache but still execute the view if anything fails
            def execute_uncached():
                return view(*args, **kwargs)

            try:
                # Skip caching if the 'unless' function returns True
                if unless is not None:
                    try:
                        if unless():
                            return execute_uncached()
                    except Exception as e:
                        current_app.logger.warning(f"Cache 'unless' function failed: {str(e)}")
                        # Continue with caching since unless check failed

                # Skip caching if we don't have a request context
                if not has_request_context():
                    current_app.logger.debug("No request context available, skipping cache")
                    return execute_uncached()

                # Get current user safely for later use
                current_user = get_current_user_safely()

                # Skip caching for authenticated users if not safe_for_anonymous
                if not safe_for_anonymous and current_user and not hasattr(current_user, 'is_authenticated'):
                    current_app.logger.debug("Skipping cache for authenticated user in unsafe mode")
                    return execute_uncached()

                # Try to generate cache key using the provided key_function
                if key_function is not None:
                    try:
                        cache_key = key_function(*args, **kwargs)
                        # Validate the returned key
                        if not isinstance(cache_key, str):
                            current_app.logger.warning(f"Custom key_function returned non-string: {type(cache_key)}")
                            cache_key = str(cache_key)
                    except Exception as e:
                        current_app.logger.warning(f"Custom key_function failed: {str(e)}")
                        # Fall back to default key generation
                        cache_key = None

                # Generate default cache key if needed
                if cache_key is None:
                    try:
                        # Base key using view name
                        cache_key = f"{key_prefix}_{view.__module__}.{view.__name__}"

                        # Add query string parameters to key
                        if request.args:
                            args_str = "_".join(f"{k}={v}" for k, v in sorted(request.args.items(multi=True)))
                            cache_key += f"_args({args_str})"

                        # Add route parameters
                        if request.view_args:
                            view_args_str = "_".join(f"{k}={v}" for k, v in sorted(request.view_args.items()))
                            cache_key += f"_route({view_args_str})"

                        # Add request method
                        cache_key += f"_method({request.method})"

                        # Add user identifier for personalized content
                        if current_user is not None:
                            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                                # For authenticated users, add user ID
                                if hasattr(current_user, 'id'):
                                    cache_key += f"_user({current_user.id})"
                                else:
                                    # If user has no ID, use a non-specific authenticated marker
                                    cache_key += "_user(auth)"
                            else:
                                # For anonymous users
                                cache_key += "_user(anon)"
                    except Exception as e:
                        current_app.logger.warning(f"Error generating default cache key: {str(e)}")
                        # If default key generation fails, skip caching
                        return execute_uncached()

                # Ensure the cache key is valid and not too long
                try:
                    # Hash long keys if enabled
                    if hash_keys and len(cache_key) > 250:
                        import hashlib
                        # Include both a hash and the original prefix for readability in logs
                        original_prefix = cache_key.split('_')[0] if '_' in cache_key else key_prefix
                        hashed_part = hashlib.sha256(cache_key.encode('utf-8')).hexdigest()
                        cache_key = f"{original_prefix}_{hashed_part}"
                except Exception as e:
                    current_app.logger.warning(f"Error processing cache key: {str(e)}")
                    # If key processing fails, skip caching
                    return execute_uncached()

                # Try to get response from cache
                cached_response = None
                try:
                    if cache:  # Check if cache is initialized
                        cached_response = cache.get(cache_key)
                        if cached_response is not None:
                            current_app.logger.debug(f"Cache hit for key: {cache_key[:50]}...")
                            return cached_response
                        else:
                            current_app.logger.debug(f"Cache miss for key: {cache_key[:50]}...")
                    else:
                        current_app.logger.warning("Cache not initialized")
                        return execute_uncached()
                except Exception as e:
                    current_app.logger.warning(f"Cache retrieval failed: {str(e)}")
                    # Continue without caching if retrieval fails

                # Execute the view function to get the response
                response = view(*args, **kwargs)

                # Cache the response if appropriate
                try:
                    if cache:  # Verify cache is available
                        # Verify the response has the expected attributes for a response object
                        is_cacheable = (
                            hasattr(response, 'status_code') and
                            200 <= response.status_code < 300 and
                            (cache_none or response is not None)
                        )

                        if is_cacheable:
                            cache.set(cache_key, response, timeout=timeout)
                            current_app.logger.debug(f"Cached response with key: {cache_key[:50]}...")
                except Exception as e:
                    current_app.logger.warning(f"Cache storage failed: {str(e)}")
                    # Continue without caching if storage fails

                return response

            except Exception as e:
                # Catch-all for any unexpected errors to ensure the view still works
                current_app.logger.error(f"Unexpected error in cache_with_key_function: {str(e)}", exc_info=True)
                return execute_uncached()

        return decorated_function
    return decorator

def optimize_query(query, page=None, per_page=None, order_by=None, max_per_page=100):
    """Optimize a SQLAlchemy query with improved performance.

    Args:
        query: The SQLAlchemy query to optimize
        page: The page number (1-indexed)
        per_page: Number of items per page
        order_by: Column(s) to order by
        max_per_page: Maximum allowed items per page

    Returns:
        Optimized query object
    """
    from sqlalchemy.orm import joinedload, contains_eager, selectinload
    from sqlalchemy import func
    from flask import current_app
    import inspect

    # If query is None, return early to avoid errors
    if query is None:
        current_app.logger.warning("optimize_query received None query")
        return query

    # Store the original query to return in case of error
    original_query = query

    try:
        # Apply eager loading for common relationships if query has entities
        # Check if query has primary entity safely
        if not hasattr(query, '_primary_entity'):
            current_app.logger.debug("Query has no _primary_entity attribute")
        elif query._primary_entity is None:
            current_app.logger.debug("Query _primary_entity is None")
        elif not hasattr(query._primary_entity, 'entity'):
            current_app.logger.debug("Query _primary_entity has no entity attribute")
        else:
            # We have a valid entity, proceed with optimizations
            entity = query._primary_entity.entity

            # Safe entity name check
            entity_name = None
            if hasattr(entity, '__name__'):
                entity_name = entity.__name__
            elif hasattr(entity, '__class__') and hasattr(entity.__class__, '__name__'):
                entity_name = entity.__class__.__name__

            if entity_name == 'Snippet':
                # Check if we're already joining to related tables
                # Initialize flags for joins
                has_tags_join = False
                has_author_join = False

                # Check for join entities safely
                try:
                    if hasattr(query, '_join_entities') and query._join_entities:
                        # Create a safe list of join entities
                        joins = []
                        for j in query._join_entities:
                            if hasattr(j, 'entity'):
                                joins.append(j)

                        # Check for existing joins
                        for j in joins:
                            if not hasattr(j, 'entity') or not hasattr(j.entity, '__name__'):
                                continue

                            join_entity_name = j.entity.__name__
                            if join_entity_name == 'Tag':
                                has_tags_join = True
                            elif join_entity_name == 'User':
                                has_author_join = True
                except Exception as e:
                    current_app.logger.warning(f"Error checking join entities: {str(e)}")

                # Apply eager loading for Snippet->tags relation
                if hasattr(entity, 'tags'):
                    try:
                        # Determine the best loading strategy
                        if has_tags_join:
                            query = query.options(contains_eager(entity.tags))
                        else:
                            # Use selectinload for collections which is more efficient than joinedload
                            # for "many" relationships
                            query = query.options(selectinload(entity.tags))
                    except Exception as e:
                        current_app.logger.warning(f"Failed to apply eager loading for tags: {str(e)}")
                else:
                    current_app.logger.debug("Entity does not have tags relationship")

                # Apply eager loading for Snippet->author relation
                if hasattr(entity, 'author'):
                    try:
                        # Use appropriate loading strategy based on joins
                        if has_author_join:
                            query = query.options(contains_eager(entity.author))
                        else:
                            # For single object references, joinedload is appropriate
                            query = query.options(joinedload(entity.author))
                    except Exception as e:
                        current_app.logger.warning(f"Failed to apply eager loading for author: {str(e)}")
                else:
                    current_app.logger.debug("Entity does not have author relationship")

        # Apply ordering if specified
        if order_by is not None:
            try:
                query = query.order_by(order_by)
            except Exception as e:
                current_app.logger.warning(f"Failed to apply order_by: {str(e)}")
                # Continue with query without ordering

        # Apply pagination if specified
        if page is not None or per_page is not None:
            try:
                # Default values for pagination if not provided
                if page is None:
                    page = 1
                if per_page is None:
                    per_page = 10

                # Convert to integers and validate
                try:
                    page = int(page)
                    per_page = int(per_page)
                except (TypeError, ValueError) as e:
                    current_app.logger.warning(f"Pagination parameter conversion error: {str(e)}")
                    page = 1
                    per_page = 10

                # Ensure parameters are within reasonable bounds
                page = max(1, page)  # Page should be at least 1
                per_page = max(1, min(per_page, max_per_page))  # Per page between 1 and max_per_page

                # Apply pagination
                query = query.limit(per_page).offset((page - 1) * per_page)
            except Exception as e:
                current_app.logger.warning(f"Failed to apply pagination: {str(e)}")
                # Continue with query without pagination

    except Exception as e:
        current_app.logger.error(f"Unexpected error in optimize_query: {str(e)}", exc_info=True)
        # If a critical error occurs, return the original query
        return original_query

    # Return the optimized query
    return query