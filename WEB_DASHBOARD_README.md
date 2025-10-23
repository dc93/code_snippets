# Media Automation Web Dashboard

🎉 **The web dashboard is now available!** You have a Sonarr/Radarr-like interface for your automation system.

## Features

✅ **Dashboard Home** - Activity feed, stats, recent downloads
✅ **Shows Management** - Add, view, and manage subscriptions
✅ **Calendar View** - See upcoming and recent episodes
✅ **Download Queue** - Monitor and manage downloads
✅ **History** - Complete download history with pagination
✅ **Settings** - System configuration and manual actions
✅ **REST API** - JSON API for integrations
✅ **Responsive Design** - Works on desktop and mobile

## Quick Start

### 1. Install Dependencies (if not already done)

```bash
source venv/bin/activate
pip install -r requirements_automation.txt
```

The web dashboard requires Flask, which is already included in the automation requirements.

### 2. Initialize Databases

```bash
# Initialize both databases if not already done
python media_db_cli.py db init
python -c "from media_automation.models import init_db; init_db()"
```

### 3. Start the Web Dashboard

```bash
python run_dashboard.py
```

The dashboard will start on **http://localhost:5001**

### 4. Open in Browser

Navigate to: **http://localhost:5001**

## Dashboard Pages

### 🏠 Dashboard (/)
- **Statistics Cards** - Shows, queue, downloads
- **Recent Activity** - Latest queue updates
- **Wanted Episodes** - Episodes ready to download
- **Recent Downloads** - Download history
- **Run Automation** - Button to trigger full cycle

### 📺 Shows (/shows)
- **Show Library** - Grid view of all subscribed shows
- **Progress Tracking** - See completion percentage
- **Quick Actions** - Pause/resume monitoring
- **Add Show** - Subscribe to new shows

### 🔍 Show Detail (/shows/<id>)
- **Show Information** - Title, year, quality settings
- **Statistics** - Total, downloaded, missing counts
- **Season Lists** - Episodes grouped by season
- **Episode Status** - Track each episode's download status

### ➕ Add Show (/shows/add)
- **Simple Form** - Title, quality, monitor settings
- **Monitor Options** - All episodes, latest season, etc.
- **Quality Profiles** - 4K, 1080p, 720p, SD

### 📅 Calendar (/calendar)
- **Timeline View** - Last 7 days + next 14 days
- **Episode Cards** - Grouped by date
- **Status Indicators** - See what's wanted, downloading, completed

### ⬇️ Queue (/queue)
- **Status Filters** - View by status (wanted, downloading, etc.)
- **Progress Bars** - Live download progress
- **Manual Actions** - Retry failed downloads
- **Bulk Operations** - Process queue, send to JDownloader

### 📜 History (/history)
- **Complete Log** - All downloads with success/failure
- **Details** - Show, episode, quality, size, date
- **Pagination** - Navigate through history
- **Filters** - Coming soon

### ⚙️ Settings (/settings)
- **Configuration** - View current settings
- **JDownloader Test** - Test connection
- **Manual Actions** - Organize files, clear queue

## API Endpoints

The dashboard includes a REST API for automation and integrations:

### Shows API

```bash
GET  /api/shows              # List all shows
GET  /api/shows/<id>         # Get show details
PUT  /api/shows/<id>         # Update show settings
DELETE /api/shows/<id>       # Delete show
```

### Queue API

```bash
GET  /api/queue              # Get download queue
POST /api/queue/<id>/retry   # Retry failed download
```

### Monitoring API

```bash
POST /api/monitor/check      # Trigger episode check
POST /api/monitor/process    # Process queue (extract links)
POST /api/jdownloader/send   # Send to JDownloader
POST /api/organize/scan      # Organize downloads
```

### Stats API

```bash
GET  /api/stats              # Get system statistics
```

### Example API Usage

```bash
# Check for new episodes
curl -X POST http://localhost:5001/api/monitor/check

# Get all shows
curl http://localhost:5001/api/shows

# Get statistics
curl http://localhost:5001/api/stats

# Retry a failed download
curl -X POST http://localhost:5001/api/queue/5/retry
```

## Using the Dashboard

### Adding Your First Show

1. Go to **Shows** page
2. Click **"Add Show"**
3. Enter the show title (exact match from oillocotv.biz)
4. Select monitoring options:
   - **All Episodes** - Download everything
   - **Future Only** - New episodes from now on
   - **Latest Season** - Only current season
   - **First Season** - Only season 1
5. Choose quality (1080p recommended)
6. Click **"Add Show"**

### Running Automation

#### From Dashboard Homepage

1. Click the **"Run Automation"** button
2. Confirms before running
3. Executes full cycle:
   - Check for new episodes
   - Extract download links
   - Send to JDownloader
   - Organize completed downloads

#### From Queue Page

- **Process Queue** - Extract links for wanted episodes
- **Send to JDownloader** - Send queued items to JD

### Monitoring Downloads

1. Go to **Queue** page
2. Use status filters to view:
   - **Wanted** - Detected but not yet processed
   - **Queued** - Links extracted, ready for JD
   - **Downloading** - Currently downloading in JD
   - **Completed** - Fully processed and organized
   - **Failed** - Errors occurred
3. Click **Retry** on failed items

### Checking History

1. Go to **History** page
2. View all past downloads
3. See success/failure status
4. Check file sizes and dates
5. Use pagination to browse

## Configuration

### Default Settings

The dashboard runs with these defaults:

```python
HOST = '0.0.0.0'  # Accessible from network
PORT = 5001       # Dashboard port
DEBUG = False     # Production mode
```

### Environment Variables

Override defaults in `.env`:

```bash
DASHBOARD_PORT=5001
DASHBOARD_HOST=0.0.0.0
DASHBOARD_DEBUG=False
```

### Run on Different Port

```bash
python -c "from media_automation.dashboard.app import run_dashboard; run_dashboard(port=8080)"
```

## Running in Production

### With Gunicorn (Recommended)

```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:5001 "media_automation.dashboard.app:create_app()"
```

### As Systemd Service

Create `/etc/systemd/system/media-automation-dashboard.service`:

```ini
[Unit]
Description=Media Automation Web Dashboard
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/code_snippets
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5001 "media_automation.dashboard.app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable media-automation-dashboard
sudo systemctl start media-automation-dashboard
```

### With Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements_automation.txt
RUN pip install gunicorn

EXPOSE 5001

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "media_automation.dashboard.app:create_app()"]
```

## Troubleshooting

### Dashboard Won't Start

**Check Python version:**
```bash
python --version  # Should be 3.8+
```

**Check dependencies:**
```bash
pip install -r requirements_automation.txt
```

**Check for port conflicts:**
```bash
lsof -i :5001
```

### Can't Access from Other Devices

**Make sure it's binding to 0.0.0.0:**
```python
# In config.py
DASHBOARD_HOST = '0.0.0.0'  # Not 127.0.0.1
```

**Check firewall:**
```bash
sudo ufw allow 5001
```

### API Requests Failing

**Check if automation database is initialized:**
```bash
python -c "from media_automation.models import init_db; init_db()"
```

**Check logs:**
```bash
tail -f logs/automation.log
```

### Shows Not Appearing

**Make sure media_db is populated:**
```bash
python media_db_cli.py db stats
python media_db_cli.py shows list
```

**If empty, scrape first:**
```bash
python media_db_cli.py scrape all --max-shows 20
```

## Features Coming Soon

These features are planned for future releases:

- 🔐 **User Authentication** - Login system
- 📱 **Mobile App** - Native iOS/Android apps
- 🔔 **Push Notifications** - Real-time alerts
- 📊 **Advanced Analytics** - Charts and graphs
- 🎨 **Themes** - Dark mode, custom themes
- 🔍 **Advanced Search** - Filter and search everywhere
- 🔗 **Plex/Jellyfin Integration** - Automatic library updates
- 📥 **Subtitle Downloads** - Automatic subtitle fetching
- 🎯 **Custom Profiles** - Per-show download settings
- 🌐 **Multi-language** - UI translations

## Tips & Tricks

### Keyboard Shortcuts

These will be added in a future update:
- `R` - Refresh page
- `A` - Add show
- `Q` - Go to queue
- `H` - Go to home

### Auto-Refresh

The dashboard auto-refreshes stats every 30 seconds when on the homepage.

### Bookmarks

Useful bookmarks to add:
- `http://localhost:5001/` - Dashboard home
- `http://localhost:5001/shows` - Show library
- `http://localhost:5001/queue?status=downloading` - Active downloads

### Browser Extensions

Compatible with:
- Ad blockers (no ads anyway!)
- Dark mode extensions
- Accessibility tools

## Security Notes

### Development Mode

The dashboard runs in development mode by default. For production:

1. Set `DEBUG=False` in config
2. Use a reverse proxy (nginx)
3. Enable HTTPS
4. Add authentication
5. Use strong `SECRET_KEY`

### Authentication

**Currently no authentication!** Anyone with network access can use the dashboard.

For production, add authentication:
1. Flask-Login for sessions
2. Basic HTTP auth with nginx
3. OAuth integration
4. API keys for API access

### Network Security

If exposing to internet:
- Use HTTPS (Let's Encrypt)
- Use strong passwords
- Enable firewall rules
- Consider VPN access

## Support

### Logs

Check logs for errors:
```bash
# Application logs
tail -f logs/automation.log

# Flask debug logs (if DEBUG=True)
# Printed to console
```

### Database

View database directly:
```bash
sqlite3 instance/media_automation.db

.tables
SELECT * FROM show_subscriptions;
SELECT * FROM episode_queue;
```

### Reset Dashboard

If things go wrong:
```bash
# Backup first!
cp instance/media_automation.db instance/media_automation.db.backup

# Reset automation database
rm instance/media_automation.db
python -c "from media_automation.models import init_db; init_db()"
```

---

**Enjoy your Sonarr/Radarr-like automation system with a beautiful web interface!** 🎉
