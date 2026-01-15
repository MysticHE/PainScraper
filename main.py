"""
Main orchestrator for Singapore Pain Point Scraper.
Runs all scrapers, classifies posts, and generates reports.
"""
import argparse
import sys
from datetime import datetime

from database import init_database, get_total_stats
from scrapers import RedditScraper, HWZScraper, NewsScraper, TwitterScraper
from classifier import classify_unclassified
from report import generate_report
from config import REDDIT_CONFIG


def run_scrapers(
    reddit: bool = True,
    hwz: bool = True,
    news: bool = True,
    twitter: bool = False,  # Disabled by default due to rate limits
) -> dict:
    """
    Run selected scrapers.

    Args:
        reddit: Run Reddit scraper
        hwz: Run HardwareZone scraper
        news: Run news scraper
        twitter: Run Twitter scraper

    Returns:
        Stats dict with counts per source
    """
    stats = {
        "reddit": 0,
        "hwz": 0,
        "news": 0,
        "twitter": 0,
    }

    if reddit:
        if REDDIT_CONFIG["client_id"] == "YOUR_CLIENT_ID_HERE":
            print("\n[SKIP] Reddit: API credentials not configured")
            print("       Get credentials at: https://www.reddit.com/prefs/apps")
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
            ids = scraper.scrape_all(max_threads=50)
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
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Singapore Pain Point Scraper - Extract and classify pain points from SG forums"
    )

    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Run all scrapers",
    )
    parser.add_argument(
        "--classify",
        action="store_true",
        help="Classify unclassified posts",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate markdown report",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run scrape, classify, and report",
    )
    parser.add_argument(
        "--reddit",
        action="store_true",
        help="Include Reddit scraper",
    )
    parser.add_argument(
        "--hwz",
        action="store_true",
        help="Include HardwareZone scraper",
    )
    parser.add_argument(
        "--news",
        action="store_true",
        help="Include news scrapers",
    )
    parser.add_argument(
        "--twitter",
        action="store_true",
        help="Include Twitter scraper (may be rate-limited)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max posts to classify per run",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize/reset database",
    )

    args = parser.parse_args()

    # If no action specified, show help
    if not any([args.scrape, args.classify, args.report, args.all, args.init_db]):
        parser.print_help()
        print("\n\nQuick start:")
        print("  python main.py --all    # Run everything")
        print("  python main.py --scrape # Just scrape")
        print("  python main.py --report # Just generate report")
        return

    print("=" * 60)
    print("Singapore Pain Point Scraper")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Initialize database
    if args.init_db or args.all or args.scrape:
        init_database()

    # Run scrapers
    if args.scrape or args.all:
        print("\n" + "=" * 40)
        print("PHASE 1: SCRAPING")
        print("=" * 40)

        # Determine which scrapers to run
        run_reddit = args.reddit or (not any([args.reddit, args.hwz, args.news, args.twitter]))
        run_hwz = args.hwz or (not any([args.reddit, args.hwz, args.news, args.twitter]))
        run_news = args.news or (not any([args.reddit, args.hwz, args.news, args.twitter]))
        run_twitter = args.twitter  # Only if explicitly requested

        scrape_stats = run_scrapers(
            reddit=run_reddit,
            hwz=run_hwz,
            news=run_news,
            twitter=run_twitter,
        )

        print("\n--- Scraping Summary ---")
        total_new = sum(scrape_stats.values())
        for source, count in scrape_stats.items():
            if count > 0:
                print(f"  {source}: {count} new posts")
        print(f"  Total new posts: {total_new}")

    # Classify posts
    if args.classify or args.all:
        print("\n" + "=" * 40)
        print("PHASE 2: CLASSIFICATION")
        print("=" * 40)

        classify_stats = classify_unclassified(limit=args.limit)

    # Generate report
    if args.report or args.all:
        print("\n" + "=" * 40)
        print("PHASE 3: REPORTING")
        print("=" * 40)

        report_path = generate_report()
        if report_path:
            print(f"\nReport generated: {report_path}")

    # Show database stats
    print("\n" + "=" * 40)
    print("DATABASE SUMMARY")
    print("=" * 40)

    stats = get_total_stats()
    print(f"  Total posts: {stats['total_posts']}")
    print(f"  Pain points identified: {stats['total_pain_points']}")
    print(f"  Sources tracked: {stats['total_sources']}")

    if stats['posts_by_source']:
        print("\n  Posts by source:")
        for source, count in stats['posts_by_source'].items():
            print(f"    {source}: {count}")

    print("\n" + "=" * 60)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
