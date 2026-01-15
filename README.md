# Singapore Pain Point Scraper

A comprehensive tool for extracting and classifying pain points from Singapore-focused online platforms. Uses local LLM (Llama 3.1 8B via Ollama) for intelligent classification.

## Features

- **Multi-Platform Scraping**: Reddit, HardwareZone EDMW, Mothership.sg, STOMP, Twitter/X
- **AI Classification**: Uses Llama 3.1 8B to categorize pain points and assess automation potential
- **SQLite Storage**: Efficient local database with deduplication
- **Markdown Reports**: Auto-generated analysis reports with trending topics
- **Scheduling Support**: Cron, Windows Task Scheduler, and GitHub Actions examples

## Quick Start

```bash
# 1. Navigate to project directory
cd ~/projects/sg-pain-point-scraper

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Start Ollama (in separate terminal)
ollama serve

# 4. Run the scraper
python main.py --all
```

## Platform Coverage

| Platform | Source | Content Type |
|----------|--------|--------------|
| Reddit | r/singapore, r/askSingapore, r/singaporefi, r/SGExams | General discussions, Q&A |
| HardwareZone | EDMW Forum | Local discussions |
| Mothership.sg | RSS Feed | News articles |
| STOMP | Web scraping | Community reports |
| Twitter/X | Selenium | Social media (rate-limited) |

## Setup

### Prerequisites

- Python 3.10+
- Ollama installed and running
- Reddit API credentials (for Reddit scraping)

### Installation

```bash
# Install Ollama (if not already installed)
# Windows: Download from https://ollama.com
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# Pull the model
ollama pull llama3.1:8b

# Install Python dependencies (already done if using venv)
pip install -r requirements.txt
```

### Reddit API Setup

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Select "script" type
4. Fill in name and description (redirect URI can be http://localhost)
5. Copy the client ID (under app name) and secret
6. Update `config.py` or set environment variables:

```bash
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
export REDDIT_USER_AGENT="SGPainPointScraper/1.0 by YourUsername"
```

## Usage

### Run Everything

```bash
python main.py --all
```

This will:
1. Scrape all platforms
2. Classify posts using Ollama
3. Generate a markdown report

### Individual Commands

```bash
# Just scrape (no classification)
python main.py --scrape

# Just classify existing posts
python main.py --classify

# Just generate report
python main.py --report

# Specific scrapers only
python main.py --scrape --reddit --news

# Include Twitter (rate-limited)
python main.py --scrape --twitter
```

### Generate Reports

```bash
# Markdown report
python report.py

# With JSON export
python report.py --json
```

### Test Individual Scrapers

```bash
# Test Reddit scraper
python -m scrapers.reddit_scraper

# Test HWZ scraper
python -m scrapers.hwz_scraper

# Test News scraper
python -m scrapers.news_scraper

# Test classifier
python classifier.py
```

## Project Structure

```
sg-pain-point-scraper/
├── config.py              # Configuration and credentials
├── main.py                # Main orchestrator
├── classifier.py          # Ollama-based classification
├── database.py            # SQLite database operations
├── report.py              # Markdown report generator
├── scheduler.py           # Cron/scheduling utilities
├── requirements.txt       # Python dependencies
├── scrapers/
│   ├── __init__.py
│   ├── reddit_scraper.py  # Reddit via PRAW
│   ├── hwz_scraper.py     # HardwareZone EDMW
│   ├── news_scraper.py    # Mothership, STOMP
│   └── twitter_scraper.py # Twitter/X via Selenium
├── reports/               # Generated reports
├── data/
│   └── painpoints.db      # SQLite database
└── README.md
```

## Pain Point Categories

Posts are classified into these categories:

- `healthcare` - Medical services, hospitals, clinics
- `transport` - MRT, buses, taxis, traffic
- `compliance` - Regulatory, legal, paperwork
- `hiring` - Recruitment, job search, HR
- `cost_of_living` - Prices, expenses, inflation
- `housing` - HDB, property, rental
- `finance` - Banking, investments, loans
- `education` - Schools, tuition, exams
- `government_services` - CPF, IRAS, government agencies
- `rental` - Property rental issues
- `food_delivery` - Grab, Foodpanda, etc.
- `banking` - Bank services, fees
- `insurance` - Insurance issues
- `telecommunications` - Mobile, internet providers
- `other` - Uncategorized

## Classification Fields

Each pain point is analyzed for:

| Field | Description |
|-------|-------------|
| `category` | Pain point category (see above) |
| `audience` | consumer, SME, or both |
| `intensity` | 1-10 scale of frustration/urgency |
| `automation_potential` | low, medium, high |
| `suggested_solution` | Brief AI solution idea |
| `keywords` | Key complaint terms |
| `summary` | One-sentence summary |

## Scheduling

### Linux/macOS (Cron)

```bash
# Show cron commands
python scheduler.py --show-cron

# Add to crontab
crontab -e
# Add: 0 6 * * * /path/to/python /path/to/scheduler.py --mode full
```

### Windows (Task Scheduler)

```bash
# Show Task Scheduler commands
python scheduler.py --show-windows
```

### GitHub Actions

```bash
# Show workflow configuration
python scheduler.py --show-github
```

Copy the output to `.github/workflows/scraper.yml` and set repository secrets:
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

## Troubleshooting

### Ollama Connection Error

```
Error connecting to Ollama
```

**Solution**: Make sure Ollama is running:
```bash
ollama serve
```

### Model Not Found

```
Model llama3.1:8b not found
```

**Solution**: Pull the model:
```bash
ollama pull llama3.1:8b
```

### Reddit API Error

```
Reddit API connection failed
```

**Solution**:
1. Verify credentials in `config.py`
2. Check if your app is approved at https://www.reddit.com/prefs/apps

### Twitter Rate Limit

```
Twitter rate limit or login wall detected
```

**Solution**: Twitter aggressively rate-limits scrapers. Options:
- Wait 15+ minutes before retrying
- Use authenticated session (not implemented)
- Rely on other sources

### HWZ Scraper Empty Results

The HWZ forum structure may change. If scraping returns empty:
1. Check if the forum is accessible in browser
2. Review CSS selectors in `hwz_scraper.py`

## Database Schema

### Posts Table
```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    content_hash TEXT UNIQUE,  -- For deduplication
    source TEXT,
    title TEXT,
    content TEXT,
    url TEXT,
    author TEXT,
    post_timestamp TEXT,
    scraped_at TEXT
);
```

### Classifications Table
```sql
CREATE TABLE classifications (
    id INTEGER PRIMARY KEY,
    post_id INTEGER UNIQUE,
    is_pain_point BOOLEAN,
    category TEXT,
    audience TEXT,
    intensity INTEGER,
    automation_potential TEXT,
    suggested_solution TEXT,
    keywords TEXT,  -- JSON array
    summary TEXT,
    raw_response TEXT,
    classified_at TEXT
);
```

## API Reference

### Database Functions

```python
from database import (
    init_database,
    insert_post,
    insert_classification,
    get_unclassified_posts,
    get_pain_points,
    get_category_stats,
    get_automation_opportunities,
)

# Get top pain points
pain_points = get_pain_points(
    category="transport",
    min_intensity=7,
    automation_potential="high",
    limit=20
)

# Get category statistics
stats = get_category_stats()
# {'transport': {'count': 45, 'avg_intensity': 7.2}, ...}
```

### Classifier

```python
from classifier import PainPointClassifier

classifier = PainPointClassifier()
result = classifier.classify_post(
    title="MRT broke down again",
    content="Third time this week...",
    source="reddit/r/singapore"
)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `python main.py --all`
5. Submit a pull request

## License

MIT License - feel free to use for research and commercial purposes.

## Disclaimer

This tool is for market research purposes. Please respect:
- Platform Terms of Service
- Rate limits and robots.txt
- User privacy (no personal data collection)
- Singapore PDPA regulations
