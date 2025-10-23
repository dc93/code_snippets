# Media Automation System - MVP (Minimal Viable Product)

A **Sonarr/Radarr-like automation system** for Italian streaming sites (oillocotv.biz and crockdown.com) with JDownloader integration.

## What This MVP Includes

✅ **Database Models** - Show subscriptions, episode queue, download history
✅ **JDownloader Integration** - Full My.JDownloader API client
✅ **Episode Monitoring** - Automatically detect new episodes
✅ **Link Extraction** - Extract download links from streaming sites
✅ **File Organization** - Automatically organize downloaded files
✅ **Smart Matching** - Match files to episodes in database

## Not Included in MVP (Future Features)

⏭️ CLI Interface (coming next)
⏭️ Web Dashboard (future)
⏭️ Automatic Scheduler/Daemon (future)
⏭️ Notifications (future)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements_automation.txt
```

This includes:
- All media_db requirements (SQLAlchemy, Selenium, etc.)
- `myjdapi` - JDownloader API client
- `apscheduler` - Task scheduling
- `watchdog` - File monitoring

### 2. Configure JDownloader

Set up your My.JDownloader credentials:

```bash
# Add to .env file
JDOWNLOADER_EMAIL=your@email.com
JDOWNLOADER_PASSWORD=yourpassword
JDOWNLOADER_DEVICE_NAME=your-jdownloader-device

# Configure paths
DOWNLOAD_FOLDER=/downloads
TV_LIBRARY_PATH=/media/tv
```

### 3. Initialize Databases

```bash
# Initialize media_db (for show/episode tracking)
python media_db_cli.py db init

# Initialize automation database (for subscriptions/queue)
python -c "from media_automation.models import init_db; init_db()"
```

### 4. Scrape Shows from oillocotv.biz

```bash
# Scrape shows into media_db
python media_db_cli.py scrape all --max-shows 20
```

## How to Use (Python API)

Since the CLI isn't built yet, use the Python API directly:

### 1. Subscribe to a Show

```python
from media_automation.models import init_db, get_session
from media_automation.models import ShowSubscription, MonitorStatus, QualityProfile

# Initialize
init_db()
session = get_session()

# Create subscription
subscription = ShowSubscription(
    title="Lucifer",
    monitored=True,
    monitor_status=MonitorStatus.ALL,
    quality_profile=QualityProfile.FULL_HD,
    preferred_source='oillocotv',
    search_missing_episodes=True
)
session.add(subscription)
session.commit()

print(f"Subscribed to {subscription.title}")
```

### 2. Check for New Episodes

```python
from media_automation.monitor import EpisodeMonitor

# Create monitor
monitor = EpisodeMonitor()

# Check all subscribed shows
result = monitor.check_all_shows()
print(f"Found {result['new_episodes']} new episodes")

# Close resources
monitor.close()
```

### 3. Process Download Queue

```python
from media_automation.monitor import EpisodeMonitor

monitor = EpisodeMonitor()

# Extract links for wanted episodes
result = monitor.process_queue(max_items=10)
print(f"Processed {result['processed']} episodes")
print(f"Success: {result['success']}, Failed: {result['failed']}")

monitor.close()
```

### 4. Send to JDownloader

```python
from media_automation.monitor import EpisodeMonitor

monitor = EpisodeMonitor()

# Send queued episodes to JDownloader
result = monitor.send_to_jdownloader(max_items=5)
print(f"Sent {result['sent']} episodes to JDownloader")
print(f"Success: {result['success']}, Failed: {result['failed']}")

monitor.close()
```

### 5. Organize Downloaded Files

```python
from media_automation.organizer import FileOrganizer

organizer = FileOrganizer()

# Scan downloads folder and organize
result = organizer.scan_downloads()
print(f"Scanned {result['scanned']} files")
print(f"Organized {result['organized']} files")
```

## Complete Automation Loop Example

```python
#!/usr/bin/env python3
"""
Complete automation loop - run this periodically (e.g., every 30 minutes)
"""
from media_automation.models import init_db
from media_automation.monitor import EpisodeMonitor
from media_automation.organizer import FileOrganizer

# Initialize
init_db()

# Create monitor and organizer
monitor = EpisodeMonitor()
organizer = FileOrganizer()

try:
    # Step 1: Check for new episodes
    print("Checking for new episodes...")
    check_result = monitor.check_all_shows()
    print(f"  → Found {check_result['new_episodes']} new episodes")

    # Step 2: Extract download links
    print("\nExtracting download links...")
    process_result = monitor.process_queue(max_items=10)
    print(f"  → Processed {process_result['processed']} episodes")

    # Step 3: Send to JDownloader
    print("\nSending to JDownloader...")
    send_result = monitor.send_to_jdownloader(max_items=5)
    print(f"  → Sent {send_result['sent']} to JDownloader")

    # Step 4: Organize completed downloads
    print("\nOrganizing downloaded files...")
    organize_result = organizer.scan_downloads()
    print(f"  → Organized {organize_result['organized']} files")

    print("\n✓ Automation loop complete")

except Exception as e:
    print(f"✗ Error: {e}")
finally:
    monitor.close()
```

Save this as `automation_loop.py` and run it with cron:

```bash
# Run every 30 minutes
*/30 * * * * cd /path/to/code_snippets && python automation_loop.py >> logs/automation.log 2>&1
```

## Database Schema

### ShowSubscription
- Show metadata and monitoring settings
- Quality preferences
- Library settings

### EpisodeQueue
- Episodes waiting to download
- Current status (wanted, downloading, completed, etc.)
- Download links and JDownloader tracking
- Error handling and retry logic

### DownloadHistory
- Complete history of all downloads
- Success/failure tracking
- File paths and metadata

## System Architecture

```
1. EPISODE MONITOR
   ↓
   Checks subscribed shows on oillocotv.biz (using media_db scraper)
   ↓
   Finds new episodes
   ↓
   Adds to EpisodeQueue (status=wanted)

2. LINK EXTRACTOR
   ↓
   Gets episodes with status=wanted
   ↓
   Extracts download links from episode pages
   ↓
   Updates status=queued

3. JDOWNLOADER CLIENT
   ↓
   Gets episodes with status=queued
   ↓
   Sends links to JDownloader
   ↓
   Updates status=downloading

4. FILE ORGANIZER
   ↓
   Watches download folder
   ↓
   Organizes completed files
   ↓
   Moves to library with proper naming
   ↓
   Updates status=completed
```

## File Naming Convention

Organized files follow this pattern:
```
{Show Title}/Season {N}/{Show Title} - S{N}E{E} - {Quality}.{ext}
```

Example:
```
Lucifer/Season 3/Lucifer - S03E05 - 1080p.mkv
```

## Configuration

All configuration is in `media_automation/config.py` and can be overridden with environment variables:

### Essential Settings

```bash
# JDownloader
JDOWNLOADER_EMAIL=your@email.com
JDOWNLOADER_PASSWORD=password
JDOWNLOADER_DEVICE_NAME=device-name

# Paths
DOWNLOAD_FOLDER=/downloads
TV_LIBRARY_PATH=/media/tv

# Quality
PREFERRED_QUALITY=1080p

# Monitoring
CHECK_INTERVAL_MINUTES=30
MAX_EPISODES_PER_CHECK=50

# Organization
AUTO_ORGANIZE=True
DELETE_AFTER_ORGANIZE=True
MINIMUM_FILE_SIZE_MB=50
```

## Next Steps

After testing the MVP, these features will be added:

1. **CLI Interface** - Easy command-line management
2. **Scheduler Daemon** - Automatic periodic checking
3. **Web Dashboard** - Sonarr-like web UI
4. **Notifications** - Email, Discord, webhooks
5. **Advanced Features** - Custom scripts, webhooks, etc.

## Troubleshooting

### JDownloader Connection Issues

```python
from media_automation.downloader import JDownloaderClient

# Test connection
try:
    with JDownloaderClient() as jd:
        print("✓ Connected to JDownloader")
        devices = jd.jd.list_devices()
        print(f"Devices: {devices}")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### Check Queue Status

```python
from media_automation.models import get_session, EpisodeQueue

session = get_session()

# Count episodes by status
from collections import Counter
statuses = [item.status.value for item in session.query(EpisodeQueue).all()]
print(Counter(statuses))
```

### View Subscriptions

```python
from media_automation.models import get_session, ShowSubscription

session = get_session()

for sub in session.query(ShowSubscription).all():
    print(f"{sub.title} - Monitored: {sub.monitored}")
    print(f"  Downloaded: {sub.episodes_downloaded}")
    print(f"  Missing: {sub.episodes_missing}")
```

## Integration with Existing media_db

This automation system builds on top of the existing `media_db` system:

- **media_db**: Stores all shows/episodes from oillocotv.biz
- **media_automation**: Tracks subscriptions and automates downloads

They share data:
- Subscriptions link to media_db shows
- Queue items link to media_db episodes
- Organized files are added to media_db library

## Support

For issues or questions, check:
- `AUTOMATION_SYSTEM_PLAN.md` - Full system architecture
- `media_db/` - Media database documentation
- Logs in `logs/automation.log`

---

**This MVP provides a fully functional automation core!** You can subscribe to shows, monitor for new episodes, and automatically download and organize them with JDownloader.
