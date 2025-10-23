# Media Database System

A comprehensive system to track TV shows and episodes from **oillocotv.biz** and match them against your personal media library.

## Features

- **Web Scraping**: Automatically scrape TV show data from oillocotv.biz
- **Database Management**: Store shows, seasons, and episodes in a local SQLite database
- **Library Tracking**: Scan your local media files and parse episode information
- **Smart Matching**: Automatically match your files to episodes in the database
- **Progress Tracking**: See which episodes you have and which are missing
- **CLI Interface**: Easy-to-use command-line interface for all operations

## Architecture

### Database Schema

The system uses four main models:

1. **Show**: Represents a TV show
   - Title, URL, description
   - Links to seasons

2. **Season**: Represents a season of a show
   - Season number
   - Links to episodes

3. **Episode**: Represents an individual episode
   - Episode number, title
   - Links from oillocotv.biz
   - Links to library items

4. **LibraryItem**: Represents a file in your library
   - File path and metadata
   - Parsed show/season/episode info
   - Match status and confidence

### Components

- **Scrapers**: Web scraping using Selenium (bypasses bot protection)
- **Parsers**: Extract show/season/episode info from filenames
- **Matchers**: Fuzzy matching between library files and database episodes
- **CLI**: Command-line interface for all operations

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements_media_db.txt
```

### 2. Install Chrome/Chromium (for Selenium)

The scraper uses Selenium with Chrome. Make sure you have Chrome or Chromium installed:

```bash
# Ubuntu/Debian
sudo apt-get install chromium-browser chromium-chromedriver

# Or install Google Chrome manually
```

### 3. Initialize Database

```bash
python media_db_cli.py db init
```

## Usage

### Database Commands

```bash
# Initialize database
python media_db_cli.py db init

# Show statistics
python media_db_cli.py db stats
```

### Scraping Commands

```bash
# Scrape all shows from oillocotv.biz
python media_db_cli.py scrape all

# Scrape first 10 shows only (for testing)
python media_db_cli.py scrape all --max-shows 10

# Scrape a specific show by URL
python media_db_cli.py scrape show https://oillocotv.biz/lucifer/

# Run browser in non-headless mode (to see what's happening)
python media_db_cli.py scrape all --no-headless
```

**Note**: Scraping takes time! The site has bot protection, so we use Selenium with delays between requests. Scraping all shows may take several hours.

### Library Management

```bash
# Add a library path
python media_db_cli.py library add /path/to/your/tv/shows --name "My TV Shows"

# List library paths
python media_db_cli.py library list

# Scan library for video files
python media_db_cli.py library scan

# Match library files to episodes
python media_db_cli.py library match

# List library items
python media_db_cli.py library items

# List only matched items
python media_db_cli.py library items --status matched

# List only unmatched items
python media_db_cli.py library items --status unmatched
```

### Show Commands

```bash
# List shows in database
python media_db_cli.py shows list

# Search for shows
python media_db_cli.py shows search "lucifer"

# Show detailed info about a specific show
python media_db_cli.py shows info 1
```

## Typical Workflow

### First Time Setup

1. **Initialize database**:
   ```bash
   python media_db_cli.py db init
   ```

2. **Scrape shows from oillocotv.biz**:
   ```bash
   # Start with a small test
   python media_db_cli.py scrape all --max-shows 10

   # Once confirmed working, scrape everything (takes a while!)
   python media_db_cli.py scrape all
   ```

3. **Add your library paths**:
   ```bash
   python media_db_cli.py library add /path/to/your/tv/shows --name "TV Shows"
   ```

4. **Scan your library**:
   ```bash
   python media_db_cli.py library scan
   ```

5. **Match files to episodes**:
   ```bash
   python media_db_cli.py library match
   ```

6. **Check results**:
   ```bash
   python media_db_cli.py db stats
   python media_db_cli.py shows list
   ```

### Checking What You Have

1. **Search for a show**:
   ```bash
   python media_db_cli.py shows search "lucifer"
   ```

2. **Get show details**:
   ```bash
   python media_db_cli.py shows info 42
   ```

   This will show:
   - Total episodes in the show
   - How many you have in your library
   - Progress per season

### Updating

1. **Re-scrape to get new episodes**:
   ```bash
   python media_db_cli.py scrape all
   ```

2. **Re-scan library for new files**:
   ```bash
   python media_db_cli.py library scan
   ```

3. **Match new files**:
   ```bash
   python media_db_cli.py library match
   ```

## File Naming Conventions

The system can parse various filename formats:

- `Show.Name.S01E02.1080p.WEB-DL.mkv`
- `Show Name 1x02 Episode Title.mp4`
- `Show.Name.Season.1.Episode.2.avi`
- `Show Name 102.mkv` (season 1, episode 2)

The parser extracts:
- Show name
- Season number
- Episode number
- Quality (1080p, 720p, etc.)
- Release group

## Configuration

Edit `media_db/config.py` to customize:

- Database location
- Scraper delays and timeouts
- Supported video extensions
- Matching thresholds
- Selenium settings

## Troubleshooting

### Selenium Issues

If scraping fails:

1. **Check Chrome/Chromium installation**:
   ```bash
   chromium-browser --version
   ```

2. **Install/update chromedriver**:
   ```bash
   sudo apt-get install chromium-chromedriver
   ```

3. **Run in non-headless mode** to see what's happening:
   ```bash
   python media_db_cli.py scrape all --no-headless
   ```

### Matching Issues

If files aren't matching:

1. **Check parsed filenames**:
   ```bash
   python media_db_cli.py library items --status unmatched
   ```

2. **Adjust filename format**: The parser may not recognize your format. Check `media_db/utils/file_parser.py`

3. **Manual matching**: You can manually update the database using SQL

4. **Lower threshold**: Edit `MATCH_THRESHOLD` in `config.py`

### Performance

- **Scraping is slow by design**: We add delays to avoid being blocked
- **First scan is slow**: Parsing thousands of files takes time
- **Database grows large**: With many shows, the database can be 50-100 MB

## Database Location

By default, the database is stored at:
```
instance/media_database.db
```

You can change this by setting the `MEDIA_DB_PATH` environment variable.

## Advanced Usage

### Enable Debug Logging

```bash
python media_db_cli.py --debug db stats
```

### Export Show Data

The models have `.to_dict()` methods for JSON export:

```python
from media_db.models import get_session, Show

session = get_session()
show = session.query(Show).first()
print(show.to_dict())
```

### Direct Database Access

```bash
sqlite3 instance/media_database.db
```

```sql
-- Find all shows with episodes
SELECT s.title, COUNT(DISTINCT se.id) as seasons, COUNT(e.id) as episodes
FROM shows s
JOIN seasons se ON se.show_id = s.id
JOIN episodes e ON e.season_id = se.id
GROUP BY s.id;

-- Find unmatched library items
SELECT file_name, show_name_parsed, season_parsed, episode_parsed
FROM library_items
WHERE match_status = 'unmatched';

-- Find what episodes you're missing
SELECT s.title, se.season_number, e.episode_number
FROM episodes e
JOIN seasons se ON e.season_id = se.id
JOIN shows s ON se.show_id = s.id
LEFT JOIN library_items li ON li.episode_id = e.id
WHERE li.id IS NULL;
```

## File Structure

```
media_db/
├── __init__.py
├── config.py                 # Configuration settings
├── models/
│   ├── __init__.py
│   ├── database.py           # Database setup
│   ├── show.py               # Show, Season, Episode models
│   └── library.py            # LibraryItem, LibraryPath models
├── scrapers/
│   ├── __init__.py
│   └── oilloco_scraper.py    # Web scraper
├── utils/
│   ├── __init__.py
│   ├── file_parser.py        # Filename parsing
│   ├── matcher.py            # Episode matching
│   └── normalizer.py         # Title normalization
└── cli/
    ├── __init__.py
    └── commands.py           # CLI commands

media_db_cli.py               # Main entry point
```

## Contributing

This is a personal project, but suggestions are welcome!

## License

Free to use and modify for personal use.

## Disclaimer

This tool is for managing your personal media library. Respect copyright laws and only use it with content you legally own or have rights to access.
