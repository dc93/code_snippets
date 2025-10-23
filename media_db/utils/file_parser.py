"""
Utilities for parsing media filenames and extracting metadata
"""
import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Comprehensive regex patterns for parsing filenames
PATTERNS = [
    # Pattern: Show.Name.S01E02.stuff
    r'^(?P<show>.+?)[\.\s]+S(?P<season>\d+)E(?P<episode>\d+)',

    # Pattern: Show.Name.1x02.stuff
    r'^(?P<show>.+?)[\.\s]+(?P<season>\d+)x(?P<episode>\d+)',

    # Pattern: Show Name - 1x02 - Episode Title
    r'^(?P<show>.+?)[\s\-]+(?P<season>\d+)x(?P<episode>\d+)',

    # Pattern: Show Name Season 1 Episode 2
    r'^(?P<show>.+?)[\.\s]+[Ss]eason[\.\s]+(?P<season>\d+)[\.\s]+[Ee]pisode[\.\s]+(?P<episode>\d+)',

    # Pattern: Show Name 102 (season 1, episode 2)
    r'^(?P<show>.+?)[\.\s]+(?P<season>\d)(?P<episode>\d{2})[\.\s]+',

    # Pattern: Show.Name.EP02 (no season)
    r'^(?P<show>.+?)[\.\s]+[Ee][Pp]?[\.\s]*(?P<episode>\d+)',
]

# Quality indicators
QUALITY_PATTERNS = [
    r'2160[pP]',
    r'1080[pP]',
    r'720[pP]',
    r'480[pP]',
    r'360[pP]',
    r'4[kK]',
    r'[Uu][Hh][Dd]',
    r'[Hh][Dd]',
    r'[Ss][Dd]',
]

# Release group patterns
RELEASE_GROUP_PATTERN = r'-([A-Za-z0-9]+)$'

# Common junk to remove from show names
JUNK_PATTERNS = [
    r'[\(\[].*?[\)\]]',  # Remove anything in parentheses or brackets
    r'\b(19|20)\d{2}\b',  # Remove years
    r'\b(HDTV|WEB-DL|BluRay|BRRip|DVDRip|WEBRip|WEB)\b',
    r'\b(x264|x265|H\.?264|H\.?265|HEVC|XviD)\b',
    r'\b(AAC|AC3|DTS|DD5\.1|MP3)\b',
    r'\b(ITA|ENG|MULTI|SUBITA)\b',
]


class FileParser:
    """
    Parse media filenames to extract show name, season, episode, and metadata.
    """

    def __init__(self):
        """Initialize the parser with compiled patterns."""
        self.patterns = [re.compile(p, re.IGNORECASE) for p in PATTERNS]
        self.quality_patterns = [re.compile(p, re.IGNORECASE) for p in QUALITY_PATTERNS]
        self.release_group_pattern = re.compile(RELEASE_GROUP_PATTERN)
        self.junk_patterns = [re.compile(p, re.IGNORECASE) for p in JUNK_PATTERNS]

    def parse(self, filename: str) -> Dict:
        """
        Parse a filename and extract metadata.

        Args:
            filename: The filename to parse

        Returns:
            Dictionary with extracted metadata
        """
        # Remove file extension
        name_without_ext = Path(filename).stem

        result = {
            'original_filename': filename,
            'show_name': None,
            'season': None,
            'episode': None,
            'quality': None,
            'release_group': None,
            'parsed': False,
        }

        # Try each pattern
        for pattern in self.patterns:
            match = pattern.search(name_without_ext)
            if match:
                groups = match.groupdict()

                # Extract show name and clean it
                show_name = groups.get('show', '')
                show_name = show_name.replace('.', ' ').replace('_', ' ')
                show_name = self._clean_show_name(show_name)

                result['show_name'] = show_name.strip()
                result['season'] = int(groups['season']) if 'season' in groups and groups['season'] else None
                result['episode'] = int(groups['episode']) if groups['episode'] else None
                result['parsed'] = True

                break

        # Extract quality
        for quality_pattern in self.quality_patterns:
            match = quality_pattern.search(name_without_ext)
            if match:
                result['quality'] = match.group(0)
                break

        # Extract release group
        match = self.release_group_pattern.search(name_without_ext)
        if match:
            result['release_group'] = match.group(1)

        if result['parsed']:
            logger.debug(f"Parsed '{filename}' -> Show: {result['show_name']}, "
                        f"S{result['season']:02d}E{result['episode']:02d}")
        else:
            logger.debug(f"Could not parse: {filename}")

        return result

    def _clean_show_name(self, show_name: str) -> str:
        """
        Clean show name by removing junk patterns.

        Args:
            show_name: Raw show name

        Returns:
            Cleaned show name
        """
        cleaned = show_name

        for junk_pattern in self.junk_patterns:
            cleaned = junk_pattern.sub('', cleaned)

        # Remove extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned.strip()

    def batch_parse(self, filenames: List[str]) -> List[Dict]:
        """
        Parse multiple filenames.

        Args:
            filenames: List of filenames

        Returns:
            List of parsed results
        """
        return [self.parse(filename) for filename in filenames]


def parse_filename(filename: str) -> Dict:
    """
    Convenience function to parse a single filename.

    Args:
        filename: The filename to parse

    Returns:
        Dictionary with extracted metadata
    """
    parser = FileParser()
    return parser.parse(filename)


def extract_season_episode(text: str) -> Optional[Tuple[int, int]]:
    """
    Extract season and episode numbers from text.

    Args:
        text: Text to search

    Returns:
        Tuple of (season, episode) or None
    """
    patterns = [
        r'[Ss](\d+)[Ee](\d+)',
        r'(\d+)x(\d+)',
        r'[Ss]eason\s*(\d+).*?[Ee]pisode\s*(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            season = int(match.group(1))
            episode = int(match.group(2))
            return (season, episode)

    return None
