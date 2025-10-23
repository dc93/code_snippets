# Media Automation System - Complete Architecture Plan

## Overview
A Sonarr/Radarr-like automation system for Italian streaming sites (oillocotv.biz and crockdown.com) integrated with JDownloader.

## System Components

### 1. Core Database Models

#### ShowSubscription
- Show metadata (title, year, status)
- Monitoring settings (which seasons to monitor)
- Quality preferences
- Root folder path
- Last check timestamp
- Links to media_db Show table

#### EpisodeQueue
- Episode to download
- Source site and URL
- Download links
- Status (wanted, downloading, downloaded, failed)
- Priority
- Quality
- JDownloader status

#### DownloadHistory
- Complete history of all downloads
- Success/failure tracking
- Error messages
- Downloaded file paths

#### SystemSettings
- Global configuration stored in database
- Override config file settings
- Per-show custom settings

### 2. JDownloader Integration (`media_automation/downloader/`)

#### jdownloader_client.py
```python
class JDownloaderClient:
    - connect() # Connect to My.JDownloader
    - add_links(urls, package_name) # Add links to queue
    - get_download_status() # Check download progress
    - get_completed_downloads() # Get finished downloads
    - cleanup_links() # Remove completed from queue
```

Uses `myjdapi` library to communicate with JDownloader instance.

### 3. Episode Monitor (`media_automation/monitor/`)

#### scheduler.py
- APScheduler-based task scheduler
- Periodic checks (every 30 minutes)
- RSS feed monitoring (every 15 minutes)
- Backlog search for missing episodes

#### episode_checker.py
```python
class EpisodeChecker:
    - check_for_new_episodes() # Main check loop
    - process_show(subscription) # Check one show
    - compare_with_library() # What do we have vs want
    - queue_missing_episodes() # Add to download queue
```

#### link_extractor.py
```python
class LinkExtractor:
    - extract_from_oilloco(episode_url) # Get links from oillocotv
    - extract_from_crockdown(file_url) # Get links from crockdown
    - filter_by_quality(links) # Select best quality
    - validate_links(urls) # Check links are valid
```

### 4. File Organization (`media_automation/organizer/`)

#### file_watcher.py
- Monitor download folder for new files
- Detect when downloads complete
- Trigger organization process

#### organizer.py
```python
class FileOrganizer:
    - organize_file(file_path) # Main organization
    - parse_filename() # Extract show/season/episode
    - match_to_episode() # Match to database episode
    - rename_file() # Apply naming template
    - move_to_library() # Move to correct folder
    - update_database() # Mark as downloaded
    - cleanup() # Delete original if configured
```

Naming templates:
- `{show}/Season {season}/{show} - S{season:02}E{episode:02} - {title}.{ext}`
- `{show}/S{season:02}/{show}.S{season:02}E{episode:02}.{quality}.{ext}`

### 5. Web Dashboard (`media_automation/dashboard/`)

#### Flask Routes:

**Main Pages:**
- `/` - Dashboard home (activity, upcoming episodes, recent downloads)
- `/shows` - Show library (add, edit, delete subscriptions)
- `/shows/<id>` - Show details (seasons, episodes, missing)
- `/calendar` - Calendar view of upcoming/recent episodes
- `/queue` - Download queue (wanted, downloading, completed)
- `/history` - Download history
- `/settings` - System settings

**API Endpoints:**
- `/api/shows` - CRUD operations for shows
- `/api/episodes/wanted` - List wanted episodes
- `/api/episodes/queue` - Download queue status
- `/api/downloads/status` - JDownloader status
- `/api/monitoring/trigger` - Manual monitoring trigger
- `/api/organize/scan` - Manual library scan

#### Templates (Jinja2):
- Base layout with navigation
- Show grid/list views
- Calendar interface
- Queue management table
- Settings forms

### 6. Notification System (`media_automation/notifications/`)

#### notifier.py
```python
class Notifier:
    - notify_new_episode(episode) # New episode available
    - notify_download_started(episode)
    - notify_download_completed(episode)
    - notify_download_failed(episode, error)
    - notify_organized(episode, path)
```

Supports:
- Email
- Webhooks (Discord, Slack, custom)
- Web push notifications

### 7. CLI Interface (`media_automation/cli/`)

```bash
# Database
automation-cli db init
automation-cli db stats

# Shows
automation-cli shows add "Lucifer" --quality 1080p --monitor all
automation-cli shows list
automation-cli shows search "breaking bad"
automation-cli shows remove 5

# Monitoring
automation-cli monitor check  # Manual check
automation-cli monitor backlog  # Search for missing episodes
automation-cli monitor status

# Downloads
automation-cli queue list
automation-cli queue retry-failed
automation-cli queue clear-completed

# Organization
automation-cli organize scan
automation-cli organize test-rename "file.mkv"

# Daemon
automation-cli daemon start
automation-cli daemon stop
automation-cli daemon status
```

## Data Flow

```
1. MONITOR LOOP (every 30 min)
   ↓
   Check subscribed shows on oillocotv.biz
   ↓
   Find new episodes
   ↓
   Compare with library (what's missing?)
   ↓
   Add to EpisodeQueue with status="wanted"

2. DOWNLOAD PROCESSOR (every 5 min)
   ↓
   Get episodes with status="wanted" from queue
   ↓
   Extract download links (oilloco → crockdown → direct links)
   ↓
   Send links to JDownloader
   ↓
   Update status="downloading"

3. DOWNLOAD MONITOR (every 5 min)
   ↓
   Check JDownloader for completed downloads
   ↓
   Update status="downloaded"
   ↓
   Trigger file organization

4. FILE ORGANIZER (on download complete)
   ↓
   Watch downloads folder
   ↓
   Parse filename
   ↓
   Match to episode in queue
   ↓
   Rename & move to library
   ↓
   Update media_db library
   ↓
   Mark episode as complete
   ↓
   Send notification
```

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements_automation.txt
```

Dependencies:
- Flask (web dashboard)
- APScheduler (task scheduling)
- myjdapi (JDownloader integration)
- selenium (web scraping)
- watchdog (file monitoring)
- click (CLI)
- All existing media_db requirements

### 2. Configure JDownloader
```bash
# Set environment variables or create .env
JDOWNLOADER_EMAIL=your@email.com
JDOWNLOADER_PASSWORD=yourpassword
JDOWNLOADER_DEVICE_NAME=your-device-name

# Or configure in web UI
```

### 3. Initialize Database
```bash
automation-cli db init
```

### 4. Configure Paths
```bash
# In web UI or CLI
automation-cli settings set download-folder /downloads
automation-cli settings set library-path /media/tv
```

### 5. Add Shows
```bash
# Via CLI
automation-cli shows add "Lucifer"

# Or via web UI at http://localhost:5001
```

### 6. Start the System
```bash
# Start daemon (monitoring + processing)
automation-cli daemon start

# Start web dashboard
automation-cli web start

# Or use systemd service (included)
```

## Configuration Files

### `.env` Example
```bash
# JDownloader
JDOWNLOADER_EMAIL=user@example.com
JDOWNLOADER_PASSWORD=password123
JDOWNLOADER_DEVICE_NAME=docker-jdownloader

# Paths
DOWNLOAD_FOLDER=/downloads
TV_LIBRARY_PATH=/media/tv

# Monitoring
CHECK_INTERVAL_MINUTES=30
RSS_CHECK_INTERVAL_MINUTES=15

# Quality
PREFERRED_QUALITY=1080p

# Notifications
ENABLE_NOTIFICATIONS=True
EMAIL_TO=user@example.com
```

### Docker Compose Integration
```yaml
version: '3.8'
services:
  jdownloader:
    image: jdownloader/jdownloader2:latest
    # ... existing config ...

  media-automation:
    build: .
    volumes:
      - ./config:/config
      - /downloads:/downloads
      - /media:/media
    environment:
      - JDOWNLOADER_EMAIL=${JDOWNLOADER_EMAIL}
      - JDOWNLOADER_PASSWORD=${JDOWNLOADER_PASSWORD}
    ports:
      - "5001:5001"  # Web dashboard
    depends_on:
      - jdownloader
```

## Features

### Like Sonarr:
✅ Show/series management
✅ Episode monitoring
✅ Automatic download queue
✅ Quality profiles
✅ Calendar view
✅ Download history
✅ Missing episodes detection
✅ Backlog search
✅ Notifications
✅ Web UI dashboard
✅ API for integrations
✅ Automatic file renaming/organization

### Unique to this system:
✅ Multi-source support (oillocotv + crockdown)
✅ JDownloader integration (no torrent client needed)
✅ Italian streaming site specific
✅ Link extraction and validation
✅ Integration with existing media_db

## Security Considerations

- Store credentials in environment variables
- Use HTTPS for web dashboard (reverse proxy)
- Implement user authentication for web UI
- Rate limit API endpoints
- Validate all user inputs
- Sanitize file paths
- Use prepared SQL statements

## Future Enhancements

1. **Additional Sources**
   - Add more Italian streaming sites
   - Support for direct download sites

2. **Advanced Features**
   - Custom scripts/webhooks
   - Multi-language support in UI
   - Mobile app
   - Plex/Jellyfin integration
   - Automatic subtitle download
   - Failed download retry with exponential backoff

3. **Performance**
   - Redis for caching
   - Celery for background tasks
   - PostgreSQL for production database

4. **Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Health checks
   - Performance analytics

## Development Timeline

1. **Phase 1**: Core models and database ✓
2. **Phase 2**: JDownloader integration
3. **Phase 3**: Episode monitoring and link extraction
4. **Phase 4**: File organization
5. **Phase 5**: Web dashboard
6. **Phase 6**: CLI interface
7. **Phase 7**: Notifications
8. **Phase 8**: Testing and documentation
9. **Phase 9**: Docker packaging
10. **Phase 10**: Production deployment

---

This system will give you a complete, automated media management solution specifically tailored for Italian streaming sites!
