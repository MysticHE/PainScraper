"""
HardwareZone EDMW forum scraper using BeautifulSoup.
"""
import time
import re
from datetime import datetime
from typing import Generator, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import HWZ_CONFIG, SCRAPE_CONFIG, PAIN_KEYWORDS
from database import insert_post


class HWZScraper:
    """Scraper for HardwareZone EDMW forum."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": SCRAPE_CONFIG["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.base_url = HWZ_CONFIG["base_url"]
        self.edmw_url = HWZ_CONFIG["edmw_url"]

    def _get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page."""
        for attempt in range(SCRAPE_CONFIG["max_retries"]):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except requests.RequestException as e:
                print(f"  Attempt {attempt + 1} failed: {e}")
                if attempt < SCRAPE_CONFIG["max_retries"] - 1:
                    time.sleep(SCRAPE_CONFIG["retry_delay"])
        return None

    def _is_pain_point_candidate(self, text: str) -> bool:
        """Check if text contains pain point indicators."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in PAIN_KEYWORDS)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        return text

    def _parse_timestamp(self, timestamp_str: str) -> Optional[str]:
        """Parse HWZ timestamp formats."""
        try:
            # Common formats on HWZ
            patterns = [
                "%b %d, %Y at %I:%M %p",
                "%d %b %Y",
                "%Y-%m-%d",
            ]
            for pattern in patterns:
                try:
                    dt = datetime.strptime(timestamp_str.strip(), pattern)
                    return dt.isoformat()
                except ValueError:
                    continue

            # Handle relative times like "Today at 3:45 PM"
            if "today" in timestamp_str.lower():
                return datetime.now().isoformat()
            if "yesterday" in timestamp_str.lower():
                return datetime.now().isoformat()

        except Exception:
            pass
        return None

    def get_thread_list(self, page: int = 1) -> Generator[dict, None, None]:
        """
        Get list of threads from EDMW forum.

        Args:
            page: Page number to fetch

        Yields:
            Thread info dictionaries
        """
        url = f"{self.edmw_url}page-{page}" if page > 1 else self.edmw_url
        soup = self._get_page(url)

        if not soup:
            print(f"Failed to fetch EDMW page {page}")
            return

        # Find thread listing - adjust selectors based on actual HWZ structure
        threads = soup.select(".structItem--thread")

        if not threads:
            # Try alternative selectors
            threads = soup.select("[data-thread-id]")

        if not threads:
            threads = soup.select(".discussionListItem")

        for thread in threads:
            try:
                # Extract thread info
                title_elem = thread.select_one(".structItem-title a") or thread.select_one("a.title")
                if not title_elem:
                    continue

                title = self._clean_text(title_elem.get_text())
                thread_url = urljoin(self.base_url, title_elem.get("href", ""))

                # Get author
                author_elem = thread.select_one(".username") or thread.select_one(".structItem-minor a")
                author = author_elem.get_text().strip() if author_elem else "Unknown"

                # Get timestamp
                time_elem = thread.select_one("time") or thread.select_one(".DateTime")
                timestamp = None
                if time_elem:
                    timestamp = time_elem.get("datetime") or time_elem.get("title")
                    if timestamp:
                        timestamp = self._parse_timestamp(timestamp)

                # Get reply count
                replies_elem = thread.select_one(".structItem-cell--meta dd")
                replies = 0
                if replies_elem:
                    try:
                        replies = int(re.sub(r"[^\d]", "", replies_elem.get_text()))
                    except ValueError:
                        pass

                yield {
                    "title": title,
                    "url": thread_url,
                    "author": author,
                    "timestamp": timestamp,
                    "replies": replies,
                    "is_candidate": self._is_pain_point_candidate(title),
                }

            except Exception as e:
                print(f"  Error parsing thread: {e}")
                continue

        time.sleep(SCRAPE_CONFIG["request_delay"])

    def get_thread_content(self, thread_url: str, max_replies: int = 20) -> Optional[dict]:
        """
        Get content from a thread.

        Args:
            thread_url: URL of the thread
            max_replies: Maximum replies to fetch

        Returns:
            Thread content dictionary
        """
        soup = self._get_page(thread_url)

        if not soup:
            return None

        try:
            # Get main post content
            posts = soup.select(".message-body")

            if not posts:
                posts = soup.select(".messageText")

            if not posts:
                posts = soup.select("[data-lb-id]")

            all_content = []

            for i, post in enumerate(posts[:max_replies + 1]):
                content = self._clean_text(post.get_text())
                if content and len(content) > 20:  # Filter very short posts
                    all_content.append(content)

            if not all_content:
                return None

            return {
                "main_post": all_content[0] if all_content else "",
                "replies": all_content[1:] if len(all_content) > 1 else [],
                "combined": " ".join(all_content[:5]),  # First 5 posts for context
            }

        except Exception as e:
            print(f"  Error parsing thread content: {e}")
            return None

    def scrape_all(self, max_threads: int = None, max_pages: int = 3) -> list:
        """
        Scrape EDMW forum threads.

        Args:
            max_threads: Maximum threads to scrape (None for config default)
            max_pages: Maximum pages to scan for threads

        Returns:
            List of saved post IDs
        """
        max_threads = max_threads or HWZ_CONFIG["max_threads"]
        saved_ids = []
        total_scraped = 0
        total_saved = 0

        print("\n=== HardwareZone EDMW Scraper ===")

        threads_collected = []

        # Collect threads from multiple pages
        for page in range(1, max_pages + 1):
            print(f"\nScanning EDMW page {page}...")

            for thread in self.get_thread_list(page):
                threads_collected.append(thread)
                if len(threads_collected) >= max_threads:
                    break

            if len(threads_collected) >= max_threads:
                break

        print(f"\nFound {len(threads_collected)} threads, processing...")

        # Process each thread
        for thread in threads_collected:
            total_scraped += 1

            # Get thread content
            content_data = self.get_thread_content(
                thread["url"],
                max_replies=HWZ_CONFIG["max_replies_per_thread"]
            )

            if not content_data:
                continue

            # Combine title and content
            full_content = f"{thread['title']}\n\n{content_data['combined']}"

            post_id = insert_post(
                source="hwz/edmw",
                title=thread["title"],
                content=full_content[:5000],  # Limit content length
                url=thread["url"],
                author=thread["author"],
                post_timestamp=thread["timestamp"],
            )

            if post_id:
                saved_ids.append(post_id)
                total_saved += 1

            time.sleep(SCRAPE_CONFIG["request_delay"])

        print(f"\nHWZ EDMW: Scraped {total_scraped} threads, saved {total_saved} new posts")
        return saved_ids


def test_scraper():
    """Test HWZ scraper functionality."""
    print("Testing HardwareZone EDMW scraper...")

    scraper = HWZScraper()

    print("\nFetching thread list (first 5):")
    count = 0
    for thread in scraper.get_thread_list(page=1):
        count += 1
        candidate = "[CANDIDATE]" if thread["is_candidate"] else ""
        print(f"  {count}. {thread['title'][:50]}... {candidate}")
        if count >= 5:
            break

    print(f"\nTest complete! Found {count} threads")


if __name__ == "__main__":
    test_scraper()
