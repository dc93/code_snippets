from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, abort, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import db, cache, limiter
from app.models import User, Snippet, Tag
from app.forms import LoginForm, RegistrationForm, SnippetForm, SearchForm
from datetime import datetime, timedelta
from sqlalchemy import or_, func
import uuid
import secrets

# Blueprints
main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__, url_prefix='/auth')
snippets = Blueprint('snippets', __name__, url_prefix='/snippets')

# Main routes
@main.route('/')
@main.route('/index')
@cache.cached(timeout=60)
def index():
    """Home page route."""
    # Import snippet_tags association table from models and query optimization
    from app.models import snippet_tags
    from app.db_optimizations import optimize_snippet_query, get_count

    try:
        # Show latest public snippets if setting enabled
        if current_app.config['ENABLE_PUBLIC_SNIPPETS']:
            # Use optimized query for snippets
            recent_snippets_query = Snippet.query.filter_by(is_public=True).order_by(
                Snippet.created_at.desc()
            ).limit(6)
            recent_snippets = optimize_snippet_query(recent_snippets_query).all()
        else:
            recent_snippets = []

        # Optimize popular tags query with proper caching
        # This query is expensive, so we cache it for longer
        cache_key = 'popular_tags'
        popular_tags = cache.get(cache_key)

        if popular_tags is None:
            popular_tags = db.session.query(
                Tag, func.count(snippet_tags.c.snippet_id).label('snippet_count')
            ).join(snippet_tags).group_by(Tag).order_by(
                func.count(snippet_tags.c.snippet_id).desc()
            ).limit(10).all()

            # Cache popular tags for 30 minutes
            cache.set(cache_key, popular_tags, timeout=1800)

        return render_template('index.html',
                            recent_snippets=recent_snippets,
                            popular_tags=popular_tags)
    except Exception as e:
        current_app.logger.error(f"Error in index route: {str(e)}")
        # Fallback to empty data on error
        return render_template('index.html',
                            recent_snippets=[],
                            popular_tags=[])

@main.route('/about')
@cache.cached(timeout=3600)  # Cache for 1 hour
def about():
    """About page route."""
    return render_template('about.html')

@main.route('/search')
def search():
    """Search snippets route."""
    # Import snippet_tags association table from models if needed
    from app.models import snippet_tags

    form = SearchForm()
    query = request.args.get('q', '')
    
    if query:
        # Search in title, description and tags
        snippets = Snippet.query.filter(
            Snippet.is_public == True,
            or_(
                Snippet.title.ilike(f'%{query}%'),
                Snippet.description.ilike(f'%{query}%'),
                Snippet.language.ilike(f'%{query}%'),
                Snippet.tags.any(Tag.name.ilike(f'%{query}%'))
            )
        ).order_by(Snippet.created_at.desc()).all()
    else:
        snippets = []
    
    return render_template('search.html', 
                           form=form, 
                           query=query, 
                           snippets=snippets)

# Auth routes
@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("10/minute")
def login():
    """User login route."""
    # Log route access with request details
    current_app.logger.debug(f"Login route accessed - Method: {request.method}, IP: {request.remote_addr}, User-Agent: {request.headers.get('User-Agent', 'Unknown')}")

    if current_user.is_authenticated:
        current_app.logger.debug(f"Already authenticated user ({current_user.username}) accessing login page - redirecting to index")
        return redirect(url_for('main.index'))

    # Create form with request data if it's a POST
    form = LoginForm()
    if request.method == 'POST':
        current_app.logger.debug(f"Processing login POST request from IP: {request.remote_addr}")
        try:
            # Log form data for debugging (excluding password)
            current_app.logger.debug(f"Login attempt for username: {form.username.data}")

            # Log if CSRF token is in the form data
            has_csrf = 'csrf_token' in request.form
            current_app.logger.debug(f"CSRF token present in form: {has_csrf}")
            if has_csrf:
                current_app.logger.debug(f"CSRF token from form: {request.form.get('csrf_token')[:10]}...")

            # Explicitly validate the form using validate_on_submit
            if form.validate_on_submit():
                current_app.logger.debug("Form validation passed with CSRF token")
                user = User.query.filter_by(username=form.username.data).first()

                if not user:
                    current_app.logger.debug(f"Login failed - username not found: {form.username.data}")
                    # Use generic message for security
                    flash('Invalid username or password', 'danger')
                    return render_template('login.html', form=form)

                # Check if account is locked first before checking password
                if user and user.is_locked_out:
                    current_app.logger.warning(f"Attempted login to locked account: {user.username}, IP: {request.remote_addr}")
                    flash('Account is temporarily locked due to too many failed attempts. Please try again later.', 'danger')
                elif user:
                    # Store the password check result but don't modify user object yet
                    password_correct = user.check_password(form.password.data, check_only=True)

                    if password_correct:
                        # Update user data in database with session management
                        try:
                            # Set all attributes in one go to minimize race conditions
                            user.last_login = datetime.utcnow()
                            user.failed_login_attempts = 0
                            user.locked_until = None

                            db.session.add(user)
                            db.session.commit()
                            current_app.logger.debug(f"Updated user login timestamp for {user.username}")

                            # Only log in after successful database update
                            current_app.logger.info(f"Successful login: {user.username}, IP: {request.remote_addr}")
                            login_user(user, remember=form.remember.data)

                        except Exception as e:
                            db.session.rollback()
                            current_app.logger.error(f"Database error during login: {str(e)}")
                            flash('A database error occurred. Please try again.', 'danger')
                            return render_template('login.html', form=form)

                        # Validate the next parameter to prevent open redirect
                        next_page = request.args.get('next')
                        current_app.logger.debug(f"Redirect 'next' parameter: {next_page}")

                        if next_page and not next_page.startswith('/'):
                            # Only allow relative URLs
                            current_app.logger.warning(f"Blocked potential open redirect to: {next_page}")
                            next_page = None

                        from app.security import is_safe_url
                        if not next_page or not is_safe_url(next_page):
                            next_page = url_for('main.index')
                            current_app.logger.debug(f"Using default redirect: {next_page}")

                        return redirect(next_page)
                    else:
                        # Handle failed login attempt in database with proper transaction
                        try:
                            # Update failed login attempts
                            user.failed_login_attempts += 1

                            # Lock account after 5 failed attempts
                            if user.failed_login_attempts >= 5:
                                user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                                current_app.logger.warning(
                                    f"Account locked: {user.username} - too many failed attempts, "
                                    f"IP: {request.remote_addr}"
                                )
                            else:
                                current_app.logger.warning(
                                    f"Failed login attempt {user.failed_login_attempts} for user: {user.username}, "
                                    f"IP: {request.remote_addr}"
                                )

                            db.session.add(user)
                            db.session.commit()
                            current_app.logger.debug(f"Updated failed login attempts for {user.username}")
                        except Exception as e:
                            db.session.rollback()
                            current_app.logger.error(f"Database error updating failed attempts: {str(e)}")

                        flash('Invalid username or password', 'danger')
                else:
                    flash('Invalid username or password', 'danger')
            else:
                current_app.logger.debug(f"Form validation failed: {form.errors}")
                # Handle CSRF errors differently (just show generic message for security)
                if 'csrf_token' in form.errors:
                    current_app.logger.warning(f"CSRF validation failed during login: {request.remote_addr}")
                    flash('Form validation failed. Please try again.', 'danger')
                else:
                    # Show field-specific errors for non-CSRF issues
                    for field, errors in form.errors.items():
                        for error in errors:
                            current_app.logger.debug(f"Form field error - {field}: {error}")
                            flash(f"{field}: {error}", 'danger')
        except Exception as e:
            db.session.rollback()  # Ensure transaction is rolled back on error
            current_app.logger.error(f"Login error: {str(e)}")
            # Log full traceback at debug level
            import traceback
            current_app.logger.debug(f"Login exception traceback: {traceback.format_exc()}")
            flash('An error occurred during login. Please try again.', 'danger')

    # Log rendering of login template
    current_app.logger.debug("Rendering login template")
    return render_template('login.html', form=form)

@auth.route('/logout')
def logout():
    """User logout route."""
    username = "anonymous"
    if current_user.is_authenticated:
        username = current_user.username
        current_app.logger.debug(f"Logout request from user: {username}, IP: {request.remote_addr}")

    logout_user()
    current_app.logger.info(f"User logged out: {username}, IP: {request.remote_addr}")
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

@auth.route('/confirm/<token>')
def confirm_email(token):
    """Email confirmation route."""
    # Handle if user is already authenticated and confirmed
    if current_user.is_authenticated and current_user.email_confirmed:
        flash('Your email is already confirmed!', 'info')
        return redirect(url_for('main.index'))

    # Find user by token
    user = User.query.filter_by(email_confirm_token=token).first()

    if not user:
        current_app.logger.warning(f"Invalid confirmation token used: {token}, IP: {request.remote_addr}")
        flash('Invalid or expired confirmation link.', 'danger')
        return redirect(url_for('auth.login'))

    # Confirm email
    if user.confirm_email(token):
        # Update user's email_confirmed status
        db.session.commit()
        current_app.logger.info(f"Email confirmed for user: {user.username}, IP: {request.remote_addr}")
        flash('Your email has been confirmed! You can now log in.', 'success')

        # If user is already logged in, refresh login session
        if current_user.is_authenticated and current_user.id == user.id:
            login_user(user)
    else:
        current_app.logger.warning(f"Expired token used for {user.username}, IP: {request.remote_addr}")
        flash('The confirmation link has expired or is invalid.', 'danger')

    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit("5/hour")
def register():
    """User registration route."""
    # Log route access with detailed request information
    current_app.logger.debug(
        f"Register route accessed - Method: {request.method}, IP: {request.remote_addr}, "
        f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
    )

    if current_user.is_authenticated:
        current_app.logger.debug(f"Already authenticated user ({current_user.username}) accessing register page - redirecting to index")
        return redirect(url_for('main.index'))

    # Check if registration is enabled
    if not current_app.config['ENABLE_REGISTRATION']:
        current_app.logger.warning(f"Registration attempt when disabled - IP: {request.remote_addr}")
        flash('Registration is currently disabled', 'warning')
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if request.method == 'POST':
        current_app.logger.debug(f"Processing registration POST request from IP: {request.remote_addr}")
        try:
            # Log form data for debugging (excluding password)
            current_app.logger.debug(
                f"Registration attempt - Username: {form.username.data}, "
                f"Email: {form.email.data}"
            )

            # Use validate_on_submit instead of validate() - this checks CSRF automatically
            if form.validate_on_submit():
                current_app.logger.debug("Registration form validation passed")
                try:
                    # Check for existing username/email before creating user
                    existing_username = User.query.filter_by(username=form.username.data).first()
                    existing_email = User.query.filter_by(email=form.email.data).first()

                    if existing_username:
                        current_app.logger.debug(f"Registration attempt with existing username: {form.username.data}")
                        flash('Username already exists. Please choose a different one.', 'danger')
                        return render_template('register.html', form=form)

                    if existing_email:
                        current_app.logger.debug(f"Registration attempt with existing email: {form.email.data}")
                        flash('Email already registered. Please use a different one.', 'danger')
                        return render_template('register.html', form=form)

                    # Create new user object
                    user = User(
                        username=form.username.data,
                        email=form.email.data,
                        email_confirmed=False  # Require email confirmation
                    )
                    user.set_password(form.password.data)
                    current_app.logger.debug(f"Created new user object for {user.username}")

                    # Generate email confirmation token
                    token = user.generate_email_token()
                    current_app.logger.debug(f"Generated confirmation token for {user.username}")

                    db.session.add(user)
                    db.session.commit()
                    current_app.logger.info(f"New user registered: {user.username}, Email: {user.email}, IP: {request.remote_addr}")

                    # Send confirmation email
                    try:
                        # Import this at function level to avoid circular imports
                        from app.utils import send_email_confirmation

                        # Import mail object to check if it's initialized
                        from app.utils import mail
                        if mail and hasattr(mail, 'app') and mail.app:
                            send_email_confirmation(user)
                            flash('Registration successful! Please check your email to confirm your account.', 'success')
                        else:
                            current_app.logger.warning("Mail not properly initialized, skipping email confirmation")
                            current_app.logger.info(f"Email confirmation token for {user.username}: {token}")
                            flash('Registration successful! Email confirmation is temporarily unavailable.', 'warning')
                    except Exception as e:
                        current_app.logger.error(f"Failed to send confirmation email: {str(e)}")
                        # Log full exception traceback
                        import traceback
                        current_app.logger.error(f"Email exception details: {traceback.format_exc()}")
                        # Log the token for development purposes
                        current_app.logger.info(f"Email confirmation token for {user.username}: {token}")
                        flash('Registration successful! Email confirmation is temporarily unavailable.', 'warning')

                    return redirect(url_for('auth.login'))
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Database error during registration: {str(e)}")
                    # Log IP address for potential abuse detection
                    current_app.logger.warning(f"Failed registration attempt from IP: {request.remote_addr}")
                    # Log detailed exception information at debug level
                    import traceback
                    current_app.logger.debug(f"Registration exception traceback: {traceback.format_exc()}")
                    flash('An error occurred during registration. Please try again.', 'danger')
            else:
                current_app.logger.debug(f"Registration form validation failed: {form.errors}")
                # Handle CSRF errors differently (just show generic message for security)
                if 'csrf_token' in form.errors:
                    current_app.logger.warning(f"CSRF validation failed during registration: {request.remote_addr}")
                    flash('Form validation failed. Please try again.', 'danger')
                else:
                    # Show field-specific errors for non-CSRF issues
                    for field, errors in form.errors.items():
                        for error in errors:
                            current_app.logger.debug(f"Form field error - {field}: {error}")
                            flash(f"{field}: {error}", 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error during registration: {str(e)}")
            # Log full traceback at debug level
            import traceback
            current_app.logger.debug(f"Registration exception traceback: {traceback.format_exc()}")
            flash('An unexpected error occurred. Please try again later.', 'danger')

    # For GET requests, we don't need to manually generate a CSRF token
    # Flask-WTF will handle it through form.hidden_tag()

    # Log template rendering
    current_app.logger.debug("Rendering registration template")
    return render_template('register.html', form=form)

# Snippet routes
@snippets.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new snippet route."""
    form = SnippetForm()

    try:
        # Get available tags for the form
        all_tags = Tag.query.all()
        form.tags.choices = [(tag.id, tag.name) for tag in all_tags]

        if form.validate_on_submit():
            try:
                # Process and save snippet
                snippet = Snippet(
                    id=str(uuid.uuid4()),
                    title=form.title.data,
                    description=form.description.data,
                    code=form.code.data,
                    language=form.language.data,
                    is_public=form.is_public.data,
                    user_id=current_user.id
                )

                # Add selected tags
                selected_tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
                snippet.tags = selected_tags

                # Add new tags if provided
                if form.new_tags.data:
                    new_tag_names = [t.strip() for t in form.new_tags.data.split(',')]
                    for tag_name in new_tag_names:
                        if tag_name:
                            tag = Tag.query.filter_by(name=tag_name).first()
                            if not tag:
                                tag = Tag(name=tag_name)
                                db.session.add(tag)
                            snippet.tags.append(tag)

                # Use from app.db_optimizations import db_hit_limit
                from app.db_optimizations import optimize_snippet_query

                db.session.add(snippet)
                db.session.commit()

                current_app.logger.info(f"New snippet created: {snippet.id} by user {current_user.id}")
                flash('Snippet created successfully!', 'success')
                return redirect(url_for('snippets.view', snippet_id=snippet.id))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error creating snippet: {str(e)}")
                flash('An error occurred while creating your snippet. Please try again.', 'danger')
        elif request.method == 'POST':
            # Handle CSRF errors differently (just show generic message for security)
            if 'csrf_token' in form.errors:
                current_app.logger.warning(f"CSRF validation failed during snippet creation: {request.remote_addr}")
                flash('Form validation failed. Please try again.', 'danger')
            else:
                # Show field-specific errors for non-CSRF issues
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f"{field}: {error}", 'danger')
    except Exception as e:
        current_app.logger.error(f"Unexpected error in snippet creation: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'danger')

    return render_template('snippets/create.html', form=form)

@snippets.route('/<snippet_id>')
def view(snippet_id):
    """View single snippet route."""
    snippet = Snippet.query.get_or_404(snippet_id)
    
    # Check if snippet is public or user is the author
    if not snippet.is_public and (not current_user.is_authenticated or current_user.id != snippet.user_id):
        abort(403)  # Forbidden
    
    # Increment view count using the model method
    snippet.increment_view()
    db.session.commit()
    # Reset the view_count_only flag after committing
    snippet._view_count_only = False
    
    return render_template('snippets/view.html', snippet=snippet)

@snippets.route('/<snippet_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(snippet_id):
    """Edit snippet route."""
    snippet = Snippet.query.get_or_404(snippet_id)
    
    # Check if user is the author
    if current_user.id != snippet.user_id:
        abort(403)  # Forbidden
    
    form = SnippetForm()
    
    # Get available tags for the form
    all_tags = Tag.query.all()
    form.tags.choices = [(tag.id, tag.name) for tag in all_tags]
    
    if request.method == 'GET':
        # Populate form with snippet data
        form.title.data = snippet.title
        form.description.data = snippet.description
        form.code.data = snippet.code
        form.language.data = snippet.language
        form.is_public.data = snippet.is_public
        form.tags.data = [tag.id for tag in snippet.tags]
    
    if form.validate_on_submit():
        # Update snippet
        snippet.title = form.title.data
        snippet.description = form.description.data
        snippet.code = form.code.data
        snippet.language = form.language.data
        snippet.is_public = form.is_public.data
        
        # Update tags
        selected_tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
        snippet.tags = selected_tags
        
        # Add new tags if provided
        if form.new_tags.data:
            new_tag_names = [t.strip() for t in form.new_tags.data.split(',')]
            for tag_name in new_tag_names:
                if tag_name:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    snippet.tags.append(tag)
        
        db.session.commit()
        
        flash('Snippet updated successfully!', 'success')
        return redirect(url_for('snippets.view', snippet_id=snippet.id))
    
    return render_template('snippets/edit.html', form=form, snippet=snippet)

@snippets.route('/<snippet_id>/delete', methods=['POST'])
@login_required
def delete(snippet_id):
    """Delete snippet route."""
    snippet = Snippet.query.get_or_404(snippet_id)
    
    # Check if user is the author
    if current_user.id != snippet.user_id:
        abort(403)  # Forbidden
    
    db.session.delete(snippet)
    db.session.commit()
    
    flash('Snippet deleted successfully!', 'success')
    return redirect(url_for('main.index'))

@snippets.route('/my')
@login_required
def my_snippets():
    """User's snippets route."""
    user_snippets = Snippet.query.filter_by(user_id=current_user.id).order_by(
        Snippet.created_at.desc()
    ).all()
    
    return render_template('snippets/my_snippets.html', snippets=user_snippets)

@snippets.route('/tag/<tag_name>')
def by_tag(tag_name):
    """View snippets by tag route."""
    # Import snippet_tags association table from models if needed
    from app.models import snippet_tags

    tag = Tag.query.filter_by(name=tag_name).first_or_404()
    
    # Get snippets with this tag that are public or owned by current user
    if current_user.is_authenticated:
        snippets = Snippet.query.filter(
            Snippet.tags.contains(tag),
            or_(
                Snippet.is_public == True,
                Snippet.user_id == current_user.id
            )
        ).order_by(Snippet.created_at.desc()).all()
    else:
        snippets = Snippet.query.filter(
            Snippet.tags.contains(tag),
            Snippet.is_public == True
        ).order_by(Snippet.created_at.desc()).all()
    
    # Get related tags (other tags that appear with this tag)
    related_tags = []

    # If we have snippets, find related tags
    if snippets:
        snippet_ids = [s.id for s in snippets]
        related_tags = db.session.query(
            Tag, func.count(snippet_tags.c.snippet_id).label('count')
        ).join(snippet_tags).filter(
            Tag.id != tag.id,
            snippet_tags.c.snippet_id.in_(snippet_ids)
        ).group_by(Tag.id).order_by(func.count(snippet_tags.c.snippet_id).desc()).limit(10).all()

    return render_template('snippets/by_tag.html', tag=tag, snippets=snippets, related_tags=related_tags)