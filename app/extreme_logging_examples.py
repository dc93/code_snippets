"""
Examples of how to use the extreme debugging and logging system in the application.

This module provides practical examples of applying the logging decorators and utilities
to various parts of the application code.
"""

import time
import random
from flask import Blueprint, render_template, request, jsonify, current_app
from .extreme_debug_implementation import (
    log_function, 
    LoggedBlock, 
    log_iterations, 
    log_condition, 
    StructuredLogger,
    log_attribute_access
)

# Create a blueprint for examples
examples_bp = Blueprint('examples', __name__)

# Create a structured logger
logger = StructuredLogger('examples')

# Example 1: Basic function logging with parameters and return value
@log_function(log_params=True, log_result=True)
def calculate_factorial(n):
    """Calculate factorial with full logging."""
    if n < 0:
        logger.error(f"Invalid input: {n} - factorial requires non-negative integer")
        raise ValueError("Factorial requires non-negative integer")
    
    if n == 0 or n == 1:
        return 1
    
    # Use a LoggedBlock to track the calculation
    with LoggedBlock("factorial_calculation", log_variables=True):
        result = 1
        # Use log_iterations to track the loop
        for i in log_iterations(range(2, n + 1), name="factorial_loop"):
            old_result = result
            result *= i
            # Manually log variable changes
            logger.debug(f"Factorial calculation step", step=i, old_result=old_result, new_result=result)
    
    return result

# Example 2: Class with attribute logging
@log_attribute_access
class ConfigSettings:
    """Example class with logged attributes."""
    
    def __init__(self, debug=False, max_items=100, cache_timeout=300):
        self.debug = debug
        self.max_items = max_items
        self.cache_timeout = cache_timeout
        self._private_val = "This won't be logged directly"
    
    @log_function()
    def update_settings(self, **kwargs):
        """Update settings with logging."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                # The attribute change is automatically logged by the class decorator
        
        return True

# Example 3: Route with comprehensive logging
@examples_bp.route('/example/<int:item_id>', methods=['GET', 'POST'])
@log_function(level=logging.INFO)
def example_route(item_id):
    """Example route with extensive logging."""
    logger.info(f"Processing example route", item_id=item_id, method=request.method)
    
    # Use log_condition for conditional logging
    if log_condition(item_id > 0, "item_id > 0"):
        # This block executes and logs when item_id > 0
        with LoggedBlock("processing_valid_item"):
            # Simulate database lookup
            time.sleep(0.1)
            item = {"id": item_id, "name": f"Item {item_id}", "status": "active"}
            logger.debug(f"Item found", item=item)
    else:
        # This is executed and logged when item_id <= 0
        logger.warning(f"Invalid item_id received", item_id=item_id)
        return jsonify({"error": "Invalid item ID"}), 400
    
    # Log different paths based on method
    if request.method == 'POST':
        with LoggedBlock("processing_post_data"):
            # Get form data
            data = request.form.to_dict()
            
            # Log data (sensitive fields will be automatically redacted)
            logger.info(f"Received form data", data=data)
            
            # Use log_condition again for form validation
            if log_condition('name' in data and data['name'], "name in data and data['name']"):
                # Update item (would be a database update in a real app)
                old_name = item['name']
                item['name'] = data['name']
                logger.info(f"Updated item name", item_id=item_id, old_name=old_name, new_name=item['name'])
                
                # Log successful result
                logger.info(f"Item update successful", item_id=item_id)
                return jsonify({"status": "success", "item": item})
            else:
                # Log validation failure
                logger.warning(f"Item update failed - name validation failed", data=data)
                return jsonify({"error": "Name is required"}), 400
    else:  # GET request
        # Log the request handling 
        logger.info(f"Returning item details", item_id=item_id)
        
        # Simulate random slow requests for performance tracking
        if random.random() < 0.2:  # 20% chance of a slow response
            time.sleep(1.5)
            logger.warning(f"Slow response generated for testing", item_id=item_id)
        
        return jsonify({"item": item})

# Example 4: Error handling with detailed logging
@examples_bp.route('/example/error/<error_type>')
@log_function()
def trigger_error(error_type):
    """Trigger different error types for testing error logging."""
    logger.info(f"Error example requested", error_type=error_type)
    
    with LoggedBlock("error_generation"):
        try:
            if error_type == 'value':
                # Generate a ValueError
                value = int("not_a_number")
            elif error_type == 'key':
                # Generate a KeyError
                data = {}
                result = data["nonexistent_key"]
            elif error_type == 'zero':
                # Generate a ZeroDivisionError
                result = 1 / 0
            elif error_type == 'custom':
                # Generate a custom application error
                logger.warning(f"Raising custom application error")
                raise ApplicationError("This is a custom application error for testing")
            else:
                # Invalid error type
                logger.warning(f"Unknown error type requested", error_type=error_type)
                return jsonify({"error": "Unknown error type"})
        except Exception as e:
            # Log the exception with full details
            logger.exception(f"Error occurred in example", error_type=error_type, error_class=e.__class__.__name__)
            
            # Return error information
            return jsonify({
                "error": str(e),
                "error_type": e.__class__.__name__,
                "message": "Error logged with full details"
            }), 500
    
    # This code won't be reached due to the exceptions
    return jsonify({"status": "success"})

# Example 5: Performance and database operation logging
@examples_bp.route('/example/performance')
@log_function()
def performance_example():
    """Example with performance tracking."""
    logger.info(f"Performance example requested")
    
    results = []
    
    # Track multiple operations with timing
    with LoggedBlock("database_simulation", log_variables=True):
        # Simulate expensive database operation
        time.sleep(0.5)
        db_results = [{"id": i, "value": f"Value {i}"} for i in range(1, 6)]
        
        # Process results with iteration logging
        for item in log_iterations(db_results, name="db_result_processing"):
            # Simulate per-item processing
            time.sleep(0.1)
            item['processed'] = True
            results.append(item)
            
        # Log completion
        logger.info(f"Database operation completed", result_count=len(results))
    
    # Simulate a cache operation
    with LoggedBlock("cache_operation"):
        cache_key = f"performance_results_{int(time.time())}"
        # Simulate cache storage
        time.sleep(0.2)
        logger.debug(f"Results cached", cache_key=cache_key, item_count=len(results))
    
    # Return the processed results
    return jsonify({
        "status": "success",
        "processing_time": "Timing details in logs",
        "results": results
    })

# Custom application error for testing
class ApplicationError(Exception):
    """Custom application error for testing."""
    pass


# Usage examples for documentation
def document_usage():
    """Document how to use the logging system (not an actual route)."""
    # 1. Function call tracking
    @log_function(level=logging.DEBUG, log_params=True, log_result=True)
    def my_function(param1, param2):
        # Function body
        return param1 + param2
    
    # 2. Code block tracking
    with LoggedBlock("important_operation", log_variables=True):
        value = 42
        # Some operations
        value += 10
    
    # 3. Loop tracking
    items = [1, 2, 3, 4, 5]
    for item in log_iterations(items, name="my_items"):
        # Process item
        pass
    
    # 4. Conditional tracking
    if log_condition(value > 50, "value > 50"):
        # This code executes when value > 50 and the condition is logged
        pass
    
    # 5. Structured logging
    logger = StructuredLogger("my_module")
    logger.info("Operation completed", duration=1.23, status="success")
    
    # 6. Attribute tracking
    @log_attribute_access
    class MyClass:
        def __init__(self):
            self.value = 0
            
        def increment(self):
            self.value += 1  # This change is automatically logged