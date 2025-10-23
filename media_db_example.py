#!/usr/bin/env python3
"""
Example usage of the Media Database System API

This demonstrates how to use the system programmatically
instead of through the CLI.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from media_db.models import init_db, get_session, Show, Season, Episode, LibraryItem
from media_db.utils import parse_filename, EpisodeMatcher, normalize_title
from media_db.scrapers import OillocoScraper


def example_parse_filenames():
    """Example: Parse media filenames."""
    print("=" * 60)
    print("Example 1: Parsing Filenames")
    print("=" * 60)

    filenames = [
        "Lucifer.S03E05.1080p.WEB-DL.mkv",
        "Arrow 5x12 Episode Title.mp4",
        "The.Walking.Dead.S10E03.HDTV.x264.avi",
        "Breaking Bad 501 HDTV.mkv",
    ]

    for filename in filenames:
        result = parse_filename(filename)
        if result['parsed']:
            print(f"\n{filename}")
            print(f"  Show: {result['show_name']}")
            print(f"  Season: {result['season']}")
            print(f"  Episode: {result['episode']}")
            print(f"  Quality: {result['quality']}")
        else:
            print(f"\n{filename} - Could not parse")


def example_normalize_titles():
    """Example: Title normalization for matching."""
    print("\n" + "=" * 60)
    print("Example 2: Normalizing Titles")
    print("=" * 60)

    titles = [
        "The Walking Dead",
        "The.Walking.Dead",
        "Walking Dead",
        "Il Trono di Spade",  # Italian for Game of Thrones
        "Game of Thrones",
    ]

    for title in titles:
        normalized = normalize_title(title)
        print(f"{title:30} -> {normalized}")


def example_database_queries():
    """Example: Database queries."""
    print("\n" + "=" * 60)
    print("Example 3: Database Queries")
    print("=" * 60)

    # Initialize database
    init_db()
    session = get_session()

    # Count shows
    show_count = session.query(Show).count()
    print(f"\nTotal shows in database: {show_count}")

    if show_count > 0:
        # Get first show
        show = session.query(Show).first()
        print(f"\nExample show: {show.title}")
        print(f"  Seasons: {show.total_seasons}")
        print(f"  Episodes: {show.total_episodes}")
        print(f"  In library: {show.in_library_count}")

        # List seasons
        for season in show.seasons:
            in_lib = sum(1 for ep in season.episodes if ep.in_library)
            print(f"  Season {season.season_number}: {season.episode_count} episodes, "
                  f"{in_lib} in library")


def example_matching():
    """Example: Episode matching."""
    print("\n" + "=" * 60)
    print("Example 4: Episode Matching")
    print("=" * 60)

    # Initialize database
    init_db()
    session = get_session()

    # Check if we have any shows
    show_count = session.query(Show).count()
    if show_count == 0:
        print("\nNo shows in database. Run scraping first:")
        print("  python media_db_cli.py scrape all --max-shows 10")
        return

    # Example: Find a show
    matcher = EpisodeMatcher()
    show_name = "Lucifer"

    matches = matcher.find_show_matches(show_name, max_results=3)

    print(f"\nSearching for: '{show_name}'")
    if matches:
        print(f"Found {len(matches)} matches:")
        for show, similarity in matches:
            print(f"  {show.title} (similarity: {similarity:.2%})")
    else:
        print("No matches found")


def example_scraper_info():
    """Example: Information about the scraper."""
    print("\n" + "=" * 60)
    print("Example 5: Web Scraper Information")
    print("=" * 60)

    print("\nThe scraper can:")
    print("  1. Scrape the complete series list from oillocotv.biz")
    print("  2. Scrape individual show pages to get seasons and episodes")
    print("  3. Scrape episode pages to get streaming links")
    print()
    print("Usage:")
    print("  # Scrape all shows (slow!)")
    print("  python media_db_cli.py scrape all")
    print()
    print("  # Scrape just 10 shows for testing")
    print("  python media_db_cli.py scrape all --max-shows 10")
    print()
    print("Note: The site has bot protection, so we use Selenium.")
    print("Make sure you have Chrome/Chromium installed!")


def example_library_workflow():
    """Example: Typical library workflow."""
    print("\n" + "=" * 60)
    print("Example 6: Complete Workflow")
    print("=" * 60)

    print("\nTypical workflow to track your library:")
    print()
    print("1. Initialize database:")
    print("   python media_db_cli.py db init")
    print()
    print("2. Scrape shows from oillocotv.biz:")
    print("   python media_db_cli.py scrape all --max-shows 10")
    print()
    print("3. Add your library path:")
    print("   python media_db_cli.py library add /path/to/shows --name 'TV Shows'")
    print()
    print("4. Scan library for video files:")
    print("   python media_db_cli.py library scan")
    print()
    print("5. Match files to episodes:")
    print("   python media_db_cli.py library match")
    print()
    print("6. Check what you have:")
    print("   python media_db_cli.py shows search 'lucifer'")
    print("   python media_db_cli.py shows info 1")
    print()
    print("7. View statistics:")
    print("   python media_db_cli.py db stats")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("MEDIA DATABASE SYSTEM - EXAMPLES")
    print("=" * 60)

    example_parse_filenames()
    example_normalize_titles()
    example_database_queries()
    example_matching()
    example_scraper_info()
    example_library_workflow()

    print("\n" + "=" * 60)
    print("For more information, see MEDIA_DB_README.md")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
