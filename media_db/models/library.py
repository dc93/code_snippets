"""
Models for personal library tracking and matching
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from .database import Base


class MatchStatus(PyEnum):
    """Status of episode matching"""
    MATCHED = 'matched'           # Successfully matched to an episode
    UNMATCHED = 'unmatched'       # Could not match to any episode
    AMBIGUOUS = 'ambiguous'       # Multiple possible matches
    MANUAL = 'manual'             # Manually matched by user


class LibraryPath(Base):
    """
    Represents a path where media files are stored
    """
    __tablename__ = 'library_paths'

    id = Column(Integer, primary_key=True)
    path = Column(String(1000), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Statistics
    total_files = Column(Integer, default=0)
    matched_files = Column(Integer, default=0)
    last_scanned = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    library_items = relationship('LibraryItem', back_populates='library_path', lazy='dynamic')

    def __repr__(self):
        return f'<LibraryPath {self.name or self.path}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'path': self.path,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'total_files': self.total_files,
            'matched_files': self.matched_files,
            'last_scanned': self.last_scanned.isoformat() if self.last_scanned else None,
        }


class LibraryItem(Base):
    """
    Represents a media file in the personal library
    """
    __tablename__ = 'library_items'

    id = Column(Integer, primary_key=True)
    library_path_id = Column(
        Integer,
        ForeignKey('library_paths.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    episode_id = Column(
        Integer,
        ForeignKey('episodes.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )

    # File information
    file_path = Column(String(1000), nullable=False, unique=True, index=True)
    file_name = Column(String(500), nullable=False, index=True)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    file_extension = Column(String(10), nullable=True)
    file_modified = Column(DateTime, nullable=True)

    # Parsed information
    show_name_parsed = Column(String(255), nullable=True, index=True)
    season_parsed = Column(Integer, nullable=True, index=True)
    episode_parsed = Column(Integer, nullable=True, index=True)
    quality = Column(String(50), nullable=True)  # 1080p, 720p, etc.
    release_group = Column(String(100), nullable=True)

    # Matching information
    match_status = Column(
        Enum(MatchStatus),
        default=MatchStatus.UNMATCHED,
        nullable=False,
        index=True
    )
    match_confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    match_method = Column(String(50), nullable=True)  # 'auto', 'manual', 'fuzzy'
    match_notes = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_verified = Column(DateTime, nullable=True)

    # Relationships
    library_path = relationship('LibraryPath', back_populates='library_items')
    episode = relationship('Episode', back_populates='library_items')

    def __repr__(self):
        return f'<LibraryItem {self.file_name}>'

    @property
    def is_matched(self):
        """Check if item is successfully matched."""
        return self.match_status == MatchStatus.MATCHED and self.episode_id is not None

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'show_name': self.show_name_parsed,
            'season': self.season_parsed,
            'episode': self.episode_parsed,
            'quality': self.quality,
            'match_status': self.match_status.value if self.match_status else None,
            'match_confidence': self.match_confidence,
            'is_matched': self.is_matched,
            'episode_id': self.episode_id,
        }
