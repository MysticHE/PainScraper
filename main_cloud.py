"""
Cloud-compatible main orchestrator for Render deployment.
Uses Groq API instead of local Ollama.
"""
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# For Render: use persistent disk if available
DATA_DIR = Path(os.getenv("RENDER_DISK_PATH", "/data"))
if DATA_DIR.exists():
    os.environ["DATABASE_PATH"] = str(DATA_DIR / "painpoints.db")
    os.environ["REPORTS_DIR"] = str(DATA_DIR / "reports")

from database import init_database, get_total_stats
from scrapers import RedditScraper, HWZScraper, NewsScraper, TwitterScraper
from classifier_cloud import classify_unclassified_cloud
from report import generate_report
from config import REDDIT_CONFIG


def run_scrapers(reddit: bool = True, hwz: bool = True, news: bool = True, twitter: bool = False) -> dict:
    """Run selected scrapers."""
    stats = {"reddit": 0, "hwz": 0, "news": 0, "twitter": 0}

    if reddit:
        client_id = os.getenv("REDDIT_CLIENT_ID", REDDIT_CONFIG["client_id"])
        if client_id == "YOUR_CLIENT_ID_HERE":
            print("\n[SKIP] Reddit: API credentials not configured")
        else:
            try:
                scraper = RedditScraper()
                ids = scraper.scrape_all(posts_per_sub=50)
                stats["reddit"] = len(ids)
            except Exception as e:
                print(f"\n[ERROR] Reddit scraper failed: {e}")

    if hwz:
        try:
            scraper = HWZScraper()
            ids = scraper.scrape_all(max_threads=30)
            stats["hwz"] = len(ids)
        except Exception as e:
            print(f"\n[ERROR] HWZ scraper failed: {e}")

    if news:
        try:
            scraper = NewsScraper()
            ids = scraper.scrape_all(fetch_full_content=False)
            stats["news"] = len(ids)
        except Exception as e:
            print(f"\n[ERROR] News scraper failed: {e}")

    if twitter:
        try:
            scraper = TwitterScraper(headless=True)
            ids = scraper.scrape_all()
            stats["twitter"] = len(ids)
        except Exception as e:
            print(f"\n[ERROR] Twitter scraper failed: {e}")

    return stats


def main():
    """Main entry point for cloud deployment."""
    parser = argparse.ArgumentParser(description="SG Pain Point Scraper (Cloud)")
    parser.add_argument("--scrape", action="store_true", help="Run scrapers")
    parser.add_argument("--classify", action="store_true", help="Classify posts")
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--all", action="store_true", help="Run all steps")
    parser.add_argument("--reddit", action="store_true", help="Include Reddit")
    parser.add_argument("--hwz", action="store_true", help="Include HWZ")
    parser.add_argument("--news", action="store_true", help="Include news")
    parser.add_argument("--twitter", action="store_true", help="Include Twitter/X")
    parser.add_argument("--limit", type=int, default=100, help="Classification limit")

    args = parser.parse_args()

    if not any([args.scrape, args.classify, args.report, args.all]):
        args.all = True  # Default to running everything

    print("=" * 60)
    print("Singapore Pain Point Scraper (Cloud Mode)")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Initialize database
    init_database()

    # Run scrapers
    if args.scrape or args.all:
        print("\n" + "=" * 40)
        print("PHASE 1: SCRAPING")
        print("=" * 40)

        no_specific = not any([args.reddit, args.hwz, args.news, args.twitter])
        scrape_stats = run_scrapers(
            reddit=args.reddit or no_specific,
            hwz=args.hwz or no_specific,
            news=args.news or no_specific,
            twitter=args.twitter,  # Twitter only runs when explicitly requested
        )

        print("\n--- Scraping Summary ---")
        total_new = sum(scrape_stats.values())
        for source, count in scrape_stats.items():
            if count > 0:
                print(f"  {source}: {count} new posts")
        print(f"  Total new posts: {total_new}")

    # Classify using cloud API
    if args.classify or args.all:
        print("\n" + "=" * 40)
        print("PHASE 2: CLASSIFICATION (Groq API)")
        print("=" * 40)

        if not os.getenv("GROQ_API_KEY"):
            print("[ERROR] GROQ_API_KEY not set. Skipping classification.")
        else:
            classify_unclassified_cloud(limit=args.limit)

    # Generate report
    if args.report or args.all:
        print("\n" + "=" * 40)
        print("PHASE 3: REPORTING")
        print("=" * 40)

        report_path = generate_report()
        if report_path:
            print(f"\nReport generated: {report_path}")

    # Summary
    print("\n" + "=" * 40)
    print("DATABASE SUMMARY")
    print("=" * 40)

    stats = get_total_stats()
    print(f"  Total posts: {stats['total_posts']}")
    print(f"  Pain points: {stats['total_pain_points']}")
    print(f"  Sources: {stats['total_sources']}")

    print("\n" + "=" * 60)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
