"""
Web scraper for oillocotv.biz

This scraper handles the site's bot protection using Selenium
and extracts show, season, and episode information.
"""
import logging
import time
import re
import random
from typing import List, Dict, Optional
from datetime import datetime
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
    OILLOCO_BASE_URL,
    OILLOCO_SERIES_LIST_URL,
    SCRAPER_DELAY_MIN,
    SCRAPER_DELAY_MAX,
    SELENIUM_HEADLESS,
    SELENIUM_PAGE_LOAD_TIMEOUT,
    USER_AGENT
)

logger = logging.getLogger(__name__)


class OillocoScraper:
    """
    Scraper for oillocotv.biz website.

    Uses Selenium to bypass bot protection and BeautifulSoup
    to parse HTML content.
    """

    def __init__(self, use_selenium=True, headless=True):
        """
        Initialize the scraper.

        Args:
            use_selenium: Use Selenium for scraping (required for bot protection)
            headless: Run browser in headless mode
        """
        self.base_url = OILLOCO_BASE_URL
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
            raise RuntimeError("Selenium is not installed")

        logger.info("Initializing Selenium WebDriver")

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(SELENIUM_PAGE_LOAD_TIMEOUT)
            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            raise

    def close(self):
        """Close the browser and cleanup."""
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
        delay = random.uniform(SCRAPER_DELAY_MIN, SCRAPER_DELAY_MAX)
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

        try:
            logger.info(f"Fetching: {url}")
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

    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup."""
        return BeautifulSoup(html, 'html.parser')

    def scrape_series_list(self) -> List[Dict]:
        """
        Scrape the complete series list page.

        Returns:
            List of dictionaries with show information
        """
        logger.info("Scraping series list")
        html = self._get_page(OILLOCO_SERIES_LIST_URL)

        if not html:
            logger.error("Failed to fetch series list page")
            return []

        soup = self._parse_html(html)
        shows = []

        # Find all show links
        # This is a generic implementation - may need adjustment based on actual HTML structure
        show_links = soup.find_all('a', href=re.compile(r'/' + r'[a-z0-9\-]+/$'))

        for link in show_links:
            href = link.get('href', '')
            if not href or href == '/':
                continue

            # Extract show information
            title = link.get_text(strip=True)
            if not title:
                continue

            full_url = urljoin(self.base_url, href)
            slug = href.strip('/').split('/')[-1]

            show_data = {
                'title': title,
                'url': full_url,
                'slug': slug,
            }

            shows.append(show_data)
            logger.debug(f"Found show: {title}")

        logger.info(f"Found {len(shows)} shows")
        return shows

    def scrape_show_page(self, show_url: str) -> Dict:
        """
        Scrape a show's page to get seasons and episodes.

        Args:
            show_url: URL of the show page

        Returns:
            Dictionary with show, seasons, and episodes data
        """
        logger.info(f"Scraping show page: {show_url}")
        html = self._get_page(show_url)

        if not html:
            logger.error(f"Failed to fetch show page: {show_url}")
            return {}

        soup = self._parse_html(html)

        show_data = {
            'url': show_url,
            'title': '',
            'description': '',
            'seasons': []
        }

        # Extract show title
        title_elem = soup.find('h1')
        if title_elem:
            show_data['title'] = title_elem.get_text(strip=True)

        # Extract description
        desc_elem = soup.find('div', class_='description') or soup.find('p')
        if desc_elem:
            show_data['description'] = desc_elem.get_text(strip=True)

        # Find episode links
        # Pattern: Show Name SxE (e.g., "Lucifer 3x05 ITA")
        episode_pattern = re.compile(r'(\d+)x(\d+)', re.IGNORECASE)
        episode_links = soup.find_all('a', text=episode_pattern)

        # Organize episodes by season
        seasons_dict = {}

        for link in episode_links:
            text = link.get_text(strip=True)
            href = link.get('href', '')

            # Extract season and episode numbers
            match = episode_pattern.search(text)
            if not match:
                continue

            season_num = int(match.group(1))
            episode_num = int(match.group(2))

            if season_num not in seasons_dict:
                seasons_dict[season_num] = {
                    'season_number': season_num,
                    'episodes': []
                }

            episode_data = {
                'episode_number': episode_num,
                'title': text,
                'url': urljoin(self.base_url, href) if href else None,
            }

            seasons_dict[season_num]['episodes'].append(episode_data)

        # Convert to list and sort
        show_data['seasons'] = sorted(seasons_dict.values(), key=lambda x: x['season_number'])

        for season in show_data['seasons']:
            season['episodes'].sort(key=lambda x: x['episode_number'])

        logger.info(f"Scraped show: {show_data['title']}, {len(show_data['seasons'])} seasons")
        return show_data

    def scrape_episode_page(self, episode_url: str) -> Dict:
        """
        Scrape an episode page to get streaming links and details.

        Args:
            episode_url: URL of the episode page

        Returns:
            Dictionary with episode details and streaming links
        """
        logger.info(f"Scraping episode page: {episode_url}")
        html = self._get_page(episode_url)

        if not html:
            logger.error(f"Failed to fetch episode page: {episode_url}")
            return {}

        soup = self._parse_html(html)

        episode_data = {
            'url': episode_url,
            'title': '',
            'description': '',
            'streaming_links': []
        }

        # Extract title
        title_elem = soup.find('h1')
        if title_elem:
            episode_data['title'] = title_elem.get_text(strip=True)

        # Extract description
        desc_elem = soup.find('div', class_='description') or soup.find('p')
        if desc_elem:
            episode_data['description'] = desc_elem.get_text(strip=True)

        # Extract streaming links
        # Look for iframe or link elements
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if src:
                episode_data['streaming_links'].append(src)

        logger.debug(f"Found {len(episode_data['streaming_links'])} streaming links")
        return episode_data

    def scrape_all_shows(self, max_shows: Optional[int] = None) -> List[Dict]:
        """
        Scrape all shows with their complete information.

        Args:
            max_shows: Maximum number of shows to scrape (None for all)

        Returns:
            List of complete show dictionaries
        """
        logger.info("Starting full scrape of all shows")

        # Get list of shows
        shows = self.scrape_series_list()

        if max_shows:
            shows = shows[:max_shows]
            logger.info(f"Limited to {max_shows} shows")

        complete_shows = []

        for i, show_basic in enumerate(shows, 1):
            logger.info(f"Scraping show {i}/{len(shows)}: {show_basic['title']}")

            try:
                show_data = self.scrape_show_page(show_basic['url'])
                if show_data:
                    # Merge basic info with detailed info
                    show_data.update(show_basic)
                    complete_shows.append(show_data)
                else:
                    logger.warning(f"Failed to scrape show: {show_basic['title']}")

            except Exception as e:
                logger.error(f"Error scraping show {show_basic['title']}: {e}")
                continue

        logger.info(f"Completed scraping {len(complete_shows)} shows")
        return complete_shows
