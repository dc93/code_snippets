"""
Title normalization utilities for matching
"""
import re
import unicodedata
from typing import Optional


def normalize_title(title: str) -> str:
    """
    Normalize a title for matching purposes.

    This function:
    - Converts to lowercase
    - Removes accents and diacritics
    - Removes special characters
    - Normalizes whitespace
    - Removes common articles

    Args:
        title: The title to normalize

    Returns:
        Normalized title
    """
    if not title:
        return ''

    # Convert to lowercase
    normalized = title.lower()

    # Remove accents/diacritics
    normalized = unicodedata.normalize('NFKD', normalized)
    normalized = ''.join([c for c in normalized if not unicodedata.combining(c)])

    # Remove special characters but keep spaces
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)

    # Remove common articles
    articles = ['the', 'a', 'an', 'il', 'lo', 'la', 'i', 'gli', 'le']
    words = normalized.split()
    words = [w for w in words if w not in articles]

    # Normalize whitespace
    normalized = ' '.join(words)
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized.strip()


def clean_filename(filename: str) -> str:
    """
    Clean a filename for display purposes.

    Args:
        filename: The filename to clean

    Returns:
        Cleaned filename
    """
    # Replace common separators with spaces
    cleaned = filename.replace('.', ' ')
    cleaned = cleaned.replace('_', ' ')
    cleaned = cleaned.replace('-', ' ')

    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)

    return cleaned.strip()


def extract_year(text: str) -> Optional[int]:
    """
    Extract a year from text (1900-2099).

    Args:
        text: Text to search

    Returns:
        Year as integer or None
    """
    match = re.search(r'\b(19|20)\d{2}\b', text)
    if match:
        return int(match.group(0))
    return None


def remove_year(text: str) -> str:
    """
    Remove year from text.

    Args:
        text: Text to process

    Returns:
        Text without year
    """
    return re.sub(r'\b(19|20)\d{2}\b', '', text).strip()
