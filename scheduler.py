"""
Scheduler for automated pain point scraping.
Can be run via cron, Task Scheduler, or GitHub Actions.
"""
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_scraper(
    scrape: bool = True,
    classify: bool = True,
    report: bool = True,
    sources: list = None,
):
    """
    Run the pain point scraper with specified options.

    Args:
        scrape: Run scrapers
        classify: Classify posts
        report: Generate report
        sources: List of sources to scrape (reddit, hwz, news, twitter)
    """
    print(f"[{datetime.now().isoformat()}] Starting scheduled scrape...")

    cmd = [sys.executable, str(PROJECT_ROOT / "main.py")]

    if scrape and classify and report:
        cmd.append("--all")
    else:
        if scrape:
            cmd.append("--scrape")
        if classify:
            cmd.append("--classify")
        if report:
            cmd.append("--report")

    if sources:
        for source in sources:
            cmd.append(f"--{source}")

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
        )

        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")

        if result.returncode != 0:
            print(f"[ERROR] Scraper exited with code {result.returncode}")
        else:
            print(f"[{datetime.now().isoformat()}] Scheduled scrape completed successfully")

    except subprocess.TimeoutExpired:
        print(f"[ERROR] Scraper timed out after 1 hour")
    except Exception as e:
        print(f"[ERROR] Failed to run scraper: {e}")


def generate_cron_commands():
    """Print cron commands for scheduling."""
    python_path = sys.executable
    script_path = Path(__file__).absolute()

    print("""
# ==========================================
# Cron Commands for Pain Point Scraper
# ==========================================

# Run full scrape daily at 6 AM
0 6 * * * {python} {script} --mode full >> /var/log/painpoint-scraper.log 2>&1

# Run quick scrape (news only) every 4 hours
0 */4 * * * {python} {script} --mode quick >> /var/log/painpoint-scraper.log 2>&1

# Generate report only at 8 AM
0 8 * * * {python} {project}/report.py >> /var/log/painpoint-scraper.log 2>&1

# Edit crontab:
# crontab -e

""".format(
        python=python_path,
        script=script_path,
        project=PROJECT_ROOT,
    ))


def generate_github_actions():
    """Print GitHub Actions workflow for scheduling."""
    workflow = """
# ==========================================
# GitHub Actions Workflow
# ==========================================
# Save this as .github/workflows/scraper.yml

name: Singapore Pain Point Scraper

on:
  schedule:
    # Run daily at 6 AM UTC
    - cron: '0 6 * * *'
  workflow_dispatch:  # Allow manual triggers

jobs:
  scrape:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Ollama
        run: |
          curl -fsSL https://ollama.com/install.sh | sh
          ollama serve &
          sleep 5
          ollama pull llama3.1:8b

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run scraper
        env:
          REDDIT_CLIENT_ID: ${{ secrets.REDDIT_CLIENT_ID }}
          REDDIT_CLIENT_SECRET: ${{ secrets.REDDIT_CLIENT_SECRET }}
          REDDIT_USER_AGENT: ${{ secrets.REDDIT_USER_AGENT }}
        run: |
          python main.py --all

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: pain-point-report
          path: reports/

      - name: Commit database updates
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add data/painpoints.db reports/
          git diff --staged --quiet || git commit -m "chore: update pain point data"
          git push
"""
    print(workflow)


def generate_windows_task():
    """Print Windows Task Scheduler commands."""
    python_path = sys.executable
    script_path = Path(__file__).absolute()

    print(f"""
# ==========================================
# Windows Task Scheduler Commands
# ==========================================

# Create scheduled task (run as Administrator):

schtasks /create /tn "PainPointScraper" /tr "\\"{python_path}\\" \\"{script_path}\\" --mode full" /sc daily /st 06:00

# To view task:
schtasks /query /tn "PainPointScraper"

# To delete task:
schtasks /delete /tn "PainPointScraper" /f

# To run task manually:
schtasks /run /tn "PainPointScraper"
""")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scheduler for Singapore Pain Point Scraper"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "quick", "classify", "report"],
        default="full",
        help="Scraping mode",
    )
    parser.add_argument(
        "--show-cron",
        action="store_true",
        help="Show cron setup commands",
    )
    parser.add_argument(
        "--show-github",
        action="store_true",
        help="Show GitHub Actions workflow",
    )
    parser.add_argument(
        "--show-windows",
        action="store_true",
        help="Show Windows Task Scheduler commands",
    )

    args = parser.parse_args()

    if args.show_cron:
        generate_cron_commands()
    elif args.show_github:
        generate_github_actions()
    elif args.show_windows:
        generate_windows_task()
    else:
        # Run the scraper based on mode
        if args.mode == "full":
            run_scraper(scrape=True, classify=True, report=True)
        elif args.mode == "quick":
            run_scraper(scrape=True, classify=True, report=False, sources=["news"])
        elif args.mode == "classify":
            run_scraper(scrape=False, classify=True, report=False)
        elif args.mode == "report":
            run_scraper(scrape=False, classify=False, report=True)
