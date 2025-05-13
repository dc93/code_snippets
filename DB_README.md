# Database Management for Code Snippets

This document explains how to manage the database for the Code Snippets application.

## Database Reset Script

The `reset_db.py` script provides functionality to delete and recreate the database, optionally creating an admin user and default tags.

### Basic Usage

To reset the database (delete and recreate it):

```bash
python reset_db.py
```

This will:
1. Delete the existing database file (if it exists)
2. Create a new empty database with all required tables
3. No default data will be added

### Creating an Admin User

To reset the database and create an admin user with default tags:

```bash
python reset_db.py --create-admin
```

This will:
1. Delete the existing database file (if it exists)
2. Create a new empty database with all required tables
3. Create an admin user with the following credentials:
   - Username: `admin`
   - Email: `admin@example.com` 
   - Password: `password123`
4. Create default tags: python, javascript, html, css, flask, django, react, vue

### Virtual Environment

If you're using a virtual environment, make sure to activate it before running the script:

```bash
source venv/bin/activate
python reset_db.py --create-admin
```

## Database Structure

The database uses SQLAlchemy ORM with the following main models:

- **User**: Stores user account information and authentication data
- **Snippet**: Stores code snippets with metadata
- **Tag**: Stores tags for categorizing snippets
- **snippet_tags**: Association table for the many-to-many relationship between snippets and tags

## Migrations

The application uses Flask-Migrate (Alembic) for database migrations. If you need to create or apply migrations, see the Flask-Migrate documentation.

## Backup

It's recommended to backup the database before making significant changes. A simple backup can be made by copying the database file:

```bash
cp instance/snippets.db instance/snippets.db.backup
```

## Production Considerations

In a production environment, consider the following:

1. Use a more robust database system (PostgreSQL, MySQL)
2. Set up regular backups
3. Use environment variables for sensitive configuration
4. Change the default admin password immediately after creation