#!/usr/bin/env python3
"""
Launch the Media Automation Web Dashboard

This starts the Flask web interface on http://localhost:5001
"""
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from media_automation.dashboard.app import run_dashboard
from media_automation.models import init_db

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════╗
║      MEDIA AUTOMATION WEB DASHBOARD                      ║
╚══════════════════════════════════════════════════════════╝
""")

    # Initialize database
    print("Initializing databases...")
    init_db()
    print("✓ Databases ready\n")

    print("Starting web dashboard...")
    print("Dashboard will be available at: http://localhost:5001")
    print("\nPress CTRL+C to stop\n")
    print("="*60)

    try:
        run_dashboard()
    except KeyboardInterrupt:
        print("\n\nShutting down dashboard...")
        print("Goodbye!")
