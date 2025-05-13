"""WSGI entry point for production deployment."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set environment to production
os.environ['FLASK_ENV'] = 'production'

# Import the application
from run import app as application

# Expose the WSGI application
if __name__ == '__main__':
    application.run()