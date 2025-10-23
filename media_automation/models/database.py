"""
Database initialization for automation system
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import logging
from pathlib import Path

from ..config import AUTOMATION_DB_URI, AUTOMATION_DB_PATH

logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

# Global engine and session factory
_engine = None
_session_factory = None


def init_db(db_uri=None, echo=False):
    """Initialize the database engine and create all tables."""
    global _engine, _session_factory

    if db_uri is None:
        db_uri = AUTOMATION_DB_URI

    # Create database directory
    db_path = Path(AUTOMATION_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initializing automation database at: {db_uri}")

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

    # Import all models
    from . import show_subscription, episode_queue, settings

    # Create all tables
    Base.metadata.create_all(_engine)
    logger.info("Automation database tables created successfully")

    # Create session factory
    _session_factory = scoped_session(
        sessionmaker(bind=_engine, expire_on_commit=False)
    )

    return _engine


def get_session():
    """Get a database session."""
    global _session_factory

    if _session_factory is None:
        init_db()

    return _session_factory()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
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

    logger.info("Automation database connections closed")


# Convenience alias
db = Base
