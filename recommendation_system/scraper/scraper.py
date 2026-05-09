"""
Tech Job Scraper — Naukri.com & LinkedIn
=========================================
Scrapes tech jobs and saves to JSON format for a recommendation system.

Usage:
    python scraper.py [--location "Bengaluru"] [--pages 5] [--output jobs.json]
    python scraper.py --demo                     # Generate sample data (no network)

Requirements:
    pip install requests beautifulsoup4 lxml
    # Browser fallback: pip install playwright && playwright install chromium
"""

import json
import time
import random
import logging
import argparse
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

TECH_KEYWORDS = [
    "software engineer", "python developer", "java developer", "full stack",
    "frontend developer", "backend developer", "data engineer", "ml engineer",
    "devops engineer", "cloud engineer", "react developer", "node.js developer",
    "data scientist", "android developer", "ios developer", "web developer",
    "software developer", "sde", "tech lead", "engineering manager",
]

SKILL_PATTERNS = [
    r"\bPython\b", r"\bJava\b", r"\bJavaScript\b", r"\bTypeScript\b",
    r"\bReact(?:\.js)?\b", r"\bVue(?:\.js)?\b", r"\bAngular\b",
    r"\bNode(?:\.js)?\b", r"\bDjango\b", r"\bFlask\b", r"\bFastAPI\b",
    r"\bSpring(?:\s*Boot)?\b", r"\bKubernetes\b", r"\bDocker\b",
    r"\bAWS\b", r"\bGCP\b", r"\bAzure\b", r"\bSQL\b", r"\bPostgreSQL\b",
    r"\bMySQL\b", r"\bMongoDB\b", r"\bRedis\b", r"\bKafka\b",
    r"\bTerraform\b", r"\bGit(?:Hub|Lab)?\b", r"\bCI/CD\b",
    r"\bHTML\b", r"\bCSS\b", r"\bBootstrap\b", r"\bTailwind\b",
    r"\bGraphQL\b", r"\bREST(?:\s*API)?\b", r"\bMicroservices\b",
    r"\bMachine Learning\b", r"\bDeep Learning\b", r"\bTensorFlow\b",
    r"\bPyTorch\b", r"\bLLM\b", r"\bOpenAI\b", r"\bLangChain\b",
    r"\bExpress(?:\.js)?\b", r"\bNext(?:\.js)?\b", r"\bNuxt(?:\.js)?\b",
    r"\bRuby\b", r"\bGo(?:lang)?\b", r"\bRust\b", r"\bScala\b",
    r"\bC\+\+\b", r"\bC#\b", r"\bSwift\b", r"\bKotlin\b",
    r"\bAndroid\b", r"\biOS\b", r"\bFlutter\b", r"\bReact Native\b",
    r"\bElastic(?:search)?\b", r"\bSpark\b", r"\bHadoop\b",
    r"\bLinux\b", r"\bBash\b", r"\bAnsible\b", r"\bJenkins\b",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def random_headers(referer: str = "https://www.google.com/") -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,en-IN;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": referer,
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Cache-Control": "max-age=0",
    }


def extract_skills(text: str) -> list:
    found, seen = [], set()
    for pattern in SKILL_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            s = m.group().strip()
            if s.lower() not in seen:
                seen.add(s.lower())
                found.append(s)
    return found


def infer_job_type(text: str) -> str:
    t = text.lower()
    if "remote" in t and "hybrid" not in t:
        return "Remote"
    if "hybrid" in t:
        return "Hybrid"
    if "onsite" in t or "on-site" in t or "work from office" in t or "wfo" in t:
        return "Onsite"
    return "Not specified"


def polite_sleep(min_s: float = 1.5, max_s: float = 4.0):
    time.sleep(random.uniform(min_s, max_s))


def get_with_retry(session, url: str, max_retries: int = 3, **kwargs):
    for attempt in range(max_retries):
        try:
            r = session.get(url, timeout=25, **kwargs)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 503):
                wait = 10 * (attempt + 1)
                log.warning("Rate-limited (HTTP %s). Waiting %ds…", r.status_code, wait)
                time.sleep(wait)
            else:
                log.warning("HTTP %s for %s", r.status_code, url)
                return None
        except requests.exceptions.ConnectionError:
            log.warning("Connection error (attempt %d) for %s", attempt + 1, url)
            time.sleep(5)
        except requests.exceptions.Timeout:
            log.warning("Timeout (attempt %d) for %s", attempt + 1, url)
    return None


# ── Naukri Scraper ───────────────────────────────────────────────────────────

class NaukriScraper:
    """
    Strategy 1 — JSON API (fastest):
        GET https://www.naukri.com/jobapi/v3/search?keyword=...&location=...

    Strategy 2 — HTML fallback:
        Parse search results page like a browser.
    """

    API_URL = "https://www.naukri.com/jobapi/v3/search"
    BASE = "https://www.naukri.com"

    def __init__(self, location: str = "Bengaluru", max_pages: int = 5):
        self.location = location
        self.max_pages = max_pages
        self.session = requests.Session()
        self._warm_up()

    def _warm_up(self):
        log.info("Warming up Naukri session…")
        self.session.headers.update(random_headers("https://www.google.com/"))
        get_with_retry(self.session, self.BASE, max_retries=2)
        polite_sleep(1.0, 2.0)
        self.session.headers.update({"appid": "109", "systemid": "Naukri"})

    def _api_params(self, keyword: str, page: int) -> dict:
        return {
            "noOfResults": 20,
            "urlType": "list_type",
            "searchType": "adv",
            "keyword": keyword,
            "location": self.location,
            "pageNo": page,
            "k": keyword,
            "l": self.location,
            "experience": "",
            "ctcFilter": "",
        }

    def _parse_api_job(self, raw: dict):
        try:
            title = raw.get("title", "").strip()
            company = raw.get("companyName", "").strip()
            placeholders = raw.get("placeholders", [])
            location = ", ".join(
                p.get("label", "") for p in placeholders if p.get("type") == "location"
            ) or self.location
            exp_list = [p.get("label", "") for p in placeholders if p.get("type") == "experience"]
            experience = exp_list[0] if exp_list else raw.get("experienceText", "Not specified")
            skill_tags = [t.get("label", "") for t in raw.get("tagsAndSkills", [])]
            description_html = raw.get("jobDescription", "")
            description = re.sub(r"<[^>]+>", " ", description_html)
            description = re.sub(r"\s+", " ", description).strip()[:300]
            all_text = f"{title} {' '.join(skill_tags)} {description}"
            skills = skill_tags if skill_tags else extract_skills(all_text)
            url = raw.get("jdURL", "") or f"https://www.naukri.com/job-listings-{raw.get('jobId','')}"
            return {
                "title": title,
                "company": company,
                "location": location,
                "job_type": infer_job_type(all_text),
                "experience": experience,
                "skills": [s.strip() for s in skills[:12] if s.strip()],
                "description": description or f"{title} role at {company}.",
                "url": url,
                "source": "naukri",
            }
        except Exception as exc:
            log.debug("API parse error: %s", exc)
            return None

    def _scrape_via_api(self, keyword: str) -> list:
        jobs, seen_urls = [], set()
        for page in range(1, self.max_pages + 1):
            r = get_with_retry(self.session, self.API_URL, params=self._api_params(keyword, page))
            if r is None:
                return []  # Blocked — signal fallback
            try:
                data = r.json()
            except ValueError:
                return []
            raw_list = data.get("jobDetails", [])
            if not raw_list:
                break
            for raw in raw_list:
                job = self._parse_api_job(raw)
                if job and job["url"] not in seen_urls:
                    seen_urls.add(job["url"])
                    jobs.append(job)
            log.info("  [Naukri API] page=%d kw='%s' → %d jobs", page, keyword, len(jobs))
            polite_sleep()
        return jobs

    def _scrape_via_html(self, keyword: str) -> list:
        jobs, seen_urls = [], set()
        kw_slug = keyword.strip().replace(" ", "-")
        loc_slug = self.location.lower().strip().replace(" ", "-")
        for page in range(1, self.max_pages + 1):
            url = f"{self.BASE}/{kw_slug}-jobs-in-{loc_slug}-{page}"
            log.info("  [Naukri HTML] %s", url)
            self.session.headers.update({"Referer": self.BASE + "/"})
            r = get_with_retry(self.session, url, max_retries=2)
            if r is None:
                break
            soup = BeautifulSoup(r.text, "lxml")
            cards = (
                soup.select("article.jobTuple")
                or soup.select("div.srp-jobtuple-wrapper")
                or soup.select("div.jobTupleHeader")
            )
            if not cards:
                log.info("  No job cards found in HTML on page %d", page)
                break
            for card in cards:
                try:
                    title_a = card.select_one("a.title") or card.select_one("a.jobTitle")
                    company_a = card.select_one("a.subTitle") or card.select_one("a.companyName")
                    exp_span = card.select_one("li.experience span, span.expwdth")
                    loc_span = card.select_one("li.location span, span.locwdth")
                    skill_lis = card.select("li.tag-li, span.tag-li")
                    desc_div = card.select_one("div.job-description, div.job-desc")
                    title = title_a.get_text(strip=True) if title_a else keyword.title()
                    href = title_a["href"] if title_a and title_a.get("href") else url
                    company = company_a.get_text(strip=True) if company_a else ""
                    exp = exp_span.get_text(strip=True) if exp_span else "Not specified"
                    loc = loc_span.get_text(strip=True) if loc_span else self.location
                    desc = desc_div.get_text(strip=True)[:300] if desc_div else ""
                    skill_texts = [s.get_text(strip=True) for s in skill_lis]
                    all_text = f"{title} {' '.join(skill_texts)} {desc}"
                    skills = skill_texts if skill_texts else extract_skills(all_text)
                    if href not in seen_urls:
                        seen_urls.add(href)
                        jobs.append({
                            "title": title, "company": company, "location": loc,
                            "job_type": infer_job_type(all_text), "experience": exp,
                            "skills": [s for s in skills[:12] if s],
                            "description": desc or f"{title} at {company}.",
                            "url": href, "source": "naukri",
                        })
                except Exception as exc:
                    log.debug("HTML card error: %s", exc)
            log.info("  [Naukri HTML] page=%d → %d jobs", page, len(jobs))
            polite_sleep(2.0, 4.0)
        return jobs

    def scrape(self, keywords=None) -> list:
        if keywords is None:
            keywords = TECH_KEYWORDS[:8]
        all_jobs, seen_urls = [], set()
        for kw in keywords:
            log.info("Naukri → '%s'", kw)
            jobs = self._scrape_via_api(kw) or self._scrape_via_html(kw)
            for j in jobs:
                if j["url"] not in seen_urls:
                    seen_urls.add(j["url"])
                    all_jobs.append(j)
        return all_jobs


# ── LinkedIn Scraper ─────────────────────────────────────────────────────────

class LinkedInScraper:
    """
    Uses LinkedIn's public (unauthenticated) guest endpoints — no login needed.
      - /jobs-guest/jobs/api/seeMoreJobPostings/search → listing cards
      - /jobs-guest/jobs/api/jobPosting/{id}          → job detail
    """

    LIST_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    GEO_IDS = {
        "bengaluru": "115145543", "hyderabad": "114187078", "mumbai": "113993",
        "delhi": "105218", "pune": "110550", "chennai": "109546", "india": "102713980",
    }

    def __init__(self, location: str = "Bengaluru, Karnataka, India", max_pages: int = 3):
        self.location = location
        self.max_pages = max_pages
        geo_key = location.lower().split(",")[0].strip()
        self.geo_id = self.GEO_IDS.get(geo_key, self.GEO_IDS["india"])
        self.session = requests.Session()
        self.session.headers.update(random_headers("https://www.linkedin.com/jobs/"))

    def _list_jobs(self, keyword: str, start: int) -> list:
        params = {
            "keywords": keyword, "location": self.location,
            "geoId": self.geo_id, "start": start, "count": 25,
        }
        r = get_with_retry(self.session, self.LIST_URL, params=params, max_retries=2)
        if r is None:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        results = []
        for li in soup.select("li"):
            a = li.find("a", class_=re.compile(r"base-card__full-link"))
            if not a:
                continue
            href = a.get("href", "")
            m = re.search(r"/(\d+)\?", href)
            if m:
                results.append({"id": m.group(1), "url": href.split("?")[0]})
        return results

    def _fetch_detail(self, job_id: str, url: str):
        r = get_with_retry(
            self.session, self.DETAIL_URL.format(job_id=job_id), max_retries=2
        )
        if r is None:
            return None
        soup = BeautifulSoup(r.text, "lxml")

        def txt(selector: str, default: str = "") -> str:
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else default

        title = txt("h2.top-card-layout__title, h1.top-card-layout__title")
        company = txt("a.topcard__org-name-link, span.topcard__flavor")
        location = txt("span.topcard__flavor--bullet")
        seniority, emp_type = "", ""
        for li in soup.select("li.description__job-criteria-item"):
            h = li.find("h3")
            v = li.find("span")
            if not h or not v:
                continue
            ht = h.get_text(strip=True).lower()
            vt = v.get_text(strip=True)
            if "seniority" in ht:
                seniority = vt
            elif "employment" in ht:
                emp_type = vt
        desc_el = soup.select_one("div.show-more-less-html__markup")
        desc = desc_el.get_text(" ", strip=True)[:300] if desc_el else ""
        all_text = f"{title} {desc} {emp_type}"
        skills = extract_skills(all_text)
        return {
            "title": title or "Tech Role", "company": company,
            "location": location or self.location,
            "job_type": infer_job_type(all_text),
            "experience": seniority or "Not specified",
            "skills": skills[:12],
            "description": desc or f"{title} at {company}.",
            "url": url, "source": "linkedin",
        }

    def scrape(self, keywords=None) -> list:
        if keywords is None:
            keywords = ["software engineer", "python developer", "full stack developer"]
        all_jobs, seen_ids = [], set()
        for kw in keywords:
            log.info("LinkedIn → '%s'", kw)
            for page in range(self.max_pages):
                listings = self._list_jobs(kw, page * 25)
                if not listings:
                    break
                for item in listings:
                    jid = item["id"]
                    if jid in seen_ids:
                        continue
                    seen_ids.add(jid)
                    detail = self._fetch_detail(jid, item["url"])
                    if detail:
                        all_jobs.append(detail)
                    polite_sleep(1.0, 2.5)
                log.info("  page=%d → %d LinkedIn jobs", page + 1, len(all_jobs))
                polite_sleep(2.0, 3.5)
        return all_jobs


# ── Demo Data ────────────────────────────────────────────────────────────────

DEMO_JOBS = [
    {
        "title": "Web Development Intern",
        "company": "Corporate Web Solutions",
        "location": "Bengaluru",
        "job_type": "Hybrid",
        "experience": "Internship",
        "skills": ["HTML", "CSS", "JavaScript", "Bootstrap", "Frontend Development", "Responsive Design", "Git"],
        "description": "Internship involving web page creation and responsive website development.",
        "url": "https://www.naukri.com/job-listings-web-development-intern-corporate-web-solutions-bengaluru-0-to-1-years-160525501891",
        "source": "naukri",
    },
    {
        "title": "Web Developer Intern",
        "company": "Stellentcg",
        "location": "Kannur, Bengaluru",
        "job_type": "Remote",
        "experience": "Internship",
        "skills": ["HTML", "CSS", "JavaScript", "React", "Node.js", "Frontend Development", "Git"],
        "description": "3-month web developer internship for fresher candidates.",
        "url": "https://www.naukri.com/job-listings-opening-for-web-developer-interns-stellent-kannur-bengaluru-0-to-1-years-131224502426",
        "source": "naukri",
    },
    {
        "title": "Web Developer Intern",
        "company": "Sakthi Cadd",
        "location": "Bengaluru",
        "job_type": "Onsite",
        "experience": "Internship",
        "skills": ["HTML", "CSS", "JavaScript", "Frontend Development", "Web Design", "Responsive UI"],
        "description": "Web development internship focused on frontend implementation.",
        "url": "https://www.naukri.com/job-listings-web-developer-intern-sakthicadd-bengaluru-0-to-1-years-121125503975",
        "source": "naukri",
    },
    {
        "title": "Python Developer Remote Intern",
        "company": "Gigafactor Solutions",
        "location": "Remote / Bengaluru",
        "job_type": "Remote",
        "experience": "Internship",
        "skills": ["Python", "Flask", "FastAPI", "SQL", "Backend Development", "REST APIs", "Git"],
        "description": "Remote Python internship involving backend development.",
        "url": "https://www.naukri.com/job-listings-python-developer-remote-interns-gigafactor-solutions-bengaluru-0-to-1-years-300126501873",
        "source": "naukri",
    },
    {
        "title": "Full Stack Developer Internship",
        "company": "Webin Technovation",
        "location": "Bengaluru, Kolkata, Mumbai",
        "job_type": "Hybrid (3 days)",
        "experience": "Internship",
        "skills": ["HTML", "CSS", "JavaScript", "React", "Node.js", "MongoDB", "Express.js", "REST API"],
        "description": "Full stack internship covering frontend and backend technologies.",
        "url": "https://www.naukri.com/job-listings-full-stack-developer-internship-webin-technovation-pvt-ltd-161224503231",
        "source": "naukri",
    },
    {
        "title": "Python Developer",
        "company": "DataTech Innovations",
        "location": "Bengaluru",
        "job_type": "Hybrid",
        "experience": "2-5 Years",
        "skills": ["Python", "Django", "FastAPI", "PostgreSQL", "Docker", "AWS", "REST API"],
        "description": "Build scalable backend services and REST APIs using Python and modern frameworks.",
        "url": "https://www.naukri.com/job-listings-python-developer-datatech-bengaluru",
        "source": "naukri",
    },
    {
        "title": "React Developer",
        "company": "FinEdge Technologies",
        "location": "Bengaluru",
        "job_type": "Onsite",
        "experience": "1-3 Years",
        "skills": ["React", "TypeScript", "Redux", "Tailwind CSS", "REST API", "Git", "Jest"],
        "description": "Develop and maintain high-performance React applications for financial dashboards.",
        "url": "https://www.linkedin.com/jobs/view/react-developer-finedge-bengaluru",
        "source": "linkedin",
    },
    {
        "title": "Machine Learning Engineer",
        "company": "AI Dynamics Labs",
        "location": "Bengaluru",
        "job_type": "Hybrid",
        "experience": "3-7 Years",
        "skills": ["Python", "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning", "AWS", "MLflow"],
        "description": "Design and deploy ML models for NLP and computer vision applications at scale.",
        "url": "https://www.naukri.com/job-listings-ml-engineer-ai-dynamics-bengaluru",
        "source": "naukri",
    },
    {
        "title": "DevOps Engineer",
        "company": "CloudNative Systems",
        "location": "Bengaluru",
        "job_type": "Remote",
        "experience": "2-4 Years",
        "skills": ["Kubernetes", "Docker", "AWS", "Terraform", "Jenkins", "CI/CD", "Linux", "Ansible"],
        "description": "Manage cloud infrastructure and CI/CD pipelines for microservices-based applications.",
        "url": "https://www.linkedin.com/jobs/view/devops-engineer-cloudnative-bengaluru",
        "source": "linkedin",
    },
    {
        "title": "Backend Engineer — Java",
        "company": "PayStream Solutions",
        "location": "Bengaluru",
        "job_type": "Onsite",
        "experience": "3-6 Years",
        "skills": ["Java", "Spring Boot", "Microservices", "Kafka", "Redis", "PostgreSQL", "Docker", "AWS"],
        "description": "Build high-throughput payment processing microservices with Java and Spring Boot.",
        "url": "https://www.naukri.com/job-listings-backend-engineer-java-paystream-bengaluru",
        "source": "naukri",
    },
    {
        "title": "Data Engineer",
        "company": "Analytix Corp",
        "location": "Bengaluru",
        "job_type": "Remote",
        "experience": "2-5 Years",
        "skills": ["Python", "Spark", "Hadoop", "SQL", "Kafka", "AWS", "Airflow", "dbt"],
        "description": "Build and maintain large-scale data pipelines and ETL systems for analytics.",
        "url": "https://www.naukri.com/job-listings-data-engineer-analytix-bengaluru",
        "source": "naukri",
    },
    {
        "title": "Android Developer",
        "company": "Mobzoid Apps",
        "location": "Bengaluru",
        "job_type": "Hybrid",
        "experience": "1-3 Years",
        "skills": ["Android", "Kotlin", "Jetpack Compose", "REST API", "Firebase", "Git", "MVVM"],
        "description": "Develop and ship native Android apps using Kotlin and modern Android architecture.",
        "url": "https://www.linkedin.com/jobs/view/android-developer-mobzoid-bengaluru",
        "source": "linkedin",
    },
    {
        "title": "SDE-2 — Full Stack",
        "company": "Flipkart",
        "location": "Bengaluru",
        "job_type": "Hybrid",
        "experience": "3-6 Years",
        "skills": ["Java", "React", "Node.js", "MySQL", "Redis", "Kafka", "AWS", "Microservices"],
        "description": "Build and scale large-scale ecommerce features across Flipkart's platform.",
        "url": "https://www.linkedin.com/jobs/view/sde2-fullstack-flipkart-bengaluru",
        "source": "linkedin",
    },
    {
        "title": "Cloud Infrastructure Engineer",
        "company": "Infosys",
        "location": "Bengaluru",
        "job_type": "Onsite",
        "experience": "2-4 Years",
        "skills": ["AWS", "Azure", "Terraform", "Kubernetes", "Docker", "Python", "CI/CD"],
        "description": "Design and manage cloud infrastructure solutions for enterprise clients.",
        "url": "https://www.naukri.com/job-listings-cloud-infra-engineer-infosys-bengaluru",
        "source": "naukri",
    },
    {
        "title": "Frontend Developer",
        "company": "Swiggy",
        "location": "Bengaluru",
        "job_type": "Hybrid",
        "experience": "2-5 Years",
        "skills": ["React", "TypeScript", "Next.js", "CSS", "GraphQL", "Jest", "Webpack"],
        "description": "Build performant and accessible web interfaces for Swiggy's consumer products.",
        "url": "https://www.linkedin.com/jobs/view/frontend-developer-swiggy-bengaluru",
        "source": "linkedin",
    },
]


def generate_demo_jobs(location: str = "Bengaluru") -> list:
    return DEMO_JOBS


# ── Deduplication & Cleaning ─────────────────────────────────────────────────

def deduplicate(jobs: list) -> list:
    seen, unique = set(), []
    for job in jobs:
        key = (job.get("title", "").lower(), job.get("company", "").lower())
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def clean_job(j: dict) -> dict:
    j.setdefault("title", "Unknown Role")
    j.setdefault("company", "Unknown Company")
    j.setdefault("location", "India")
    j.setdefault("job_type", "Not specified")
    j.setdefault("experience", "Not specified")
    j.setdefault("skills", [])
    j.setdefault("description", "")
    j.setdefault("url", "")
    j.setdefault("source", "unknown")
    return j


# ── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Tech Job Scraper — Naukri & LinkedIn",
    )
    parser.add_argument("--location", default="Bengaluru", help="Target city")
    parser.add_argument("--pages", type=int, default=3, help="Pages per keyword")
    parser.add_argument("--output", default="tech_jobs.json", help="Output JSON file")
    parser.add_argument(
        "--sources", nargs="+", choices=["naukri", "linkedin"],
        default=["naukri", "linkedin"],
    )
    parser.add_argument("--keywords", nargs="+", default=None)
    parser.add_argument(
        "--demo", action="store_true",
        help="Generate sample JSON without network calls (useful for pipeline testing)",
    )
    args = parser.parse_args()

    if args.demo:
        log.info("Demo mode — generating sample data (no network calls)")
        jobs = generate_demo_jobs(args.location)
    else:
        all_jobs: list = []
        if "naukri" in args.sources:
            log.info("=== Scraping Naukri.com ===")
            scraper = NaukriScraper(location=args.location, max_pages=args.pages)
            nj = scraper.scrape(args.keywords)
            log.info("Naukri: %d jobs found", len(nj))
            all_jobs.extend(nj)
        if "linkedin" in args.sources:
            log.info("=== Scraping LinkedIn ===")
            scraper = LinkedInScraper(
                location=f"{args.location}, Karnataka, India",
                max_pages=args.pages,
            )
            lj = scraper.scrape(args.keywords)
            log.info("LinkedIn: %d jobs found", len(lj))
            all_jobs.extend(lj)
        jobs = [clean_job(j) for j in deduplicate(all_jobs)]
        if not jobs:
            log.warning("No jobs scraped — sites may be blocking requests.")
            log.warning("Try:  python scraper_browser.py  (Playwright fallback)")
            log.warning("Or:   python scraper.py --demo   (sample data)")

    output = {
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "total": len(jobs),
        "location": args.location,
        "jobs": jobs,
    }
    out_path = Path(args.output)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    log.info("Saved %d jobs → %s", len(jobs), out_path)


if __name__ == "__main__":
    main()
