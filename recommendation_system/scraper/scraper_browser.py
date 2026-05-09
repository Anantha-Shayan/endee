"""
scraper_browser.py — Playwright-based fallback for when Naukri/LinkedIn block requests.

Use this when scraper.py gets 403/429 errors. Playwright renders JavaScript
and handles bot-detection more gracefully.

Install:
    pip install playwright
    playwright install chromium

Usage:
    python scraper_browser.py --location "Bengaluru" --pages 3 --output jobs.json
"""

import asyncio
import json
import re
import logging
import argparse
import random
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SKILL_PATTERNS = [
    r"\bPython\b", r"\bJava\b", r"\bJavaScript\b", r"\bTypeScript\b",
    r"\bReact(?:\.js)?\b", r"\bVue(?:\.js)?\b", r"\bAngular\b",
    r"\bNode(?:\.js)?\b", r"\bDjango\b", r"\bFlask\b", r"\bFastAPI\b",
    r"\bSpring(?:\s*Boot)?\b", r"\bKubernetes\b", r"\bDocker\b",
    r"\bAWS\b", r"\bGCP\b", r"\bAzure\b", r"\bSQL\b", r"\bPostgreSQL\b",
    r"\bMySQL\b", r"\bMongoDB\b", r"\bRedis\b", r"\bKafka\b",
    r"\bTerraform\b", r"\bGit\b", r"\bCI/CD\b", r"\bHTML\b", r"\bCSS\b",
    r"\bGraphQL\b", r"\bREST(?:\s*API)?\b", r"\bMicroservices\b",
    r"\bMachine Learning\b", r"\bDeep Learning\b", r"\bTensorFlow\b",
    r"\bPyTorch\b", r"\bExpress(?:\.js)?\b", r"\bNext(?:\.js)?\b",
    r"\bGo(?:lang)?\b", r"\bRust\b", r"\bScala\b", r"\bKotlin\b",
    r"\bSwift\b", r"\bFlutter\b", r"\bReact Native\b",
]


def extract_skills(text: str) -> list[str]:
    found, seen = [], set()
    for p in SKILL_PATTERNS:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            s = m.group().strip()
            if s.lower() not in seen:
                seen.add(s.lower())
                found.append(s)
    return found


def infer_job_type(text: str) -> str:
    t = text.lower()
    if "remote" in t:
        return "Remote"
    if "hybrid" in t:
        return "Hybrid"
    if "onsite" in t or "on-site" in t:
        return "Onsite"
    return "Not specified"


async def scrape_naukri_browser(
    location: str, keywords: list[str], max_pages: int
) -> list[dict]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return []

    jobs: list[dict] = []
    seen_urls: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()
        # Block images/fonts to speed up
        await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda r: r.abort())

        for kw in keywords:
            for pg in range(1, max_pages + 1):
                kw_slug = kw.replace(" ", "-")
                loc_slug = location.lower().replace(" ", "-")
                url = f"https://www.naukri.com/{kw_slug}-jobs-in-{loc_slug}-{pg}"
                log.info("Naukri browser → %s (page %d)", kw, pg)

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000 + random.randint(500, 1500))
                except Exception as exc:
                    log.warning("Page load failed: %s", exc)
                    break

                # Each job card
                cards = await page.query_selector_all("article.jobTuple")
                if not cards:
                    cards = await page.query_selector_all("div.srp-jobtuple-wrapper")

                if not cards:
                    log.info("No job cards found on page %d", pg)
                    break

                for card in cards:
                    try:
                        title_el = await card.query_selector("a.title")
                        company_el = await card.query_selector("a.subTitle")
                        exp_el = await card.query_selector("li.experience span.ellipsis")
                        loc_el = await card.query_selector("li.location span.ellipsis")
                        skills_els = await card.query_selector_all("li.tag-li")
                        desc_el = await card.query_selector("div.job-description")

                        title = await title_el.inner_text() if title_el else kw.title()
                        company = await company_el.inner_text() if company_el else ""
                        exp = await exp_el.inner_text() if exp_el else "Not specified"
                        loc = await loc_el.inner_text() if loc_el else location
                        desc = await desc_el.inner_text() if desc_el else ""
                        skill_texts = [await el.inner_text() for el in skills_els]
                        href = await title_el.get_attribute("href") if title_el else ""

                        all_text = f"{title} {' '.join(skill_texts)} {desc}"
                        skills = skill_texts if skill_texts else extract_skills(all_text)

                        if href and href not in seen_urls:
                            seen_urls.add(href)
                            jobs.append({
                                "title": title.strip(),
                                "company": company.strip(),
                                "location": loc.strip(),
                                "job_type": infer_job_type(all_text),
                                "experience": exp.strip(),
                                "skills": [s.strip() for s in skills[:12]],
                                "description": desc.strip()[:300],
                                "url": href,
                                "source": "naukri",
                            })
                    except Exception as exc:
                        log.debug("Card parse error: %s", exc)

                log.info("  Collected %d Naukri jobs so far", len(jobs))
                await page.wait_for_timeout(random.randint(1500, 3000))

        await browser.close()
    return jobs


async def scrape_linkedin_browser(
    location: str, keywords: list[str], max_pages: int
) -> list[dict]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []

    jobs: list[dict] = []
    seen_ids: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = await ctx.new_page()
        await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda r: r.abort())

        for kw in keywords:
            for pg in range(max_pages):
                start = pg * 25
                url = (
                    f"https://www.linkedin.com/jobs/search/"
                    f"?keywords={kw.replace(' ', '%20')}"
                    f"&location={location.replace(' ', '%20')}"
                    f"&start={start}"
                )
                log.info("LinkedIn browser → %s (page %d)", kw, pg + 1)

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                except Exception as exc:
                    log.warning("LinkedIn page load failed: %s", exc)
                    break

                cards = await page.query_selector_all("ul.jobs-search__results-list li")
                if not cards:
                    break

                for card in cards:
                    try:
                        title_el = await card.query_selector("h3.base-search-card__title")
                        company_el = await card.query_selector("h4.base-search-card__subtitle")
                        loc_el = await card.query_selector("span.job-search-card__location")
                        link_el = await card.query_selector("a.base-card__full-link")

                        title = await title_el.inner_text() if title_el else ""
                        company = await company_el.inner_text() if company_el else ""
                        loc = await loc_el.inner_text() if loc_el else location
                        href = await link_el.get_attribute("href") if link_el else ""

                        jid_match = re.search(r"/(\d+)\?", href or "")
                        if not jid_match:
                            continue
                        jid = jid_match.group(1)
                        if jid in seen_ids:
                            continue
                        seen_ids.add(jid)

                        # Fetch detail page
                        detail_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jid}"
                        detail_page = await ctx.new_page()
                        try:
                            await detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=20000)
                            desc_el = await detail_page.query_selector("div.show-more-less-html__markup")
                            desc = await desc_el.inner_text() if desc_el else ""
                        except Exception:
                            desc = ""
                        finally:
                            await detail_page.close()

                        all_text = f"{title} {desc}"
                        skills = extract_skills(all_text)

                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "job_type": infer_job_type(all_text),
                            "experience": "Not specified",
                            "skills": skills[:12],
                            "description": desc.strip()[:300],
                            "url": href.split("?")[0] if href else "",
                            "source": "linkedin",
                        })
                        await page.wait_for_timeout(random.randint(800, 1800))
                    except Exception as exc:
                        log.debug("Card error: %s", exc)

                log.info("  Collected %d LinkedIn jobs so far", len(jobs))

        await browser.close()
    return jobs


async def main_async(args):
    all_jobs = []

    if "naukri" in args.sources:
        log.info("=== Browser scraping Naukri ===")
        kws = args.keywords or ["software engineer", "python developer", "full stack"]
        naukri_jobs = await scrape_naukri_browser(args.location, kws, args.pages)
        log.info("Naukri: %d jobs", len(naukri_jobs))
        all_jobs.extend(naukri_jobs)

    if "linkedin" in args.sources:
        log.info("=== Browser scraping LinkedIn ===")
        kws = args.keywords or ["software engineer", "data engineer", "frontend developer"]
        li_jobs = await scrape_linkedin_browser(
            f"{args.location}, Karnataka, India", kws, args.pages
        )
        log.info("LinkedIn: %d jobs", len(li_jobs))
        all_jobs.extend(li_jobs)

    # Deduplicate
    seen, unique = set(), []
    for j in all_jobs:
        key = (j["title"].lower(), j["company"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(j)

    output = {
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "total": len(unique),
        "jobs": unique,
    }
    Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False))
    log.info("✅ Saved %d jobs → %s", len(unique), args.output)


def main():
    parser = argparse.ArgumentParser(description="Browser-based Tech Job Scraper")
    parser.add_argument("--location", default="Bengaluru")
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--output", default="tech_jobs.json")
    parser.add_argument("--sources", nargs="+", choices=["naukri", "linkedin"], default=["naukri", "linkedin"])
    parser.add_argument("--keywords", nargs="+", default=None)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
