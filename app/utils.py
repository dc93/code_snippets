import re
import bleach
from flask import current_app, render_template, url_for
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_all_lexers
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
from threading import Thread
from flask_mail import Message, Mail

# Create a default mail instance - will be properly initialized in create_app
mail = Mail()

def set_mail_instance(mail_instance):
    """Set the global mail instance from the initialized app.

    Args:
        mail_instance: An initialized Flask-Mail instance
    """
    global mail
    mail = mail_instance

def get_available_languages():
    """Get a list of all available languages for syntax highlighting."""
    return sorted([(name.lower(), name) for lexer in get_all_lexers() for name in lexer[1]])

def highlight_code(code, language):
    """Highlight code using Pygments."""
    try:
        lexer = get_lexer_by_name(language, stripall=True)
    except ClassNotFound:
        # If language not found, try plaintext
        try:
            lexer = get_lexer_by_name('text', stripall=True)
        except ClassNotFound:
            # If all else fails, just return the code without highlighting
            return code
    
    formatter = HtmlFormatter(linenos=True, cssclass='highlight')
    highlighted = highlight(code, lexer, formatter)
    return highlighted

def sanitize_html(text):
    """Sanitize HTML content to prevent XSS."""
    allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                   'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                   'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'hr',
                   'br', 'div', 'span', 'table', 'thead', 'tbody',
                   'tr', 'th', 'td']
    
    allowed_attrs = {
        '*': ['class', 'id'],
        'a': ['href', 'rel', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
    }
    
    return bleach.clean(text, tags=allowed_tags, attributes=allowed_attrs, strip=True)

def is_valid_password(password):
    """
    Validate password complexity.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    if len(password) < 8:
        return False
    
    checks = [
        re.search(r'[A-Z]', password),  # uppercase
        re.search(r'[a-z]', password),  # lowercase
        re.search(r'[0-9]', password),  # digit
        re.search(r'[^A-Za-z0-9]', password)  # special char
    ]
    
    # Require at least 3 of the 4 criteria
    return sum(1 for check in checks if check) >= 3

def truncate_text(text, max_length=100):
    """Truncate text to a maximum length and add ellipsis."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + '...'

def get_snippet_size_limit():
    """Get maximum snippet size from config."""
    return current_app.config.get('MAX_SNIPPET_SIZE', 100000)

def send_async_email(app, msg, max_retries=3, retry_delay=2):
    """Send email asynchronously with retry mechanism.

    Args:
        app: Flask application instance
        msg: Email message object
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 2)

    Returns:
        Boolean indicating success
    """
    import time

    # Track success status
    success = False
    last_error = None
    retry_count = 0

    with app.app_context():
        while retry_count <= max_retries and not success:
            try:
                if retry_count > 0:
                    app.logger.info(f"Retry attempt {retry_count} for email to {msg.recipients}")

                mail.send(msg)
                app.logger.info(f"Email sent successfully to {msg.recipients}")
                success = True

            except ConnectionError as e:
                # Network errors are retriable
                last_error = e
                retry_count += 1
                if retry_count <= max_retries:
                    app.logger.warning(f"Connection error sending email, will retry: {str(e)}")
                    time.sleep(retry_delay)
                else:
                    app.logger.error(f"Failed to send email after {max_retries} retries: {str(e)}")
                    app.logger.error("Connection error details", exc_info=True)

            except Exception as e:
                # Non-connection errors might not be retriable
                last_error = e
                app.logger.error(f"Failed to send email: {str(e)}")
                app.logger.error("Email error details", exc_info=True)

                # Only retry certain types of errors that might be temporary
                if isinstance(e, (TimeoutError, OSError)):
                    retry_count += 1
                    if retry_count <= max_retries:
                        app.logger.warning(f"Retriable error, will retry in {retry_delay}s")
                        time.sleep(retry_delay)
                    else:
                        app.logger.error(f"Failed to send email after {max_retries} retries")
                else:
                    # Non-retriable error
                    app.logger.error("Non-retriable error, giving up")
                    break

    return success

def create_email_message(subject, recipients, text_body, html_body=None, sender=None, app=None):
    """Create an email message object.

    Args:
        subject: Email subject
        recipients: Email recipient(s) - string or list
        text_body: Plain text email body
        html_body: HTML version of email body (optional)
        sender: Email sender address (optional)
        app: Flask application instance (optional)

    Returns:
        Message object or None if creation fails
    """
    try:
        # Validate inputs
        if not subject or not text_body:
            raise ValueError("Email subject and body are required")

        # Check and normalize recipients
        if isinstance(recipients, str):
            if not recipients.strip():
                raise ValueError("Empty recipient email address")
            recipients_list = [recipients.strip()]
        elif isinstance(recipients, (list, tuple)):
            if not recipients:
                raise ValueError("Empty recipients list")
            recipients_list = [r.strip() for r in recipients if r and r.strip()]
            if not recipients_list:
                raise ValueError("No valid recipients in list")
        else:
            raise TypeError("Recipients must be a string or list of strings")

        # Get configuration from app or current_app
        try:
            config = app.config if app else current_app.config
        except RuntimeError:
            # Fallback values if no app context
            config = {'MAIL_DEFAULT_SENDER': 'noreply@codesnippets.com'}

        # Use default sender if none provided
        if not sender:
            sender = config.get('MAIL_DEFAULT_SENDER', 'noreply@codesnippets.com')

        # Create the message
        msg = Message(subject, sender=sender, recipients=recipients_list)
        msg.body = text_body
        if html_body:
            msg.html = html_body

        return msg

    except Exception as e:
        # Log error and return None
        import logging
        logger = logging.getLogger('email')
        logger.error(f"Error creating email message: {str(e)}")
        return None

def send_email(subject, recipients, text_body, html_body=None, sender=None, priority='normal'):
    """Send an email with improved error handling.

    Args:
        subject: Email subject
        recipients: Email recipient(s) - string or list
        text_body: Plain text email body
        html_body: HTML version of email body (optional)
        sender: Email sender address (optional)
        priority: Email priority ('high', 'normal', 'low')

    Returns:
        Boolean indicating if the email was sent successfully
    """
    # Set up logging - both in and outside of app context
    import logging
    logger = logging.getLogger('email')

    # Input validation
    if not subject or not recipients or not text_body:
        logger.error("Cannot send email: Missing required parameters (subject, recipients, or body)")
        return False

    # Format recipients for logging
    recipients_str = recipients if isinstance(recipients, str) else ', '.join(recipients)

    # Email sending process
    try:
        # Use current application context if available
        from flask import current_app
        app = current_app._get_current_object()

        # Handle testing mode
        if app.config.get('TESTING', False):
            app.logger.info(f"Test mode - email would be sent to {recipients_str}: {subject}")
            return True

        # Handle suppressed sending (for development)
        if app.config.get('MAIL_SUPPRESS_SEND', False):
            app.logger.info(f"Email sending suppressed: {subject} to {recipients_str}")
            app.logger.debug(f"Email content: {text_body[:100]}{'...' if len(text_body) > 100 else ''}")
            return True

        # Validate email configuration
        if not app.config.get('MAIL_SERVER'):
            app.logger.error("Email server not configured")
            return False

        # Create message object
        msg = create_email_message(subject, recipients, text_body, html_body, sender, app)
        if not msg:
            app.logger.error("Failed to create email message")
            return False

        # Set priority headers if specified
        if priority == 'high':
            msg.extra_headers = {'X-Priority': '1', 'Importance': 'high'}
        elif priority == 'low':
            msg.extra_headers = {'X-Priority': '5', 'Importance': 'low'}

        # Send email in a background thread
        thread = Thread(target=send_async_email, args=(app, msg))
        thread.daemon = True  # Make thread daemon so it doesn't block app shutdown
        thread.start()

        app.logger.info(f"Email queued: '{subject}' to {recipients_str}")
        return True

    except RuntimeError as e:
        # Handle case where there's no application context
        logger.warning(f"Email sending outside app context: {str(e)}")

        # Fall back to direct mail send without thread if mail is initialized
        try:
            if not mail:
                logger.error("Cannot send email: Mail not initialized")
                return False

            if not hasattr(mail, 'app') or not mail.app:
                logger.error("Cannot send email: Mail app not initialized")
                return False

            # Create message directly
            msg = create_email_message(subject, recipients, text_body, html_body, sender)
            if not msg:
                logger.error("Failed to create email message outside app context")
                return False

            # Set priority headers if specified
            if priority == 'high':
                msg.extra_headers = {'X-Priority': '1', 'Importance': 'high'}
            elif priority == 'low':
                msg.extra_headers = {'X-Priority': '5', 'Importance': 'low'}

            # Send directly (no async in this case)
            mail.send(msg)
            logger.info(f"Email sent directly (no app context): '{subject}' to {recipients_str}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email directly: {str(e)}")
            return False

    except Exception as e:
        # Catch any other exceptions to prevent email failures from breaking the app
        logger.error(f"Unexpected error sending email: {str(e)}", exc_info=True)
        return False

def send_email_confirmation(user):
    """Send email confirmation to a user."""
    token = user.email_confirm_token
    confirmation_url = url_for('auth.confirm_email', token=token, _external=True)

    # Generate the email content
    subject = "Confirm Your Email - CodeSnippets"

    # Plain text version
    text_body = f"""
    Hello {user.username},

    Thank you for registering with CodeSnippets! To complete your registration and activate your account,
    please confirm your email address by clicking the link below:

    {confirmation_url}

    This link will expire in 24 hours.

    If you did not register for a CodeSnippets account, please ignore this email.

    Thanks,
    The CodeSnippets Team
    """

    # HTML version
    html_body = render_template('auth/email_confirmation.html',
                               user=user,
                               confirmation_url=confirmation_url)

    # Send the email
    send_email(subject, user.email, text_body, html_body)

    current_app.logger.info(f"Confirmation email sent to {user.email} for user {user.username}")

    # For development, log the confirmation URL
    if current_app.debug:
        current_app.logger.debug(f"Confirmation URL for {user.username}: {confirmation_url}")