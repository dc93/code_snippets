#!/usr/bin/env python3
"""
Script to delete and recreate the database for the CodeSnippets application.
Also creates a test admin user if requested.
"""

import os
import sys
import argparse
from app import create_app, db
from app.models import User, Tag

def reset_database(create_admin=False):
    """
    Delete and recreate the database.
    
    Args:
        create_admin (bool): Whether to create an admin user
    
    Returns:
        bool: True if successful, False otherwise
    """
    print("Starting database reset process...")
    
    # Create application context
    app = create_app('development')
    
    with app.app_context():
        # Get the database file path
        db_path = os.path.join(app.instance_path, 'snippets.db')
        
        # Check if database file exists
        if os.path.exists(db_path):
            print(f"Removing existing database file: {db_path}")
            try:
                # Close all connections before removing
                db.session.remove()
                db.engine.dispose()
                
                # Delete the file
                os.remove(db_path)
                print("Database file deleted successfully.")
            except Exception as e:
                print(f"Error removing database file: {str(e)}")
                return False
        else:
            print(f"No database file found at {db_path}")
        
        # Ensure instance directory exists
        if not os.path.exists(app.instance_path):
            print(f"Creating instance directory: {app.instance_path}")
            os.makedirs(app.instance_path, exist_ok=True)
        
        print("Creating new database...")
        try:
            # Create the tables using SQLAlchemy's create_all
            db.create_all()
            
            # Print confirmation
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Created tables: {tables}")
            
            # Create admin user if requested
            if create_admin:
                print("Creating admin user...")
                admin = User(
                    username="admin",
                    email="admin@example.com",
                    email_confirmed=True
                )
                admin.set_password("password123")
                db.session.add(admin)
                
                # Create some default tags
                default_tags = ["python", "javascript", "html", "css", "flask", "django", "react", "vue"]
                for tag_name in default_tags:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                
                db.session.commit()
                print(f"Admin user created with username 'admin' and password 'password123'")
                print(f"Default tags created: {default_tags}")
            
            return True
        except Exception as e:
            print(f"Error creating database: {str(e)}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset the database for CodeSnippets application")
    parser.add_argument("--create-admin", action="store_true", help="Create an admin user")
    args = parser.parse_args()
    
    success = reset_database(create_admin=args.create_admin)
    if success:
        print("Database reset completed successfully!")
        sys.exit(0)
    else:
        print("Database reset failed.")
        sys.exit(1)