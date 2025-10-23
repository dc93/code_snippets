"""
Flask routes for Media Automation Dashboard
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime, timedelta
from collections import Counter
import json

from ..models.database import get_session
from ..models.show_subscription import ShowSubscription, MonitorStatus, QualityProfile
from ..models.episode_queue import EpisodeQueue, QueueStatus, DownloadHistory
from ..models.settings import SystemSettings
from ..monitor import EpisodeMonitor
from ..organizer import FileOrganizer
from ..downloader import JDownloaderClient

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)


# ============================================================================
# MAIN PAGES
# ============================================================================

@main_bp.route('/')
def index():
    """Dashboard home page."""
    session = get_session()

    # Get statistics
    total_shows = session.query(ShowSubscription).count()
    monitored_shows = session.query(ShowSubscription).filter_by(monitored=True).count()

    total_queue = session.query(EpisodeQueue).count()
    downloading = session.query(EpisodeQueue).filter(
        EpisodeQueue.status.in_([QueueStatus.DOWNLOADING, QueueStatus.QUEUED])
    ).count()

    recent_history = session.query(DownloadHistory).order_by(
        DownloadHistory.timestamp.desc()
    ).limit(10).all()

    # Get recent queue activity
    recent_queue = session.query(EpisodeQueue).order_by(
        EpisodeQueue.last_updated.desc()
    ).limit(10).all()

    # Get upcoming episodes (next 7 days)
    upcoming = session.query(EpisodeQueue).filter(
        EpisodeQueue.status == QueueStatus.WANTED
    ).order_by(EpisodeQueue.added_date.desc()).limit(10).all()

    return render_template(
        'index.html',
        total_shows=total_shows,
        monitored_shows=monitored_shows,
        total_queue=total_queue,
        downloading=downloading,
        recent_history=recent_history,
        recent_queue=recent_queue,
        upcoming=upcoming
    )


@main_bp.route('/shows')
def shows():
    """Shows library page."""
    session = get_session()

    # Get all subscriptions
    subscriptions = session.query(ShowSubscription).order_by(
        ShowSubscription.title
    ).all()

    return render_template('shows.html', subscriptions=subscriptions)


@main_bp.route('/shows/<int:show_id>')
def show_detail(show_id):
    """Show detail page."""
    session = get_session()

    subscription = session.query(ShowSubscription).get(show_id)
    if not subscription:
        flash('Show not found', 'error')
        return redirect(url_for('main.shows'))

    # Get episodes for this show
    episodes = session.query(EpisodeQueue).filter_by(
        subscription_id=show_id
    ).order_by(
        EpisodeQueue.season_number.desc(),
        EpisodeQueue.episode_number.desc()
    ).all()

    # Group by season
    seasons = {}
    for ep in episodes:
        if ep.season_number not in seasons:
            seasons[ep.season_number] = []
        seasons[ep.season_number].append(ep)

    return render_template(
        'show_detail.html',
        subscription=subscription,
        seasons=seasons
    )


@main_bp.route('/shows/add', methods=['GET', 'POST'])
def add_show():
    """Add new show subscription."""
    if request.method == 'POST':
        session = get_session()

        title = request.form.get('title')
        monitor_status = request.form.get('monitor_status', 'all')
        quality = request.form.get('quality', '1080p')

        # Create subscription
        subscription = ShowSubscription(
            title=title,
            monitored=True,
            monitor_status=MonitorStatus[monitor_status.upper()],
            quality_profile=QualityProfile[quality.upper().replace('P', '')],
            preferred_source='oillocotv',
            search_missing_episodes=True
        )

        session.add(subscription)
        session.commit()

        flash(f'Successfully added {title}', 'success')
        return redirect(url_for('main.shows'))

    return render_template('add_show.html')


@main_bp.route('/calendar')
def calendar():
    """Calendar view of episodes."""
    session = get_session()

    # Get episodes from last 7 days and next 14 days
    start_date = datetime.utcnow() - timedelta(days=7)
    end_date = datetime.utcnow() + timedelta(days=14)

    episodes = session.query(EpisodeQueue).filter(
        EpisodeQueue.added_date.between(start_date, end_date)
    ).order_by(EpisodeQueue.added_date).all()

    # Group by date
    calendar_data = {}
    for ep in episodes:
        date_key = ep.added_date.strftime('%Y-%m-%d')
        if date_key not in calendar_data:
            calendar_data[date_key] = []
        calendar_data[date_key].append(ep)

    return render_template('calendar.html', calendar_data=calendar_data)


@main_bp.route('/queue')
def queue():
    """Download queue page."""
    session = get_session()

    # Get filter from query params
    status_filter = request.args.get('status', 'all')

    query = session.query(EpisodeQueue)

    if status_filter != 'all':
        query = query.filter(EpisodeQueue.status == QueueStatus[status_filter.upper()])

    queue_items = query.order_by(
        EpisodeQueue.priority.desc(),
        EpisodeQueue.added_date.desc()
    ).all()

    # Get status counts
    all_items = session.query(EpisodeQueue).all()
    status_counts = Counter(item.status.value for item in all_items)

    return render_template(
        'queue.html',
        queue_items=queue_items,
        status_counts=status_counts,
        current_filter=status_filter
    )


@main_bp.route('/history')
def history():
    """Download history page."""
    session = get_session()

    # Get pagination params
    page = request.args.get('page', 1, type=int)
    per_page = 50

    history_query = session.query(DownloadHistory).order_by(
        DownloadHistory.timestamp.desc()
    )

    total = history_query.count()
    history_items = history_query.offset((page - 1) * per_page).limit(per_page).all()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'history.html',
        history_items=history_items,
        page=page,
        total_pages=total_pages,
        total=total
    )


@main_bp.route('/settings')
def settings():
    """Settings page."""
    session = get_session()

    # Get all settings
    all_settings = session.query(SystemSettings).all()

    # Group by category
    settings_by_category = {}
    for setting in all_settings:
        category = setting.category or 'general'
        if category not in settings_by_category:
            settings_by_category[category] = []
        settings_by_category[category].append(setting)

    return render_template('settings.html', settings=settings_by_category)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@api_bp.route('/shows')
def api_shows():
    """Get all shows."""
    session = get_session()
    shows = session.query(ShowSubscription).all()
    return jsonify([show.to_dict() for show in shows])


@api_bp.route('/shows/<int:show_id>', methods=['GET', 'PUT', 'DELETE'])
def api_show(show_id):
    """Get, update, or delete a show."""
    session = get_session()
    show = session.query(ShowSubscription).get(show_id)

    if not show:
        return jsonify({'error': 'Show not found'}), 404

    if request.method == 'GET':
        return jsonify(show.to_dict())

    elif request.method == 'PUT':
        data = request.get_json()

        if 'monitored' in data:
            show.monitored = data['monitored']
        if 'monitor_status' in data:
            show.monitor_status = MonitorStatus[data['monitor_status'].upper()]
        if 'quality_profile' in data:
            show.quality_profile = QualityProfile[data['quality_profile'].upper()]

        session.commit()
        return jsonify(show.to_dict())

    elif request.method == 'DELETE':
        session.delete(show)
        session.commit()
        return jsonify({'success': True})


@api_bp.route('/queue')
def api_queue():
    """Get download queue."""
    session = get_session()
    items = session.query(EpisodeQueue).all()
    return jsonify([item.to_dict() for item in items])


@api_bp.route('/queue/<int:item_id>/retry', methods=['POST'])
def api_retry_download(item_id):
    """Retry a failed download."""
    session = get_session()
    item = session.query(EpisodeQueue).get(item_id)

    if not item:
        return jsonify({'error': 'Item not found'}), 404

    item.status = QueueStatus.WANTED
    item.retry_count += 1
    item.last_error = None
    session.commit()

    return jsonify({'success': True, 'item': item.to_dict()})


@api_bp.route('/monitor/check', methods=['POST'])
def api_trigger_check():
    """Manually trigger episode check."""
    try:
        monitor = EpisodeMonitor()
        result = monitor.check_all_shows()
        monitor.close()

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/monitor/process', methods=['POST'])
def api_process_queue():
    """Process the download queue."""
    try:
        monitor = EpisodeMonitor()
        result = monitor.process_queue(max_items=10)
        monitor.close()

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/jdownloader/send', methods=['POST'])
def api_send_to_jdownloader():
    """Send queued items to JDownloader."""
    try:
        monitor = EpisodeMonitor()
        result = monitor.send_to_jdownloader(max_items=5)
        monitor.close()

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/organize/scan', methods=['POST'])
def api_organize_scan():
    """Scan and organize downloads."""
    try:
        organizer = FileOrganizer()
        result = organizer.scan_downloads()

        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/stats')
def api_stats():
    """Get dashboard statistics."""
    session = get_session()

    stats = {
        'shows': {
            'total': session.query(ShowSubscription).count(),
            'monitored': session.query(ShowSubscription).filter_by(monitored=True).count()
        },
        'queue': {
            'total': session.query(EpisodeQueue).count(),
            'wanted': session.query(EpisodeQueue).filter_by(status=QueueStatus.WANTED).count(),
            'downloading': session.query(EpisodeQueue).filter_by(status=QueueStatus.DOWNLOADING).count(),
            'completed': session.query(EpisodeQueue).filter_by(status=QueueStatus.COMPLETED).count(),
            'failed': session.query(EpisodeQueue).filter_by(status=QueueStatus.FAILED).count()
        },
        'history': {
            'total': session.query(DownloadHistory).count(),
            'successful': session.query(DownloadHistory).filter_by(success=True).count(),
            'failed': session.query(DownloadHistory).filter_by(success=False).count()
        }
    }

    return jsonify(stats)


@api_bp.route('/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update settings."""
    session = get_session()

    if request.method == 'GET':
        settings = session.query(SystemSettings).all()
        return jsonify([s.to_dict() for s in settings])

    elif request.method == 'POST':
        data = request.get_json()

        for key, value in data.items():
            SystemSettings.set_setting(session, key, value)

        return jsonify({'success': True})
