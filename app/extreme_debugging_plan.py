"""
Extreme Debugging and Comprehensive Logging Plan for Code Snippets Application

This module implements an extreme debugging and comprehensive logging system
that captures and records all aspects of application behavior and operations.
"""

import time
import logging
import inspect
import json
import threading
import os
import sys
import io
import traceback
import functools
import uuid
import psutil
import gzip
from datetime import datetime
from flask import request, current_app, g, has_request_context
from flask_login import current_user
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm.attributes import get_history
from werkzeug.datastructures import MultiDict

# Configure logging
def configure_extreme_logging(app):
    """Configure extreme logging for the application."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(app.root_path), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configuration from app config
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'DEBUG'))
    log_format = app.config.get('LOG_FORMAT', '%(asctime)s.%(msecs)03d %(levelname)s [%(thread)d] %(name)s: %(message)s')
    log_date_format = '%Y-%m-%d %H:%M:%S'
    log_max_bytes = app.config.get('LOG_MAX_BYTES', 10485760)  # 10MB
    log_backup_count = app.config.get('LOG_BACKUP_COUNT', 20)
    
    # Create formatters
    standard_formatter = logging.Formatter(log_format, log_date_format)
    json_formatter = JsonFormatter()
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Main log file handler with rotation
    main_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'code_snippets.log'),
        maxBytes=log_max_bytes,
        backupCount=log_backup_count
    )
    main_handler.setLevel(log_level)
    main_handler.setFormatter(standard_formatter)
    root_logger.addHandler(main_handler)
    
    # Debug log file handler with all details
    debug_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'debug.log'),
        maxBytes=log_max_bytes,
        backupCount=log_backup_count
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(standard_formatter)
    root_logger.addHandler(debug_handler)
    
    # Error log with only warnings and above
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=log_max_bytes,
        backupCount=log_backup_count
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(standard_formatter)
    root_logger.addHandler(error_handler)
    
    # JSON structured log for machine processing
    json_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'structured.json.log'),
        maxBytes=log_max_bytes,
        backupCount=log_backup_count
    )
    json_handler.setLevel(log_level)
    json_handler.setFormatter(json_formatter)
    root_logger.addHandler(json_handler)
    
    # Console handler for development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(standard_formatter)
        root_logger.addHandler(console_handler)
    
    # Category-specific loggers
    configure_category_loggers(log_dir, log_max_bytes, log_backup_count)
    
    # Set Flask logger
    app.logger.handlers = []
    for handler in root_logger.handlers:
        app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    app.logger.propagate = False
    
    # Add WSGI logging middleware
    app.wsgi_app = RequestLoggingMiddleware(app.wsgi_app)
    
    # Setup log compression task
    setup_log_compression(log_dir)
    
    return app

def configure_category_loggers(log_dir, log_max_bytes, log_backup_count):
    """Configure category-specific loggers."""
    categories = [
        ('performance', logging.INFO),
        ('security', logging.INFO),
        ('database', logging.INFO),
        ('api', logging.INFO),
        ('auth', logging.INFO),
        ('user_activity', logging.INFO),
        ('exceptions', logging.ERROR)
    ]
    
    for category, level in categories:
        category_logger = logging.getLogger(category)
        category_logger.setLevel(level)
        category_logger.propagate = True  # Also log to root logger
        
        # Category-specific file
        handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, f'{category}.log'),
            maxBytes=log_max_bytes,
            backupCount=log_backup_count
        )
        handler.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d %(levelname)s [%(thread)d]: %(message)s',
            '%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        category_logger.addHandler(handler)

# Log compression utility
def setup_log_compression(log_dir):
    """Set up log compression for old log files."""
    def compress_logs():
        """Compress log files older than 1 day."""
        import glob
        import time
        
        # Find rotated log files (e.g., app.log.1, app.log.2)
        log_pattern = os.path.join(log_dir, '*.log.*')
        current_time = time.time()
        one_day_ago = current_time - 86400
        
        for log_file in glob.glob(log_pattern):
            # Skip already compressed files
            if log_file.endswith('.gz'):
                continue
                
            # Check file modification time
            if os.path.getmtime(log_file) < one_day_ago:
                try:
                    # Compress the file
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(f'{log_file}.gz', 'wb') as f_out:
                            f_out.writelines(f_in)
                    
                    # Remove the original file after successful compression
                    os.remove(log_file)
                    logging.info(f"Compressed log file: {log_file}")
                except Exception as e:
                    logging.error(f"Failed to compress log file {log_file}: {str(e)}")
    
    # Run immediately and then schedule periodic compression
    compress_logs()
    
    # Schedule compression to run daily
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(compress_logs, 'interval', hours=24)
    scheduler.start()

# JSON formatter for structured logging
class JsonFormatter(logging.Formatter):
    """Format log records as JSON objects."""
    
    def format(self, record):
        """Format the log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread_id': record.thread,
            'thread_name': threading.current_thread().name,
            'process_id': record.process
        }
        
        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add request context if available
        if has_request_context():
            log_data['request'] = {
                'url': request.url,
                'method': request.method,
                'endpoint': request.endpoint,
                'remote_addr': request.remote_addr,
                'user_agent': str(request.user_agent)
            }
            
            # Add user info if authenticated
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                log_data['user'] = {
                    'id': getattr(current_user, 'id', None),
                    'username': getattr(current_user, 'username', None)
                }
                
            # Add request args if present (sanitize sensitive data)
            if request.args:
                log_data['request']['args'] = sanitize_sensitive_data(request.args.to_dict())
                
            # Add request form data if present (sanitize sensitive data)
            if request.form and request.form.to_dict():
                log_data['request']['form'] = sanitize_sensitive_data(request.form.to_dict())
                
            # Add request headers if debug mode
            if current_app and current_app.debug:
                log_data['request']['headers'] = dict(request.headers)
        
        # Add extra attributes if present
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
            
        return json.dumps(log_data)

# Sanitize sensitive data before logging
def sanitize_sensitive_data(data, sensitive_keys=None):
    """Remove or mask sensitive data before logging."""
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'token', 'secret', 'key', 'auth', 'credential', 'credit_card',
            'ssn', 'social', 'birth', 'address', 'zip', 'postal', 'phone',
            'security_question', 'security_answer', 'api_key'
        ]
        
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, (dict, list)):
                sanitized[key] = sanitize_sensitive_data(value, sensitive_keys)
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, list):
        return [sanitize_sensitive_data(item, sensitive_keys) for item in data]
    else:
        return data

# Request logging middleware
class RequestLoggingMiddleware:
    """WSGI middleware to log all requests and responses."""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('request')
        
    def __call__(self, environ, start_response):
        # Generate a unique ID for this request for tracing
        request_id = str(uuid.uuid4())
        environ['REQUEST_ID'] = request_id
        
        # Log start of request
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')
        remote_addr = environ.get('REMOTE_ADDR', '')
        
        self.logger.info(
            f"Request started: {method} {path} from {remote_addr} [ID: {request_id}]"
        )
        
        # Record start time
        start_time = time.time()
        
        # Custom response handler to capture status code
        def custom_start_response(status, headers, exc_info=None):
            elapsed_ms = (time.time() - start_time) * 1000
            status_code = int(status.split(' ')[0])
            
            # Determine log level based on status code
            level = logging.INFO
            if status_code >= 500:
                level = logging.ERROR
            elif status_code >= 400:
                level = logging.WARNING
                
            self.logger.log(
                level,
                f"Request completed: {method} {path} - {status} - {elapsed_ms:.2f}ms [ID: {request_id}]"
            )
            
            # Add response headers for debugging
            headers.append(('X-Request-ID', request_id))
            if current_app.debug:
                headers.append(('X-Response-Time', f"{elapsed_ms:.2f}ms"))
                
            return start_response(status, headers, exc_info)
        
        # Call the application with our custom response handler
        return self.app(environ, custom_start_response)

# Function decorator for extreme logging
def extreme_log(level=logging.DEBUG, log_params=True, log_result=True, log_execution_time=True):
    """Decorator for extreme function logging."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get source code information
            filename = inspect.getfile(func)
            lines, start_line = inspect.getsourcelines(func)
            func_name = func.__name__
            module_name = func.__module__
            
            # Format calling arguments for logging (safely)
            call_args = []
            for i, arg in enumerate(args):
                arg_name = f"arg{i}"
                # Try to get actual parameter names if available
                if i < len(inspect.getfullargspec(func).args):
                    arg_name = inspect.getfullargspec(func).args[i]
                call_args.append(f"{arg_name}={safe_repr(arg)}")
            
            for k, v in kwargs.items():
                call_args.append(f"{k}={safe_repr(v)}")
            
            call_signature = ", ".join(call_args)
            
            # Create logger - use module name for categorization
            logger = logging.getLogger(module_name)
            
            # Generate a unique ID for tracing this function call
            call_id = str(uuid.uuid4())[:8]
            
            # Log function entry
            entry_message = f"ENTER {func_name} [ID:{call_id}] - Line {start_line} in {filename}"
            if log_params and (args or kwargs):
                entry_message += f" with params: {call_signature}"
            
            logger.log(level, entry_message)
            
            # Track execution time
            start_time = time.time()
            
            # Execute the function
            try:
                result = func(*args, **kwargs)
                
                # Calculate execution time
                execution_time = (time.time() - start_time) * 1000
                
                # Log successful execution and result
                exit_message = f"EXIT {func_name} [ID:{call_id}] - Executed in {execution_time:.2f}ms"
                if log_result:
                    exit_message += f" - Result: {safe_repr(result)}"
                
                # Determine log level based on execution time
                time_level = level
                if execution_time > 1000:  # Slow executions (>1s)
                    time_level = logging.WARNING
                    exit_message += " - SLOW EXECUTION"
                
                logger.log(time_level if log_execution_time else level, exit_message)
                
                return result
            except Exception as e:
                # Calculate execution time
                execution_time = (time.time() - start_time) * 1000
                
                # Log the exception with full details
                error_message = (
                    f"ERROR in {func_name} [ID:{call_id}] - {type(e).__name__}: {str(e)} "
                    f"- Execution failed after {execution_time:.2f}ms"
                )
                
                logger.error(error_message, exc_info=True)
                
                # Re-raise the exception
                raise
        
        return wrapper
    return decorator

# Safe object representation for logging
def safe_repr(obj, max_length=1000):
    """Create a safe string representation of an object for logging."""
    try:
        if isinstance(obj, (str, int, float, bool, type(None))):
            return repr(obj)
        elif isinstance(obj, (list, tuple)):
            if len(obj) > 10:
                return f"{type(obj).__name__} with {len(obj)} items"
            return repr([safe_repr(x) for x in obj[:10]])
        elif isinstance(obj, dict):
            if len(obj) > 10:
                return f"dict with {len(obj)} items"
            return repr({k: safe_repr(v) for k, v in list(obj.items())[:10]})
        elif hasattr(obj, '__dict__'):
            # For objects with __dict__, represent as ClassName(attr=value, ...)
            class_name = type(obj).__name__
            attrs = {k: safe_repr(v) for k, v in obj.__dict__.items() 
                    if not k.startswith('_')}
            if len(attrs) > 5:
                return f"{class_name} with {len(attrs)} attributes"
            attrs_str = ", ".join(f"{k}={v}" for k, v in list(attrs.items())[:5])
            return f"{class_name}({attrs_str})"
        else:
            # For other objects, use str() or repr() with a limit
            rep = repr(obj)
            if len(rep) > max_length:
                return rep[:max_length] + "..."
            return rep
    except Exception as e:
        # If representation fails, return a safe fallback
        return f"<{type(obj).__name__} - repr failed: {str(e)}>"

# Thread-local storage for request tracing
request_context = threading.local()

# Tracing middleware
class TracingMiddleware:
    """Middleware to implement distributed tracing across requests."""
    
    def __init__(self, app):
        self.app = app
        
    def __call__(self, environ, start_response):
        # Extract trace ID from headers or generate a new one
        trace_id = environ.get('HTTP_X_TRACE_ID', str(uuid.uuid4()))
        span_id = str(uuid.uuid4())
        
        # Store in thread-local for access throughout this request
        request_context.trace_id = trace_id
        request_context.span_id = span_id
        request_context.spans = []
        
        # Add trace ID to environment for access in the application
        environ['trace_id'] = trace_id
        environ['span_id'] = span_id
        
        # Log request with trace information
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')
        logging.info(f"Trace: {trace_id} - Starting request {method} {path}")
        
        # Custom response handler that adds trace ID to response headers
        def traced_start_response(status, headers, exc_info=None):
            headers.append(('X-Trace-ID', trace_id))
            headers.append(('X-Span-ID', span_id))
            
            # Log the response
            status_code = int(status.split(' ')[0])
            logging.info(
                f"Trace: {trace_id} - Completed request with status {status_code}"
            )
            
            return start_response(status, headers, exc_info)
        
        # Call the application with our traced response handler
        return self.app(environ, traced_start_response)

# Span context manager for tracing code sections
class TraceSpan:
    """Context manager for tracing code spans within a request."""
    
    def __init__(self, name, extra_data=None):
        self.name = name
        self.extra_data = extra_data or {}
        self.start_time = None
        self.span_id = str(uuid.uuid4())
        
    def __enter__(self):
        self.start_time = time.time()
        
        # Get parent trace ID if available
        trace_id = getattr(request_context, 'trace_id', None) or str(uuid.uuid4())
        parent_span_id = getattr(request_context, 'span_id', None)
        
        # Log span start
        logging.debug(
            f"Trace: {trace_id} - Span: {self.span_id} - "
            f"Starting span '{self.name}'"
        )
        
        # Store span info
        span_info = {
            'name': self.name,
            'span_id': self.span_id,
            'parent_span_id': parent_span_id,
            'trace_id': trace_id,
            'start_time': self.start_time,
            'extra_data': self.extra_data
        }
        
        if hasattr(request_context, 'spans'):
            request_context.spans.append(span_info)
            
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000
        trace_id = getattr(request_context, 'trace_id', None) or 'unknown'
        
        if exc_type is not None:
            # Log span error
            logging.error(
                f"Trace: {trace_id} - Span: {self.span_id} - "
                f"Error in span '{self.name}': {exc_type.__name__}: {str(exc_val)}",
                exc_info=(exc_type, exc_val, exc_tb)
            )
        else:
            # Log span completion
            logging.debug(
                f"Trace: {trace_id} - Span: {self.span_id} - "
                f"Completed span '{self.name}' in {duration:.2f}ms"
            )
            
        # Update span info with duration and completion status
        if hasattr(request_context, 'spans'):
            for span in request_context.spans:
                if span['span_id'] == self.span_id:
                    span['duration_ms'] = duration
                    span['has_error'] = exc_type is not None
                    break

# Variable state tracking
def log_variable_change(var_name, old_value, new_value, module_name=None):
    """Log changes to variable values."""
    if module_name is None:
        frame = inspect.currentframe().f_back
        module_name = frame.f_globals.get('__name__', 'unknown')
        line_number = frame.f_lineno
        filename = frame.f_code.co_filename
    else:
        line_number = 0
        filename = "unknown"
    
    logger = logging.getLogger(module_name)
    logger.debug(
        f"VARIABLE CHANGE: {var_name} at {filename}:{line_number} - "
        f"Old: {safe_repr(old_value)} -> New: {safe_repr(new_value)}"
    )

# Resource monitoring
def monitor_resources(app):
    """Periodically log system resource usage."""
    def log_resources():
        """Log current resource usage."""
        process = psutil.Process(os.getpid())
        
        # Memory usage
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        # CPU usage
        cpu_percent = process.cpu_percent(interval=0.1)
        
        # Open files
        try:
            open_files = len(process.open_files())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            open_files = -1
            
        # Connections
        try:
            connections = len(process.connections())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            connections = -1
            
        # Threads
        threads = process.num_threads()
        
        # Log the data
        logger = logging.getLogger('performance')
        logger.info(
            f"RESOURCES: Memory: {memory_info.rss / (1024 * 1024):.1f}MB ({memory_percent:.1f}%), "
            f"CPU: {cpu_percent:.1f}%, Open files: {open_files}, "
            f"Connections: {connections}, Threads: {threads}"
        )
        
        # Additional check for high resource usage
        if memory_percent > 70 or cpu_percent > 80:
            logger.warning(
                f"HIGH RESOURCE USAGE: Memory: {memory_percent:.1f}%, "
                f"CPU: {cpu_percent:.1f}%"
            )
    
    # Schedule resource monitoring
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(log_resources, 'interval', seconds=60)
    scheduler.start()

# Database Event Tracking
def configure_database_tracking(app):
    """Configure detailed tracking of database operations."""
    # SQLAlchemy model change tracking
    @event.listens_for(app.db.session, 'before_flush')
    def before_flush(session, flush_context, instances):
        """Log all model changes before they are flushed to the database."""
        logger = logging.getLogger('database')
        
        # Track new objects
        for obj in session.new:
            class_name = obj.__class__.__name__
            try:
                # Try to get a primary key or identifier
                if hasattr(obj, 'id') and obj.id is not None:
                    identifier = obj.id
                elif hasattr(obj, 'name') and obj.name is not None:
                    identifier = obj.name
                else:
                    identifier = id(obj)
                    
                # Log the creation
                logger.info(f"DB CREATE: {class_name}({identifier}) - New object created")
                
                # Log all attribute values
                attrs = {k: v for k, v in obj.__dict__.items() 
                        if not k.startswith('_')}
                logger.debug(f"DB CREATE DETAILS: {class_name}({identifier}) - {safe_repr(attrs)}")
            except Exception as e:
                logger.error(f"Error logging DB CREATE: {str(e)}")
        
        # Track modified objects
        for obj in session.dirty:
            if not session.is_modified(obj):
                continue
                
            class_name = obj.__class__.__name__
            try:
                # Try to get a primary key or identifier
                if hasattr(obj, 'id') and obj.id is not None:
                    identifier = obj.id
                elif hasattr(obj, 'name') and obj.name is not None:
                    identifier = obj.name
                else:
                    identifier = id(obj)
                
                # Log the modification with changed attributes
                logger.info(f"DB UPDATE: {class_name}({identifier}) - Object modified")
                
                # Get specific attribute changes
                changes = {}
                for attr in obj.__dict__:
                    if attr.startswith('_'):
                        continue
                        
                    # Use SQLAlchemy's history tracking if possible
                    if hasattr(obj, '__mapper__') and attr in obj.__mapper__.attrs:
                        history = get_history(obj, attr)
                        if history.has_changes():
                            changes[attr] = {
                                'old': history.deleted[0] if history.deleted else None,
                                'new': history.added[0] if history.added else None
                            }
                
                if changes:
                    logger.debug(f"DB UPDATE DETAILS: {class_name}({identifier}) - Changes: {safe_repr(changes)}")
            except Exception as e:
                logger.error(f"Error logging DB UPDATE: {str(e)}")
        
        # Track deleted objects
        for obj in session.deleted:
            class_name = obj.__class__.__name__
            try:
                # Try to get a primary key or identifier
                if hasattr(obj, 'id') and obj.id is not None:
                    identifier = obj.id
                elif hasattr(obj, 'name') and obj.name is not None:
                    identifier = obj.name
                else:
                    identifier = id(obj)
                    
                # Log the deletion
                logger.info(f"DB DELETE: {class_name}({identifier}) - Object deleted")
                
                # Log object details that is being deleted
                attrs = {k: v for k, v in obj.__dict__.items() 
                        if not k.startswith('_')}
                logger.debug(f"DB DELETE DETAILS: {class_name}({identifier}) - {safe_repr(attrs)}")
            except Exception as e:
                logger.error(f"Error logging DB DELETE: {str(e)}")

# SQL Query Logging Enhancement
@event.listens_for(Engine, "before_cursor_execute")
def enhanced_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Enhanced query logging - start timer and log query details."""
    conn.info.setdefault('query_start_time', []).append(time.time())
    
    # Add trace context if available
    if hasattr(request_context, 'trace_id'):
        conn.info.setdefault('trace_context', {})
        conn.info['trace_context']['trace_id'] = request_context.trace_id
        conn.info['trace_context']['span_id'] = request_context.span_id
    
    # Log the query
    logger = logging.getLogger('database')
    query_type = statement.split()[0] if statement else "Unknown"
    
    # For select queries, log what's being queried
    if query_type.lower() == 'select':
        tables = extract_tables_from_query(statement)
        table_str = ', '.join(tables) if tables else 'unknown'
        logger.debug(f"DB QUERY STARTED: {query_type} from {table_str}")
    else:
        logger.debug(f"DB QUERY STARTED: {query_type}")
    
    # In debug mode, log the full query and parameters
    if current_app and current_app.debug:
        # Safely log parameters
        safe_params = sanitize_sensitive_data(parameters)
        logger.debug(f"DB QUERY: {statement}\nParameters: {safe_params}")

@event.listens_for(Engine, "after_cursor_execute")
def enhanced_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Enhanced query logging - end timer and log results."""
    if not conn.info.get('query_start_time'):
        return
        
    total_time = time.time() - conn.info['query_start_time'].pop()
    
    # Get tracing context if available
    trace_context = conn.info.get('trace_context', {})
    trace_id = trace_context.get('trace_id', 'unknown')
    
    # Determine what to log based on query type and duration
    query_type = statement.split()[0].lower() if statement else "unknown"
    row_count = cursor.rowcount if hasattr(cursor, 'rowcount') else -1
    
    logger = logging.getLogger('database')
    
    # Log based on duration and query type
    if total_time > 1.0:  # Very slow queries (>1s)
        logger.warning(
            f"DB QUERY SLOW: {query_type.upper()} took {total_time:.4f}s - "
            f"Rows: {row_count} - Trace: {trace_id}"
        )
        # For slow queries, also log the actual query
        logger.warning(f"Slow query: {statement[:500]}...")
    elif total_time > 0.1:  # Moderately slow (>100ms)
        logger.warning(
            f"DB QUERY MODERATE: {query_type.upper()} took {total_time:.4f}s - "
            f"Rows: {row_count} - Trace: {trace_id}"
        )
    else:
        logger.debug(
            f"DB QUERY COMPLETED: {query_type.upper()} took {total_time:.4f}s - "
            f"Rows: {row_count} - Trace: {trace_id}"
        )
    
    # For select queries, add result count in debug mode
    if query_type == 'select' and current_app and current_app.debug:
        logger.debug(f"DB QUERY RESULT: {row_count} rows returned")

def extract_tables_from_query(query):
    """Extract table names from a SQL query (simple implementation)."""
    import re
    
    # Look for table names after FROM and JOIN clauses
    # This is a simplified approach and may not work for all queries
    table_pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    matches = re.findall(table_pattern, query, re.IGNORECASE)
    
    return matches

# Exception logging enhancement
class ExtremeExceptionLogger:
    """Enhanced exception logging with detailed context."""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('exceptions')
        
        # Replace the default exception handler
        app.register_error_handler(Exception, self.log_exception)
        
    def log_exception(self, exception):
        """Log exceptions with extreme detail."""
        # Get exception details
        exc_type = type(exception).__name__
        exc_msg = str(exception)
        
        # Get traceback
        tb_frames = traceback.extract_tb(sys.exc_info()[2])
        
        # Build detailed exception report
        report = {
            'timestamp': datetime.now().isoformat(),
            'exception_type': exc_type,
            'exception_message': exc_msg,
            'traceback': [
                {
                    'file': frame.filename,
                    'line': frame.lineno,
                    'function': frame.name,
                    'code': frame.line
                }
                for frame in tb_frames
            ]
        }
        
        # Add request context if available
        if has_request_context():
            report['request'] = {
                'url': request.url,
                'method': request.method,
                'path': request.path,
                'endpoint': request.endpoint,
                'remote_addr': request.remote_addr,
                'user_agent': str(request.user_agent),
                'args': sanitize_sensitive_data(request.args.to_dict()),
                'form': sanitize_sensitive_data(request.form.to_dict()) if request.form else None,
            }
            
            # Add user info if authenticated
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                report['user'] = {
                    'id': getattr(current_user, 'id', None),
                    'username': getattr(current_user, 'username', None)
                }
                
        # Add runtime context
        report['runtime'] = {
            'python_version': sys.version,
            'app_name': self.app.name,
            'app_debug': self.app.debug,
            'app_testing': self.app.testing,
            'memory_usage': f"{psutil.Process().memory_info().rss / (1024 * 1024):.1f}MB",
            'cpu_percent': psutil.Process().cpu_percent(),
            'thread_id': threading.get_ident(),
            'thread_name': threading.current_thread().name
        }
        
        # Add trace context if available
        if hasattr(request_context, 'trace_id'):
            report['trace'] = {
                'trace_id': request_context.trace_id,
                'span_id': request_context.span_id
            }
            
        # Log the exception with full context
        self.logger.error(
            f"EXCEPTION: {exc_type}: {exc_msg}",
            extra={'extra_data': {'exception_report': report}}
        )
        
        # Log to separate error file with full traceback
        self.logger.error(
            f"Exception details:", exc_info=sys.exc_info()
        )
        
        # Re-raise to let Flask handle the response
        raise exception

# Performance metrics collection
class PerformanceMetrics:
    """Collect and log detailed performance metrics."""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('performance')
        self.metrics = {}
        
        # Register before request handler
        app.before_request(self.before_request)
        
        # Register after request handler
        app.after_request(self.after_request)
        
    def before_request(self):
        """Initialize performance tracking for this request."""
        g.start_time = time.time()
        g.metrics = {
            'db_queries': 0,
            'db_time': 0,
            'template_renders': 0,
            'template_time': 0
        }
        
    def after_request(self, response):
        """Log performance metrics for this request."""
        if not hasattr(g, 'start_time'):
            return response
            
        # Calculate total request time
        total_time = (time.time() - g.start_time) * 1000  # ms
        
        # Get metrics collected during request
        metrics = getattr(g, 'metrics', {})
        
        # Add response size
        if hasattr(response, 'data'):
            metrics['response_size'] = len(response.data)
            
        # Determine if this was a slow request
        is_slow = False
        threshold = 500  # ms
        
        # Adjust threshold based on request type
        if request.path.startswith('/static/'):
            threshold = 100  # Static requests should be faster
        elif request.method != 'GET':
            threshold = 1000  # Allow more time for non-GET requests
            
        if total_time > threshold:
            is_slow = True
            
        # Log the metrics
        log_level = logging.WARNING if is_slow else logging.INFO
        
        # Create a structured metrics report
        metrics_report = {
            'url': request.path,
            'method': request.method,
            'status_code': response.status_code,
            'total_time_ms': f"{total_time:.2f}",
            'db_queries': metrics.get('db_queries', 0),
            'db_time_ms': f"{metrics.get('db_time', 0):.2f}",
            'template_renders': metrics.get('template_renders', 0),
            'template_time_ms': f"{metrics.get('template_time', 0):.2f}",
            'response_size_bytes': metrics.get('response_size', 0)
        }
        
        # Add trace information if available
        if hasattr(request_context, 'trace_id'):
            metrics_report['trace_id'] = request_context.trace_id
            
        # Log the metrics
        if is_slow:
            self.logger.warning(
                f"SLOW REQUEST: {request.method} {request.path} - {total_time:.2f}ms",
                extra={'extra_data': {'metrics': metrics_report}}
            )
        else:
            self.logger.info(
                f"REQUEST METRICS: {request.method} {request.path} - {total_time:.2f}ms",
                extra={'extra_data': {'metrics': metrics_report}}
            )
            
        # Add performance headers in debug mode
        if self.app.debug:
            response.headers['X-Performance-Time'] = f"{total_time:.2f}ms"
            response.headers['X-DB-Queries'] = str(metrics.get('db_queries', 0))
            
        # Aggregate metrics for global statistics
        endpoint = request.endpoint or 'unknown'
        if endpoint not in self.metrics:
            self.metrics[endpoint] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0
            }
            
        stat = self.metrics[endpoint]
        stat['count'] += 1
        stat['total_time'] += total_time
        stat['min_time'] = min(stat['min_time'], total_time)
        stat['max_time'] = max(stat['max_time'], total_time)
        
        return response
        
    def record_db_query(self, duration):
        """Record a database query execution."""
        if has_request_context() and hasattr(g, 'metrics'):
            g.metrics['db_queries'] = g.metrics.get('db_queries', 0) + 1
            g.metrics['db_time'] = g.metrics.get('db_time', 0) + duration
            
    def record_template_render(self, template_name, duration):
        """Record a template rendering operation."""
        if has_request_context() and hasattr(g, 'metrics'):
            g.metrics['template_renders'] = g.metrics.get('template_renders', 0) + 1
            g.metrics['template_time'] = g.metrics.get('template_time', 0) + duration
            
    def log_global_stats(self):
        """Log global performance statistics."""
        self.logger.info("GLOBAL PERFORMANCE STATISTICS:")
        
        for endpoint, stats in sorted(
            self.metrics.items(), 
            key=lambda x: x[1]['total_time'], 
            reverse=True
        ):
            avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            
            self.logger.info(
                f"Endpoint: {endpoint} - Count: {stats['count']} - "
                f"Avg: {avg_time:.2f}ms - Min: {stats['min_time']:.2f}ms - "
                f"Max: {stats['max_time']:.2f}ms"
            )

# Main function to initialize all extreme debugging components
def init_extreme_debugging(app):
    """Initialize the extreme debugging and logging system."""
    # Configure basic logging
    app = configure_extreme_logging(app)
    
    # Initialize exception logger
    app.extreme_exception_logger = ExtremeExceptionLogger(app)
    
    # Initialize performance metrics
    app.performance_metrics = PerformanceMetrics(app)
    
    # Add tracing middleware
    app.wsgi_app = TracingMiddleware(app.wsgi_app)
    
    # Set up resource monitoring
    monitor_resources(app)
    
    # Configure database tracking
    if hasattr(app, 'db'):
        configure_database_tracking(app)
    
    # Log system startup
    app.logger.info(f"=== APPLICATION STARTING IN {app.env.upper()} MODE ===")
    app.logger.info(f"Python version: {sys.version}")
    import flask
    app.logger.info(f"Flask version: {flask.__version__}")
    
    # Log configuration settings (excluding sensitive values)
    safe_config = sanitize_sensitive_data(app.config.copy())
    app.logger.debug(f"Application configuration: {safe_config}")
    
    # Setup periodic logging of global stats
    @app.before_first_request
    def setup_periodic_stats():
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            app.performance_metrics.log_global_stats, 
            'interval', 
            minutes=10
        )
        scheduler.start()
    
    # Register shutdown logging
    import atexit
    
    def log_shutdown():
        app.logger.info("=== APPLICATION SHUTTING DOWN ===")
        
    atexit.register(log_shutdown)
    
    return app

# Helper decorator to time function execution
def timed_execution(f):
    """Decorator to time and log function execution."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = f(*args, **kwargs)
            return result
        finally:
            execution_time = (time.time() - start_time) * 1000
            
            # Determine logging level based on execution time
            level = logging.DEBUG
            
            if execution_time > 1000:
                level = logging.WARNING
            elif execution_time > 100:
                level = logging.INFO
                
            # Log with appropriate level
            func_name = f.__name__
            module_name = f.__module__
            
            logger = logging.getLogger('performance')
            logger.log(
                level,
                f"FUNCTION TIMING: {module_name}.{func_name} "
                f"executed in {execution_time:.2f}ms"
            )
            
            # Record in performance metrics if available
            if has_request_context() and hasattr(current_app, 'performance_metrics'):
                # Categorize the function for metrics
                if module_name.endswith('db') or 'model' in module_name.lower():
                    current_app.performance_metrics.record_db_query(execution_time / 1000)
                elif 'template' in module_name.lower() or func_name.startswith('render_'):
                    current_app.performance_metrics.record_template_render(
                        f"{module_name}.{func_name}", 
                        execution_time / 1000
                    )
    
    return decorated_function