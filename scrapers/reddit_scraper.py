"""
Reddit scraper using PRAW for Singapore subreddits.
"""
import time
from datetime import datetime
from typing import Generator

import praw
from praw.exceptions import PRAWException

from config import REDDIT_CONFIG, SUBREDDITS, PAIN_KEYWORDS, SCRAPE_CONFIG
from database import insert_post


class RedditScraper:
    """Scraper for Singapore-related subreddits using PRAW."""

    def __init__(self):
        self.reddit = None
        self._init_reddit()

    def _init_reddit(self):
        """Initialize Reddit API connection."""
        try:
            self.reddit = praw.Reddit(
                client_id=REDDIT_CONFIG["client_id"],
                client_secret=REDDIT_CONFIG["client_secret"],
                user_agent=REDDIT_CONFIG["user_agent"],
                username=REDDIT_CONFIG.get("username") or None,
                password=REDDIT_CONFIG.get("password") or None,
            )
            # Test connection
            self.reddit.user.me()
            print("Reddit API connected successfully")
        except Exception as e:
            print(f"Reddit API connection failed: {e}")
            print("Running in read-only mode (limited functionality)")
            self.reddit = praw.Reddit(
                client_id=REDDIT_CONFIG["client_id"],
                client_secret=REDDIT_CONFIG["client_secret"],
                user_agent=REDDIT_CONFIG["user_agent"],
            )

    def _is_pain_point_candidate(self, text: str) -> bool:
        """Check if text contains pain point indicators."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in PAIN_KEYWORDS)

    def scrape_subreddit(
        self,
        subreddit_name: str,
        limit: int = 100,
        sort: str = "new",
    ) -> Generator[dict, None, None]:
        """
        Scrape posts from a subreddit.

        Args:
            subreddit_name: Name of subreddit to scrape
            limit: Maximum posts to fetch
            sort: Sort method (new, hot, top, rising)

        Yields:
            Post dictionaries
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            if sort == "new":
                posts = subreddit.new(limit=limit)
            elif sort == "hot":
                posts = subreddit.hot(limit=limit)
            elif sort == "top":
                posts = subreddit.top(limit=limit, time_filter="week")
            elif sort == "rising":
                posts = subreddit.rising(limit=limit)
            else:
                posts = subreddit.new(limit=limit)

            for post in posts:
                combined_text = f"{post.title} {post.selftext}"

                yield {
                    "source": f"reddit/r/{subreddit_name}",
                    "title": post.title,
                    "content": post.selftext or post.title,
                    "url": f"https://reddit.com{post.permalink}",
                    "author": str(post.author) if post.author else "[deleted]",
                    "post_timestamp": datetime.fromtimestamp(post.created_utc).isoformat(),
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "is_candidate": self._is_pain_point_candidate(combined_text),
                }

                time.sleep(SCRAPE_CONFIG["request_delay"] / 2)

        except PRAWException as e:
            print(f"Error scraping r/{subreddit_name}: {e}")
        except Exception as e:
            print(f"Unexpected error scraping r/{subreddit_name}: {e}")

    def search_subreddit(
        self,
        subreddit_name: str,
        query: str,
        limit: int = 50,
    ) -> Generator[dict, None, None]:
        """
        Search a subreddit for specific keywords.

        Args:
            subreddit_name: Name of subreddit
            query: Search query
            limit: Maximum results

        Yields:
            Post dictionaries
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            for post in subreddit.search(query, limit=limit, sort="new"):
                yield {
                    "source": f"reddit/r/{subreddit_name}",
                    "title": post.title,
                    "content": post.selftext or post.title,
                    "url": f"https://reddit.com{post.permalink}",
                    "author": str(post.author) if post.author else "[deleted]",
                    "post_timestamp": datetime.fromtimestamp(post.created_utc).isoformat(),
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "is_candidate": True,  # Search results are candidates by default
                }

                time.sleep(SCRAPE_CONFIG["request_delay"] / 2)

        except PRAWException as e:
            print(f"Error searching r/{subreddit_name}: {e}")
        except Exception as e:
            print(f"Unexpected error searching r/{subreddit_name}: {e}")

    def scrape_all(self, posts_per_sub: int = 50) -> list:
        """
        Scrape all configured subreddits.

        Args:
            posts_per_sub: Posts to fetch per subreddit

        Returns:
            List of saved post IDs
        """
        saved_ids = []
        total_scraped = 0
        total_saved = 0

        print("\n=== Reddit Scraper ===")

        # Scrape each subreddit
        for subreddit in SUBREDDITS:
            print(f"\nScraping r/{subreddit}...")
            sub_count = 0

            for post in self.scrape_subreddit(subreddit, limit=posts_per_sub):
                total_scraped += 1
                post_id = insert_post(
                    source=post["source"],
                    title=post["title"],
                    content=post["content"],
                    url=post["url"],
                    author=post["author"],
                    post_timestamp=post["post_timestamp"],
                )
                if post_id:
                    saved_ids.append(post_id)
                    total_saved += 1
                    sub_count += 1

            print(f"  Saved {sub_count} new posts from r/{subreddit}")

        # Search for pain point keywords across all subreddits
        print("\nSearching for pain point keywords...")
        search_queries = [
            "frustrated", "hate this", "waste of time",
            "how do I", "anyone else experiencing",
        ]

        for subreddit in SUBREDDITS:
            for query in search_queries[:2]:  # Limit searches to avoid rate limiting
                for post in self.search_subreddit(subreddit, query, limit=20):
                    total_scraped += 1
                    post_id = insert_post(
                        source=post["source"],
                        title=post["title"],
                        content=post["content"],
                        url=post["url"],
                        author=post["author"],
                        post_timestamp=post["post_timestamp"],
                    )
                    if post_id:
                        saved_ids.append(post_id)
                        total_saved += 1

        print(f"\nReddit: Scraped {total_scraped} posts, saved {total_saved} new posts")
        return saved_ids


def test_scraper():
    """Test Reddit scraper functionality."""
    print("Testing Reddit scraper...")

    if REDDIT_CONFIG["client_id"] == "YOUR_CLIENT_ID_HERE":
        print("ERROR: Please configure Reddit API credentials in config.py")
        print("Get credentials at: https://www.reddit.com/prefs/apps")
        return

    scraper = RedditScraper()

    # Test scraping one subreddit
    print("\nTesting r/singapore scrape (5 posts):")
    count = 0
    for post in scraper.scrape_subreddit("singapore", limit=5):
        count += 1
        candidate = "[CANDIDATE]" if post["is_candidate"] else ""
        print(f"  {count}. {post['title'][:60]}... {candidate}")

    print(f"\nTest complete! Found {count} posts")


if __name__ == "__main__":
    test_scraper()
