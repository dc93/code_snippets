#!/bin/bash
# Quick setup script for Media Database System

echo "==================================="
echo "Media Database System Setup"
echo "==================================="
echo

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  No virtual environment detected!"
    echo "Consider activating your virtual environment first:"
    echo "  source venv/bin/activate"
    echo
    read -p "Continue anyway? (y/N): " continue
    if [ "$continue" != "y" ] && [ "$continue" != "Y" ]; then
        exit 1
    fi
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements_media_db.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo

# Check for Chrome/Chromium
echo "🔍 Checking for Chrome/Chromium..."
if command -v chromium-browser &> /dev/null; then
    echo "✓ Chromium found: $(chromium-browser --version)"
elif command -v google-chrome &> /dev/null; then
    echo "✓ Chrome found: $(google-chrome --version)"
else
    echo "⚠️  Chrome/Chromium not found!"
    echo "For web scraping, you need to install Chrome or Chromium:"
    echo "  Ubuntu/Debian: sudo apt-get install chromium-browser chromium-chromedriver"
    echo "  Manual: Download Chrome from https://www.google.com/chrome/"
    echo
fi

# Initialize database
echo
echo "🗄️  Initializing database..."
python media_db_cli.py db init

if [ $? -ne 0 ]; then
    echo "❌ Failed to initialize database"
    exit 1
fi

echo
echo "==================================="
echo "✅ Setup Complete!"
echo "==================================="
echo
echo "Next steps:"
echo
echo "1. Scrape shows from oillocotv.biz:"
echo "   python media_db_cli.py scrape all --max-shows 10"
echo
echo "2. Add your library path:"
echo "   python media_db_cli.py library add /path/to/your/shows --name \"My Shows\""
echo
echo "3. Scan your library:"
echo "   python media_db_cli.py library scan"
echo
echo "4. Match files to episodes:"
echo "   python media_db_cli.py library match"
echo
echo "5. Check results:"
echo "   python media_db_cli.py db stats"
echo
echo "For more info, see MEDIA_DB_README.md"
echo
