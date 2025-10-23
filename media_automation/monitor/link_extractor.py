"""
Extract download links from streaming sites
"""
import logging
import re
import time
import random
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from bs4 import BeautifulSoup

from ..config import (
    SOURCES,
    USER_AGENT,
    REQUEST_TIMEOUT,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
    USE_SELENIUM,
    SELENIUM_HEADLESS,
    QUALITY_ORDER,
    PREFERRED_QUALITY
)

logger = logging.getLogger(__name__)


class LinkExtractor:
    """
    Extract download links from episode pages on streaming sites.
    """

    def __init__(self, use_selenium=USE_SELENIUM, headless=SELENIUM_HEADLESS):
        """
        Initialize link extractor.

        Args:
            use_selenium: Use Selenium for extraction
            headless: Run browser in headless mode
        """
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.headless = headless
        self.driver = None

        if self.use_selenium and not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available. Install with: pip install selenium")
            self.use_selenium = False

    def __enter__(self):
        """Context manager entry."""
        if self.use_selenium:
            self._init_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _init_driver(self):
        """Initialize Selenium WebDriver."""
        if not SELENIUM_AVAILABLE:
            return

        logger.info("Initializing Selenium WebDriver for link extraction")

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(REQUEST_TIMEOUT)
            logger.info("Selenium WebDriver initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            self.use_selenium = False

    def close(self):
        """Close the browser."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None

    def _random_delay(self):
        """Add random delay between requests."""
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    def _get_page(self, url: str) -> Optional[str]:
        """
        Fetch page content using Selenium.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None on error
        """
        if not self.driver:
            self._init_driver()

        if not self.driver:
            logger.error("Cannot fetch page: Selenium not available")
            return None

        try:
            logger.info(f"Fetching page: {url}")
            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Additional wait for dynamic content
            time.sleep(2)

            html = self.driver.page_source
            self._random_delay()
            return html

        except TimeoutException:
            logger.error(f"Timeout loading page: {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    def extract_links(
        self,
        episode_url: str,
        source_site: str = 'oillocotv',
        preferred_quality: str = PREFERRED_QUALITY
    ) -> Dict:
        """
        Extract download links from an episode page.

        Args:
            episode_url: URL of the episode page
            source_site: Source site name ('oillocotv' or 'crockdown')
            preferred_quality: Preferred video quality

        Returns:
            Dictionary with extraction results
        """
        logger.info(f"Extracting links from {source_site}: {episode_url}")

        if source_site == 'oillocotv':
            return self._extract_from_oilloco(episode_url, preferred_quality)
        elif source_site == 'crockdown':
            return self._extract_from_crockdown(episode_url, preferred_quality)
        else:
            logger.error(f"Unknown source site: {source_site}")
            return {'success': False, 'error': 'Unknown source site', 'links': []}

    def _extract_from_oilloco(self, episode_url: str, preferred_quality: str) -> Dict:
        """
        Extract links from oillocotv.biz episode page.

        Args:
            episode_url: Episode page URL
            preferred_quality: Preferred quality

        Returns:
            Dictionary with links and metadata
        """
        html = self._get_page(episode_url)
        if not html:
            return {'success': False, 'error': 'Failed to fetch page', 'links': []}

        soup = BeautifulSoup(html, 'html.parser')

        links = []

        # Look for iframe sources (streaming links)
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if src and self._is_valid_link(src):
                links.append({
                    'url': src,
                    'type': 'iframe',
                    'quality': 'unknown',
                    'host': self._get_host(src)
                })

        # Look for direct links
        # Common patterns: <a href="...">Download</a>, <a href="...">1080p</a>
        link_elements = soup.find_all('a', href=True)
        for elem in link_elements:
            href = elem.get('href', '')
            text = elem.get_text(strip=True).lower()

            # Check if it's a download link
            if any(keyword in text for keyword in ['download', 'scarica', 'mirror', 'link']):
                if self._is_valid_link(href):
                    quality = self._extract_quality_from_text(text)
                    links.append({
                        'url': href if href.startswith('http') else urljoin(episode_url, href),
                        'type': 'direct',
                        'quality': quality,
                        'host': self._get_host(href)
                    })

        # Look for crockdown links specifically
        crockdown_links = [link for link in links if 'crockdown.com' in link['url'].lower()]

        # Filter and sort by quality
        filtered_links = self._filter_by_quality(links, preferred_quality)

        return {
            'success': len(links) > 0,
            'links': filtered_links,
            'all_links': links,
            'crockdown_links': crockdown_links,
            'source_url': episode_url,
        }

    def _extract_from_crockdown(self, file_url: str, preferred_quality: str) -> Dict:
        """
        Extract direct download links from crockdown.com.

        Args:
            file_url: Crockdown file URL
            preferred_quality: Preferred quality

        Returns:
            Dictionary with links and metadata
        """
        html = self._get_page(file_url)
        if not html:
            return {'success': False, 'error': 'Failed to fetch page', 'links': []}

        soup = BeautifulSoup(html, 'html.parser')

        links = []

        # Look for download buttons/links
        download_links = soup.find_all('a', class_=re.compile(r'download|btn'))
        for elem in download_links:
            href = elem.get('href', '')
            if self._is_valid_link(href):
                links.append({
                    'url': href if href.startswith('http') else urljoin(file_url, href),
                    'type': 'direct',
                    'quality': preferred_quality,  # Assume quality from episode info
                    'host': self._get_host(href)
                })

        # If no links found, look for any valid URLs in the page
        if not links:
            all_links = soup.find_all('a', href=True)
            for elem in all_links:
                href = elem.get('href', '')
                if self._is_direct_download_link(href):
                    links.append({
                        'url': href,
                        'type': 'direct',
                        'quality': preferred_quality,
                        'host': self._get_host(href)
                    })

        return {
            'success': len(links) > 0,
            'links': links,
            'source_url': file_url,
        }

    def _is_valid_link(self, url: str) -> bool:
        """Check if URL is a valid download/streaming link."""
        if not url or len(url) < 10:
            return False

        # Exclude common non-download links
        exclude_patterns = [
            'javascript:',
            'mailto:',
            '#',
            'about:',
        ]

        url_lower = url.lower()
        for pattern in exclude_patterns:
            if url_lower.startswith(pattern):
                return False

        return True

    def _is_direct_download_link(self, url: str) -> bool:
        """Check if URL is a direct download link."""
        if not self._is_valid_link(url):
            return False

        # Common file hosting/download domains
        download_hosts = [
            'crockdown.com',
            'uptobox.com',
            'rapidgator.net',
            'uploaded.net',
            'turbobit.net',
            'nitroflare.com',
            '1fichier.com',
        ]

        url_lower = url.lower()
        return any(host in url_lower for host in download_hosts)

    def _get_host(self, url: str) -> str:
        """Extract hostname from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return 'unknown'

    def _extract_quality_from_text(self, text: str) -> str:
        """Extract video quality from text."""
        text_lower = text.lower()

        for quality in QUALITY_ORDER:
            if quality.lower() in text_lower:
                return quality

        # Check for common quality indicators
        if '4k' in text_lower or 'uhd' in text_lower:
            return '2160p'
        elif 'full hd' in text_lower or 'fullhd' in text_lower:
            return '1080p'
        elif 'hd' in text_lower:
            return '720p'

        return 'unknown'

    def _filter_by_quality(self, links: List[Dict], preferred_quality: str) -> List[Dict]:
        """
        Filter and sort links by quality preference.

        Args:
            links: List of link dictionaries
            preferred_quality: Preferred quality

        Returns:
            Sorted list of links
        """
        if not links:
            return []

        # Sort by quality preference
        def quality_score(link):
            quality = link.get('quality', 'unknown')
            if quality == preferred_quality:
                return 0
            elif quality in QUALITY_ORDER:
                return QUALITY_ORDER.index(quality)
            else:
                return 999

        sorted_links = sorted(links, key=quality_score)
        return sorted_links

    def get_best_link(self, links: List[Dict]) -> Optional[Dict]:
        """
        Get the best link from a list based on quality and availability.

        Args:
            links: List of link dictionaries

        Returns:
            Best link or None
        """
        if not links:
            return None

        # Prefer direct links over iframes
        direct_links = [link for link in links if link.get('type') == 'direct']
        if direct_links:
            return direct_links[0]

        return links[0]
