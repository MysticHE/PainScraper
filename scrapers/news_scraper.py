"""
News scraper for Singapore news and complaint sites.
Uses feedparser for RSS and BeautifulSoup for HTML scraping.
"""
import time
import re
from datetime import datetime
from typing import Generator, Optional
from urllib.parse import urljoin

import requests
import feedparser
from bs4 import BeautifulSoup

from config import NEWS_SOURCES, SCRAPE_CONFIG, PAIN_KEYWORDS
from database import insert_post


class NewsScraper:
    """Scraper for Singapore news sites and complaint platforms."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": SCRAPE_CONFIG["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

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
        # Additional news-specific keywords
        news_pain_keywords = PAIN_KEYWORDS + [
            "complaint", "complain", "upset", "angry", "outrage",
            "concern", "worried", "issue", "problem", "fail",
            "delay", "shortage", "increase", "hike", "expensive",
        ]
        return any(keyword.lower() in text_lower for keyword in news_pain_keywords)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        return text

    def _parse_rss_date(self, date_str: str) -> Optional[str]:
        """Parse RSS feed date formats."""
        try:
            # feedparser usually provides structured time
            if isinstance(date_str, time.struct_time):
                return datetime(*date_str[:6]).isoformat()

            # Common RSS date formats
            patterns = [
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S GMT",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
            ]

            for pattern in patterns:
                try:
                    dt = datetime.strptime(date_str.strip(), pattern)
                    return dt.isoformat()
                except ValueError:
                    continue

        except Exception:
            pass
        return datetime.now().isoformat()

    def scrape_mothership_rss(self, limit: int = 50) -> Generator[dict, None, None]:
        """
        Scrape Mothership.sg RSS feed.

        Args:
            limit: Maximum articles to fetch

        Yields:
            Article dictionaries
        """
        print("  Fetching Mothership.sg RSS...")

        try:
            feed = feedparser.parse(NEWS_SOURCES["mothership"]["rss_url"])

            if feed.bozo:
                print(f"  Warning: RSS feed parsing issues: {feed.bozo_exception}")

            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))

                # Clean HTML from summary
                if summary:
                    soup = BeautifulSoup(summary, "lxml")
                    summary = soup.get_text()

                combined_text = f"{title} {summary}"

                yield {
                    "source": "mothership.sg",
                    "title": self._clean_text(title),
                    "content": self._clean_text(summary),
                    "url": entry.get("link", ""),
                    "author": entry.get("author", "Mothership"),
                    "post_timestamp": self._parse_rss_date(
                        entry.get("published_parsed") or entry.get("published", "")
                    ),
                    "is_candidate": self._is_pain_point_candidate(combined_text),
                }

        except Exception as e:
            print(f"  Error scraping Mothership RSS: {e}")

    def scrape_stomp(self, limit: int = 30) -> Generator[dict, None, None]:
        """
        Scrape STOMP.sg for community reports/complaints.

        Args:
            limit: Maximum articles to fetch

        Yields:
            Article dictionaries
        """
        print("  Fetching STOMP.sg...")

        soup = self._get_page(NEWS_SOURCES["stomp"]["url"])
        if not soup:
            print("  Failed to fetch STOMP")
            return

        try:
            # Find article cards - adjust selectors based on actual site structure
            articles = soup.select("article") or soup.select(".card")

            if not articles:
                articles = soup.select("[class*='story']")

            count = 0
            for article in articles:
                if count >= limit:
                    break

                try:
                    # Extract title
                    title_elem = article.select_one("h2 a") or article.select_one("h3 a") or article.select_one("a")
                    if not title_elem:
                        continue

                    title = self._clean_text(title_elem.get_text())
                    url = title_elem.get("href", "")
                    if url and not url.startswith("http"):
                        url = urljoin(NEWS_SOURCES["stomp"]["url"], url)

                    # Extract summary/description
                    summary_elem = article.select_one("p") or article.select_one(".excerpt")
                    summary = summary_elem.get_text().strip() if summary_elem else ""

                    # Extract timestamp
                    time_elem = article.select_one("time") or article.select_one("[class*='date']")
                    timestamp = None
                    if time_elem:
                        timestamp = time_elem.get("datetime") or time_elem.get_text()

                    combined_text = f"{title} {summary}"

                    yield {
                        "source": "stomp.sg",
                        "title": title,
                        "content": self._clean_text(summary) if summary else title,
                        "url": url,
                        "author": "STOMP",
                        "post_timestamp": timestamp,
                        "is_candidate": self._is_pain_point_candidate(combined_text),
                    }

                    count += 1

                except Exception as e:
                    print(f"  Error parsing STOMP article: {e}")
                    continue

        except Exception as e:
            print(f"  Error scraping STOMP: {e}")

        time.sleep(SCRAPE_CONFIG["request_delay"])

    def scrape_article_content(self, url: str) -> Optional[str]:
        """
        Fetch full article content from URL.

        Args:
            url: Article URL

        Returns:
            Article text content
        """
        soup = self._get_page(url)
        if not soup:
            return None

        try:
            # Try common article content selectors
            content_selectors = [
                "article",
                ".article-content",
                ".post-content",
                ".entry-content",
                "[itemprop='articleBody']",
                ".story-body",
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Remove scripts, styles, ads
                    for elem in content_elem.select("script, style, .ad, .advertisement"):
                        elem.decompose()

                    text = self._clean_text(content_elem.get_text())
                    if len(text) > 100:
                        return text[:3000]  # Limit length

            # Fallback: get all paragraph text
            paragraphs = soup.select("p")
            text = " ".join(p.get_text().strip() for p in paragraphs[:10])
            return self._clean_text(text)[:3000] if text else None

        except Exception as e:
            print(f"  Error fetching article content: {e}")
            return None

    def scrape_all(self, fetch_full_content: bool = False) -> list:
        """
        Scrape all configured news sources.

        Args:
            fetch_full_content: Whether to fetch full article content

        Returns:
            List of saved post IDs
        """
        saved_ids = []
        total_scraped = 0
        total_saved = 0

        print("\n=== News Scraper ===")

        # Scrape Mothership RSS
        print("\nScraping Mothership.sg...")
        for article in self.scrape_mothership_rss(limit=50):
            total_scraped += 1

            content = article["content"]
            if fetch_full_content and article["url"]:
                full_content = self.scrape_article_content(article["url"])
                if full_content:
                    content = full_content
                time.sleep(SCRAPE_CONFIG["request_delay"])

            post_id = insert_post(
                source=article["source"],
                title=article["title"],
                content=content,
                url=article["url"],
                author=article["author"],
                post_timestamp=article["post_timestamp"],
            )

            if post_id:
                saved_ids.append(post_id)
                total_saved += 1

        # Scrape STOMP
        print("\nScraping STOMP.sg...")
        for article in self.scrape_stomp(limit=30):
            total_scraped += 1

            content = article["content"]
            if fetch_full_content and article["url"]:
                full_content = self.scrape_article_content(article["url"])
                if full_content:
                    content = full_content
                time.sleep(SCRAPE_CONFIG["request_delay"])

            post_id = insert_post(
                source=article["source"],
                title=article["title"],
                content=content,
                url=article["url"],
                author=article["author"],
                post_timestamp=article["post_timestamp"],
            )

            if post_id:
                saved_ids.append(post_id)
                total_saved += 1

        print(f"\nNews: Scraped {total_scraped} articles, saved {total_saved} new posts")
        return saved_ids


def test_scraper():
    """Test news scraper functionality."""
    print("Testing News scraper...")

    scraper = NewsScraper()

    print("\nTesting Mothership.sg RSS (5 articles):")
    count = 0
    for article in scraper.scrape_mothership_rss(limit=5):
        count += 1
        candidate = "[CANDIDATE]" if article["is_candidate"] else ""
        print(f"  {count}. {article['title'][:50]}... {candidate}")

    print("\nTesting STOMP.sg (5 articles):")
    count = 0
    for article in scraper.scrape_stomp(limit=5):
        count += 1
        candidate = "[CANDIDATE]" if article["is_candidate"] else ""
        print(f"  {count}. {article['title'][:50]}... {candidate}")

    print("\nTest complete!")


if __name__ == "__main__":
    test_scraper()
