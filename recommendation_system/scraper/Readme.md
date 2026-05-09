# Tech Job Scraper — Naukri & LinkedIn

Scrapes tech jobs from Naukri.com and LinkedIn and saves them to a structured JSON file for your job recommendation system.

---

## Files

| File | Purpose |
|------|---------|
| `scraper.py` | **Primary scraper** — uses HTTP requests + Naukri's JSON API |
| `scraper_browser.py` | **Fallback scraper** — uses Playwright (handles JS & bot-detection) |
| `requirements.txt` | Python dependencies |

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (For browser fallback only) Install Chromium
playwright install chromium
```

---

## Usage

### Option A — Fast HTTP scraper (try this first)

```bash
# Basic: scrape Bengaluru tech jobs
python scraper.py

# Custom location, 5 pages per keyword
python scraper.py --location "Hyderabad" --pages 5

# Scrape only Naukri, with specific keywords
python scraper.py --sources naukri --keywords "python developer" "data engineer" "devops"

# Full control
python scraper.py \
  --location "Bengaluru" \
  --pages 4 \
  --sources naukri linkedin \
  --keywords "software engineer" "full stack developer" "ml engineer" \
  --output my_jobs.json
```

### Option B — Browser scraper (if Option A gets blocked)

```bash
python scraper_browser.py --location "Bengaluru" --pages 3 --output jobs.json
```

---

## Output Format

```json
{
  "scraped_at": "2025-05-10T08:30:00Z",
  "total": 142,
  "jobs": [
    {
      "title": "Full Stack Developer",
      "company": "Acme Corp",
      "location": "Bengaluru",
      "job_type": "Hybrid",
      "experience": "2-5 years",
      "skills": ["React", "Node.js", "MongoDB", "Docker", "AWS"],
      "description": "Build and maintain scalable web applications...",
      "url": "https://www.naukri.com/job-listings-...",
      "source": "naukri"
    }
  ]
}
```

---

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--location` | `Bengaluru` | City to search jobs in |
| `--pages` | `3` | Pages to scrape per keyword (more = more jobs, slower) |
| `--output` | `tech_jobs.json` | Output file path |
| `--sources` | `naukri linkedin` | Which sites to scrape |
| `--keywords` | *(auto)* | Override default tech keywords |

---

## Notes & Tips

- **Rate limiting**: The scraper adds random delays (1.5–4s) between requests to be polite and avoid bans.
- **Anti-bot**: Naukri's JSON API (`/jobapi/v3/search`) is more reliable than scraping HTML. If it returns 403, switch to `scraper_browser.py`.
- **LinkedIn**: The public (non-login) guest API works without authentication for basic listings.
- **Scale**: For large-scale scraping (1000+ jobs), use a proxy rotation service and increase `--pages`.
- **Scheduling**: Run via cron or a scheduler (e.g. APScheduler) to refresh the dataset daily.

### Example cron (daily at 7 AM)
```cron
0 7 * * * /usr/bin/python3 /path/to/scraper.py --pages 5 --output /data/jobs.json
```
