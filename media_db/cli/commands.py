"""
CLI commands for media database management
"""
import click
import logging
import json
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

from ..models.database import init_db, get_session, session_scope
from ..models.show import Show, Season, Episode
from ..models.library import LibraryItem, LibraryPath, MatchStatus
from ..scrapers import OillocoScraper
from ..utils import FileParser, EpisodeMatcher
from ..config import SUPPORTED_VIDEO_EXTENSIONS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(debug):
    """Media Database CLI - Manage your TV show library."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")


# Database commands
@cli.group()
def db():
    """Database management commands."""
    pass


@db.command()
def init():
    """Initialize the database."""
    click.echo("Initializing database...")
    try:
        init_db()
        click.echo(click.style("✓ Database initialized successfully", fg='green'))
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        raise click.Abort()


@db.command()
def stats():
    """Show database statistics."""
    session = get_session()

    show_count = session.query(Show).count()
    season_count = session.query(Season).count()
    episode_count = session.query(Episode).count()
    library_count = session.query(LibraryItem).count()
    matched_count = session.query(LibraryItem).filter(
        LibraryItem.match_status == MatchStatus.MATCHED
    ).count()

    stats_data = [
        ["Shows", show_count],
        ["Seasons", season_count],
        ["Episodes", episode_count],
        ["Library Items", library_count],
        ["Matched Items", matched_count],
        ["Match Rate", f"{(matched_count/library_count*100):.1f}%" if library_count > 0 else "N/A"],
    ]

    click.echo("\n" + click.style("Database Statistics", fg='cyan', bold=True))
    click.echo(tabulate(stats_data, headers=["Metric", "Value"], tablefmt="simple"))
    click.echo()


# Scraping commands
@cli.group()
def scrape():
    """Web scraping commands."""
    pass


@scrape.command()
@click.option('--max-shows', type=int, default=None, help='Maximum number of shows to scrape')
@click.option('--headless/--no-headless', default=True, help='Run browser in headless mode')
def all(max_shows, headless):
    """Scrape all shows from oillocotv.biz."""
    click.echo("Starting full scrape of oillocotv.biz...")
    click.echo("This may take a while...\n")

    try:
        with OillocoScraper(use_selenium=True, headless=headless) as scraper:
            shows_data = scraper.scrape_all_shows(max_shows=max_shows)

        if not shows_data:
            click.echo(click.style("No shows found", fg='yellow'))
            return

        click.echo(f"\nScraped {len(shows_data)} shows")
        click.echo("Saving to database...")

        saved_count = 0
        with session_scope() as session:
            for show_data in shows_data:
                try:
                    # Check if show already exists
                    existing = session.query(Show).filter_by(url=show_data['url']).first()

                    if existing:
                        show = existing
                        show.last_scraped = datetime.utcnow()
                    else:
                        show = Show(
                            title=show_data['title'],
                            title_normalized=show_data['title'].lower(),
                            url=show_data['url'],
                            slug=show_data.get('slug'),
                            description=show_data.get('description'),
                            last_scraped=datetime.utcnow()
                        )
                        session.add(show)
                        session.flush()

                    # Add seasons and episodes
                    for season_data in show_data.get('seasons', []):
                        season_num = season_data['season_number']

                        # Check if season exists
                        season = session.query(Season).filter_by(
                            show_id=show.id,
                            season_number=season_num
                        ).first()

                        if not season:
                            season = Season(
                                show_id=show.id,
                                season_number=season_num
                            )
                            session.add(season)
                            session.flush()

                        # Add episodes
                        for episode_data in season_data.get('episodes', []):
                            episode_num = episode_data['episode_number']

                            # Check if episode exists
                            episode = session.query(Episode).filter_by(
                                season_id=season.id,
                                episode_number=episode_num
                            ).first()

                            if not episode:
                                episode = Episode(
                                    season_id=season.id,
                                    episode_number=episode_num,
                                    title_italian=episode_data.get('title'),
                                    page_url=episode_data.get('url')
                                )
                                session.add(episode)

                    saved_count += 1

                except Exception as e:
                    logger.error(f"Error saving show {show_data['title']}: {e}")
                    continue

        click.echo(click.style(f"✓ Saved {saved_count} shows to database", fg='green'))

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        raise click.Abort()


@scrape.command()
@click.argument('show_url')
@click.option('--headless/--no-headless', default=True, help='Run browser in headless mode')
def show(show_url, headless):
    """Scrape a specific show by URL."""
    click.echo(f"Scraping show: {show_url}\n")

    try:
        with OillocoScraper(use_selenium=True, headless=headless) as scraper:
            show_data = scraper.scrape_show_page(show_url)

        if not show_data:
            click.echo(click.style("Failed to scrape show", fg='red'))
            return

        click.echo(f"Title: {show_data['title']}")
        click.echo(f"Seasons: {len(show_data['seasons'])}")
        click.echo(f"Total Episodes: {sum(len(s['episodes']) for s in show_data['seasons'])}")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'))
        raise click.Abort()


# Library commands
@cli.group()
def library():
    """Personal library management commands."""
    pass


@library.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--name', help='Name for this library path')
def add(path, name):
    """Add a library path."""
    path = str(Path(path).resolve())

    with session_scope() as session:
        # Check if path already exists
        existing = session.query(LibraryPath).filter_by(path=path).first()
        if existing:
            click.echo(click.style(f"Path already exists: {path}", fg='yellow'))
            return

        lib_path = LibraryPath(
            path=path,
            name=name or Path(path).name
        )
        session.add(lib_path)

    click.echo(click.style(f"✓ Added library path: {path}", fg='green'))


@library.command()
def list():
    """List all library paths."""
    session = get_session()
    paths = session.query(LibraryPath).all()

    if not paths:
        click.echo("No library paths configured")
        return

    data = []
    for p in paths:
        data.append([
            p.id,
            p.name or '-',
            p.path,
            p.total_files,
            p.matched_files,
            '✓' if p.is_active else '✗'
        ])

    click.echo("\n" + click.style("Library Paths", fg='cyan', bold=True))
    click.echo(tabulate(
        data,
        headers=['ID', 'Name', 'Path', 'Files', 'Matched', 'Active'],
        tablefmt='simple'
    ))
    click.echo()


@library.command()
@click.option('--path-id', type=int, help='Scan specific library path by ID')
def scan(path_id):
    """Scan library paths for media files."""
    session = get_session()

    if path_id:
        paths = [session.query(LibraryPath).get(path_id)]
        if not paths[0]:
            click.echo(click.style(f"Library path {path_id} not found", fg='red'))
            return
    else:
        paths = session.query(LibraryPath).filter_by(is_active=True).all()

    if not paths:
        click.echo("No library paths to scan")
        return

    parser = FileParser()
    total_found = 0

    for lib_path in paths:
        click.echo(f"\nScanning: {lib_path.path}")
        path_obj = Path(lib_path.path)

        if not path_obj.exists():
            click.echo(click.style(f"  ✗ Path does not exist", fg='red'))
            continue

        # Find all video files
        video_files = []
        for ext in SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(path_obj.rglob(f'*{ext}'))

        click.echo(f"  Found {len(video_files)} video files")

        added_count = 0
        with session_scope() as session:
            for video_file in video_files:
                file_path = str(video_file.resolve())
                file_name = video_file.name

                # Check if already in database
                existing = session.query(LibraryItem).filter_by(file_path=file_path).first()
                if existing:
                    continue

                # Parse filename
                parsed = parser.parse(file_name)

                # Create library item
                item = LibraryItem(
                    library_path_id=lib_path.id,
                    file_path=file_path,
                    file_name=file_name,
                    file_size=video_file.stat().st_size,
                    file_extension=video_file.suffix,
                    file_modified=datetime.fromtimestamp(video_file.stat().st_mtime),
                    show_name_parsed=parsed.get('show_name'),
                    season_parsed=parsed.get('season'),
                    episode_parsed=parsed.get('episode'),
                    quality=parsed.get('quality'),
                    release_group=parsed.get('release_group'),
                    match_status=MatchStatus.UNMATCHED
                )
                session.add(item)
                added_count += 1

            # Update library path stats
            lib_path.total_files = len(video_files)
            lib_path.last_scanned = datetime.utcnow()

        click.echo(click.style(f"  ✓ Added {added_count} new files", fg='green'))
        total_found += added_count

    click.echo(f"\n{click.style(f'Total: {total_found} new files added', fg='green')}")


@library.command()
def match():
    """Match library items to episodes."""
    click.echo("Matching library items to episodes...\n")

    matcher = EpisodeMatcher()
    matched, total = matcher.match_all_unmatched()

    click.echo(click.style(f"✓ Matched {matched}/{total} items", fg='green'))


@library.command()
@click.option('--status', type=click.Choice(['all', 'matched', 'unmatched']), default='all')
@click.option('--limit', type=int, default=50, help='Number of items to show')
def items(status, limit):
    """List library items."""
    session = get_session()

    query = session.query(LibraryItem)

    if status == 'matched':
        query = query.filter(LibraryItem.match_status == MatchStatus.MATCHED)
    elif status == 'unmatched':
        query = query.filter(LibraryItem.match_status == MatchStatus.UNMATCHED)

    items = query.limit(limit).all()

    if not items:
        click.echo("No library items found")
        return

    data = []
    for item in items:
        status_icon = '✓' if item.is_matched else '✗'
        episode_info = '-'

        if item.episode:
            ep = item.episode
            episode_info = f"{ep.season.show.title} {ep.episode_code}"
        elif item.show_name_parsed:
            episode_info = f"{item.show_name_parsed} S{item.season_parsed or '?'}E{item.episode_parsed or '?'}"

        data.append([
            item.id,
            status_icon,
            item.file_name[:50],
            episode_info[:50],
        ])

    click.echo("\n" + click.style("Library Items", fg='cyan', bold=True))
    click.echo(tabulate(
        data,
        headers=['ID', 'Status', 'Filename', 'Matched To'],
        tablefmt='simple'
    ))
    click.echo()


# Show commands
@cli.group()
def shows():
    """Show management commands."""
    pass


@shows.command()
@click.option('--limit', type=int, default=20, help='Number of shows to list')
def list(limit):
    """List shows in database."""
    session = get_session()
    shows = session.query(Show).limit(limit).all()

    if not shows:
        click.echo("No shows in database")
        return

    data = []
    for show in shows:
        data.append([
            show.id,
            show.title,
            show.total_seasons,
            show.total_episodes,
            show.in_library_count,
        ])

    click.echo("\n" + click.style("Shows", fg='cyan', bold=True))
    click.echo(tabulate(
        data,
        headers=['ID', 'Title', 'Seasons', 'Episodes', 'In Library'],
        tablefmt='simple'
    ))
    click.echo()


@shows.command()
@click.argument('show_id', type=int)
def info(show_id):
    """Show detailed information about a show."""
    session = get_session()
    show = session.query(Show).get(show_id)

    if not show:
        click.echo(click.style(f"Show {show_id} not found", fg='red'))
        return

    click.echo("\n" + click.style(show.title, fg='cyan', bold=True))
    click.echo(f"ID: {show.id}")
    click.echo(f"URL: {show.url}")
    click.echo(f"Seasons: {show.total_seasons}")
    click.echo(f"Episodes: {show.total_episodes}")
    click.echo(f"In Library: {show.in_library_count}/{show.total_episodes}")
    if show.description:
        click.echo(f"\nDescription:\n{show.description}")

    # List seasons
    click.echo("\n" + click.style("Seasons", fg='cyan'))
    season_data = []
    for season in show.seasons:
        in_lib = sum(1 for ep in season.episodes if ep.in_library)
        season_data.append([
            season.season_number,
            season.episode_count,
            in_lib,
            f"{(in_lib/season.episode_count*100):.0f}%" if season.episode_count > 0 else "0%"
        ])

    click.echo(tabulate(
        season_data,
        headers=['Season', 'Episodes', 'In Library', 'Progress'],
        tablefmt='simple'
    ))
    click.echo()


@shows.command()
@click.argument('query')
def search(query):
    """Search for shows by name."""
    session = get_session()
    shows = session.query(Show).filter(
        Show.title.ilike(f'%{query}%')
    ).all()

    if not shows:
        click.echo(f"No shows found matching '{query}'")
        return

    data = []
    for show in shows:
        data.append([
            show.id,
            show.title,
            show.total_seasons,
            show.total_episodes,
            show.in_library_count,
        ])

    click.echo("\n" + click.style(f"Search results for '{query}'", fg='cyan', bold=True))
    click.echo(tabulate(
        data,
        headers=['ID', 'Title', 'Seasons', 'Episodes', 'In Library'],
        tablefmt='simple'
    ))
    click.echo()


if __name__ == '__main__':
    cli()
