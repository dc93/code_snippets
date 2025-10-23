"""
Automatic file organization and library management
"""
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import json

from ..models.database import get_session
from ..models.episode_queue import EpisodeQueue, QueueStatus, DownloadHistory
from ..config import (
    TV_LIBRARY_PATH,
    DOWNLOAD_FOLDER,
    AUTO_ORGANIZE,
    DELETE_AFTER_ORGANIZE,
    MINIMUM_FILE_SIZE_MB,
    SUPPORTED_VIDEO_EXTENSIONS
)

# Import from media_db
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from media_db.utils import parse_filename
from media_db.models import get_session as get_media_db_session, LibraryItem, LibraryPath, MatchStatus

logger = logging.getLogger(__name__)


class FileOrganizer:
    """
    Organizes downloaded files into the library.
    """

    def __init__(self):
        """Initialize file organizer."""
        self.session = get_session()
        self.media_db_session = get_media_db_session()
        self.library_path = Path(TV_LIBRARY_PATH)
        self.download_folder = Path(DOWNLOAD_FOLDER)

    def scan_downloads(self) -> Dict:
        """
        Scan download folder for completed files.

        Returns:
            Dictionary with scan results
        """
        logger.info(f"Scanning downloads folder: {self.download_folder}")

        if not self.download_folder.exists():
            logger.warning(f"Download folder does not exist: {self.download_folder}")
            return {'scanned': 0, 'organized': 0, 'errors': 0}

        # Find video files
        video_files = []
        for ext in SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(self.download_folder.rglob(f'*{ext}'))

        logger.info(f"Found {len(video_files)} video files")

        organized = 0
        errors = 0

        for video_file in video_files:
            # Check minimum file size
            file_size_mb = video_file.stat().st_size / (1024 * 1024)
            if file_size_mb < MINIMUM_FILE_SIZE_MB:
                logger.debug(f"Skipping small file: {video_file.name} ({file_size_mb:.1f}MB)")
                continue

            try:
                result = self.organize_file(video_file)
                if result['success']:
                    organized += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error(f"Error organizing {video_file.name}: {e}")
                errors += 1

        logger.info(f"Scan complete: {len(video_files)} scanned, {organized} organized, {errors} errors")

        return {
            'scanned': len(video_files),
            'organized': organized,
            'errors': errors
        }

    def organize_file(self, file_path: Path) -> Dict:
        """
        Organize a single file into the library.

        Args:
            file_path: Path to the file to organize

        Returns:
            Dictionary with organization result
        """
        logger.info(f"Organizing file: {file_path.name}")

        if not file_path.exists():
            return {'success': False, 'error': 'File does not exist'}

        # Parse filename
        parsed = parse_filename(file_path.name)
        if not parsed['parsed']:
            logger.warning(f"Could not parse filename: {file_path.name}")
            return {'success': False, 'error': 'Could not parse filename'}

        show_name = parsed['show_name']
        season = parsed['season']
        episode = parsed['episode']
        quality = parsed['quality']

        logger.info(f"Parsed as: {show_name} S{season:02d}E{episode:02d} {quality or ''}")

        # Find matching episode in queue
        queue_item = self.session.query(EpisodeQueue).filter(
            EpisodeQueue.show_title.ilike(f'%{show_name}%'),
            EpisodeQueue.season_number == season,
            EpisodeQueue.episode_number == episode,
            EpisodeQueue.status.in_([QueueStatus.DOWNLOADING, QueueStatus.QUEUED])
        ).first()

        if not queue_item:
            logger.warning(f"No matching episode in queue for: {show_name} S{season:02d}E{episode:02d}")
            # Still try to organize based on parsed info
            show_title = show_name
        else:
            show_title = queue_item.show_title

        # Build target path
        target_dir = self.library_path / show_title / f"Season {season}"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Build new filename
        new_filename = f"{show_title} - S{season:02d}E{episode:02d}"
        if quality:
            new_filename += f" - {quality}"
        new_filename += file_path.suffix

        target_path = target_dir / new_filename

        # Check if file already exists
        if target_path.exists():
            logger.warning(f"File already exists: {target_path}")
            # Delete the download if configured
            if DELETE_AFTER_ORGANIZE:
                file_path.unlink()
                logger.info(f"Deleted duplicate: {file_path}")
            return {'success': False, 'error': 'File already exists in library'}

        try:
            # Move or copy file
            if DELETE_AFTER_ORGANIZE:
                shutil.move(str(file_path), str(target_path))
                logger.info(f"Moved to: {target_path}")
            else:
                shutil.copy2(str(file_path), str(target_path))
                logger.info(f"Copied to: {target_path}")

            # Update queue item if found
            if queue_item:
                queue_item.status = QueueStatus.COMPLETED
                queue_item.downloaded_file_path = str(file_path)
                queue_item.final_file_path = str(target_path)
                queue_item.completed_date = datetime.utcnow()
                self.session.commit()

                # Add to download history
                self._add_to_history(queue_item, success=True, final_path=str(target_path))

                # Update subscription stats
                subscription = queue_item.subscription_id
                if subscription:
                    from ..models.show_subscription import ShowSubscription
                    sub = self.session.query(ShowSubscription).get(subscription)
                    if sub:
                        sub.episodes_downloaded += 1
                        self.session.commit()

            # Add to media_db library
            self._add_to_media_db_library(target_path, parsed)

            return {
                'success': True,
                'target_path': str(target_path),
                'show': show_title,
                'season': season,
                'episode': episode
            }

        except Exception as e:
            logger.error(f"Failed to organize file: {e}")
            if queue_item:
                queue_item.status = QueueStatus.FAILED
                queue_item.last_error = f"Organization failed: {str(e)}"
                self.session.commit()
            return {'success': False, 'error': str(e)}

    def _add_to_history(
        self,
        queue_item: EpisodeQueue,
        success: bool,
        final_path: Optional[str] = None
    ):
        """Add download to history."""
        try:
            history = DownloadHistory(
                subscription_id=queue_item.subscription_id,
                show_title=queue_item.show_title,
                season_number=queue_item.season_number,
                episode_number=queue_item.episode_number,
                episode_title=queue_item.episode_title,
                source_site=queue_item.source_site,
                source_url=queue_item.source_url,
                quality=queue_item.quality,
                file_size=queue_item.downloaded_file_size,
                success=success,
                status_message="Completed" if success else "Failed",
                error_message=queue_item.last_error if not success else None,
                downloaded_file=queue_item.downloaded_file_path,
                final_location=final_path,
                grabbed_date=queue_item.grabbed_date,
                download_start=queue_item.grabbed_date,
                download_end=queue_item.downloaded_date,
                timestamp=datetime.utcnow(),
                manual=queue_item.manual_grab
            )
            self.session.add(history)
            self.session.commit()
        except Exception as e:
            logger.error(f"Failed to add to history: {e}")

    def _add_to_media_db_library(self, file_path: Path, parsed: Dict):
        """Add organized file to media_db library."""
        try:
            # Check if already in media_db
            existing = self.media_db_session.query(LibraryItem).filter_by(
                file_path=str(file_path)
            ).first()

            if existing:
                logger.debug(f"File already in media_db library: {file_path.name}")
                return

            # Get or create library path
            lib_path_obj = self.media_db_session.query(LibraryPath).filter_by(
                path=str(self.library_path)
            ).first()

            if not lib_path_obj:
                lib_path_obj = LibraryPath(
                    path=str(self.library_path),
                    name="TV Library",
                    is_active=True
                )
                self.media_db_session.add(lib_path_obj)
                self.media_db_session.commit()

            # Create library item
            item = LibraryItem(
                library_path_id=lib_path_obj.id,
                file_path=str(file_path),
                file_name=file_path.name,
                file_size=file_path.stat().st_size,
                file_extension=file_path.suffix,
                file_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                show_name_parsed=parsed.get('show_name'),
                season_parsed=parsed.get('season'),
                episode_parsed=parsed.get('episode'),
                quality=parsed.get('quality'),
                release_group=parsed.get('release_group'),
                match_status=MatchStatus.MATCHED  # Assume matched since we organized it
            )
            self.media_db_session.add(item)
            self.media_db_session.commit()

            logger.info(f"Added to media_db library: {file_path.name}")

        except Exception as e:
            logger.error(f"Failed to add to media_db library: {e}")
            self.media_db_session.rollback()
