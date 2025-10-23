# Debian 12 Installation Guide for Media Automation System

## System Requirements

- **OS**: Debian 12 (Bookworm)
- **Python**: 3.9+ (Debian 12 comes with Python 3.11)
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 5GB for system + space for your media library
- **Network**: Internet connection for scraping and JDownloader

---

## Step 1: Install System Dependencies

### Update System

```bash
sudo apt update
sudo apt upgrade -y
```

### Install Python and Development Tools

```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    wget \
    curl
```

### Install SQLite (Database)

```bash
sudo apt install -y sqlite3 libsqlite3-dev
```

### Install Chrome/Chromium (for Web Scraping)

**Option A: Chromium (Recommended for Debian)**

```bash
sudo apt install -y chromium chromium-driver
```

**Option B: Google Chrome (Alternative)**

```bash
# Download Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Install Chrome
sudo apt install -y ./google-chrome-stable_current_amd64.deb

# Install ChromeDriver
sudo apt install -y chromium-driver

# Cleanup
rm google-chrome-stable_current_amd64.deb
```

### Install Additional Libraries (for Python packages)

```bash
sudo apt install -y \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    libjpeg-dev
```

---

## Step 2: Verify Installations

### Check Python Version

```bash
python3 --version
# Should show: Python 3.11.x
```

### Check pip

```bash
pip3 --version
# Should show pip version
```

### Check Chrome/Chromium

```bash
chromium --version
# OR
google-chrome --version
```

### Check ChromeDriver

```bash
chromedriver --version
```

---

## Step 3: Setup Project

### Navigate to Project Directory

```bash
cd /home/user/code_snippets
```

### Create Virtual Environment

```bash
python3 -m venv venv
```

### Activate Virtual Environment

```bash
source venv/bin/activate
```

You should see `(venv)` in your prompt.

### Upgrade pip

```bash
pip install --upgrade pip setuptools wheel
```

---

## Step 4: Install Python Dependencies

### Install All Requirements

```bash
pip install -r requirements_automation.txt
```

This installs:
- **Flask** - Web framework for dashboard
- **SQLAlchemy** - Database ORM
- **Click** - CLI interface
- **Selenium** - Web scraping
- **BeautifulSoup4** - HTML parsing
- **myjdapi** - JDownloader API client
- **APScheduler** - Task scheduling
- **watchdog** - File monitoring
- **tabulate** - Pretty tables
- And all dependencies

### Verify Installation

```bash
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import sqlalchemy; print('SQLAlchemy:', sqlalchemy.__version__)"
python -c "import selenium; print('Selenium:', selenium.__version__)"
python -c "import myjdapi; print('myjdapi: OK')"
```

---

## Step 5: Fix Common Debian Issues

### If ChromeDriver Doesn't Work

Sometimes Debian's packaged chromedriver is outdated. Install manually:

```bash
# Get latest ChromeDriver version
CHROME_VERSION=$(chromium --version | grep -oP '\d+\.\d+\.\d+\.\d+')
DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE")

# Download ChromeDriver
wget "https://chromedriver.storage.googleapis.com/${DRIVER_VERSION}/chromedriver_linux64.zip"

# Extract and install
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

# Cleanup
rm chromedriver_linux64.zip
```

### If Selenium Can't Find Chrome

Create symlink:

```bash
sudo ln -s /usr/bin/chromium /usr/bin/google-chrome
```

### If pip Install Fails with "externally-managed-environment"

Debian 12 uses PEP 668. Use venv (you already did) or:

```bash
# If not using venv, use this flag (NOT RECOMMENDED)
pip install --break-system-packages -r requirements_automation.txt
```

But **use venv instead** (recommended and safer)!

---

## Step 6: Configure System

### Create .env File

```bash
cd /home/user/code_snippets
nano .env
```

Add this configuration:

```bash
# JDownloader Configuration (REQUIRED)
JDOWNLOADER_EMAIL=your@email.com
JDOWNLOADER_PASSWORD=yourpassword
JDOWNLOADER_DEVICE_NAME=your-device-name

# Paths (REQUIRED)
DOWNLOAD_FOLDER=/downloads
TV_LIBRARY_PATH=/media/tv

# Quality Settings (OPTIONAL)
PREFERRED_QUALITY=1080p

# Monitoring (OPTIONAL)
CHECK_INTERVAL_MINUTES=30
RSS_CHECK_INTERVAL_MINUTES=15
MAX_EPISODES_PER_CHECK=50

# Dashboard (OPTIONAL)
DASHBOARD_PORT=5001
DASHBOARD_HOST=0.0.0.0
DASHBOARD_DEBUG=False

# Organization (OPTIONAL)
AUTO_ORGANIZE=True
DELETE_AFTER_ORGANIZE=True
MINIMUM_FILE_SIZE_MB=50
```

Save with `CTRL+O`, `ENTER`, `CTRL+X`

### Create Required Directories

```bash
# Create download and media directories
sudo mkdir -p /downloads /media/tv

# Set ownership (replace 'user' with your username)
sudo chown -R $USER:$USER /downloads /media/tv

# Create logs directory
mkdir -p /home/user/code_snippets/logs
```

---

## Step 7: Initialize Databases

### Initialize Media Database

```bash
cd /home/user/code_snippets
source venv/bin/activate
python media_db_cli.py db init
```

### Initialize Automation Database

```bash
python -c "from media_automation.models import init_db; init_db()"
```

You should see success messages.

---

## Step 8: Test the System

### Test Media DB CLI

```bash
python media_db_cli.py --help
```

### Test Dashboard (Quick Test)

```bash
python -c "from media_automation.dashboard.app import create_app; app = create_app(); print('Dashboard OK')"
```

### Test JDownloader Connection

```bash
python -c "
from media_automation.downloader import JDownloaderClient
try:
    with JDownloaderClient() as jd:
        print('✓ JDownloader connected!')
except Exception as e:
    print(f'✗ Error: {e}')
"
```

---

## Step 9: Start Using the System

### Option A: Start Web Dashboard

```bash
python run_dashboard.py
```

**Access at:** http://your-debian-ip:5001

### Option B: Run Automation Script

```bash
python run_automation.py
```

### Option C: Scrape Shows First

```bash
# Scrape shows from oillocotv.biz
python media_db_cli.py scrape all --max-shows 20
```

---

## Troubleshooting for Debian 12

### Problem: "ModuleNotFoundError"

**Solution**: Make sure venv is activated

```bash
source venv/bin/activate
pip install -r requirements_automation.txt
```

### Problem: "chromedriver: not found"

**Solution**: Install chromium-driver

```bash
sudo apt install chromium-driver
```

### Problem: Permission denied on /downloads

**Solution**: Fix ownership

```bash
sudo chown -R $USER:$USER /downloads /media/tv
```

### Problem: Port 5001 already in use

**Solution**: Use different port

```bash
# Edit .env
DASHBOARD_PORT=8080

# Or run with custom port
python -c "from media_automation.dashboard.app import run_dashboard; run_dashboard(port=8080)"
```

### Problem: Can't connect to JDownloader

**Solution**: Check credentials in .env

```bash
# Verify .env has correct credentials
cat .env | grep JDOWNLOADER

# Test connection manually
python -c "
from media_automation.downloader import JDownloaderClient
client = JDownloaderClient()
client.connect()
"
```

---

## Complete Dependency List

### System Packages (apt)

```
python3                 # Python interpreter
python3-pip            # Python package manager
python3-venv           # Virtual environments
python3-dev            # Python development files
build-essential        # Compilation tools
git                    # Version control
wget                   # Download tool
curl                   # Transfer tool
sqlite3                # Database
libsqlite3-dev        # SQLite development files
chromium              # Web browser for scraping
chromium-driver       # ChromeDriver for Selenium
libxml2-dev           # XML library
libxslt1-dev          # XSLT library
libffi-dev            # Foreign function interface
libssl-dev            # SSL library
zlib1g-dev            # Compression library
libjpeg-dev           # JPEG library
```

### Python Packages (pip)

```
Flask>=2.3.0              # Web framework
SQLAlchemy>=2.0.0         # Database ORM
click>=8.1.0              # CLI framework
selenium>=4.15.0          # Web automation
beautifulsoup4>=4.12.0    # HTML parsing
requests>=2.31.0          # HTTP requests
myjdapi>=1.1.6            # JDownloader API
apscheduler>=3.10.0       # Task scheduling
watchdog>=3.0.0           # File monitoring
tabulate>=0.9.0           # Pretty tables
colorama>=0.4.6           # Colored output
python-dotenv>=1.0.0      # Environment variables
lxml>=4.9.0               # XML/HTML parser
```

---

## Quick Installation Script

Save this as `debian_setup.sh`:

```bash
#!/bin/bash
set -e

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y \
    python3 python3-pip python3-venv python3-dev \
    build-essential git wget curl \
    sqlite3 libsqlite3-dev \
    chromium chromium-driver \
    libxml2-dev libxslt1-dev libffi-dev libssl-dev zlib1g-dev libjpeg-dev

echo "Creating directories..."
sudo mkdir -p /downloads /media/tv
sudo chown -R $USER:$USER /downloads /media/tv
mkdir -p logs

echo "Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements_automation.txt

echo "Initializing databases..."
python media_db_cli.py db init
python -c "from media_automation.models import init_db; init_db()"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your JDownloader credentials"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python run_dashboard.py"
echo "4. Open: http://localhost:5001"
```

Make it executable and run:

```bash
chmod +x debian_setup.sh
./debian_setup.sh
```

---

## Memory and Performance Tips for Debian

### If Running on Low RAM (< 2GB)

Add swap space:

```bash
# Create 2GB swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Optimize Selenium for Headless

In `.env`:

```bash
SELENIUM_HEADLESS=True
```

This uses less memory.

---

## Firewall Configuration (if needed)

### Allow Dashboard Port

```bash
# If using UFW firewall
sudo ufw allow 5001/tcp

# Or iptables
sudo iptables -A INPUT -p tcp --dport 5001 -j ACCEPT
```

---

## All Set! 🎉

You're now ready to run the system on Debian 12!

**Start the dashboard:**

```bash
cd /home/user/code_snippets
source venv/bin/activate
python run_dashboard.py
```

**Access:** http://your-ip:5001
