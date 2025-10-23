#!/usr/bin/env python3
"""
Simple automation script - Run this to automate your TV downloads!

This script:
1. Checks for new episodes
2. Extracts download links
3. Sends to JDownloader
4. Organizes completed downloads
"""
import sys
import os
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from media_automation.models import init_db, get_session
from media_automation.models import ShowSubscription, MonitorStatus, QualityProfile
from media_automation.monitor import EpisodeMonitor
from media_automation.organizer import FileOrganizer


def setup_example_subscription():
    """Add an example subscription (modify this!)"""
    session = get_session()

    # Check if we already have subscriptions
    existing = session.query(ShowSubscription).count()
    if existing > 0:
        print(f"✓ Found {existing} existing subscriptions")
        return

    print("No subscriptions found. Adding example subscription...")
    print("EDIT THIS FILE to add your own shows!")

    # Example subscription - CHANGE THIS!
    sub = ShowSubscription(
        title="Lucifer",  # Change to your show
        monitored=True,
        monitor_status=MonitorStatus.ALL,
        quality_profile=QualityProfile.FULL_HD,
        preferred_source='oillocotv',
        search_missing_episodes=True
    )
    session.add(sub)
    session.commit()
    print(f"✓ Subscribed to: {sub.title}")


def list_subscriptions():
    """List all subscribed shows"""
    session = get_session()
    subs = session.query(ShowSubscription).all()

    if not subs:
        print("\n⚠️  No shows subscribed yet!")
        print("Edit run_automation.py and add your shows in setup_example_subscription()")
        return False

    print("\n" + "="*60)
    print("SUBSCRIBED SHOWS")
    print("="*60)
    for sub in subs:
        status = "✓ MONITORING" if sub.monitored else "✗ PAUSED"
        print(f"{status} | {sub.title}")
        print(f"        Downloaded: {sub.episodes_downloaded} | Missing: {sub.episodes_missing}")
        if sub.last_monitored:
            print(f"        Last checked: {sub.last_monitored.strftime('%Y-%m-%d %H:%M')}")
    print("="*60)
    return True


def run_automation():
    """Run the complete automation cycle"""
    print("\n" + "="*60)
    print("STARTING AUTOMATION CYCLE")
    print("="*60)

    monitor = EpisodeMonitor()
    organizer = FileOrganizer()

    try:
        # Step 1: Check for new episodes
        print("\n[1/4] Checking for new episodes...")
        check_result = monitor.check_all_shows()
        print(f"      → Checked {check_result['checked']} shows")
        print(f"      → Found {check_result['new_episodes']} new episodes")

        # Step 2: Extract download links
        print("\n[2/4] Extracting download links...")
        process_result = monitor.process_queue(max_items=10)
        print(f"      → Processed {process_result['processed']} episodes")
        print(f"      → Success: {process_result['success']} | Failed: {process_result['failed']}")

        # Step 3: Send to JDownloader
        print("\n[3/4] Sending to JDownloader...")
        try:
            send_result = monitor.send_to_jdownloader(max_items=5)
            print(f"      → Sent {send_result['sent']} episodes")
            print(f"      → Success: {send_result['success']} | Failed: {send_result['failed']}")
        except Exception as e:
            print(f"      ⚠️  JDownloader error: {e}")
            print(f"      Check your JDOWNLOADER_EMAIL and JDOWNLOADER_PASSWORD in .env")

        # Step 4: Organize completed downloads
        print("\n[4/4] Organizing downloaded files...")
        organize_result = organizer.scan_downloads()
        print(f"      → Scanned {organize_result['scanned']} files")
        print(f"      → Organized {organize_result['organized']} files")

        print("\n" + "="*60)
        print("✓ AUTOMATION CYCLE COMPLETE")
        print("="*60)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        monitor.close()


def show_queue_status():
    """Show what's in the download queue"""
    from media_automation.models import EpisodeQueue
    from collections import Counter

    session = get_session()
    queue_items = session.query(EpisodeQueue).all()

    if not queue_items:
        print("\n📭 Download queue is empty")
        return

    print("\n" + "="*60)
    print("DOWNLOAD QUEUE STATUS")
    print("="*60)

    # Count by status
    statuses = Counter(item.status.value for item in queue_items)
    for status, count in statuses.items():
        print(f"{status.upper()}: {count}")

    # Show recent items
    print("\nRecent episodes:")
    for item in queue_items[-10:]:
        status_icon = {
            'wanted': '⏳',
            'searching': '🔍',
            'queued': '📥',
            'downloading': '⬇️',
            'downloaded': '✓',
            'completed': '✅',
            'failed': '❌'
        }.get(item.status.value, '?')

        print(f"{status_icon} {item.show_title} {item.episode_code} [{item.status.value}]")
    print("="*60)


def main():
    """Main entry point"""
    print("""
╔══════════════════════════════════════════════════════════╗
║       MEDIA AUTOMATION SYSTEM (MVP)                      ║
║       Sonarr/Radarr for Italian Streaming Sites          ║
╚══════════════════════════════════════════════════════════╝
""")

    # Initialize database
    print("Initializing databases...")
    init_db()
    print("✓ Databases ready")

    # Setup example subscription if needed
    setup_example_subscription()

    # List subscriptions
    has_subs = list_subscriptions()

    if not has_subs:
        print("\n💡 Quick Start:")
        print("   1. Edit this file (run_automation.py)")
        print("   2. Modify setup_example_subscription() to add your shows")
        print("   3. Run this script again")
        return

    # Show queue status
    show_queue_status()

    # Ask to run automation
    print("\n" + "="*60)
    response = input("Run automation cycle now? (y/N): ")
    if response.lower() == 'y':
        run_automation()
        show_queue_status()
    else:
        print("Skipped. Run with 'python run_automation.py' to start.")


if __name__ == '__main__':
    main()
