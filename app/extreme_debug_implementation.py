"""
Implementation module for extreme debugging in the Code Snippets application.

This module provides decorator functions and utilities that can be applied
throughout the codebase to achieve extreme logging of all operations.
"""

import time
import functools
import inspect
import logging
import json
import threading
import uuid
import traceback
from datetime import datetime
from flask import request, current_app, g, has_request_context
from flask_login import current_user

# Function entry/exit decorator with parameter and result logging
def log_function(level=logging.DEBUG, log_params=True, log_result=True):
    """Decorator to log function entry and exit with parameters and results."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get caller information
            frame = inspect.currentframe().f_back
            caller_info = ""
            if frame:
                caller_file = frame.f_code.co_filename
                caller_line = frame.f_lineno
                caller_func = frame.f_code.co_name
                caller_info = f" - Called from {caller_func} in {caller_file}:{caller_line}"
            
            # Generate unique ID for this call for tracing
            call_id = str(uuid.uuid4())[:8]
            
            # Get function details
            func_name = func.__name__
            module_name = func.__module__
            file_path = inspect.getfile(func)
            line_no = inspect.getsourcelines(func)[1]
            
            # Get thread information
            thread_id = threading.get_ident()
            thread_name = threading.current_thread().name
            
            # Format arguments for logging (sanitizing sensitive data)
            arg_str = ""
            if log_params and (args or kwargs):
                # Format positional args
                args_repr = [_safe_repr(arg) for arg in args]
                
                # Format keyword args (filter sensitive information)
                kwargs_repr = [
                    f"{k}={'***REDACTED***' if _is_sensitive_param(k) else _safe_repr(v)}"
                    for k, v in kwargs.items()
                ]
                
                all_args = args_repr + kwargs_repr
                arg_str = f" - Args: ({', '.join(all_args)})"
            
            # Get request context information if available
            request_info = ""
            if has_request_context():
                endpoint = request.endpoint or "unknown"
                method = request.method
                path = request.path
                remote_addr = request.remote_addr
                request_info = f" - Request: {method} {path} ({endpoint}) from {remote_addr}"
            
            # Log function entry
            logger = logging.getLogger(module_name)
            logger.log(
                level,
                f"ENTER {func_name} [ID:{call_id}] at {file_path}:{line_no} "
                f"[Thread:{thread_id}/{thread_name}]{request_info}{caller_info}{arg_str}"
            )
            
            # Measure execution time
            start_time = time.time()
            
            # Execute the function
            try:
                result = func(*args, **kwargs)
                
                # Calculate execution time
                exec_time = time.time() - start_time
                
                # Format result for logging
                result_str = ""
                if log_result:
                    result_str = f" - Result: {_safe_repr(result)}"
                
                # Determine log level based on execution time
                time_level = level
                time_str = ""
                if exec_time > 1.0:  # Slow execution (>1s)
                    time_level = logging.WARNING
                    time_str = " - SLOW EXECUTION"
                
                # Log function exit
                logger.log(
                    time_level,
                    f"EXIT {func_name} [ID:{call_id}] - Execution time: {exec_time:.4f}s"
                    f"{time_str}{result_str}"
                )
                
                return result
            except Exception as e:
                # Calculate execution time
                exec_time = time.time() - start_time
                
                # Log the exception
                logger.error(
                    f"ERROR in {func_name} [ID:{call_id}] - {type(e).__name__}: {str(e)} "
                    f"- Failed after {exec_time:.4f}s",
                    exc_info=True
                )
                
                # Re-raise the exception
                raise
        
        return wrapper
    return decorator

# Helper function to create safe string representations
def _safe_repr(obj, max_length=1000):
    """Create a safe string representation of an object for logging."""
    try:
        if isinstance(obj, (str, int, float, bool, type(None))):
            if isinstance(obj, str) and len(obj) > max_length:
                return f"{obj[:max_length]}... [truncated, total length: {len(obj)}]"
            return repr(obj)
        elif isinstance(obj, (list, tuple)):
            if len(obj) > 10:
                return f"{type(obj).__name__} with {len(obj)} items"
            return repr([_safe_repr(x) for x in obj[:10]])
        elif isinstance(obj, dict):
            if len(obj) > 10:
                return f"dict with {len(obj)} items"
            # Filter sensitive keys
            safe_dict = {}
            for k, v in list(obj.items())[:10]:
                if _is_sensitive_param(k):
                    safe_dict[k] = "***REDACTED***"
                else:
                    safe_dict[k] = _safe_repr(v)
            return repr(safe_dict)
        elif hasattr(obj, '__dict__'):
            # For objects with __dict__, represent as ClassName(attr=value, ...)
            class_name = type(obj).__name__
            attrs = {}
            for k, v in obj.__dict__.items():
                if not k.startswith('_'):
                    if _is_sensitive_param(k):
                        attrs[k] = "***REDACTED***"
                    else:
                        attrs[k] = _safe_repr(v)
            
            if len(attrs) > 5:
                return f"{class_name} with {len(attrs)} attributes"
            
            attrs_str = ", ".join(f"{k}={v}" for k, v in list(attrs.items())[:5])
            return f"{class_name}({attrs_str})"
        else:
            # For other objects, use str() or repr() with a limit
            rep = repr(obj)
            if len(rep) > max_length:
                return rep[:max_length] + f"... [truncated, total length: {len(rep)}]"
            return rep
    except Exception as e:
        # If representation fails, return a safe fallback
        return f"<{type(obj).__name__} - repr failed: {str(e)}>"

# Check if a parameter name might contain sensitive information
def _is_sensitive_param(param_name):
    """Check if a parameter name might contain sensitive information."""
    sensitive_patterns = [
        'password', 'secret', 'token', 'auth', 'key', 'credential',
        'private', 'security', 'hash', 'salt', 'pin', 'cipher'
    ]
    
    param_lower = param_name.lower()
    return any(pattern in param_lower for pattern in sensitive_patterns)

# Variable tracking decorator for class attributes
def log_attribute_access(cls):
    """Class decorator to log all attribute access and modification."""
    # Store original __getattribute__ and __setattr__
    orig_getattribute = cls.__getattribute__
    orig_setattr = cls.__setattr__
    
    def logged_getattribute(self, name):
        """Log attribute access."""
        # Skip logging for private attributes and methods
        if not name.startswith('__') and not name.startswith('_') and not callable(getattr(cls, name, None)):
            value = orig_getattribute(self, name)
            
            # Get caller information
            frame = inspect.currentframe().f_back
            caller_info = ""
            if frame:
                caller_file = frame.f_code.co_filename
                caller_line = frame.f_lineno
                caller_func = frame.f_code.co_name
                caller_info = f" in {caller_func} at {caller_file}:{caller_line}"
            
            # Log the attribute access
            logger = logging.getLogger(cls.__module__)
            logger.debug(
                f"ATTR READ: {cls.__name__}.{name} = {_safe_repr(value)}{caller_info}"
            )
        
        return orig_getattribute(self, name)
    
    def logged_setattr(self, name, value):
        """Log attribute modification."""
        # For non-private attributes, log the change
        if not name.startswith('__') and not name.startswith('_'):
            # Get the old value if the attribute exists
            old_value = getattr(self, name, "<not set>") if hasattr(self, name) else "<not set>"
            
            # Get caller information
            frame = inspect.currentframe().f_back
            caller_info = ""
            if frame:
                caller_file = frame.f_code.co_filename
                caller_line = frame.f_lineno
                caller_func = frame.f_code.co_name
                caller_info = f" in {caller_func} at {caller_file}:{caller_line}"
            
            # Log the attribute change
            logger = logging.getLogger(cls.__module__)
            
            # Redact sensitive values
            if _is_sensitive_param(name):
                logger.debug(
                    f"ATTR WRITE: {cls.__name__}.{name} = ***REDACTED***{caller_info}"
                )
            else:
                logger.debug(
                    f"ATTR WRITE: {cls.__name__}.{name} changed from "
                    f"{_safe_repr(old_value)} to {_safe_repr(value)}{caller_info}"
                )
        
        # Call the original __setattr__
        orig_setattr(self, name, value)
    
    # Replace the methods
    cls.__getattribute__ = logged_getattribute
    cls.__setattr__ = logged_setattr
    
    return cls

# Context manager for tracking blocks of code
class LoggedBlock:
    """Context manager for logging code blocks with timing."""
    
    def __init__(self, block_name, level=logging.DEBUG, log_variables=False):
        self.block_name = block_name
        self.level = level
        self.log_variables = log_variables
        self.start_time = None
        self.logger = logging.getLogger()
        
        # Get caller information
        frame = inspect.currentframe().f_back
        self.caller_file = frame.f_code.co_filename if frame else "unknown"
        self.caller_line = frame.f_lineno if frame else 0
        self.caller_func = frame.f_code.co_name if frame else "unknown"
        self.caller_module = frame.f_globals.get('__name__', 'unknown') if frame else "unknown"
        
        # Use the caller's module logger
        self.logger = logging.getLogger(self.caller_module)
        
        # Generate a unique ID for this block
        self.block_id = str(uuid.uuid4())[:8]
        
        # Store initial frame locals if logging variables
        self.initial_locals = None
        if self.log_variables:
            if frame:
                self.initial_locals = frame.f_locals.copy()
    
    def __enter__(self):
        """Log block entry."""
        self.start_time = time.time()
        
        # Log entry
        self.logger.log(
            self.level,
            f"BLOCK START: {self.block_name} [ID:{self.block_id}] "
            f"at {self.caller_file}:{self.caller_line} in {self.caller_func}"
        )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log block exit with timing and optionally changed variables."""
        exec_time = time.time() - self.start_time
        
        # Determine log level based on execution time
        exit_level = self.level
        time_str = ""
        if exec_time > 1.0:  # Slow execution (>1s)
            exit_level = logging.WARNING
            time_str = " - SLOW EXECUTION"
        
        if exc_type is not None:
            # Log with exception
            self.logger.error(
                f"BLOCK ERROR: {self.block_name} [ID:{self.block_id}] - "
                f"{exc_type.__name__}: {str(exc_val)} - "
                f"Failed after {exec_time:.4f}s",
                exc_info=(exc_type, exc_val, exc_tb)
            )
        else:
            # Log successful completion
            self.logger.log(
                exit_level,
                f"BLOCK END: {self.block_name} [ID:{self.block_id}] - "
                f"Execution time: {exec_time:.4f}s{time_str}"
            )
            
            # Log changed variables if requested
            if self.log_variables and self.initial_locals is not None:
                # Get current locals
                frame = inspect.currentframe().f_back
                if frame:
                    current_locals = frame.f_locals
                    
                    # Find changed variables
                    changes = {}
                    for name, value in current_locals.items():
                        # Skip internals, functions, and unchanged values
                        if (name.startswith('_') or 
                            callable(value) or
                            name not in self.initial_locals or
                            self.initial_locals[name] == value):
                            continue
                        
                        # Add to changes
                        if _is_sensitive_param(name):
                            changes[name] = "***REDACTED***"
                        else:
                            changes[name] = _safe_repr(value)
                    
                    if changes:
                        self.logger.log(
                            self.level,
                            f"BLOCK VARIABLES: {self.block_name} [ID:{self.block_id}] - "
                            f"Changed variables: {changes}"
                        )
        
        # Don't suppress exceptions
        return False

# Loop iteration logging
def log_iterations(iterable, name=None, level=logging.DEBUG, log_items=True, log_interval=1):
    """Wrapper for iterables to log iterations."""
    if name is None:
        # Try to get the variable name
        frame = inspect.currentframe().f_back
        if frame:
            # Look for the iterable in the calling frame's variables
            for var_name, var_value in frame.f_locals.items():
                if var_value is iterable:
                    name = var_name
                    break
        
        if name is None:
            name = f"iterable({type(iterable).__name__})"
    
    # Get caller information
    frame = inspect.currentframe().f_back
    caller_info = ""
    if frame:
        caller_file = frame.f_code.co_filename
        caller_line = frame.f_lineno
        caller_func = frame.f_code.co_name
        caller_module = frame.f_globals.get('__name__', 'unknown')
        caller_info = f" at {caller_file}:{caller_line} in {caller_func}"
        logger = logging.getLogger(caller_module)
    else:
        logger = logging.getLogger(__name__)
    
    # Try to get length if possible for progress tracking
    try:
        total_items = len(iterable)
        logger.log(
            level,
            f"LOOP START: Iterating over {name} with {total_items} items{caller_info}"
        )
    except (TypeError, AttributeError):
        total_items = None
        logger.log(
            level,
            f"LOOP START: Iterating over {name} (unknown size){caller_info}"
        )
    
    # Start timing
    start_time = time.time()
    
    # Iterate with logging
    for i, item in enumerate(iterable):
        # Log at specified intervals or always for small iterables
        if log_items and (i % log_interval == 0 or (total_items and total_items <= 10)):
            if _is_sensitive_param(name):
                logger.log(
                    level,
                    f"LOOP ITEM: {name}[{i}] - ***REDACTED***"
                )
            else:
                logger.log(
                    level,
                    f"LOOP ITEM: {name}[{i}] - {_safe_repr(item)}"
                )
        
        # Log progress periodically for large iterables
        if total_items and total_items > 10 and i > 0 and i % (total_items // 10) == 0:
            progress = (i / total_items) * 100
            elapsed = time.time() - start_time
            estimated_total = elapsed / (i / total_items) if i > 0 else 0
            remaining = estimated_total - elapsed
            
            logger.log(
                level,
                f"LOOP PROGRESS: {name} - {i}/{total_items} ({progress:.1f}%) - "
                f"Elapsed: {elapsed:.2f}s, Estimated remaining: {remaining:.2f}s"
            )
        
        yield item
    
    # Log completion
    elapsed = time.time() - start_time
    iteration_count = i + 1 if 'i' in locals() else 0
    
    logger.log(
        level,
        f"LOOP END: Completed iteration over {name} - {iteration_count} items "
        f"processed in {elapsed:.4f}s ({iteration_count/elapsed:.2f} items/s)"
    )

# Conditional statement logging
def log_condition(condition, condition_str=None, level=logging.DEBUG):
    """Log a conditional statement evaluation."""
    # Evaluate the condition
    result = bool(condition)
    
    # If condition string not provided, try to get it from the caller's context
    if condition_str is None:
        frame = inspect.currentframe().f_back
        if frame:
            # Try to extract the condition text from the source code
            source_lines, line_no = inspect.getsourcelines(frame)
            relative_line = frame.f_lineno - line_no
            if 0 <= relative_line < len(source_lines):
                line = source_lines[relative_line].strip()
                # Extract the condition from a line like "if log_condition(..., ...):"
                if "log_condition(" in line and "):" in line:
                    start_idx = line.find("log_condition(") + len("log_condition(")
                    end_idx = line.rfind("):")
                    condition_str = line[start_idx:end_idx].strip()
        
        # If still not found, use a generic description
        if condition_str is None:
            condition_str = "<condition>"
    
    # Get caller information
    frame = inspect.currentframe().f_back
    caller_info = ""
    if frame:
        caller_file = frame.f_code.co_filename
        caller_line = frame.f_lineno
        caller_func = frame.f_code.co_name
        caller_module = frame.f_globals.get('__name__', 'unknown')
        caller_info = f" at {caller_file}:{caller_line} in {caller_func}"
        logger = logging.getLogger(caller_module)
    else:
        logger = logging.getLogger(__name__)
    
    # Log the condition evaluation
    logger.log(
        level,
        f"CONDITION: '{condition_str}' evaluated to {result}{caller_info}"
    )
    
    return result

# JSON-formatted structured logging
class StructuredLogger:
    """Logger that outputs structured JSON logs with consistent format."""
    
    def __init__(self, name=None):
        """Initialize with a logger name."""
        self.logger = logging.getLogger(name or __name__)
    
    def _log(self, level, message, **extra):
        """Log a message with structured extra data."""
        # Get caller information
        frame = inspect.currentframe().f_back.f_back  # Skip the specific log method
        caller_info = {}
        if frame:
            caller_info = {
                'file': frame.f_code.co_filename,
                'line': frame.f_lineno,
                'function': frame.f_code.co_name,
                'module': frame.f_globals.get('__name__', 'unknown')
            }
        
        # Get thread information
        thread_info = {
            'thread_id': threading.get_ident(),
            'thread_name': threading.current_thread().name
        }
        
        # Get request context if available
        request_info = {}
        if has_request_context():
            request_info = {
                'url': request.url,
                'method': request.method,
                'endpoint': request.endpoint,
                'remote_addr': request.remote_addr
            }
            
            # Add user info if authenticated
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                request_info['user'] = {
                    'id': getattr(current_user, 'id', None),
                    'username': getattr(current_user, 'username', None)
                }
        
        # Combine all data
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': logging.getLevelName(level),
            'message': message,
            'logger': self.logger.name,
            'caller': caller_info,
            'thread': thread_info
        }
        
        # Add request context if available
        if request_info:
            log_data['request'] = request_info
            
        # Add extra data provided by the caller
        if extra:
            # Sanitize any sensitive data
            sanitized_extra = {}
            for k, v in extra.items():
                if _is_sensitive_param(k):
                    sanitized_extra[k] = "***REDACTED***"
                else:
                    sanitized_extra[k] = v
                    
            log_data['extra'] = sanitized_extra
        
        # Convert to JSON and log
        try:
            json_data = json.dumps(log_data, default=str)
            self.logger.log(level, json_data)
        except Exception as e:
            # Fallback if JSON conversion fails
            self.logger.error(f"Failed to create JSON log: {str(e)}")
            self.logger.log(level, message, extra=extra)
    
    def debug(self, message, **extra):
        """Log a DEBUG level message."""
        self._log(logging.DEBUG, message, **extra)
    
    def info(self, message, **extra):
        """Log an INFO level message."""
        self._log(logging.INFO, message, **extra)
    
    def warning(self, message, **extra):
        """Log a WARNING level message."""
        self._log(logging.WARNING, message, **extra)
    
    def error(self, message, **extra):
        """Log an ERROR level message."""
        self._log(logging.ERROR, message, **extra)
    
    def critical(self, message, **extra):
        """Log a CRITICAL level message."""
        self._log(logging.CRITICAL, message, **extra)
    
    def exception(self, message, **extra):
        """Log an exception with traceback."""
        # Add exception info to the log
        exc_type, exc_value, exc_traceback = traceback.exc_info()
        extra['exception'] = {
            'type': exc_type.__name__ if exc_type else None,
            'message': str(exc_value) if exc_value else None,
            'traceback': traceback.format_exc() if exc_traceback else None
        }
        
        self._log(logging.ERROR, message, **extra)

# Request context logging
def log_request_context(app):
    """Configure request context logging for Flask."""
    
    @app.before_request
    def log_request_start():
        """Log the start of a request with detailed information."""
        logger = logging.getLogger('request')
        
        # Generate a unique ID for this request
        request_id = str(uuid.uuid4())
        g.request_id = request_id
        g.request_start_time = time.time()
        
        # Build request information
        request_info = {
            'id': request_id,
            'method': request.method,
            'url': request.url,
            'endpoint': request.endpoint,
            'remote_addr': request.remote_addr,
            'user_agent': str(request.user_agent),
            'content_type': request.content_type,
            'content_length': request.content_length,
        }
        
        # Add query parameters if present
        if request.args:
            request_info['query_params'] = _safe_repr(request.args.to_dict())
            
        # Add form data if present (and not a file upload)
        if request.form and not request.files and request.content_type != 'multipart/form-data':
            form_data = request.form.to_dict()
            # Filter sensitive data
            for key in list(form_data.keys()):
                if _is_sensitive_param(key):
                    form_data[key] = "***REDACTED***"
            request_info['form_data'] = _safe_repr(form_data)
            
        # Add file upload information if present
        if request.files:
            files_info = {}
            for name, file in request.files.items():
                files_info[name] = {
                    'filename': file.filename,
                    'content_type': file.content_type,
                    'size': len(file.read()) if file.content_length is None else file.content_length
                }
                # Reset file position after reading
                if hasattr(file, 'seek'):
                    file.seek(0)
            request_info['files'] = files_info
            
        # Add headers (excluding sensitive ones)
        headers = {}
        for name, value in request.headers:
            if name.lower() in ('authorization', 'cookie', 'x-csrf-token'):
                headers[name] = "***REDACTED***"
            else:
                headers[name] = value
        request_info['headers'] = headers
        
        # Add user information if authenticated
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            request_info['user'] = {
                'id': getattr(current_user, 'id', None),
                'username': getattr(current_user, 'username', None)
            }
            
        # Log the request start
        logger.info(f"REQUEST START: {request.method} {request.path}", extra={'request': request_info})
        
        # Store request info for later
        g.request_info = request_info
        
    @app.after_request
    def log_request_end(response):
        """Log the end of a request with response information."""
        if not hasattr(g, 'request_start_time'):
            return response
            
        # Calculate request duration
        duration = time.time() - g.request_start_time
        
        # Get request ID
        request_id = getattr(g, 'request_id', 'unknown')
        
        # Build response information
        response_info = {
            'status_code': response.status_code,
            'content_type': response.content_type,
            'content_length': response.content_length,
            'duration_ms': int(duration * 1000)
        }
        
        # Add response headers
        response_info['headers'] = dict(response.headers)
        
        # Determine log level based on status code
        level = logging.INFO
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING
            
        # Log the response
        logger = logging.getLogger('request')
        logger.log(
            level,
            f"REQUEST END: {request.method} {request.path} - {response.status_code} - {duration:.4f}s",
            extra={'request_id': request_id, 'response': response_info}
        )
        
        # Add request ID and timing headers in debug mode
        if current_app.debug:
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Response-Time'] = f"{duration:.4f}s"
            
        return response
        
    @app.teardown_request
    def log_request_errors(exception):
        """Log any unhandled exceptions during the request."""
        if exception is None:
            return
            
        # Get request ID
        request_id = getattr(g, 'request_id', 'unknown')
        
        # Log the exception with full details
        logger = logging.getLogger('exceptions')
        logger.error(
            f"UNHANDLED EXCEPTION: {type(exception).__name__}: {str(exception)} - "
            f"Request ID: {request_id}",
            exc_info=True
        )
        
# Database query and model change logging
class DatabaseLogger:
    """Database operation logger for SQLAlchemy."""
    
    @staticmethod
    def setup(db, app):
        """Configure database logging for the application."""
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        from flask_sqlalchemy import get_state
        
        # Track query execution time
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log query before execution."""
            # Store the start time in connection info
            conn.info.setdefault('query_start_time', []).append(time.time())
            
            # Add request context info
            if has_request_context():
                # Get request ID from g if available
                request_id = getattr(g, 'request_id', None) or 'unknown'
                
                conn.info.setdefault('request_context', {})
                conn.info['request_context'] = {
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.path,
                    'user_id': getattr(current_user, 'id', None) if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                }
                
            # Log the query
            logger = logging.getLogger('database')
            
            # Get query type for logging categorization
            query_type = statement.split()[0].lower() if statement else "unknown"
            
            # Format parameters for logging (sanitizing sensitive data)
            safe_params = None
            if parameters:
                if isinstance(parameters, dict):
                    # Sanitize sensitive parameters in dictionaries
                    safe_params = {}
                    for k, v in parameters.items():
                        if _is_sensitive_param(k):
                            safe_params[k] = "***REDACTED***"
                        else:
                            safe_params[k] = v
                else:
                    # For non-dict parameters, just use as is
                    safe_params = parameters
            
            # Log the query with different levels based on query type
            level = logging.DEBUG
            
            # Use higher levels for data-modifying operations
            if query_type in ('insert', 'update', 'delete'):
                level = logging.INFO
                
            logger.log(
                level, 
                f"DB QUERY START: {query_type.upper()} - {statement[:1000]}" +
                (f" - Parameters: {_safe_repr(safe_params)}" if safe_params else "")
            )
            
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log query after execution with results."""
            if not conn.info.get('query_start_time'):
                return
                
            # Calculate execution time
            total_time = time.time() - conn.info['query_start_time'].pop()
            
            # Get request context info
            request_context = conn.info.get('request_context', {})
            request_id = request_context.get('request_id', 'unknown')
            
            # Get affected rows or result count
            result_count = -1
            if hasattr(cursor, 'rowcount'):
                result_count = cursor.rowcount
                
            # Get query type
            query_type = statement.split()[0].lower() if statement else "unknown"
            
            # Determine log level based on execution time and query type
            level = logging.DEBUG
            
            if total_time > 1.0:  # Very slow queries (>1s)
                level = logging.WARNING
            elif total_time > 0.1:  # Moderately slow (>100ms)
                level = logging.INFO
                
            # Use higher levels for data-modifying operations
            if query_type in ('insert', 'update', 'delete'):
                level = max(level, logging.INFO)
                
            logger = logging.getLogger('database')
            logger.log(
                level,
                f"DB QUERY END: {query_type.upper()} took {total_time:.4f}s - "
                f"Affected rows: {result_count} - Request ID: {request_id}"
            )
            
            # Log slow queries with more details
            if total_time > 0.5:  # Threshold for detailed logging
                logger.warning(
                    f"SLOW DB QUERY: {total_time:.4f}s - {statement[:1000]} - "
                    f"Request: {request_context.get('method', 'N/A')} {request_context.get('path', 'N/A')}"
                )
                
        # Track model changes
        @event.listens_for(db.session, 'before_flush')
        def log_model_changes(session, flush_context, instances):
            """Log model changes before they are committed to the database."""
            logger = logging.getLogger('database')
            
            # Track new instances
            for instance in session.new:
                model_name = instance.__class__.__name__
                
                # Try to get a useful identifier
                identifier = "<no id>"
                if hasattr(instance, 'id') and instance.id is not None:
                    identifier = f"id={instance.id}"
                elif hasattr(instance, 'name') and instance.name is not None:
                    identifier = f"name={instance.name}"
                    
                # Log the creation
                logger.info(f"DB CREATE: New {model_name}({identifier})")
                
                # In debug mode, log all attributes
                if app.debug:
                    attrs = {}
                    for key, value in instance.__dict__.items():
                        if not key.startswith('_'):
                            if _is_sensitive_param(key):
                                attrs[key] = "***REDACTED***"
                            else:
                                attrs[key] = _safe_repr(value)
                                
                    logger.debug(f"DB CREATE DETAILS: {model_name}({identifier}) - {attrs}")
                    
            # Track dirty (modified) instances
            for instance in session.dirty:
                if not session.is_modified(instance):
                    continue
                    
                model_name = instance.__class__.__name__
                
                # Try to get a useful identifier
                identifier = "<no id>"
                if hasattr(instance, 'id') and instance.id is not None:
                    identifier = f"id={instance.id}"
                elif hasattr(instance, 'name') and instance.name is not None:
                    identifier = f"name={instance.name}"
                    
                # Log the update
                logger.info(f"DB UPDATE: Modified {model_name}({identifier})")
                
                # In debug mode, log attribute changes
                if app.debug:
                    # Get attribute changes
                    changes = {}
                    for attr in instance.__dict__:
                        if attr.startswith('_'):
                            continue
                            
                        # Try to get history
                        history = db.session.get_history(instance, attr)
                        if history.has_changes():
                            # Format the change
                            if _is_sensitive_param(attr):
                                changes[attr] = {
                                    'old': "***REDACTED***",
                                    'new': "***REDACTED***"
                                }
                            else:
                                changes[attr] = {
                                    'old': _safe_repr(history.deleted[0] if history.deleted else None),
                                    'new': _safe_repr(history.added[0] if history.added else None)
                                }
                                
                    if changes:
                        logger.debug(f"DB UPDATE DETAILS: {model_name}({identifier}) - Changes: {changes}")
                        
            # Track deleted instances
            for instance in session.deleted:
                model_name = instance.__class__.__name__
                
                # Try to get a useful identifier
                identifier = "<no id>"
                if hasattr(instance, 'id') and instance.id is not None:
                    identifier = f"id={instance.id}"
                elif hasattr(instance, 'name') and instance.name is not None:
                    identifier = f"name={instance.name}"
                    
                # Log the deletion
                logger.info(f"DB DELETE: Deleted {model_name}({identifier})")
                
        # Log session events
        @event.listens_for(db.session, 'after_commit')
        def log_after_commit(session):
            """Log after successful commit."""
            logger = logging.getLogger('database')
            
            # Count the changes
            new_count = len(session.new)
            update_count = sum(1 for instance in session.dirty if session.is_modified(instance))
            delete_count = len(session.deleted)
            
            if new_count > 0 or update_count > 0 or delete_count > 0:
                logger.info(f"DB COMMIT: {new_count} new, {update_count} updated, {delete_count} deleted")
                
        @event.listens_for(db.session, 'after_rollback')
        def log_after_rollback(session):
            """Log after rollback."""
            logger = logging.getLogger('database')
            
            # Count the changes that were rolled back
            new_count = len(session.new)
            update_count = sum(1 for instance in session.dirty if session.is_modified(instance))
            delete_count = len(session.deleted)
            
            logger.warning(f"DB ROLLBACK: {new_count} new, {update_count} updated, {delete_count} deleted operations rolled back")
            
        return db