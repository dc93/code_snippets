# Media Automation System - Quick Start Guide

## ⚠️ IMPORTANT: NO WEB GUI YET

The **MVP (Minimal Viable Product)** I built is **fully functional** but does **NOT** have a web interface yet.

**What you get now:**
- ✅ Full automation via Python scripts
- ✅ JDownloader integration
- ✅ Automatic episode detection
- ✅ File organization

**What's coming later:**
- ⏭️ Web dashboard (like Sonarr/Radarr)
- ⏭️ CLI commands
- ⏭️ Notifications

---

## 🚀 Step-by-Step Setup

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install all requirements
pip install -r requirements_automation.txt
```

This installs:
- JDownloader API client (`myjdapi`)
- All media_db requirements
- Task scheduler
- File monitoring

### 2. Configure Your Settings

Create or edit `.env` file in the project root:

```bash
# JDownloader credentials (REQUIRED)
JDOWNLOADER_EMAIL=your@email.com
JDOWNLOADER_PASSWORD=yourpassword
JDOWNLOADER_DEVICE_NAME=your-device-name

# Paths (REQUIRED)
DOWNLOAD_FOLDER=/downloads
TV_LIBRARY_PATH=/media/tv

# Quality preferences (OPTIONAL)
PREFERRED_QUALITY=1080p

# Monitoring (OPTIONAL)
CHECK_INTERVAL_MINUTES=30
```

**How to find your JDownloader device name:**
1. Go to https://my.jdownloader.org
2. Login with your credentials
3. Your device name is shown in the devices list

### 3. Initialize Databases

```bash
# Initialize media database (stores all shows/episodes)
python media_db_cli.py db init

# Initialize automation database (stores subscriptions/queue)
python -c "from media_automation.models import init_db; init_db()"
```

### 4. Scrape Shows from oillocotv.biz

```bash
# Scrape shows (start with a small number for testing)
python media_db_cli.py scrape all --max-shows 20

# This takes a while! Be patient.
# You can check progress in logs/media_db.log
```

### 5. Edit the Automation Script

Open `run_automation.py` and modify the `setup_example_subscription()` function:

```python
def setup_example_subscription():
    """Add your shows here!"""
    session = get_session()

    # Add your first show
    sub = ShowSubscription(
        title="Lucifer",              # ← CHANGE THIS to your show
        monitored=True,                # Monitor this show
        monitor_status=MonitorStatus.ALL,  # Download all episodes
        quality_profile=QualityProfile.FULL_HD,  # 1080p
        preferred_source='oillocotv',
        search_missing_episodes=True
    )
    session.add(sub)

    # Add more shows
    sub2 = ShowSubscription(
        title="Breaking Bad",          # ← Another show
        monitored=True,
        monitor_status=MonitorStatus.LATEST_SEASON,  # Only latest season
        quality_profile=QualityProfile.HD,  # 720p
        preferred_source='oillocotv'
    )
    session.add(sub2)

    session.commit()
```

**Monitor Options:**
- `MonitorStatus.ALL` - Download all episodes
- `MonitorStatus.LATEST_SEASON` - Only the latest season
- `MonitorStatus.FIRST_SEASON` - Only the first season
- `MonitorStatus.FUTURE` - Only new episodes from now on
- `MonitorStatus.NONE` - Don't monitor (manual only)

**Quality Options:**
- `QualityProfile.UHD` - 2160p (4K)
- `QualityProfile.FULL_HD` - 1080p
- `QualityProfile.HD` - 720p
- `QualityProfile.SD` - 480p
- `QualityProfile.ANY` - Any quality

### 6. Run the Automation!

```bash
python run_automation.py
```

This will:
1. Show your subscribed shows
2. Display current queue status
3. Ask if you want to run the automation cycle

**The automation cycle does:**
1. ✅ Check for new episodes on oillocotv.biz
2. ✅ Extract download links
3. ✅ Send links to your JDownloader
4. ✅ Organize completed downloads into your library

---

## 🔄 Automated Running (Cron)

To run automatically every 30 minutes:

```bash
# Edit crontab
crontab -e

# Add this line (adjust path):
*/30 * * * * cd /path/to/code_snippets && /path/to/venv/bin/python run_automation.py >> logs/automation_cron.log 2>&1
```

Or create a systemd service (see below).

---

## 📊 Checking Status

### View Subscribed Shows

```python
python -c "
from media_automation.models import get_session, ShowSubscription
session = get_session()
for sub in session.query(ShowSubscription).all():
    print(f'{sub.title} - Downloaded: {sub.episodes_downloaded}, Missing: {sub.episodes_missing}')
"
```

### View Download Queue

```python
python -c "
from media_automation.models import get_session, EpisodeQueue
from collections import Counter
session = get_session()
items = session.query(EpisodeQueue).all()
statuses = Counter(i.status.value for i in items)
print('Queue Status:')
for status, count in statuses.items():
    print(f'  {status}: {count}')
"
```

### View Recent Downloads

```python
python -c "
from media_automation.models import get_session, DownloadHistory
session = get_session()
history = session.query(DownloadHistory).order_by(DownloadHistory.timestamp.desc()).limit(10).all()
for h in history:
    status = '✓' if h.success else '✗'
    print(f'{status} {h.show_title} S{h.season_number:02d}E{h.episode_number:02d}')
"
```

---

## 🛠️ Troubleshooting

### JDownloader Not Connecting

Test your connection:

```python
python -c "
from media_automation.downloader import JDownloaderClient
try:
    with JDownloaderClient() as jd:
        print('✓ Connected to JDownloader')
        devices = jd.jd.list_devices()
        print(f'Devices: {[d[\"name\"] for d in devices]}')
except Exception as e:
    print(f'✗ Connection failed: {e}')
"
```

**Common issues:**
- Wrong email/password in `.env`
- Wrong device name
- JDownloader not running
- Not connected to My.JDownloader (enable in JDownloader settings)

### No Episodes Found

Make sure you:
1. Scraped shows: `python media_db_cli.py scrape all --max-shows 20`
2. Used exact show names from the scraper
3. Set `monitored=True` in subscription

Check what shows are available:
```bash
python media_db_cli.py shows list
python media_db_cli.py shows search "lucifer"
```

### Files Not Organizing

Check your paths in `.env`:
```bash
DOWNLOAD_FOLDER=/downloads        # Where JDownloader saves files
TV_LIBRARY_PATH=/media/tv         # Where organized files go
```

Make sure both directories exist and are writable.

---

## 📁 Directory Structure

```
/home/user/code_snippets/
├── media_db/                  # Media database system
├── media_automation/          # Automation system
│   ├── models/               # Database models
│   ├── downloader/           # JDownloader client
│   ├── monitor/              # Episode monitoring
│   └── organizer/            # File organization
├── run_automation.py         # ← Main script to run!
├── .env                      # ← Your configuration
└── instance/
    ├── media_database.db     # Media database
    └── media_automation.db   # Automation database
```

---

## 🎯 Typical Workflow

### First Time Setup
1. Install dependencies
2. Configure `.env` with JDownloader credentials
3. Initialize databases
4. Scrape shows from oillocotv.biz
5. Edit `run_automation.py` to add your shows
6. Run `python run_automation.py`

### Daily Use
- Automation runs automatically (via cron or systemd)
- New episodes are detected
- Links sent to JDownloader
- Files organized automatically
- Check status with `python run_automation.py`

### Adding New Shows
1. Check if show exists: `python media_db_cli.py shows search "show name"`
2. Edit `run_automation.py` and add new subscription
3. Run script to subscribe
4. Next cycle will start monitoring

---

## 🔮 Future Features (Not in MVP)

These will be added in future updates:

### Web Dashboard (Phase 2)
- Sonarr-like web interface
- Visual calendar of episodes
- Click to search/download
- Progress tracking
- Settings management

### CLI Interface (Phase 2)
```bash
automation-cli shows add "Lucifer" --quality 1080p
automation-cli queue list
automation-cli daemon start
```

### Notifications (Phase 3)
- Email alerts
- Discord/Slack webhooks
- Web push notifications

---

## 📖 Documentation Files

- **AUTOMATION_MVP_README.md** - Detailed MVP documentation (this file)
- **AUTOMATION_SYSTEM_PLAN.md** - Complete system architecture
- **MEDIA_DB_README.md** - Media database documentation
- **run_automation.py** - Main automation script (edit this!)

---

## ❓ FAQ

**Q: Do I need the web dashboard to use this?**
A: No! The automation works perfectly via the Python script. The web dashboard is just a nice UI for the future.

**Q: How do I stop monitoring a show?**
A: Edit the database or modify the script to set `monitored=False`

**Q: Can I manually add an episode to download?**
A: Yes! Create an `EpisodeQueue` entry with `manual_grab=True`

**Q: What if my show isn't on oillocotv.biz?**
A: Currently only oillocotv.biz and crockdown.com are supported. More sources can be added.

**Q: Does this download automatically?**
A: YES! It sends links to JDownloader which downloads automatically.

**Q: Where do organized files go?**
A: To `TV_LIBRARY_PATH` in this structure: `Show Name/Season N/Show - S01E02.mkv`

---

## 🆘 Need Help?

1. Check logs: `logs/automation.log`
2. Run with debug: Edit script and add logging
3. Test JDownloader connection
4. Verify show exists in media_db
5. Check file permissions on folders

---

## ✅ You're Ready!

The system is **fully functional** even without a web GUI. Just:
1. Configure `.env`
2. Edit `run_automation.py` with your shows
3. Run it!

The automation will handle everything from detection to organized library files!
