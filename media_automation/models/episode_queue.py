"""
Episode queue and download history models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from .database import Base


class QueueStatus(PyEnum):
    """Status of episode in download queue"""
    WANTED = 'wanted'              # Detected, ready to download
    SEARCHING = 'searching'        # Looking for links
    QUEUED = 'queued'              # Links sent to JDownloader
    DOWNLOADING = 'downloading'    # Currently downloading
    DOWNLOADED = 'downloaded'      # Download complete
    ORGANIZING = 'organizing'      # Moving/renaming file
    COMPLETED = 'completed'        # Fully processed and in library
    FAILED = 'failed'              # Failed to download/process
    IGNORED = 'ignored'            # User marked to ignore


class EpisodeQueue(Base):
    """
    Represents an episode in the download queue.
    """
    __tablename__ = 'episode_queue'

    id = Column(Integer, primary_key=True)

    # Relationships
    subscription_id = Column(
        Integer,
        ForeignKey('show_subscriptions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    media_db_episode_id = Column(Integer, nullable=True, index=True)  # Link to media_db

    # Episode information
    show_title = Column(String(255), nullable=False, index=True)
    season_number = Column(Integer, nullable=False, index=True)
    episode_number = Column(Integer, nullable=False, index=True)
    episode_title = Column(String(255), nullable=True)

    # Source information
    source_site = Column(String(50), nullable=False)  # 'oillocotv', 'crockdown'
    source_url = Column(String(1000), nullable=True)  # Episode page URL
    download_links = Column(Text, nullable=True)      # JSON array of links

    # Download settings
    quality = Column(String(20), nullable=True)
    language = Column(String(10), nullable=True)
    release_group = Column(String(100), nullable=True)

    # Status tracking
    status = Column(
        SQLEnum(QueueStatus),
        default=QueueStatus.WANTED,
        nullable=False,
        index=True
    )
    priority = Column(Integer, default=0, nullable=False)  # Higher = more important

    # JDownloader tracking
    jdownloader_link_ids = Column(Text, nullable=True)  # JSON array of JD link IDs
    jdownloader_package_id = Column(String(100), nullable=True)
    download_progress = Column(Float, default=0.0, nullable=False)  # 0-100

    # File information (after download)
    downloaded_file_path = Column(String(1000), nullable=True)
    downloaded_file_size = Column(Integer, nullable=True)  # Bytes
    final_file_path = Column(String(1000), nullable=True)  # After organization

    # Error handling
    retry_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    added_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    grabbed_date = Column(DateTime, nullable=True)  # When links were sent to JD
    downloaded_date = Column(DateTime, nullable=True)  # When download completed
    completed_date = Column(DateTime, nullable=True)  # When fully processed
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Metadata
    manual_grab = Column(Boolean, default=False, nullable=False)  # User manually added
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f'<EpisodeQueue {self.show_title} S{self.season_number:02d}E{self.episode_number:02d} ({self.status.value})>'

    @property
    def episode_code(self):
        """Get episode code in SxxExx format."""
        return f'S{self.season_number:02d}E{self.episode_number:02d}'

    @property
    def is_downloading(self):
        """Check if currently downloading."""
        return self.status in [QueueStatus.DOWNLOADING, QueueStatus.QUEUED]

    @property
    def can_retry(self):
        """Check if download can be retried."""
        return self.status == QueueStatus.FAILED and self.retry_count < 3

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'show_title': self.show_title,
            'season': self.season_number,
            'episode': self.episode_number,
            'episode_code': self.episode_code,
            'episode_title': self.episode_title,
            'status': self.status.value if self.status else None,
            'quality': self.quality,
            'source_site': self.source_site,
            'download_progress': self.download_progress,
            'added_date': self.added_date.isoformat() if self.added_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
        }


class DownloadHistory(Base):
    """
    Complete history of all download attempts.
    """
    __tablename__ = 'download_history'

    id = Column(Integer, primary_key=True)

    # Episode information
    subscription_id = Column(Integer, nullable=True, index=True)
    show_title = Column(String(255), nullable=False, index=True)
    season_number = Column(Integer, nullable=False)
    episode_number = Column(Integer, nullable=False)
    episode_title = Column(String(255), nullable=True)

    # Download information
    source_site = Column(String(50), nullable=False)
    source_url = Column(String(1000), nullable=True)
    quality = Column(String(20), nullable=True)
    file_size = Column(Integer, nullable=True)

    # Result
    success = Column(Boolean, nullable=False, index=True)
    status_message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Files
    downloaded_file = Column(String(1000), nullable=True)
    final_location = Column(String(1000), nullable=True)

    # Timing
    grabbed_date = Column(DateTime, nullable=True)
    download_start = Column(DateTime, nullable=True)
    download_end = Column(DateTime, nullable=True)
    download_duration_seconds = Column(Integer, nullable=True)

    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    manual = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        status = "✓" if self.success else "✗"
        return f'<DownloadHistory {status} {self.show_title} S{self.season_number:02d}E{self.episode_number:02d}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'show_title': self.show_title,
            'season': self.season_number,
            'episode': self.episode_number,
            'episode_title': self.episode_title,
            'success': self.success,
            'quality': self.quality,
            'file_size': self.file_size,
            'source_site': self.source_site,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'duration': self.download_duration_seconds,
        }
