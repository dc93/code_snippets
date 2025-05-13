from flask import current_app
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, Regexp
from app.models import User
from app.security import password_meets_requirements, sanitize_input
import re

class LoginForm(FlaskForm):
    """User login form."""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64),
        # Sanitize and validate username format
        Regexp(r'^[A-Za-z0-9_.-]+$', message='Username can only contain letters, numbers, underscore, dash, and period')
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

    def validate_username(self, username):
        """Sanitize username input."""
        if username.data:
            username.data = sanitize_input(username.data)

    def validate_password(self, password):
        """Sanitize password input."""
        # Make sure we don't modify the password, just validate it's not empty
        if not password.data or len(password.data.strip()) == 0:
            raise ValidationError('Password cannot be empty.')

class RegistrationForm(FlaskForm):
    """User registration form."""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64),
        Regexp(r'^[A-Za-z0-9_.-]+$', message='Username can only contain letters, numbers, underscore, dash, and period')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    # Add reCAPTCHA for production environment
    # recaptcha = RecaptchaField()
    terms = BooleanField('I agree to the Terms of Service and Privacy Policy', validators=[
        DataRequired(message='You must agree to the terms to register')
    ])
    submit = SubmitField('Register')


    def validate_username(self, username):
        """Check if username already exists and sanitize input."""
        # Sanitize input
        username.data = sanitize_input(username.data)

        # Check for existing user
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')

    def validate_email(self, email):
        """Check if email already exists and sanitize input."""
        # Sanitize input
        email.data = sanitize_input(email.data)

        # Check for existing user
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

    def validate_password(self, password):
        """Validate password meets security requirements."""
        if not password_meets_requirements(password.data):
            raise ValidationError(
                'Password must be at least 8 characters and include at least 3 of the following: '
                'uppercase letters, lowercase letters, numbers, and special characters.'
            )

class SnippetForm(FlaskForm):
    """Snippet creation and editing form."""
    title = StringField('Title', validators=[
        DataRequired(),
        Length(min=3, max=100)
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500)
    ])
    code = TextAreaField('Code', validators=[
        DataRequired(),
        Length(max=100000, message="Code snippet exceeds maximum size limit")
    ])
    language = SelectField('Language', choices=[
        ('python', 'Python'),
        ('javascript', 'JavaScript'),
        ('html', 'HTML'),
        ('css', 'CSS'),
        ('java', 'Java'),
        ('c', 'C'),
        ('cpp', 'C++'),
        ('csharp', 'C#'),
        ('php', 'PHP'),
        ('ruby', 'Ruby'),
        ('go', 'Go'),
        ('rust', 'Rust'),
        ('typescript', 'TypeScript'),
        ('swift', 'Swift'),
        ('kotlin', 'Kotlin'),
        ('sql', 'SQL'),
        ('bash', 'Bash/Shell'),
        ('json', 'JSON'),
        ('markdown', 'Markdown'),
        ('yaml', 'YAML'),
        ('xml', 'XML'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    is_public = BooleanField('Make Public')
    tags = SelectMultipleField('Tags', coerce=int, validators=[Optional()])
    new_tags = StringField('New Tags (comma separated)', validators=[Optional()])
    submit = SubmitField('Save Snippet')

    def validate_title(self, title):
        """Sanitize title input."""
        title.data = sanitize_input(title.data)

    def validate_description(self, description):
        """Sanitize description input."""
        if description.data:
            description.data = sanitize_input(description.data)

    def validate_new_tags(self, new_tags):
        """Sanitize new tags input."""
        if new_tags.data:
            new_tags.data = sanitize_input(new_tags.data)

            # Validate tag format
            tags = [tag.strip() for tag in new_tags.data.split(',')]
            for tag in tags:
                if tag and not re.match(r'^[A-Za-z0-9_-]+$', tag):
                    raise ValidationError('Tags can only contain letters, numbers, underscore, and dash.')

class SearchForm(FlaskForm):
    """Search form for snippets."""
    query = StringField('Search', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    submit = SubmitField('Search')

    def validate_query(self, query):
        """Sanitize search query input."""
        query.data = sanitize_input(query.data)