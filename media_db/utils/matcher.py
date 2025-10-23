"""
Episode matching utilities for personal library
"""
import logging
from typing import List, Optional, Tuple
from difflib import SequenceMatcher

from ..models.database import get_session
from ..models.show import Show, Episode
from ..models.library import LibraryItem, MatchStatus
from .normalizer import normalize_title
from .file_parser import FileParser

logger = logging.getLogger(__name__)


class EpisodeMatcher:
    """
    Match library items to episodes in the database.
    """

    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize the matcher.

        Args:
            similarity_threshold: Minimum similarity score for matching (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold
        self.parser = FileParser()

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize both strings
        norm1 = normalize_title(str1)
        norm2 = normalize_title(str2)

        # Calculate similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity

    def find_show_matches(self, show_name: str, max_results: int = 5) -> List[Tuple[Show, float]]:
        """
        Find shows matching a given name.

        Args:
            show_name: Show name to match
            max_results: Maximum number of results

        Returns:
            List of (Show, similarity_score) tuples
        """
        session = get_session()
        all_shows = session.query(Show).all()

        matches = []
        for show in all_shows:
            similarity = self.calculate_similarity(show_name, show.title)
            if similarity >= self.similarity_threshold:
                matches.append((show, similarity))

        # Sort by similarity descending
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches[:max_results]

    def find_episode(
        self,
        show_name: str,
        season: int,
        episode: int
    ) -> Optional[Episode]:
        """
        Find an episode in the database.

        Args:
            show_name: Show name
            season: Season number
            episode: Episode number

        Returns:
            Episode object or None
        """
        session = get_session()

        # Find matching show
        show_matches = self.find_show_matches(show_name, max_results=1)
        if not show_matches:
            logger.debug(f"No show match for: {show_name}")
            return None

        show, similarity = show_matches[0]
        logger.debug(f"Matched show '{show_name}' to '{show.title}' (similarity: {similarity:.2f})")

        # Find the episode
        episode_obj = session.query(Episode).join(Episode.season).filter(
            Episode.season.has(show_id=show.id),
            Episode.season.has(season_number=season),
            Episode.episode_number == episode
        ).first()

        return episode_obj

    def match_library_item(self, library_item: LibraryItem) -> bool:
        """
        Try to match a library item to an episode.

        Args:
            library_item: The library item to match

        Returns:
            True if matched successfully, False otherwise
        """
        session = get_session()

        # Parse the filename if not already parsed
        if not library_item.show_name_parsed:
            parsed = self.parser.parse(library_item.file_name)
            if parsed['parsed']:
                library_item.show_name_parsed = parsed['show_name']
                library_item.season_parsed = parsed['season']
                library_item.episode_parsed = parsed['episode']
                library_item.quality = parsed['quality']
                library_item.release_group = parsed['release_group']
            else:
                library_item.match_status = MatchStatus.UNMATCHED
                library_item.match_notes = "Could not parse filename"
                session.commit()
                return False

        # Try to find the episode
        episode = self.find_episode(
            library_item.show_name_parsed,
            library_item.season_parsed,
            library_item.episode_parsed
        )

        if episode:
            # Get similarity for confidence score
            show_matches = self.find_show_matches(library_item.show_name_parsed, max_results=1)
            confidence = show_matches[0][1] if show_matches else 0.0

            library_item.episode_id = episode.id
            library_item.match_status = MatchStatus.MATCHED
            library_item.match_confidence = confidence
            library_item.match_method = 'auto'
            library_item.match_notes = f"Matched to {episode.season.show.title}"

            session.commit()
            logger.info(f"Matched: {library_item.file_name} -> {episode.season.show.title} "
                       f"S{episode.season.season_number:02d}E{episode.episode_number:02d}")
            return True
        else:
            library_item.match_status = MatchStatus.UNMATCHED
            library_item.match_notes = "No matching episode found in database"
            session.commit()
            logger.debug(f"No match for: {library_item.file_name}")
            return False

    def match_all_unmatched(self) -> Tuple[int, int]:
        """
        Try to match all unmatched library items.

        Returns:
            Tuple of (matched_count, total_processed)
        """
        session = get_session()

        unmatched = session.query(LibraryItem).filter(
            LibraryItem.match_status == MatchStatus.UNMATCHED
        ).all()

        matched_count = 0
        total = len(unmatched)

        logger.info(f"Attempting to match {total} unmatched items")

        for item in unmatched:
            if self.match_library_item(item):
                matched_count += 1

        logger.info(f"Matched {matched_count}/{total} items")
        return (matched_count, total)

    def rematch_all(self) -> Tuple[int, int]:
        """
        Re-match all library items.

        Returns:
            Tuple of (matched_count, total_processed)
        """
        session = get_session()

        all_items = session.query(LibraryItem).all()
        total = len(all_items)
        matched_count = 0

        logger.info(f"Re-matching {total} items")

        for item in all_items:
            # Reset match status
            item.match_status = MatchStatus.UNMATCHED
            item.episode_id = None
            session.commit()

            if self.match_library_item(item):
                matched_count += 1

        logger.info(f"Matched {matched_count}/{total} items")
        return (matched_count, total)
