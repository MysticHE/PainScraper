"""
Configuration settings for Singapore Pain Point Scraper.
Update credentials before running.
"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATABASE_PATH = DATA_DIR / "painpoints.db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Reddit API Credentials
# Get yours at: https://www.reddit.com/prefs/apps (create "script" type app)
REDDIT_CONFIG = {
    "client_id": os.getenv("REDDIT_CLIENT_ID", "YOUR_CLIENT_ID_HERE"),
    "client_secret": os.getenv("REDDIT_CLIENT_SECRET", "YOUR_CLIENT_SECRET_HERE"),
    "user_agent": os.getenv("REDDIT_USER_AGENT", "SGPainPointScraper/1.0 by YourUsername"),
    "username": os.getenv("REDDIT_USERNAME", ""),  # Optional
    "password": os.getenv("REDDIT_PASSWORD", ""),  # Optional
}

# Target subreddits for Singapore market research
SUBREDDITS = [
    "singapore",      # General Singapore discussions
    "askSingapore",   # Problem-seeking posts
    "singaporefi",    # Financial pain points
    "SGExams",        # Education/career anxiety
]

# Keywords indicating pain points
PAIN_KEYWORDS = [
    "frustrated", "hate", "annoying", "waste of time",
    "how do I", "anyone else", "problem with", "issue with",
    "terrible", "horrible", "worst", "ridiculous",
    "expensive", "overpriced", "rip off", "scam",
    "slow", "inefficient", "broken", "doesn't work",
    "help me", "need advice", "struggling with",
]

# Ollama settings
OLLAMA_CONFIG = {
    "model": "llama3.1:8b",
    "host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "timeout": 120,
}

# Pain point categories for classification
CATEGORIES = [
    "healthcare",
    "transport",
    "compliance",
    "hiring",
    "cost_of_living",
    "housing",
    "finance",
    "education",
    "government_services",
    "rental",
    "food_delivery",
    "banking",
    "insurance",
    "telecommunications",
    "other",
]

# Target audiences
AUDIENCES = ["consumer", "SME", "both"]

# HardwareZone EDMW settings
HWZ_CONFIG = {
    "base_url": "https://forums.hardwarezone.com.sg",
    "edmw_url": "https://forums.hardwarezone.com.sg/forums/eat-drink-man-woman.16/",
    "max_threads": 50,
    "max_replies_per_thread": 20,
}

# News sources
NEWS_SOURCES = {
    "mothership": {
        "rss_url": "https://mothership.sg/feed/",
        "name": "Mothership.sg",
    },
    "stomp": {
        "url": "https://stomp.straitstimes.com/",
        "name": "STOMP",
    },
}

# Twitter/X settings (basic scraping - may be rate limited)
TWITTER_CONFIG = {
    "hashtags": ["#singapore", "#sgproblems", "#singaporelife"],
    "keywords": ["singapore frustrated", "singapore complaint", "sg annoying"],
    "max_tweets": 100,
}

# Scraping settings
SCRAPE_CONFIG = {
    "request_delay": 2,  # Seconds between requests
    "max_retries": 3,
    "retry_delay": 5,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Classification prompt template
CLASSIFICATION_PROMPT = """Analyze the following post from Singapore and extract pain points.

POST TITLE: {title}
POST CONTENT: {content}
SOURCE: {source}

Classify this post and respond with ONLY valid JSON (no markdown, no explanation):
{{
    "is_pain_point": true/false,
    "pain_point_category": "one of: healthcare, transport, compliance, hiring, cost_of_living, housing, finance, education, government_services, rental, food_delivery, banking, insurance, telecommunications, other",
    "target_audience": "consumer, SME, or both",
    "intensity": 1-10 (how frustrated/urgent is this),
    "automation_potential": "low, medium, or high (can AI/software solve this?)",
    "suggested_solution": "brief 1-2 sentence AI automation idea",
    "keywords": ["list", "of", "main", "complaint", "keywords"],
    "summary": "one sentence summary of the pain point"
}}

If this is NOT a pain point (just news, meme, casual chat), set is_pain_point to false and fill other fields with null."""
