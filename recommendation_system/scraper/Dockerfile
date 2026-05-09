# Use official Playwright image — comes with Chromium pre-installed on Ubuntu 22.04
FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

WORKDIR /app

#COPY requirements.txt .
COPY scraper.py .
COPY scraper_browser.py .

RUN pip install --no-cache-dir requests beautifulsoup4 lxml

RUN mkdir -p /app/output

# Default command — runs the browser scraper and saves to /app/output/tech_jobs.json
# All args can be overridden at docker run time
ENTRYPOINT ["python", "scraper_browser.py"]
CMD ["--location", "Bengaluru", "--pages", "3", "--output", "/app/output/tech_jobs.json"]
