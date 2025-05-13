from app import db, login_manager, bcrypt
from flask_login import UserMixin
from flask import current_app
from datetime import datetime, timedelta
import uuid
import secrets
from sqlalchemy import event
from sqlalchemy.ext.hybrid import hybrid_property

@login_manager.user_loader
def load_user(user_id):
    """Load a user by ID for Flask-Login."""
    user = User.query.get(user_id)
    if user and user.is_active:
        return user
    return None

# Association table for snippet tags
snippet_tags = db.Table('snippet_tags',
    db.Column('snippet_id', db.String(36), db.ForeignKey('snippets.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    """User model for authentication and snippet ownership."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirm_token = db.Column(db.String(100), nullable=True)
    token_expiration = db.Column(db.DateTime, nullable=True)

    # Relationships
    snippets = db.relationship('Snippet', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set the user password."""
        # Use the configured number of bcrypt rounds
        log_rounds = current_app.config.get('BCRYPT_LOG_ROUNDS', 12)
        self.password_hash = bcrypt.generate_password_hash(
            password, rounds=log_rounds
        ).decode('utf-8')

    def check_password(self, password, check_only=False):
        """Check password against stored hash.

        Args:
            password: The password to check
            check_only: If True, only verify password without updating internal state

        Returns:
            bool: True if password matches, False otherwise
        """
        # Check for account lockout
        if self.is_locked_out:
            return False

        result = bcrypt.check_password_hash(self.password_hash, password)

        # Only update login attempt counter if not in check_only mode
        if not check_only:
            if result:
                # Reset failed attempts on successful login
                self.failed_login_attempts = 0
                self.locked_until = None
            else:
                # Increment failed attempts and possibly lock account
                self.failed_login_attempts += 1
                if self.failed_login_attempts >= 5:  # Lock after 5 failed attempts
                    self.locked_until = datetime.utcnow() + timedelta(minutes=15)  # Lock for 15 minutes

        return result

    @property
    def is_locked_out(self):
        """Check if the account is currently locked out."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        # Reset lockout if the time has passed
        if self.locked_until:
            self.locked_until = None
        return False

    def generate_email_token(self):
        """Generate a secure token for email confirmation."""
        token = secrets.token_urlsafe(32)
        self.email_confirm_token = token
        self.token_expiration = datetime.utcnow() + timedelta(days=1)  # Token valid for 24 hours
        return token

    def confirm_email(self, token):
        """Confirm email with token."""
        if token != self.email_confirm_token:
            return False

        if self.token_expiration < datetime.utcnow():
            return False

        self.email_confirmed = True
        self.email_confirm_token = None
        self.token_expiration = None
        return True

    def __repr__(self):
        return f'<User {self.username}>'

class Snippet(db.Model):
    """Code snippet model."""
    __tablename__ = 'snippets'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expiration = db.Column(db.DateTime, nullable=True)  # Optional expiration date
    share_token = db.Column(db.String(64), nullable=True, unique=True, index=True)  # Token for sharing private snippets

    # Relationships
    tags = db.relationship('Tag', secondary=snippet_tags, lazy='subquery',
                          backref=db.backref('snippets', lazy=True))

    # Non-persistent attributes
    _view_count_only = False  # Flag for view count updates

    def __repr__(self):
        return f'<Snippet {self.title}>'

    @property
    def formatted_date(self):
        """Return formatted date for display."""
        return self.created_at.strftime('%B %d, %Y')

    @property
    def is_expired(self):
        """Check if snippet has expired."""
        if self.expiration is None:
            return False
        return datetime.utcnow() > self.expiration

    def generate_share_token(self):
        """Generate a secure token for sharing private snippets."""
        token = secrets.token_urlsafe(48)
        self.share_token = token
        return token

    def increment_view(self):
        """Safely increment the view count."""
        self.views += 1
        # Set flag to indicate this is only a view count update
        # This helps the event listener ignore these common updates
        self._view_count_only = True
        return self.views

    def is_accessible_by(self, user):
        """Check if a user can access this snippet."""
        # Public snippets are accessible by anyone
        if self.is_public:
            return True

        # Expired snippets are not accessible
        if self.is_expired:
            return False

        # Owner can always access their own snippets
        if user and user.is_authenticated and user.id == self.user_id:
            return True

        return False

class Tag(db.Model):
    """Tag model for categorizing snippets."""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False, index=True)
    
    def __repr__(self):
        return f'<Tag {self.name}>'

# Event listener to track snippet updates
@event.listens_for(Snippet, 'before_update')
def track_snippet_updates(mapper, connection, target):
    """Track significant changes to snippets for auditing purposes."""
    # Skip tracking for view count changes only
    if hasattr(target, '_view_count_only') and target._view_count_only:
        return

    # Here we could add logging or tracking for significant updates
    # For now, just ensuring view count changes don't trigger other logic
    pass