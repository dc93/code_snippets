"""
Models for TV Shows, Seasons, and Episodes
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Show(Base):
    """
    Represents a TV show from oillocotv.biz
    """
    __tablename__ = 'shows'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    title_normalized = Column(String(255), nullable=False, index=True)  # For matching
    original_title = Column(String(255), nullable=True)
    url = Column(String(500), nullable=True, unique=True)
    slug = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    poster_url = Column(String(500), nullable=True)
    year_start = Column(Integer, nullable=True)
    year_end = Column(Integer, nullable=True)
    status = Column(String(50), nullable=True)  # ongoing, completed, cancelled
    genres = Column(String(500), nullable=True)  # Comma-separated
    imdb_id = Column(String(20), nullable=True, index=True)
    tvdb_id = Column(Integer, nullable=True, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_scraped = Column(DateTime, nullable=True)

    # Relationships
    seasons = relationship('Season', back_populates='show', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f'<Show {self.title} ({self.id})>'

    @property
    def total_seasons(self):
        """Get total number of seasons."""
        return self.seasons.count()

    @property
    def total_episodes(self):
        """Get total number of episodes across all seasons."""
        total = 0
        for season in self.seasons:
            total += season.episodes.count()
        return total

    @property
    def in_library_count(self):
        """Count how many episodes are in the personal library."""
        count = 0
        for season in self.seasons:
            for episode in season.episodes:
                if episode.library_items.count() > 0:
                    count += 1
        return count

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'original_title': self.original_title,
            'url': self.url,
            'description': self.description,
            'year_start': self.year_start,
            'year_end': self.year_end,
            'status': self.status,
            'genres': self.genres.split(',') if self.genres else [],
            'total_seasons': self.total_seasons,
            'total_episodes': self.total_episodes,
            'in_library': self.in_library_count,
        }


class Season(Base):
    """
    Represents a season of a TV show
    """
    __tablename__ = 'seasons'
    __table_args__ = (
        UniqueConstraint('show_id', 'season_number', name='uq_show_season'),
    )

    id = Column(Integer, primary_key=True)
    show_id = Column(Integer, ForeignKey('shows.id', ondelete='CASCADE'), nullable=False, index=True)
    season_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    air_date = Column(DateTime, nullable=True)
    poster_url = Column(String(500), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    show = relationship('Show', back_populates='seasons')
    episodes = relationship('Episode', back_populates='season', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f'<Season {self.season_number} of Show {self.show_id}>'

    @property
    def episode_count(self):
        """Get number of episodes in this season."""
        return self.episodes.count()

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'season_number': self.season_number,
            'title': self.title,
            'description': self.description,
            'air_date': self.air_date.isoformat() if self.air_date else None,
            'episode_count': self.episode_count,
        }


class Episode(Base):
    """
    Represents an episode of a TV show
    """
    __tablename__ = 'episodes'
    __table_args__ = (
        UniqueConstraint('season_id', 'episode_number', name='uq_season_episode'),
    )

    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey('seasons.id', ondelete='CASCADE'), nullable=False, index=True)
    episode_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    title_italian = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    air_date = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in minutes

    # Links and metadata from oillocotv
    page_url = Column(String(500), nullable=True)
    streaming_links = Column(Text, nullable=True)  # JSON array of links

    # Episode identifiers
    imdb_id = Column(String(20), nullable=True, index=True)
    tvdb_id = Column(Integer, nullable=True, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    season = relationship('Season', back_populates='episodes')
    library_items = relationship('LibraryItem', back_populates='episode', lazy='dynamic')

    def __repr__(self):
        season_num = self.season.season_number if self.season else '?'
        return f'<Episode S{season_num:02d}E{self.episode_number:02d}>'

    @property
    def in_library(self):
        """Check if this episode is in the personal library."""
        return self.library_items.count() > 0

    @property
    def episode_code(self):
        """Get episode code in SxxExx format."""
        if self.season:
            return f'S{self.season.season_number:02d}E{self.episode_number:02d}'
        return f'E{self.episode_number:02d}'

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'episode_number': self.episode_number,
            'episode_code': self.episode_code,
            'title': self.title,
            'title_italian': self.title_italian,
            'description': self.description,
            'air_date': self.air_date.isoformat() if self.air_date else None,
            'duration': self.duration,
            'page_url': self.page_url,
            'in_library': self.in_library,
        }
