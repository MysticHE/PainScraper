"""
Twitter/X scraper using Selenium for Singapore-related complaints.
Note: Twitter scraping is heavily rate-limited and may require authentication.
"""
import time
import re
from datetime import datetime
from typing import Generator, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from config import TWITTER_CONFIG, SCRAPE_CONFIG, PAIN_KEYWORDS
from database import insert_post


class TwitterScraper:
    """
    Scraper for Twitter/X using Selenium.

    Note: Twitter has strong anti-scraping measures. This scraper:
    - May be rate-limited or blocked
    - Works best with a logged-in session
    - Should be used sparingly
    """

    def __init__(self, headless: bool = True):
        self.driver = None
        self.headless = headless
        self._rate_limit_hit = False

    def _init_driver(self):
        """Initialize Chrome WebDriver."""
        if self.driver:
            return

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f"--user-agent={SCRAPE_CONFIG['user_agent']}")

        # Disable automation flags
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception as e:
            print(f"Failed to initialize Chrome driver: {e}")
            raise

    def _close_driver(self):
        """Close WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _is_pain_point_candidate(self, text: str) -> bool:
        """Check if text contains pain point indicators."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in PAIN_KEYWORDS)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        return text

    def _scroll_page(self, scrolls: int = 3):
        """Scroll page to load more tweets."""
        for _ in range(scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

    def search_tweets(
        self,
        query: str,
        max_tweets: int = 50,
    ) -> Generator[dict, None, None]:
        """
        Search for tweets using Twitter's search.

        Args:
            query: Search query
            max_tweets: Maximum tweets to fetch

        Yields:
            Tweet dictionaries
        """
        if self._rate_limit_hit:
            print("  Rate limit previously hit, skipping...")
            return

        try:
            self._init_driver()

            # Navigate to Twitter search
            search_url = f"https://twitter.com/search?q={query}&src=typed_query&f=live"
            self.driver.get(search_url)

            # Wait for tweets to load
            time.sleep(5)

            # Check for rate limit or login wall
            page_source = self.driver.page_source.lower()
            if "rate limit" in page_source or "login" in page_source:
                print("  Twitter rate limit or login wall detected")
                self._rate_limit_hit = True
                return

            # Scroll to load more tweets
            self._scroll_page(scrolls=3)

            # Find tweet elements
            tweet_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                '[data-testid="tweet"]'
            )

            if not tweet_elements:
                # Try alternative selector
                tweet_elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    'article[role="article"]'
                )

            count = 0
            seen_texts = set()

            for tweet in tweet_elements:
                if count >= max_tweets:
                    break

                try:
                    # Get tweet text
                    text_elem = tweet.find_element(
                        By.CSS_SELECTOR,
                        '[data-testid="tweetText"]'
                    )
                    text = self._clean_text(text_elem.text)

                    # Skip duplicates
                    if text in seen_texts or len(text) < 20:
                        continue
                    seen_texts.add(text)

                    # Get author
                    try:
                        author_elem = tweet.find_element(
                            By.CSS_SELECTOR,
                            '[data-testid="User-Name"] a'
                        )
                        author = author_elem.text.split("\n")[0]
                    except NoSuchElementException:
                        author = "Unknown"

                    # Get timestamp
                    try:
                        time_elem = tweet.find_element(By.CSS_SELECTOR, "time")
                        timestamp = time_elem.get_attribute("datetime")
                    except NoSuchElementException:
                        timestamp = datetime.now().isoformat()

                    # Get tweet URL
                    try:
                        link_elem = tweet.find_element(
                            By.CSS_SELECTOR,
                            'a[href*="/status/"]'
                        )
                        url = link_elem.get_attribute("href")
                    except NoSuchElementException:
                        url = search_url

                    yield {
                        "source": "twitter/x",
                        "title": text[:100] + "..." if len(text) > 100 else text,
                        "content": text,
                        "url": url,
                        "author": author,
                        "post_timestamp": timestamp,
                        "is_candidate": self._is_pain_point_candidate(text),
                    }

                    count += 1

                except Exception as e:
                    continue

                time.sleep(0.5)

        except TimeoutException:
            print("  Timeout waiting for Twitter to load")
            self._rate_limit_hit = True
        except Exception as e:
            print(f"  Error scraping Twitter: {e}")

    def scrape_hashtags(
        self,
        hashtags: list = None,
        max_per_tag: int = 30,
    ) -> Generator[dict, None, None]:
        """
        Scrape tweets from specific hashtags.

        Args:
            hashtags: List of hashtags to scrape
            max_per_tag: Maximum tweets per hashtag

        Yields:
            Tweet dictionaries
        """
        hashtags = hashtags or TWITTER_CONFIG["hashtags"]

        for hashtag in hashtags:
            if self._rate_limit_hit:
                break

            print(f"  Searching {hashtag}...")
            query = hashtag if hashtag.startswith("#") else f"#{hashtag}"

            for tweet in self.search_tweets(query, max_tweets=max_per_tag):
                yield tweet

            time.sleep(SCRAPE_CONFIG["request_delay"] * 2)

    def scrape_all(self) -> list:
        """
        Scrape Twitter for Singapore pain points.

        Returns:
            List of saved post IDs
        """
        saved_ids = []
        total_scraped = 0
        total_saved = 0

        print("\n=== Twitter/X Scraper ===")
        print("Note: Twitter has strong anti-scraping measures. Results may be limited.")

        try:
            # Search hashtags
            print("\nSearching Singapore hashtags...")
            for tweet in self.scrape_hashtags(max_per_tag=30):
                total_scraped += 1

                post_id = insert_post(
                    source=tweet["source"],
                    title=tweet["title"],
                    content=tweet["content"],
                    url=tweet["url"],
                    author=tweet["author"],
                    post_timestamp=tweet["post_timestamp"],
                )

                if post_id:
                    saved_ids.append(post_id)
                    total_saved += 1

            # Search keywords if not rate limited
            if not self._rate_limit_hit:
                print("\nSearching pain point keywords...")
                for keyword in TWITTER_CONFIG["keywords"][:2]:
                    for tweet in self.search_tweets(keyword, max_tweets=20):
                        total_scraped += 1

                        post_id = insert_post(
                            source=tweet["source"],
                            title=tweet["title"],
                            content=tweet["content"],
                            url=tweet["url"],
                            author=tweet["author"],
                            post_timestamp=tweet["post_timestamp"],
                        )

                        if post_id:
                            saved_ids.append(post_id)
                            total_saved += 1

                    time.sleep(SCRAPE_CONFIG["request_delay"] * 2)

        finally:
            self._close_driver()

        print(f"\nTwitter: Scraped {total_scraped} tweets, saved {total_saved} new posts")

        if self._rate_limit_hit:
            print("Note: Rate limit was hit. Consider running again later.")

        return saved_ids


def test_scraper():
    """Test Twitter scraper functionality."""
    print("Testing Twitter scraper...")
    print("Note: This may fail due to Twitter's anti-scraping measures.")

    scraper = TwitterScraper(headless=True)

    try:
        print("\nSearching #singapore (5 tweets):")
        count = 0
        for tweet in scraper.search_tweets("#singapore", max_tweets=5):
            count += 1
            candidate = "[CANDIDATE]" if tweet["is_candidate"] else ""
            print(f"  {count}. @{tweet['author']}: {tweet['content'][:50]}... {candidate}")

        print(f"\nTest complete! Found {count} tweets")

    except Exception as e:
        print(f"Test failed: {e}")
        print("Twitter scraping may be blocked. This is expected behavior.")

    finally:
        scraper._close_driver()


if __name__ == "__main__":
    test_scraper()
