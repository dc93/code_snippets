"""
Enhanced routes module with extreme logging applied.

This module contains routing functions with comprehensive logging applied
via decorators and context managers from the extreme_debug_implementation module.
"""

from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, abort, current_app, g
from flask_login import login_user, logout_user, current_user, login_required
from app import db, cache, limiter
from app.models import User, Snippet, Tag
from app.forms import LoginForm, RegistrationForm, SnippetForm, SearchForm
from datetime import datetime, timedelta
from sqlalchemy import or_, func
import uuid
import traceback
import secrets
import time

# Import extreme logging utilities
from app.extreme_debug_implementation import (
    log_function, 
    LoggedBlock, 
    log_iterations, 
    log_condition, 
    StructuredLogger,
    log_attribute_access,
    _safe_repr
)

# Create a structured logger
logger = StructuredLogger('app.routes')

# Blueprints
main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__, url_prefix='/auth')
snippets = Blueprint('snippets', __name__, url_prefix='/snippets')

# Main routes
@main.route('/')
@main.route('/index')
@cache.cached(timeout=60)
@log_function(level=logging.INFO)
def index():
    """Home page route."""
    # Import snippet_tags association table from models and query optimization
    from app.models import snippet_tags
    from app.db_optimizations import optimize_snippet_query, get_count

    with LoggedBlock("index_page_processing", log_variables=True):
        try:
            logger.debug("Processing index page request")
            
            # Show latest public snippets if setting enabled
            recent_snippets = []
            if log_condition(current_app.config['ENABLE_PUBLIC_SNIPPETS'], "config['ENABLE_PUBLIC_SNIPPETS']"):
                logger.debug("Fetching recent public snippets")
                # Use optimized query for snippets
                with LoggedBlock("query_recent_snippets"):
                    recent_snippets_query = Snippet.query.filter_by(is_public=True).order_by(
                        Snippet.created_at.desc()
                    ).limit(6)
                    recent_snippets = optimize_snippet_query(recent_snippets_query).all()
                logger.debug(f"Found {len(recent_snippets)} recent public snippets")
            else:
                logger.debug("Public snippets are disabled")

            # Optimize popular tags query with proper caching
            # This query is expensive, so we cache it for longer
            cache_key = 'popular_tags'
            popular_tags = None
            
            with LoggedBlock("fetch_popular_tags"):
                # Try to get from cache first
                popular_tags = cache.get(cache_key)
                
                if log_condition(popular_tags is None, "popular_tags is None"):
                    logger.debug("Popular tags not found in cache, querying database")
                    
                    # Execute the query
                    query_start = time.time()
                    popular_tags = db.session.query(
                        Tag, func.count(snippet_tags.c.snippet_id).label('snippet_count')
                    ).join(snippet_tags).group_by(Tag).order_by(
                        func.count(snippet_tags.c.snippet_id).desc()
                    ).limit(10).all()
                    query_time = time.time() - query_start
                    
                    logger.debug(f"Popular tags query executed in {query_time:.4f}s, found {len(popular_tags)} tags")
                    
                    # Cache popular tags for 30 minutes
                    cache.set(cache_key, popular_tags, timeout=1800)
                    logger.debug("Popular tags stored in cache with 30-minute timeout")
                else:
                    logger.debug(f"Found {len(popular_tags)} popular tags in cache")

            # Track template rendering time
            render_start = time.time()
            response = render_template('index.html',
                                    recent_snippets=recent_snippets,
                                    popular_tags=popular_tags)
            render_time = time.time() - render_start
            
            logger.debug(f"Template rendering completed in {render_time:.4f}s")
            
            return response
        except Exception as e:
            logger.exception("Error in index route", error=str(e))
            
            # Fallback to empty data on error
            return render_template('index.html',
                                recent_snippets=[],
                                popular_tags=[])

@main.route('/about')
@cache.cached(timeout=3600)  # Cache for 1 hour
@log_function()
def about():
    """About page route."""
    logger.debug("About page requested", user=getattr(current_user, 'id', None))
    return render_template('about.html')

@main.route('/search')
@log_function()
def search():
    """Search snippets route."""
    with LoggedBlock("search_processing", log_variables=True):
        # Import snippet_tags association table from models if needed
        from app.models import snippet_tags
        
        # Track performance
        search_start = time.time()
        
        form = SearchForm()
        query = request.args.get('q', '')
        
        logger.debug(f"Processing search request", query=query)
        
        snippets = []
        if query:
            # Log search query for analytics
            logger.info(f"User search query", 
                        query=query, 
                        user_id=getattr(current_user, 'id', None),
                        ip_address=request.remote_addr)
            
            # Search in title, description and tags
            with LoggedBlock("search_database_query"):
                snippets_query = Snippet.query.filter(
                    Snippet.is_public == True,
                    or_(
                        Snippet.title.ilike(f'%{query}%'),
                        Snippet.description.ilike(f'%{query}%'),
                        Snippet.language.ilike(f'%{query}%'),
                        Snippet.tags.any(Tag.name.ilike(f'%{query}%'))
                    )
                ).order_by(Snippet.created_at.desc())
                
                # Execute query
                snippets = snippets_query.all()
            
            logger.debug(f"Search found {len(snippets)} matching snippets")
        
        # Calculate execution time
        search_time = time.time() - search_start
        logger.debug(f"Search completed in {search_time:.4f}s")
        
        # Set metrics in request context
        g.search_time = search_time
        g.result_count = len(snippets)
        
        # Log slow searches
        if search_time > 0.5:  # More than 500ms is considered slow
            logger.warning(f"Slow search query detected", 
                          query=query, 
                          execution_time=search_time,
                          result_count=len(snippets))
        
        return render_template('search.html', 
                               form=form, 
                               query=query, 
                               snippets=snippets)

# Auth routes
@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("10/minute")
@log_function(level=logging.INFO)
def login():
    """User login route."""
    # Log route access with request details
    logger.info(f"Login route accessed", 
               method=request.method, 
               ip=request.remote_addr, 
               user_agent=request.headers.get('User-Agent', 'Unknown'),
               route="auth.login")

    # Track authenticated users
    if log_condition(current_user.is_authenticated, "current_user.is_authenticated"):
        logger.debug(f"Already authenticated user accessing login page",
                   username=current_user.username,
                   user_id=current_user.id)
        return redirect(url_for('main.index'))

    form = LoginForm()
    
    # Handle form submission
    if request.method == 'POST':
        with LoggedBlock("login_post_processing", log_variables=True):
            logger.debug(f"Processing login POST request", ip=request.remote_addr)
            
            try:
                # Log attempt (username only, never log passwords)
                logger.debug(f"Login attempt", username=form.username.data)
                
                # Explicitly validate the form
                if log_condition(form.validate(), "form.validate()"):
                    logger.debug("Form validation passed")
                    
                    # Find user
                    with LoggedBlock("user_lookup"):
                        user = User.query.filter_by(username=form.username.data).first()
                    
                    if not log_condition(user is not None, "user is not None"):
                        logger.debug(f"Login failed - username not found", 
                                   username=form.username.data,
                                   ip=request.remote_addr)
                        # Use generic message for security
                        flash('Invalid username or password', 'danger')
                        return render_template('login.html', form=form)
                    
                    # Check account lock status
                    if log_condition(user and user.is_locked_out, "user and user.is_locked_out"):
                        logger.warning(f"Attempted login to locked account", 
                                     username=user.username, 
                                     ip=request.remote_addr,
                                     locked_until=user.locked_until)
                        flash('Account is temporarily locked due to too many failed attempts. Please try again later.', 'danger')
                    elif user:
                        # Store the password check result but don't modify user object yet
                        with LoggedBlock("password_verification"):
                            password_correct = user.check_password(form.password.data, check_only=True)
                        
                        if log_condition(password_correct, "password_correct"):
                            # Log successful verification
                            logger.debug("Password verification successful")
                            
                            # Update user data in database with session management
                            try:
                                with LoggedBlock("update_user_login_data"):
                                    # Set all attributes in one go to minimize race conditions
                                    user.last_login = datetime.utcnow()
                                    user.failed_login_attempts = 0
                                    user.locked_until = None
                                    
                                    db.session.add(user)
                                    db.session.commit()
                                
                                logger.debug(f"Updated user login timestamp", username=user.username)
                                
                                # Only log in after successful database update
                                logger.info(f"Successful login", 
                                          username=user.username, 
                                          user_id=user.id,
                                          ip=request.remote_addr)
                                
                                # Log remember me choice
                                logger.debug(f"Remember me setting", 
                                           remember=form.remember.data)
                                
                                login_user(user, remember=form.remember.data)
                                
                            except Exception as e:
                                db.session.rollback()
                                logger.error(f"Database error during login", 
                                           error=str(e),
                                           traceback=traceback.format_exc())
                                flash('A database error occurred. Please try again.', 'danger')
                                return render_template('login.html', form=form)
                            
                            # Validate the next parameter to prevent open redirect
                            next_page = request.args.get('next')
                            logger.debug(f"Redirect 'next' parameter", next_page=next_page)
                            
                            if log_condition(next_page and not next_page.startswith('/'), 
                                          "next_page and not next_page.startswith('/')"):
                                # Only allow relative URLs
                                logger.warning(f"Blocked potential open redirect", 
                                             target_url=next_page, 
                                             username=user.username)
                                next_page = None
                            
                            from app.security import is_safe_url
                            if log_condition(not next_page or not is_safe_url(next_page), 
                                          "not next_page or not is_safe_url(next_page)"):
                                next_page = url_for('main.index')
                                logger.debug(f"Using default redirect", url=next_page)
                            
                            return redirect(next_page)
                        else:
                            # Handle failed login attempt in database with proper transaction
                            try:
                                with LoggedBlock("update_failed_login_attempts"):
                                    # Update failed login attempts
                                    user.failed_login_attempts += 1
                                    
                                    # Lock account after 5 failed attempts
                                    if user.failed_login_attempts >= 5:
                                        lock_time = datetime.utcnow() + timedelta(minutes=15)
                                        user.locked_until = lock_time
                                        logger.warning(
                                            f"Account locked due to too many failed attempts", 
                                            username=user.username,
                                            ip=request.remote_addr,
                                            attempt_count=user.failed_login_attempts,
                                            locked_until=lock_time
                                        )
                                    else:
                                        logger.warning(
                                            f"Failed login attempt", 
                                            username=user.username,
                                            ip=request.remote_addr, 
                                            attempt_count=user.failed_login_attempts
                                        )
                                    
                                    db.session.add(user)
                                    db.session.commit()
                                
                                logger.debug(f"Updated failed login attempts", 
                                           username=user.username,
                                           count=user.failed_login_attempts)
                            except Exception as e:
                                db.session.rollback()
                                logger.error(f"Database error updating failed attempts", 
                                           error=str(e), 
                                           traceback=traceback.format_exc())
                            
                            flash('Invalid username or password', 'danger')
                    else:
                        flash('Invalid username or password', 'danger')
                else:
                    logger.debug(f"Form validation failed", errors=form.errors)
                    # Handle CSRF errors differently (just show generic message for security)
                    if 'csrf_token' in form.errors:
                        logger.warning(f"CSRF validation failed during login", 
                                     ip=request.remote_addr,
                                     user_agent=request.headers.get('User-Agent'))
                        flash('Form validation failed. Please try again.', 'danger')
                    else:
                        # Show field-specific errors for non-CSRF issues
                        for field, errors in form.errors.items():
                            for error in errors:
                                logger.debug(f"Form field error", field=field, error=error)
                                flash(f"{field}: {error}", 'danger')
            except Exception as e:
                db.session.rollback()  # Ensure transaction is rolled back on error
                logger.error(f"Login error", 
                           error=str(e), 
                           traceback=traceback.format_exc())
                flash('An error occurred during login. Please try again.', 'danger')

    # Log rendering of login template
    logger.debug("Rendering login template")
    return render_template('login.html', form=form)

@auth.route('/logout')
@log_function(level=logging.INFO)
def logout():
    """User logout route."""
    username = "anonymous"
    user_id = None
    
    if log_condition(current_user.is_authenticated, "current_user.is_authenticated"):
        username = current_user.username
        user_id = current_user.id
        logger.debug(f"Logout request", 
                   username=username, 
                   user_id=user_id,
                   ip=request.remote_addr)

    with LoggedBlock("user_logout_process"):
        logout_user()
    
    logger.info(f"User logged out", 
               username=username, 
               user_id=user_id,
               ip=request.remote_addr)
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

@auth.route('/confirm/<token>')
@log_function(level=logging.INFO)
def confirm_email(token):
    """Email confirmation route."""
    logger.info(f"Email confirmation attempt", 
               token_hash=hash(token),  # Log hash instead of actual token for security
               ip=request.remote_addr)
    
    # Handle if user is already authenticated and confirmed
    if log_condition(current_user.is_authenticated and current_user.email_confirmed,
                  "current_user.is_authenticated and current_user.email_confirmed"):
        logger.debug(f"Already confirmed user accessing confirmation link",
                   username=current_user.username,
                   user_id=current_user.id)
        flash('Your email is already confirmed!', 'info')
        return redirect(url_for('main.index'))

    # Find user by token
    with LoggedBlock("token_verification"):
        user = User.query.filter_by(email_confirm_token=token).first()

    if not log_condition(user is not None, "user is not None"):
        logger.warning(f"Invalid confirmation token used",
                     token_hash=hash(token),
                     ip=request.remote_addr)
        flash('Invalid or expired confirmation link.', 'danger')
        return redirect(url_for('auth.login'))

    # Confirm email
    with LoggedBlock("email_confirmation_process"):
        confirmation_result = user.confirm_email(token)
    
    if log_condition(confirmation_result, "confirmation_result"):
        # Update user's email_confirmed status
        with LoggedBlock("database_commit"):
            db.session.commit()
            
        logger.info(f"Email confirmed successfully", 
                   username=user.username, 
                   user_id=user.id,
                   ip=request.remote_addr)
        flash('Your email has been confirmed! You can now log in.', 'success')

        # If user is already logged in, refresh login session
        if log_condition(current_user.is_authenticated and current_user.id == user.id,
                      "current_user.is_authenticated and current_user.id == user.id"):
            logger.debug(f"Refreshing login session after confirmation",
                       username=user.username,
                       user_id=user.id)
            login_user(user)
    else:
        logger.warning(f"Expired/invalid token used for confirmation", 
                     username=user.username, 
                     user_id=user.id,
                     ip=request.remote_addr)
        flash('The confirmation link has expired or is invalid.', 'danger')

    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit("5/hour")
@log_function(level=logging.INFO)
def register():
    """User registration route."""
    # Log route access with detailed request information
    logger.info(f"Register route accessed", 
               method=request.method, 
               ip=request.remote_addr, 
               user_agent=request.headers.get('User-Agent', 'Unknown'))

    if log_condition(current_user.is_authenticated, "current_user.is_authenticated"):
        logger.debug(f"Already authenticated user accessing register page", 
                   username=current_user.username)
        return redirect(url_for('main.index'))

    # Check if registration is enabled
    if not log_condition(current_app.config['ENABLE_REGISTRATION'], "current_app.config['ENABLE_REGISTRATION']"):
        logger.warning(f"Registration attempt when disabled", ip=request.remote_addr)
        flash('Registration is currently disabled', 'warning')
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    
    if request.method == 'POST':
        with LoggedBlock("registration_post_processing", log_variables=True):
            logger.debug(f"Processing registration POST request", ip=request.remote_addr)
            
            try:
                # Validate CSRF token manually first
                from app.security import require_csrf
                if not log_condition(require_csrf(request), "require_csrf(request)"):
                    logger.warning(f"CSRF validation failed during registration", 
                                 ip=request.remote_addr)
                    flash('Security validation failed. Please refresh the page and try again.', 'danger')
                    return render_template('register.html', form=form)

                # Log form data for debugging (excluding password)
                logger.debug(f"Registration attempt", 
                           username=form.username.data, 
                           email=form.email.data)

                if log_condition(form.validate(), "form.validate()"):
                    logger.debug("Registration form validation passed")
                    
                    try:
                        # Check for existing username/email before creating user
                        with LoggedBlock("check_existing_credentials"):
                            existing_username = User.query.filter_by(username=form.username.data).first()
                            existing_email = User.query.filter_by(email=form.email.data).first()

                        if log_condition(existing_username is not None, "existing_username is not None"):
                            logger.debug(f"Registration attempt with existing username", 
                                       username=form.username.data)
                            flash('Username already exists. Please choose a different one.', 'danger')
                            return render_template('register.html', form=form)

                        if log_condition(existing_email is not None, "existing_email is not None"):
                            logger.debug(f"Registration attempt with existing email", 
                                       email=form.email.data)
                            flash('Email already registered. Please use a different one.', 'danger')
                            return render_template('register.html', form=form)

                        # Create new user object
                        with LoggedBlock("user_creation"):
                            user = User(
                                username=form.username.data,
                                email=form.email.data,
                                email_confirmed=False  # Require email confirmation
                            )
                            user.set_password(form.password.data)
                        
                        logger.debug(f"Created new user object", username=user.username)

                        # Generate email confirmation token
                        with LoggedBlock("token_generation"):
                            token = user.generate_email_token()
                        
                        logger.debug(f"Generated confirmation token", 
                                   username=user.username,
                                   token_hash=hash(token))

                        with LoggedBlock("database_commit"):
                            db.session.add(user)
                            db.session.commit()
                        
                        logger.info(f"New user registered", 
                                  username=user.username, 
                                  email=user.email, 
                                  user_id=user.id,
                                  ip=request.remote_addr)

                        # Send confirmation email
                        try:
                            with LoggedBlock("send_confirmation_email"):
                                from app.utils import send_email_confirmation
                                send_email_confirmation(user)
                            
                            logger.debug(f"Confirmation email sent", 
                                       username=user.username,
                                       email=user.email)
                            flash('Registration successful! Please check your email to confirm your account.', 'success')
                        except Exception as e:
                            logger.error(f"Failed to send confirmation email", 
                                       error=str(e),
                                       username=user.username,
                                       email=user.email)
                            # Log the token for development purposes
                            logger.info(f"Email confirmation token", 
                                      username=user.username, 
                                      token_hash=hash(token))
                            flash('Registration successful! Email confirmation is temporarily unavailable.', 'warning')

                        return redirect(url_for('auth.login'))
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Database error during registration", 
                                   error=str(e),
                                   traceback=traceback.format_exc())
                        # Log IP address for potential abuse detection
                        logger.warning(f"Failed registration attempt", ip=request.remote_addr)
                        flash('An error occurred during registration. Please try again.', 'danger')
                else:
                    logger.debug(f"Registration form validation failed", errors=form.errors)
                    # Handle CSRF errors differently (just show generic message for security)
                    if 'csrf_token' in form.errors:
                        logger.warning(f"CSRF validation failed during registration", 
                                     ip=request.remote_addr)
                        flash('Form validation failed. Please try again.', 'danger')
                    else:
                        # Show field-specific errors for non-CSRF issues
                        for field, errors in form.errors.items():
                            for error in errors:
                                logger.debug(f"Form field error", field=field, error=error)
                                flash(f"{field}: {error}", 'danger')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Unexpected error during registration", 
                           error=str(e),
                           traceback=traceback.format_exc())
                flash('An unexpected error occurred. Please try again later.', 'danger')

    # Generate a new CSRF token for GET requests to ensure freshness
    if request.method == 'GET':
        with LoggedBlock("generate_csrf_token"):
            from flask import session
            session['csrf_token'] = secrets.token_hex(32)
        
        logger.debug("Generated fresh CSRF token for registration form")

    # Log template rendering
    logger.debug("Rendering registration template")
    return render_template('register.html', form=form)

# Snippet routes
@snippets.route('/create', methods=['GET', 'POST'])
@login_required
@log_function()
def create():
    """Create new snippet route."""
    logger.debug(f"Snippet creation page accessed",
                user_id=current_user.id,
                username=current_user.username)
                
    form = SnippetForm()

    try:
        # Get available tags for the form
        with LoggedBlock("fetch_all_tags"):
            all_tags = Tag.query.all()
            form.tags.choices = [(tag.id, tag.name) for tag in all_tags]
            logger.debug(f"Loaded {len(all_tags)} tags for form")

        if form.validate_on_submit():
            with LoggedBlock("snippet_creation", log_variables=True):
                try:
                    # Generate unique ID
                    snippet_id = str(uuid.uuid4())
                    logger.debug(f"Generated snippet ID", id=snippet_id)
                    
                    # Process and save snippet
                    snippet = Snippet(
                        id=snippet_id,
                        title=form.title.data,
                        description=form.description.data,
                        code=form.code.data,
                        language=form.language.data,
                        is_public=form.is_public.data,
                        user_id=current_user.id
                    )
                    
                    logger.debug(f"Created snippet object", 
                               id=snippet_id,
                               title=form.title.data,
                               language=form.language.data,
                               is_public=form.is_public.data,
                               code_length=len(form.code.data))

                    # Add selected tags
                    with LoggedBlock("process_selected_tags"):
                        selected_tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
                        snippet.tags = selected_tags
                        logger.debug(f"Added {len(selected_tags)} existing tags to snippet")

                    # Add new tags if provided
                    if form.new_tags.data:
                        with LoggedBlock("process_new_tags"):
                            new_tag_names = [t.strip() for t in form.new_tags.data.split(',')]
                            new_tags_added = 0
                            
                            for tag_name in log_iterations(new_tag_names, "new_tag_names"):
                                if tag_name:
                                    tag = Tag.query.filter_by(name=tag_name).first()
                                    if not tag:
                                        tag = Tag(name=tag_name)
                                        db.session.add(tag)
                                        logger.debug(f"Created new tag", name=tag_name)
                                        new_tags_added += 1
                                    snippet.tags.append(tag)
                                    
                            logger.debug(f"Processed new tags", 
                                       count=len(new_tag_names),
                                       added=new_tags_added)

                    # Save to database
                    with LoggedBlock("database_commit"):
                        db.session.add(snippet)
                        db.session.commit()

                    logger.info(f"New snippet created", 
                               snippet_id=snippet.id,
                               user_id=current_user.id,
                               username=current_user.username,
                               is_public=snippet.is_public)
                    flash('Snippet created successfully!', 'success')
                    return redirect(url_for('snippets.view', snippet_id=snippet.id))
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error creating snippet", 
                               error=str(e),
                               traceback=traceback.format_exc())
                    flash('An error occurred while creating your snippet. Please try again.', 'danger')
        elif request.method == 'POST':
            logger.debug(f"Snippet creation form validation failed", errors=form.errors)
            # Handle CSRF errors differently (just show generic message for security)
            if 'csrf_token' in form.errors:
                logger.warning(f"CSRF validation failed during snippet creation", 
                             ip=request.remote_addr)
                flash('Form validation failed. Please try again.', 'danger')
            else:
                # Show field-specific errors for non-CSRF issues
                for field, errors in form.errors.items():
                    for error in errors:
                        logger.debug(f"Form field error", field=field, error=error)
                        flash(f"{field}: {error}", 'danger')
    except Exception as e:
        logger.error(f"Unexpected error in snippet creation", 
                   error=str(e),
                   traceback=traceback.format_exc())
        flash('An unexpected error occurred. Please try again later.', 'danger')

    return render_template('snippets/create.html', form=form)

@snippets.route('/<snippet_id>')
@log_function()
def view(snippet_id):
    """View single snippet route."""
    with LoggedBlock("view_snippet", log_variables=True):
        logger.debug(f"Viewing snippet", 
                   snippet_id=snippet_id,
                   user_id=getattr(current_user, 'id', None))
                   
        # Fetch snippet with optimized query
        with LoggedBlock("fetch_snippet"):
            snippet = Snippet.query.get_or_404(snippet_id)
            logger.debug(f"Found snippet", 
                       title=snippet.title,
                       author=snippet.author.username if snippet.author else 'unknown',
                       language=snippet.language)
        
        # Check if snippet is public or user is the author
        if not log_condition(snippet.is_public or (current_user.is_authenticated and current_user.id == snippet.user_id),
                          "snippet.is_public or (current_user.is_authenticated and current_user.id == snippet.user_id)"):
            logger.warning(f"Unauthorized snippet access attempt", 
                         snippet_id=snippet_id,
                         user_id=getattr(current_user, 'id', None),
                         ip=request.remote_addr)
            abort(403)  # Forbidden
        
        # Increment view count using the model method
        with LoggedBlock("increment_view_count"):
            snippet.increment_view()
            db.session.commit()
            # Reset the view_count_only flag after committing
            snippet._view_count_only = False
            logger.debug(f"Incremented view count", 
                       snippet_id=snippet_id,
                       new_count=snippet.views)
        
        return render_template('snippets/view.html', snippet=snippet)

@snippets.route('/<snippet_id>/edit', methods=['GET', 'POST'])
@login_required
@log_function()
def edit(snippet_id):
    """Edit snippet route."""
    with LoggedBlock("edit_snippet", log_variables=True):
        logger.debug(f"Editing snippet", 
                  snippet_id=snippet_id,
                  user_id=current_user.id)
                  
        # Fetch snippet
        with LoggedBlock("fetch_snippet"):
            snippet = Snippet.query.get_or_404(snippet_id)
            logger.debug(f"Found snippet to edit", 
                      title=snippet.title,
                      author_id=snippet.user_id)
        
        # Check if user is the author
        if not log_condition(current_user.id == snippet.user_id, "current_user.id == snippet.user_id"):
            logger.warning(f"Unauthorized snippet edit attempt", 
                        snippet_id=snippet_id,
                        user_id=current_user.id,
                        owner_id=snippet.user_id,
                        ip=request.remote_addr)
            abort(403)  # Forbidden
        
        form = SnippetForm()
        
        # Get available tags for the form
        with LoggedBlock("get_available_tags"):
            all_tags = Tag.query.all()
            form.tags.choices = [(tag.id, tag.name) for tag in all_tags]
            logger.debug(f"Loaded {len(all_tags)} tags for form")
        
        if request.method == 'GET':
            with LoggedBlock("populate_form"):
                # Populate form with snippet data
                form.title.data = snippet.title
                form.description.data = snippet.description
                form.code.data = snippet.code
                form.language.data = snippet.language
                form.is_public.data = snippet.is_public
                form.tags.data = [tag.id for tag in snippet.tags]
                logger.debug(f"Populated form with existing snippet data")
        
        if form.validate_on_submit():
            with LoggedBlock("update_snippet"):
                # Track old values for logging
                old_values = {
                    'title': snippet.title,
                    'description': snippet.description,
                    'language': snippet.language,
                    'is_public': snippet.is_public,
                    'code_length': len(snippet.code),
                    'tags': [tag.name for tag in snippet.tags]
                }
                
                # Update snippet
                snippet.title = form.title.data
                snippet.description = form.description.data
                snippet.code = form.code.data
                snippet.language = form.language.data
                snippet.is_public = form.is_public.data
                
                logger.debug(f"Updated snippet fields", 
                          title_changed=(old_values['title'] != snippet.title),
                          language_changed=(old_values['language'] != snippet.language),
                          visibility_changed=(old_values['is_public'] != snippet.is_public),
                          code_size_changed=(old_values['code_length'] != len(snippet.code)))
                
                # Update tags
                with LoggedBlock("update_tags"):
                    selected_tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
                    snippet.tags = selected_tags
                    
                    # Add new tags if provided
                    new_tags_added = 0
                    if form.new_tags.data:
                        new_tag_names = [t.strip() for t in form.new_tags.data.split(',')]
                        for tag_name in log_iterations(new_tag_names, "new_tag_names"):
                            if tag_name:
                                tag = Tag.query.filter_by(name=tag_name).first()
                                if not tag:
                                    tag = Tag(name=tag_name)
                                    db.session.add(tag)
                                    new_tags_added += 1
                                snippet.tags.append(tag)
                    
                    new_tags = [tag.name for tag in snippet.tags]
                    logger.debug(f"Updated snippet tags", 
                              old_tags=old_values['tags'],
                              new_tags=new_tags,
                              new_tags_added=new_tags_added)
                
                with LoggedBlock("save_changes"):
                    db.session.commit()
                
                logger.info(f"Snippet updated", 
                          snippet_id=snippet.id,
                          user_id=current_user.id,
                          username=current_user.username)
                flash('Snippet updated successfully!', 'success')
                return redirect(url_for('snippets.view', snippet_id=snippet.id))
            
        elif request.method == 'POST':
            logger.debug(f"Snippet edit form validation failed", errors=form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{field}: {error}", 'danger')
        
        return render_template('snippets/edit.html', form=form, snippet=snippet)

@snippets.route('/<snippet_id>/delete', methods=['POST'])
@login_required
@log_function(level=logging.INFO)
def delete(snippet_id):
    """Delete snippet route."""
    with LoggedBlock("delete_snippet", log_variables=True):
        logger.info(f"Snippet deletion requested", 
                  snippet_id=snippet_id,
                  user_id=current_user.id)
                  
        # Fetch snippet
        with LoggedBlock("fetch_snippet"):
            snippet = Snippet.query.get_or_404(snippet_id)
            logger.debug(f"Found snippet to delete", 
                      title=snippet.title,
                      author_id=snippet.user_id)
        
        # Check if user is the author
        if not log_condition(current_user.id == snippet.user_id, "current_user.id == snippet.user_id"):
            logger.warning(f"Unauthorized snippet delete attempt", 
                         snippet_id=snippet_id,
                         user_id=current_user.id,
                         owner_id=snippet.user_id,
                         ip=request.remote_addr)
            abort(403)  # Forbidden
        
        # Store information for logging
        snippet_info = {
            'id': snippet.id,
            'title': snippet.title,
            'language': snippet.language,
            'created_at': snippet.created_at,
            'tags': [tag.name for tag in snippet.tags]
        }
        
        with LoggedBlock("delete_from_database"):
            db.session.delete(snippet)
            db.session.commit()
        
        logger.info(f"Snippet deleted successfully", 
                  snippet_info=snippet_info,
                  user_id=current_user.id,
                  username=current_user.username)
        flash('Snippet deleted successfully!', 'success')
        return redirect(url_for('main.index'))

@snippets.route('/my')
@login_required
@log_function()
def my_snippets():
    """User's snippets route."""
    with LoggedBlock("fetch_user_snippets"):
        logger.debug(f"Fetching snippets for user", 
                   user_id=current_user.id,
                   username=current_user.username)
                   
        # Query user snippets with optimized query
        from app.db_optimizations import optimize_snippet_query
        
        query = Snippet.query.filter_by(user_id=current_user.id).order_by(
            Snippet.created_at.desc()
        )
        
        user_snippets = optimize_snippet_query(query).all()
        
        logger.debug(f"Found {len(user_snippets)} snippets for user",
                   user_id=current_user.id)
    
    return render_template('snippets/my_snippets.html', snippets=user_snippets)

@snippets.route('/tag/<tag_name>')
@log_function()
def by_tag(tag_name):
    """View snippets by tag route."""
    with LoggedBlock("snippets_by_tag", log_variables=True):
        logger.debug(f"Viewing snippets by tag", 
                   tag=tag_name,
                   user_id=getattr(current_user, 'id', None))
                   
        # Import snippet_tags association table from models if needed
        from app.models import snippet_tags
        
        # Find the tag
        with LoggedBlock("find_tag"):
            tag = Tag.query.filter_by(name=tag_name).first_or_404()
            logger.debug(f"Found tag", id=tag.id, name=tag.name)
        
        # Get snippets with this tag that are public or owned by current user
        with LoggedBlock("query_snippets_by_tag"):
            if log_condition(current_user.is_authenticated, "current_user.is_authenticated"):
                snippets = Snippet.query.filter(
                    Snippet.tags.contains(tag),
                    or_(
                        Snippet.is_public == True,
                        Snippet.user_id == current_user.id
                    )
                ).order_by(Snippet.created_at.desc()).all()
                logger.debug(f"Found {len(snippets)} snippets with tag for authenticated user",
                          tag=tag_name,
                          user_id=current_user.id)
            else:
                snippets = Snippet.query.filter(
                    Snippet.tags.contains(tag),
                    Snippet.is_public == True
                ).order_by(Snippet.created_at.desc()).all()
                logger.debug(f"Found {len(snippets)} public snippets with tag",
                          tag=tag_name)
        
        # Get related tags (other tags that appear with this tag)
        related_tags = []
        
        # If we have snippets, find related tags
        if log_condition(len(snippets) > 0, "len(snippets) > 0"):
            with LoggedBlock("find_related_tags"):
                snippet_ids = [s.id for s in snippets]
                related_tags = db.session.query(
                    Tag, func.count(snippet_tags.c.snippet_id).label('count')
                ).join(snippet_tags).filter(
                    Tag.id != tag.id,
                    snippet_tags.c.snippet_id.in_(snippet_ids)
                ).group_by(Tag.id).order_by(func.count(snippet_tags.c.snippet_id).desc()).limit(10).all()
                
                logger.debug(f"Found {len(related_tags)} related tags")
        
        return render_template('snippets/by_tag.html', tag=tag, snippets=snippets, related_tags=related_tags)