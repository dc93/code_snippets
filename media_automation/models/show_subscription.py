"""
Show subscription models for automation
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum
from datetime import datetime
from enum import Enum as PyEnum
from .database import Base


class MonitorStatus(PyEnum):
    """Monitoring status for shows"""
    ALL = 'all'                    # Monitor all episodes
    FUTURE = 'future'              # Only new episodes from now on
    LATEST_SEASON = 'latest'       # Only the latest season
    FIRST_SEASON = 'first'         # Only first season
    NONE = 'none'                  # Don't monitor (manual)


class QualityProfile(PyEnum):
    """Quality preferences"""
    ANY = 'any'
    SD = '480p'
    HD = '720p'
    FULL_HD = '1080p'
    UHD = '2160p'


class ShowSubscription(Base):
    """
    Represents a TV show that's being monitored for automatic downloads.
    """
    __tablename__ = 'show_subscriptions'

    id = Column(Integer, primary_key=True)

    # Link to media_db Show (if exists)
    media_db_show_id = Column(Integer, nullable=True, index=True)

    # Show information
    title = Column(String(255), nullable=False, index=True)
    year = Column(Integer, nullable=True)
    tvdb_id = Column(Integer, nullable=True, index=True)
    imdb_id = Column(String(20), nullable=True, index=True)

    # Monitoring settings
    monitored = Column(Boolean, default=True, nullable=False, index=True)
    monitor_status = Column(
        SQLEnum(MonitorStatus),
        default=MonitorStatus.ALL,
        nullable=False
    )

    # Quality preferences
    quality_profile = Column(
        SQLEnum(QualityProfile),
        default=QualityProfile.FULL_HD,
        nullable=False
    )

    # Library settings
    root_folder = Column(String(500), nullable=True)  # Where to save (overrides default)
    season_folder = Column(Boolean, default=True, nullable=False)  # Create season folders

    # Source preferences
    preferred_source = Column(String(50), default='oillocotv', nullable=False)
    language_preference = Column(String(10), default='ITA', nullable=False)

    # Search settings
    search_missing_episodes = Column(Boolean, default=True, nullable=False)
    backlog_search_enabled = Column(Boolean, default=True, nullable=False)

    # Metadata
    added_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_monitored = Column(DateTime, nullable=True)
    last_episode_added = Column(DateTime, nullable=True)

    # Statistics
    total_episodes_monitored = Column(Integer, default=0, nullable=False)
    episodes_downloaded = Column(Integer, default=0, nullable=False)
    episodes_missing = Column(Integer, default=0, nullable=False)

    # Notes
    tags = Column(String(500), nullable=True)  # Comma-separated tags
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f'<ShowSubscription {self.title} (monitored={self.monitored})>'

    @property
    def is_monitored(self):
        """Check if show is being actively monitored."""
        return self.monitored and self.monitor_status != MonitorStatus.NONE

    @property
    def completion_percentage(self):
        """Calculate download completion percentage."""
        if self.total_episodes_monitored == 0:
            return 0.0
        return (self.episodes_downloaded / self.total_episodes_monitored) * 100

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'year': self.year,
            'monitored': self.monitored,
            'monitor_status': self.monitor_status.value if self.monitor_status else None,
            'quality_profile': self.quality_profile.value if self.quality_profile else None,
            'total_episodes': self.total_episodes_monitored,
            'downloaded': self.episodes_downloaded,
            'missing': self.episodes_missing,
            'completion': f"{self.completion_percentage:.1f}%",
            'last_monitored': self.last_monitored.isoformat() if self.last_monitored else None,
        }
