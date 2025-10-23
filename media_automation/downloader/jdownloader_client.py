"""
JDownloader API client using My.JDownloader
"""
import logging
from typing import List, Dict, Optional
import json

try:
    import myjdapi
    MYJDAPI_AVAILABLE = True
except ImportError:
    MYJDAPI_AVAILABLE = False

from ..config import (
    JDOWNLOADER_EMAIL,
    JDOWNLOADER_PASSWORD,
    JDOWNLOADER_DEVICE_NAME,
    JDOWNLOADER_APP_KEY
)

logger = logging.getLogger(__name__)


class JDownloaderError(Exception):
    """Custom exception for JDownloader errors."""
    pass


class JDownloaderClient:
    """
    Client for interacting with JDownloader via My.JDownloader API.
    """

    def __init__(self, email=None, password=None, device_name=None, app_key=None):
        """
        Initialize JDownloader client.

        Args:
            email: My.JDownloader email
            password: My.JDownloader password
            device_name: JDownloader device name
            app_key: Application key for API
        """
        if not MYJDAPI_AVAILABLE:
            raise JDownloaderError(
                "myjdapi library not installed. Install with: pip install myjdapi"
            )

        self.email = email or JDOWNLOADER_EMAIL
        self.password = password or JDOWNLOADER_PASSWORD
        self.device_name = device_name or JDOWNLOADER_DEVICE_NAME
        self.app_key = app_key or JDOWNLOADER_APP_KEY

        if not all([self.email, self.password]):
            raise JDownloaderError(
                "JDownloader credentials not configured. "
                "Set JDOWNLOADER_EMAIL and JDOWNLOADER_PASSWORD environment variables."
            )

        self.jd = None
        self.device = None
        self._connected = False

    def connect(self) -> bool:
        """
        Connect to My.JDownloader and get device.

        Returns:
            True if connected successfully
        """
        try:
            logger.info("Connecting to My.JDownloader...")

            # Create API instance
            self.jd = myjdapi.Myjdapi()
            self.jd.set_app_key(self.app_key)

            # Connect
            self.jd.connect(self.email, self.password)
            logger.info("Connected to My.JDownloader API")

            # Get device
            self.jd.update_devices()
            devices = self.jd.list_devices()

            if not devices:
                raise JDownloaderError("No JDownloader devices found")

            # Find specified device or use first one
            if self.device_name:
                self.device = next(
                    (d for d in devices if d['name'] == self.device_name),
                    None
                )
                if not self.device:
                    logger.warning(
                        f"Device '{self.device_name}' not found. "
                        f"Available devices: {[d['name'] for d in devices]}"
                    )
                    self.device = devices[0]
            else:
                self.device = devices[0]

            logger.info(f"Using JDownloader device: {self.device['name']}")
            self._connected = True
            return True

        except Exception as e:
            logger.error(f"Failed to connect to JDownloader: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from My.JDownloader."""
        if self.jd:
            try:
                self.jd.disconnect()
                logger.info("Disconnected from My.JDownloader")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to JDownloader."""
        return self._connected

    def add_links(
        self,
        urls: List[str],
        package_name: str = "Media Automation",
        download_path: Optional[str] = None
    ) -> Dict:
        """
        Add download links to JDownloader.

        Args:
            urls: List of URLs to download
            package_name: Name for the download package
            download_path: Optional custom download path

        Returns:
            Dictionary with result information
        """
        if not self.is_connected():
            if not self.connect():
                raise JDownloaderError("Not connected to JDownloader")

        try:
            logger.info(f"Adding {len(urls)} links to JDownloader: {package_name}")

            # Build parameters
            params = {
                "links": "\n".join(urls),
                "packageName": package_name,
                "autostart": True,
                "autoextract": False,
            }

            if download_path:
                params["destinationFolder"] = download_path

            # Add links via linkgrabber
            response = self.device.linkgrabber.add_links(params)

            logger.info(f"Links added successfully: {response}")

            # Get the link IDs for tracking
            link_ids = self._get_recent_link_ids(package_name)

            return {
                'success': True,
                'package_name': package_name,
                'url_count': len(urls),
                'link_ids': link_ids,
                'response': response
            }

        except Exception as e:
            logger.error(f"Failed to add links: {e}")
            raise JDownloaderError(f"Failed to add links: {e}")

    def _get_recent_link_ids(self, package_name: str) -> List[str]:
        """Get link IDs for recently added package."""
        try:
            # Query linkgrabber for the package
            links = self.device.linkgrabber.query_links()

            # Filter by package name
            matching_links = [
                link for link in links
                if link.get('packageName') == package_name
            ]

            return [str(link.get('uuid')) for link in matching_links if link.get('uuid')]

        except Exception as e:
            logger.error(f"Error getting link IDs: {e}")
            return []

    def get_download_status(self, link_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Get download status for links.

        Args:
            link_ids: Optional list of specific link IDs to check

        Returns:
            List of download status dictionaries
        """
        if not self.is_connected():
            if not self.connect():
                raise JDownloaderError("Not connected to JDownloader")

        try:
            # Get downloads from linkgrabber and downloads list
            linkgrabber_links = self.device.linkgrabber.query_links()
            download_links = self.device.downloads.query_links()

            all_links = linkgrabber_links + download_links

            if link_ids:
                # Filter by specified IDs
                all_links = [
                    link for link in all_links
                    if str(link.get('uuid')) in link_ids
                ]

            status_list = []
            for link in all_links:
                status_list.append({
                    'id': str(link.get('uuid')),
                    'name': link.get('name'),
                    'url': link.get('url'),
                    'status': link.get('status'),
                    'enabled': link.get('enabled'),
                    'bytes_total': link.get('bytesTotal', 0),
                    'bytes_loaded': link.get('bytesLoaded', 0),
                    'progress': self._calculate_progress(link),
                    'package_name': link.get('packageName'),
                })

            return status_list

        except Exception as e:
            logger.error(f"Failed to get download status: {e}")
            return []

    def _calculate_progress(self, link: Dict) -> float:
        """Calculate download progress percentage."""
        bytes_total = link.get('bytesTotal', 0)
        bytes_loaded = link.get('bytesLoaded', 0)

        if bytes_total > 0:
            return (bytes_loaded / bytes_total) * 100
        return 0.0

    def get_completed_downloads(self) -> List[Dict]:
        """
        Get list of completed downloads.

        Returns:
            List of completed download dictionaries
        """
        if not self.is_connected():
            if not self.connect():
                raise JDownloaderError("Not connected to JDownloader")

        try:
            # Get packages from downloads
            packages = self.device.downloads.query_packages()

            completed = []
            for package in packages:
                # Check if package is finished
                if package.get('finished', False):
                    # Get links in this package
                    links = self.device.downloads.query_links({
                        'packageUUIDs': [package.get('uuid')]
                    })

                    for link in links:
                        if link.get('finished', False):
                            completed.append({
                                'id': str(link.get('uuid')),
                                'name': link.get('name'),
                                'package_name': package.get('name'),
                                'download_path': link.get('downloadPath'),
                                'file_size': link.get('bytesTotal'),
                                'finished': True,
                            })

            return completed

        except Exception as e:
            logger.error(f"Failed to get completed downloads: {e}")
            return []

    def cleanup_completed(self, link_ids: Optional[List[str]] = None):
        """
        Remove completed downloads from JDownloader.

        Args:
            link_ids: Optional list of specific link IDs to clean up
        """
        if not self.is_connected():
            if not self.connect():
                raise JDownloaderError("Not connected to JDownloader")

        try:
            if link_ids:
                # Remove specific links
                self.device.downloads.remove_links(link_ids=link_ids)
                logger.info(f"Cleaned up {len(link_ids)} completed downloads")
            else:
                # Clean up all finished packages
                self.device.downloads.cleanup(
                    action="DELETE_FINISHED",
                    mode="REMOVE_LINKS_AND_DELETE_FILES",
                    selection_type="FINISHED"
                )
                logger.info("Cleaned up all completed downloads")

        except Exception as e:
            logger.error(f"Failed to cleanup downloads: {e}")

    def pause_downloads(self):
        """Pause all downloads."""
        if not self.is_connected():
            return

        try:
            self.device.downloadcontroller.pause()
            logger.info("Downloads paused")
        except Exception as e:
            logger.error(f"Failed to pause downloads: {e}")

    def resume_downloads(self):
        """Resume all downloads."""
        if not self.is_connected():
            return

        try:
            self.device.downloadcontroller.start()
            logger.info("Downloads resumed")
        except Exception as e:
            logger.error(f"Failed to resume downloads: {e}")

    def get_speed(self) -> int:
        """
        Get current download speed.

        Returns:
            Download speed in bytes per second
        """
        if not self.is_connected():
            return 0

        try:
            status = self.device.downloadcontroller.get_current_state()
            return status.get('speed', 0)
        except Exception as e:
            logger.error(f"Failed to get download speed: {e}")
            return 0

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
