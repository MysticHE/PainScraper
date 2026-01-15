# SG Pain Point Scraper - Project Instructions

## IMPORTANT: Read First

- **Deployment**: GitHub Actions ONLY (not local)
- **Classification**: Groq API (not Ollama)
- **API Keys**: Stored in GitHub Secrets (not local env)
- **Dashboard**: Auto-deployed to GitHub Pages

**DO NOT** ask about local deployment or Ollama - this project runs entirely via GitHub Actions.

---

## Project Status (as of 2026-01-15)

### Working Platforms

| Platform | Status | Method |
|----------|--------|--------|
| **Mothership.sg** | ✅ Working | RSS feed (`feedparser`) |
| **STOMP** | ✅ Working | Web scraping (`/singapore-seen/` pattern) |
| **HardwareZone** | ✅ Working | Web scraping (EDMW forum) |

### Pending Platforms

| Platform | Status | Blocker |
|----------|--------|---------|
| **Reddit** | ⏳ Pending | Awaiting API approval from Reddit |
| **Twitter/X** | ❌ Disabled | Rate limits, low priority |

---

## How This Project Works

```
GitHub Actions (main.yml)
    │
    ├── Scrape: Mothership + STOMP + HWZ
    │
    ├── Classify: Groq API (llama-3.1-8b-instant)
    │
    ├── Generate: Dashboard HTML
    │
    └── Deploy: GitHub Pages
```

### GitHub Secrets (already configured)

| Secret | Purpose |
|--------|---------|
| `GROQ_API_KEY` | Classification API |
| `GITHUB_TOKEN` | Auto-provided for deployment |

### Live Dashboard

**URL**: https://mystiche.github.io/PainScraper/

---

## Phase 2: Reddit Integration

### When Reddit API is Approved

1. **Add secrets to GitHub**:
   - Go to: GitHub → Repo → Settings → Secrets → Actions
   - Add: `REDDIT_CLIENT_ID`
   - Add: `REDDIT_CLIENT_SECRET`

2. **Update workflow** (`main.yml`) to include Reddit env vars:
   ```yaml
   env:
     GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
     REDDIT_CLIENT_ID: ${{ secrets.REDDIT_CLIENT_ID }}
     REDDIT_CLIENT_SECRET: ${{ secrets.REDDIT_CLIENT_SECRET }}
   ```

3. **Update main_cloud.py** to enable Reddit scraper

### Target Subreddits (config.py)
- r/singapore
- r/askSingapore
- r/singaporefi
- r/SGExams

---

## Trigger Deployment

### Via GitHub CLI
```bash
gh workflow run main.yml --ref main
gh run list --limit 3
```

### Via GitHub Web
1. Go to: https://github.com/MysticHE/PainScraper/actions
2. Click "SG Pain Point Scraper"
3. Click "Run workflow"

### Schedule
- Auto-runs daily at 6 AM UTC

---

## File Structure

```
sg-pain-point-scraper/
├── main_cloud.py          # Cloud entry point (used by GitHub Actions)
├── classifier_cloud.py    # Groq API classifier
├── config.py              # Configuration
├── database.py            # SQLite operations
├── generate_dashboard.py  # Dashboard generator
├── scrapers/
│   ├── news_scraper.py    # Mothership + STOMP ✅
│   ├── hwz_scraper.py     # HardwareZone ✅
│   ├── reddit_scraper.py  # Reddit (pending API)
│   └── twitter_scraper.py # Twitter (disabled)
├── .github/workflows/
│   └── main.yml           # GitHub Actions workflow
└── docs/
    └── index.html         # Dashboard (auto-deployed)
```

---

## Known Issues

- [ ] Silent failures in scrapers (no retry logic)
- [ ] No structured logging
- [ ] Timestamps not normalized across sources

---

## Next Steps After Reddit Approval

1. Add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` to GitHub Secrets
2. Update `main.yml` to pass Reddit credentials
3. Enable Reddit in `main_cloud.py`
4. Trigger workflow to test
