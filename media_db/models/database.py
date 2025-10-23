"""
Database initialization and session management
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import logging
from pathlib import Path

from ..config import MEDIA_DB_URI, MEDIA_DB_PATH

logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

# Global engine and session factory
_engine = None
_session_factory = None


def init_db(db_uri=None, echo=False):
    """
    Initialize the database engine and create all tables.

    Args:
        db_uri: Database URI (default from config)
        echo: Enable SQL query logging

    Returns:
        SQLAlchemy engine
    """
    global _engine, _session_factory

    if db_uri is None:
        db_uri = MEDIA_DB_URI

    # Create database directory if it doesn't exist
    db_path = Path(MEDIA_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initializing database at: {db_uri}")

    # Create engine
    _engine = create_engine(
        db_uri,
        echo=echo,
        connect_args={'check_same_thread': False} if 'sqlite' in db_uri else {}
    )

    # Enable foreign keys for SQLite
    if 'sqlite' in db_uri:
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # Import all models to ensure they're registered
    from . import show, library

    # Create all tables
    Base.metadata.create_all(_engine)
    logger.info("Database tables created successfully")

    # Create session factory
    _session_factory = scoped_session(
        sessionmaker(bind=_engine, expire_on_commit=False)
    )

    return _engine


def get_session():
    """
    Get a database session.

    Returns:
        SQLAlchemy session
    """
    global _session_factory

    if _session_factory is None:
        init_db()

    return _session_factory()


@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.

    Usage:
        with session_scope() as session:
            session.add(obj)
            # Changes are automatically committed
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Session rollback due to error: {e}")
        raise
    finally:
        session.close()


def close_db():
    """Close database connections and cleanup."""
    global _session_factory, _engine

    if _session_factory:
        _session_factory.remove()
        _session_factory = None

    if _engine:
        _engine.dispose()
        _engine = None

    logger.info("Database connections closed")


# Convenience alias
db = Base
