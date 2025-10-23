# Complete Media Automation System - Final Guide

## 🎉 CONGRATULATIONS! You Now Have a Complete System!

I've built you a **full Sonarr/Radarr-like automation system** with:

✅ Media database for tracking shows/episodes
✅ Automation core with JDownloader integration
✅ **Web dashboard** with beautiful UI
✅ Automatic episode monitoring
✅ Automatic link extraction
✅ Automatic file organization
✅ Complete REST API

---

## 📦 What You Got

### 1. Media Database System (`media_db/`)

Tracks all shows and episodes from oillocotv.biz:

- **Database models** for shows, seasons, episodes
- **Web scraper** for oillocotv.biz (Selenium-based)
- **File parser** for extracting metadata from filenames
- **Smart matcher** for linking files to episodes
- **CLI tool** (`media_db_cli.py`) for management

### 2. Automation Core (`media_automation/`)

The engine that makes everything automatic:

- **Database models** for subscriptions, queue, history
- **JDownloader client** for My.JDownloader API
- **Episode monitor** that checks for new episodes
- **Link extractor** for streaming sites
- **File organizer** that moves/renames downloads

### 3. Web Dashboard (`media_automation/dashboard/`)

Beautiful web interface:

- **Dashboard home** - Activity and stats
- **Shows management** - Add/edit subscriptions
- **Calendar** - Timeline view of episodes
- **Queue** - Download management
- **History** - Complete audit log
- **Settings** - Configuration
- **REST API** - JSON endpoints for everything

---

## 🚀 Getting Started

### Step 1: Install Everything

```bash
# Activate virtual environment
source venv/bin/activate

# Install all dependencies
pip install -r requirements_automation.txt
```

### Step 2: Configure

Create `.env` file:

```bash
# JDownloader (REQUIRED)
JDOWNLOADER_EMAIL=your@email.com
JDOWNLOADER_PASSWORD=yourpassword
JDOWNLOADER_DEVICE_NAME=your-device-name

# Paths (REQUIRED)
DOWNLOAD_FOLDER=/downloads
TV_LIBRARY_PATH=/media/tv

# Optional
PREFERRED_QUALITY=1080p
CHECK_INTERVAL_MINUTES=30
```

### Step 3: Initialize Databases

```bash
# Media database (stores shows/episodes from website)
python media_db_cli.py db init

# Automation database (stores subscriptions/queue)
python -c "from media_automation.models import init_db; init_db()"
```

### Step 4: Scrape Shows

```bash
# Scrape shows from oillocotv.biz
python media_db_cli.py scrape all --max-shows 50

# This takes a while! Go get coffee ☕
```

### Step 5: Start the Web Dashboard

```bash
python run_dashboard.py
```

**Open browser:** http://localhost:5001

---

## 🎯 Using the System

### Via Web Dashboard (Recommended!)

1. **Open dashboard:** http://localhost:5001
2. **Add shows:** Click "Shows" → "Add Show"
3. **Configure:** Choose quality and monitoring options
4. **Click "Run Automation"** on homepage
5. **Watch it work!** Monitor queue and history

### Via Python Script

If you prefer automation without clicking:

```bash
python run_automation.py
```

This runs the full cycle automatically.

### Via Cron (For Automation)

Add to crontab for automatic checking:

```bash
# Every 30 minutes
*/30 * * * * cd /path/to/code_snippets && python run_automation.py >> logs/cron.log 2>&1
```

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  WEB DASHBOARD (NEW!)                    │
│              http://localhost:5001                       │
│  Dashboard | Shows | Calendar | Queue | History         │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  AUTOMATION CORE                         │
│  • Episode Monitor (checks for new episodes)             │
│  • Link Extractor (gets download links)                 │
│  • JDownloader Client (sends to JD)                      │
│  • File Organizer (moves to library)                    │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   DATA LAYER                             │
│  • Media Database (shows/episodes from oillocotv.biz)   │
│  • Automation Database (subscriptions/queue/history)    │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│               EXTERNAL SERVICES                          │
│  • oillocotv.biz (episode source)                       │
│  • JDownloader (downloads)                               │
│  • Your Media Library (organized files)                 │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Complete File Structure

```
code_snippets/
├── media_db/                      # Media database system
│   ├── models/                    # Database models
│   ├── scrapers/                  # Web scrapers
│   ├── utils/                     # Utilities
│   └── cli/                       # CLI commands
│
├── media_automation/              # Automation system
│   ├── models/                    # Database models
│   ├── downloader/                # JDownloader client
│   ├── monitor/                   # Episode monitoring
│   ├── organizer/                 # File organization
│   └── dashboard/                 # ⭐ WEB DASHBOARD
│       ├── templates/             # HTML templates
│       ├── static/                # CSS/JS
│       ├── app.py                 # Flask app
│       └── routes.py              # Routes/API
│
├── instance/                      # Databases
│   ├── media_database.db          # Shows/episodes
│   └── media_automation.db        # Subscriptions/queue
│
├── logs/                          # Log files
│
├── run_dashboard.py               # ⭐ START WEB DASHBOARD
├── run_automation.py              # Run automation loop
├── media_db_cli.py                # Media DB CLI
│
└── Documentation:
    ├── WEB_DASHBOARD_README.md    # ⭐ Dashboard guide
    ├── AUTOMATION_MVP_README.md   # Automation guide
    ├── MEDIA_DB_README.md         # Media DB guide
    ├── QUICKSTART.md              # Quick start
    └── COMPLETE_SYSTEM_GUIDE.md   # This file
```

---

## 🎮 Usage Examples

### Example 1: Subscribe to a Show

**Via Web Dashboard:**
1. Go to "Shows" → "Add Show"
2. Enter: "Lucifer"
3. Quality: 1080p
4. Monitor: All Episodes
5. Click "Add Show"

**Via Python:**
```python
from media_automation.models import *
session = get_session()

sub = ShowSubscription(
    title="Lucifer",
    monitored=True,
    monitor_status=MonitorStatus.ALL,
    quality_profile=QualityProfile.FULL_HD
)
session.add(sub)
session.commit()
```

### Example 2: Run Automation

**Via Web Dashboard:**
- Click "Run Automation" button on homepage

**Via Script:**
```bash
python run_automation.py
```

**Via API:**
```bash
curl -X POST http://localhost:5001/api/monitor/check
curl -X POST http://localhost:5001/api/monitor/process
curl -X POST http://localhost:5001/api/jdownloader/send
curl -X POST http://localhost:5001/api/organize/scan
```

### Example 3: Check Status

**Via Web Dashboard:**
- Open Queue page
- See all statuses with filters

**Via API:**
```bash
curl http://localhost:5001/api/stats
```

---

## 🔄 Complete Workflow

### Automatic Workflow (Set and Forget)

1. **Setup** (one time):
   - Install dependencies
   - Configure `.env`
   - Initialize databases
   - Scrape shows
   - Add subscriptions via web dashboard

2. **Add to cron**:
   ```bash
   */30 * * * * cd /path/to/code_snippets && python run_automation.py
   ```

3. **That's it!** The system will:
   - Check for new episodes every 30 minutes
   - Extract download links
   - Send to JDownloader
   - Organize downloaded files
   - Update database

### Manual Workflow (On-Demand)

1. **Start web dashboard:**
   ```bash
   python run_dashboard.py
   ```

2. **Open browser:** http://localhost:5001

3. **Add shows** as you want them

4. **Click "Run Automation"** when you want to check

5. **Monitor progress** in Queue page

---

## 🛠️ Troubleshooting

### Web Dashboard Won't Start

```bash
# Check Python
python --version  # Need 3.8+

# Reinstall requirements
pip install -r requirements_automation.txt

# Check port
lsof -i :5001  # Should be free
```

### JDownloader Not Connecting

```bash
# Test connection
python -c "
from media_automation.downloader import JDownloaderClient
with JDownloaderClient() as jd:
    print('Connected!')
"
```

Check `.env` has correct credentials!

### No Episodes Found

```bash
# Check media database
python media_db_cli.py db stats

# If empty, scrape first
python media_db_cli.py scrape all --max-shows 20
```

### Files Not Organizing

Check paths in `.env`:
- `DOWNLOAD_FOLDER` - Where JDownloader saves
- `TV_LIBRARY_PATH` - Where you want organized files

Make sure both directories exist and are writable!

---

## 📚 Documentation Index

- **WEB_DASHBOARD_README.md** - Complete web dashboard guide
- **AUTOMATION_MVP_README.md** - Automation system details
- **MEDIA_DB_README.md** - Media database system
- **AUTOMATION_SYSTEM_PLAN.md** - Full architecture
- **QUICKSTART.md** - Quick start guide
- **COMPLETE_SYSTEM_GUIDE.md** - This file

---

## 🎯 What's Next?

The system is **complete and functional!** Future enhancements could include:

- 🔐 User authentication
- 📱 Mobile app
- 🔔 Push notifications
- 📊 Advanced analytics
- 🎨 Dark mode
- 🌐 Multi-language support
- 📥 Subtitle downloads
- 🔗 Plex/Jellyfin integration

But right now, you have a **fully working Sonarr/Radarr clone** for Italian streaming sites!

---

## ✅ Summary

You now have:

✅ **Web Dashboard** - Beautiful UI at http://localhost:5001
✅ **Full Automation** - Monitors, downloads, organizes
✅ **JDownloader Integration** - Works with your Docker instance
✅ **Complete API** - JSON endpoints for everything
✅ **Two Databases** - Shows and automation tracking
✅ **File Organization** - Automatic Plex-style naming
✅ **Progress Tracking** - See what you have vs. what you want

**Start the dashboard and enjoy your automation system!**

```bash
python run_dashboard.py
```

Then open: **http://localhost:5001**

🎉 **DONE!**
