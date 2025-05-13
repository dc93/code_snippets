"""Database optimization utilities."""
from flask import current_app, request
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time
import logging
import functools
from app import db

# Configure query performance logging
logger = logging.getLogger('db.performance')

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log query execution time - start timer."""
    conn.info.setdefault('query_start_time', []).append(time.time())

    # Add the URL and user info to the connection for logging context
    from flask import request, has_request_context
    from flask_login import current_user

    # Set a flag to prevent recursive calls
    if getattr(conn, '_in_user_check', False):
        return

    try:
        if has_request_context():
            conn.info.setdefault('request_context', {})
            conn.info['request_context']['path'] = request.path

            # Avoid recursion by setting a flag
            conn._in_user_check = True

            # Check for user authentication
            user_info = 'anonymous'
            if hasattr(current_user, 'is_authenticated'):
                is_authenticated = current_user.is_authenticated
                if is_authenticated and hasattr(current_user, 'username'):
                    user_info = current_user.username

            conn.info['request_context']['user'] = user_info
    finally:
        # Always reset the flag
        conn._in_user_check = False

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log query execution time - end timer and log."""
    total = time.time() - conn.info['query_start_time'].pop()

    # Get context info if available
    context_info = ""
    if 'request_context' in conn.info:
        ctx = conn.info['request_context']
        context_info = f" [Path: {ctx.get('path', 'N/A')}, User: {ctx.get('user', 'N/A')}]"

    # Truncate long statements for logs
    statement_short = statement[:500] + "..." if len(statement) > 500 else statement

    # Log based on query execution time thresholds
    if total > 0.5:  # Very slow queries (>500ms)
        logger.warning(f"VERY SLOW QUERY: {total:.3f}s{context_info}\n{statement}\nParameters: {parameters}")
    elif total > 0.1:  # Slow queries (>100ms)
        logger.warning(f"Slow Query: {total:.3f}s{context_info}\n{statement_short}\nParameters: {parameters}")
    elif current_app.debug:
        # For debug mode, log all queries but add more detail for anything >20ms
        if total > 0.02:
            logger.debug(f"Query: {total:.3f}s{context_info}\n{statement_short}")
        else:
            # Only log the query time and type for very fast queries to reduce log size
            query_type = statement.split()[0] if statement else "Unknown"
            logger.debug(f"Query: {total:.3f}s - {query_type}")

def db_hit_limit(f):
    """Decorator to limit and monitor database hits.

    This decorator tracks the number of database queries executed within a function
    and logs warnings when the number of queries exceeds a configurable threshold.

    Args:
        f: The function to decorate

    Returns:
        Decorated function with query counting
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Initialize counter for this request
        query_count = 0

        # Store original execute method
        old_execute = db.engine.execute

        def execute_wrapper(*exec_args, **exec_kwargs):
            """Wrap the execute method to count queries."""
            nonlocal query_count
            query_count += 1

            # Log excessive queries (configurable limit, default 50)
            query_limit = current_app.config.get('DB_QUERY_LIMIT', 50)
            if query_count > query_limit:
                current_app.logger.warning(
                    f"Excessive database queries: {query_count} "
                    f"queries for {request.path}"
                )

            return old_execute(*exec_args, **exec_kwargs)

        # Replace the execute method
        db.engine.execute = execute_wrapper
        try:
            return f(*args, **kwargs)
        finally:
            # Restore the original execute method
            db.engine.execute = old_execute

            # Log total query count for profiling
            if current_app.debug and query_count > 10:
                current_app.logger.debug(
                    f"Database query count: {query_count} for {request.path}"
                )

    return decorated_function

def optimize_snippet_query(query):
    """Optimize a query specifically for snippets.

    Args:
        query: The SQLAlchemy query to optimize

    Returns:
        Optimized SQLAlchemy query

    Raises:
        TypeError: If query is not a valid SQLAlchemy query
    """
    from sqlalchemy.orm import joinedload
    from app.models import Snippet
    from sqlalchemy.orm.query import Query
    from flask import current_app

    # Validate input
    if not isinstance(query, Query):
        error_msg = f"Expected SQLAlchemy query, got {type(query).__name__}"
        current_app.logger.error(error_msg)
        raise TypeError(error_msg)

    try:
        # Use eager loading for common relationships
        query = query.options(
            joinedload(Snippet.tags),
            joinedload(Snippet.author)
        )

        return query
    except Exception as e:
        # Log the error but don't fail completely - return original query
        current_app.logger.error(f"Error optimizing snippet query: {str(e)}")
        current_app.logger.debug(f"Query optimization error details", exc_info=True)
        return query

def optimize_pagination(query, page, per_page, max_per_page=100):
    """Optimize a query for pagination."""
    # Validate and constrain pagination parameters
    try:
        page = int(page) if page is not None else 1
        per_page = int(per_page) if per_page is not None else 10
    except (TypeError, ValueError):
        page = 1
        per_page = 10
    
    # Ensure page is at least 1
    page = max(1, page)
    
    # Constrain per_page to a reasonable range
    per_page = min(max(1, per_page), max_per_page)
    
    # Apply limit and offset for efficient pagination
    return query.limit(per_page).offset((page - 1) * per_page)

def get_count(query):
    """Efficiently get count of query results without fetching all rows."""
    from sqlalchemy import func
    
    # Get just the count using a subquery
    count_query = query.statement.with_only_columns([func.count()]).order_by(None)
    count = query.session.execute(count_query).scalar()
    
    return count