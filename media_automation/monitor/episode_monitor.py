"""
Episode monitoring system - checks for new episodes
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json

from ..models.database import get_session, session_scope
from ..models.show_subscription import ShowSubscription, MonitorStatus
from ..models.episode_queue import EpisodeQueue, QueueStatus
from .link_extractor import LinkExtractor

# Import from media_db
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from media_db.models import get_session as get_media_db_session, Show, Episode, Season
from media_db.scrapers import OillocoScraper

logger = logging.getLogger(__name__)


class EpisodeMonitor:
    """
    Monitors subscribed shows for new episodes and adds them to download queue.
    """

    def __init__(self):
        """Initialize episode monitor."""
        self.session = get_session()
        self.media_db_session = get_media_db_session()
        self.link_extractor = LinkExtractor()

    def check_all_shows(self) -> Dict:
        """
        Check all monitored shows for new episodes.

        Returns:
            Dictionary with check results
        """
        logger.info("Starting episode check for all monitored shows")

        subscriptions = self.session.query(ShowSubscription).filter(
            ShowSubscription.monitored == True
        ).all()

        if not subscriptions:
            logger.info("No shows are being monitored")
            return {
                'checked': 0,
                'new_episodes': 0,
                'shows_processed': []
            }

        total_new = 0
        shows_processed = []

        for subscription in subscriptions:
            try:
                result = self.check_show(subscription)
                total_new += result['new_episodes']
                shows_processed.append({
                    'show': subscription.title,
                    'new_episodes': result['new_episodes']
                })
            except Exception as e:
                logger.error(f"Error checking {subscription.title}: {e}")
                shows_processed.append({
                    'show': subscription.title,
                    'error': str(e)
                })

        logger.info(f"Check complete: {len(subscriptions)} shows, {total_new} new episodes")

        return {
            'checked': len(subscriptions),
            'new_episodes': total_new,
            'shows_processed': shows_processed
        }

    def check_show(self, subscription: ShowSubscription) -> Dict:
        """
        Check a single show for new episodes.

        Args:
            subscription: Show subscription to check

        Returns:
            Dictionary with check results
        """
        logger.info(f"Checking show: {subscription.title}")

        # Get show from media_db
        media_db_show = None
        if subscription.media_db_show_id:
            media_db_show = self.media_db_session.query(Show).get(subscription.media_db_show_id)

        if not media_db_show:
            # Try to find show by title
            media_db_show = self.media_db_session.query(Show).filter(
                Show.title.ilike(f'%{subscription.title}%')
            ).first()

            if media_db_show:
                subscription.media_db_show_id = media_db_show.id
                self.session.commit()

        if not media_db_show:
            logger.warning(f"Show not found in media_db: {subscription.title}")
            return {'new_episodes': 0, 'error': 'Show not found in media_db'}

        # Get episodes from media_db
        episodes = self._get_monitored_episodes(media_db_show, subscription)

        # Compare with what we already have queued/downloaded
        new_episodes = self._find_missing_episodes(episodes, subscription)

        # Add to queue
        added_count = 0
        for episode_info in new_episodes:
            if self._add_to_queue(episode_info, subscription):
                added_count += 1

        # Update subscription stats
        subscription.last_monitored = datetime.utcnow()
        if added_count > 0:
            subscription.last_episode_added = datetime.utcnow()
        self.session.commit()

        logger.info(f"{subscription.title}: Found {added_count} new episodes")

        return {
            'new_episodes': added_count,
            'total_checked': len(episodes)
        }

    def _get_monitored_episodes(
        self,
        show: Show,
        subscription: ShowSubscription
    ) -> List[Episode]:
        """
        Get episodes that should be monitored based on subscription settings.

        Args:
            show: Media DB show
            subscription: Show subscription

        Returns:
            List of episodes to monitor
        """
        all_episodes = []

        for season in show.seasons:
            # Check if this season should be monitored
            if not self._should_monitor_season(season, subscription):
                continue

            for episode in season.episodes:
                all_episodes.append(episode)

        return all_episodes

    def _should_monitor_season(self, season: Season, subscription: ShowSubscription) -> bool:
        """
        Check if a season should be monitored based on subscription settings.

        Args:
            season: Season to check
            subscription: Show subscription

        Returns:
            True if season should be monitored
        """
        if subscription.monitor_status == MonitorStatus.ALL:
            return True
        elif subscription.monitor_status == MonitorStatus.NONE:
            return False
        elif subscription.monitor_status == MonitorStatus.FIRST_SEASON:
            return season.season_number == 1
        elif subscription.monitor_status == MonitorStatus.LATEST_SEASON:
            # Get max season number for the show
            max_season = max((s.season_number for s in season.show.seasons), default=0)
            return season.season_number == max_season
        elif subscription.monitor_status == MonitorStatus.FUTURE:
            # Only monitor if season has recent air date
            if season.air_date:
                return season.air_date >= datetime.utcnow() - timedelta(days=30)
            return True  # If no air date, include it

        return True

    def _find_missing_episodes(
        self,
        episodes: List[Episode],
        subscription: ShowSubscription
    ) -> List[Dict]:
        """
        Find episodes that are not yet queued or downloaded.

        Args:
            episodes: List of episodes from media_db
            subscription: Show subscription

        Returns:
            List of episode info dictionaries for missing episodes
        """
        missing = []

        for episode in episodes:
            # Check if already in queue
            existing = self.session.query(EpisodeQueue).filter(
                EpisodeQueue.subscription_id == subscription.id,
                EpisodeQueue.season_number == episode.season.season_number,
                EpisodeQueue.episode_number == episode.episode_number
            ).first()

            if existing:
                # Skip if already queued (unless failed and can retry)
                if existing.status != QueueStatus.FAILED or not existing.can_retry:
                    continue

            # This episode is missing
            missing.append({
                'media_db_episode_id': episode.id,
                'show_title': episode.season.show.title,
                'season_number': episode.season.season_number,
                'episode_number': episode.episode_number,
                'episode_title': episode.title_italian or episode.title,
                'source_url': episode.page_url,
            })

        return missing

    def _add_to_queue(self, episode_info: Dict, subscription: ShowSubscription) -> bool:
        """
        Add episode to download queue.

        Args:
            episode_info: Episode information dictionary
            subscription: Show subscription

        Returns:
            True if added successfully
        """
        try:
            # Create queue entry
            queue_item = EpisodeQueue(
                subscription_id=subscription.id,
                media_db_episode_id=episode_info.get('media_db_episode_id'),
                show_title=episode_info['show_title'],
                season_number=episode_info['season_number'],
                episode_number=episode_info['episode_number'],
                episode_title=episode_info.get('episode_title'),
                source_site=subscription.preferred_source,
                source_url=episode_info.get('source_url'),
                quality=subscription.quality_profile.value,
                language=subscription.language_preference,
                status=QueueStatus.WANTED,
                priority=0,  # Default priority
            )

            self.session.add(queue_item)
            self.session.commit()

            logger.info(
                f"Added to queue: {episode_info['show_title']} "
                f"S{episode_info['season_number']:02d}E{episode_info['episode_number']:02d}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to add episode to queue: {e}")
            self.session.rollback()
            return False

    def process_queue(self, max_items: int = 10) -> Dict:
        """
        Process items in the download queue (extract links and send to JDownloader).

        Args:
            max_items: Maximum number of items to process

        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing download queue (max {max_items} items)")

        # Get wanted episodes
        wanted = self.session.query(EpisodeQueue).filter(
            EpisodeQueue.status == QueueStatus.WANTED
        ).order_by(
            EpisodeQueue.priority.desc(),
            EpisodeQueue.added_date.asc()
        ).limit(max_items).all()

        if not wanted:
            logger.info("No episodes in queue")
            return {'processed': 0, 'success': 0, 'failed': 0}

        processed = 0
        success = 0
        failed = 0

        for queue_item in wanted:
            try:
                logger.info(f"Processing: {queue_item.show_title} {queue_item.episode_code}")

                # Update status
                queue_item.status = QueueStatus.SEARCHING
                self.session.commit()

                # Extract links
                if not queue_item.source_url:
                    logger.warning(f"No source URL for {queue_item.episode_code}")
                    queue_item.status = QueueStatus.FAILED
                    queue_item.last_error = "No source URL available"
                    queue_item.error_count += 1
                    self.session.commit()
                    failed += 1
                    continue

                links_result = self.link_extractor.extract_links(
                    queue_item.source_url,
                    queue_item.source_site,
                    queue_item.quality
                )

                if not links_result.get('success') or not links_result.get('links'):
                    logger.warning(f"No links found for {queue_item.episode_code}")
                    queue_item.status = QueueStatus.FAILED
                    queue_item.last_error = "No download links found"
                    queue_item.error_count += 1
                    self.session.commit()
                    failed += 1
                    continue

                # Store links
                queue_item.download_links = json.dumps(links_result['links'])
                queue_item.status = QueueStatus.QUEUED
                queue_item.grabbed_date = datetime.utcnow()
                self.session.commit()

                logger.info(f"Successfully extracted links for {queue_item.episode_code}")
                success += 1

            except Exception as e:
                logger.error(f"Error processing {queue_item.episode_code}: {e}")
                queue_item.status = QueueStatus.FAILED
                queue_item.last_error = str(e)
                queue_item.error_count += 1
                self.session.commit()
                failed += 1

            processed += 1

        logger.info(f"Queue processing complete: {processed} processed, {success} success, {failed} failed")

        return {
            'processed': processed,
            'success': success,
            'failed': failed
        }

    def send_to_jdownloader(self, max_items: int = 5) -> Dict:
        """
        Send queued episodes to JDownloader.

        Args:
            max_items: Maximum number of items to send

        Returns:
            Dictionary with send results
        """
        from ..downloader import JDownloaderClient, JDownloaderError

        logger.info(f"Sending episodes to JDownloader (max {max_items} items)")

        # Get queued episodes (links extracted, ready to download)
        queued = self.session.query(EpisodeQueue).filter(
            EpisodeQueue.status == QueueStatus.QUEUED
        ).order_by(
            EpisodeQueue.priority.desc(),
            EpisodeQueue.grabbed_date.asc()
        ).limit(max_items).all()

        if not queued:
            logger.info("No episodes ready to send to JDownloader")
            return {'sent': 0, 'success': 0, 'failed': 0}

        sent = 0
        success = 0
        failed = 0

        try:
            with JDownloaderClient() as jd_client:
                for queue_item in queued:
                    try:
                        # Parse links
                        links = json.loads(queue_item.download_links) if queue_item.download_links else []
                        if not links:
                            continue

                        # Get URLs from links
                        urls = [link['url'] for link in links]

                        # Package name
                        package_name = f"{queue_item.show_title} {queue_item.episode_code}"

                        # Send to JDownloader
                        result = jd_client.add_links(urls, package_name=package_name)

                        if result.get('success'):
                            queue_item.status = QueueStatus.DOWNLOADING
                            queue_item.jdownloader_link_ids = json.dumps(result.get('link_ids', []))
                            self.session.commit()

                            logger.info(f"Sent to JDownloader: {package_name}")
                            success += 1
                        else:
                            queue_item.status = QueueStatus.FAILED
                            queue_item.last_error = "Failed to add to JDownloader"
                            queue_item.error_count += 1
                            self.session.commit()
                            failed += 1

                    except Exception as e:
                        logger.error(f"Error sending {queue_item.episode_code} to JDownloader: {e}")
                        queue_item.status = QueueStatus.FAILED
                        queue_item.last_error = str(e)
                        queue_item.error_count += 1
                        self.session.commit()
                        failed += 1

                    sent += 1

        except JDownloaderError as e:
            logger.error(f"JDownloader connection error: {e}")
            return {'sent': 0, 'success': 0, 'failed': 0, 'error': str(e)}

        logger.info(f"JDownloader send complete: {sent} sent, {success} success, {failed} failed")

        return {
            'sent': sent,
            'success': success,
            'failed': failed
        }

    def close(self):
        """Cleanup resources."""
        if self.link_extractor:
            self.link_extractor.close()
