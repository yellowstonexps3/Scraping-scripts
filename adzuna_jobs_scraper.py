#!/usr/bin/env python3
"""
Selenium job scraper for Adzuna listings across multiple countries.

Example:
  python adzuna_jobs_scraper.py \
    --query "film industry" \
    --countries "United States,United Kingdom,Canada" \
    --max-pages 3 \
    --output film_industry_jobs_worldwide.csv
"""

import argparse
import csv
import random
import sys
import time
from datetime import datetime
from urllib.parse import quote_plus, urljoin

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

ADZUNA_DOMAINS = {
    "United States": "https://www.adzuna.com",
    "United Kingdom": "https://www.adzuna.co.uk",
    "India": "https://www.adzuna.co.in",
    "Canada": "https://www.adzuna.ca",
    "Australia": "https://www.adzuna.com.au",
    "Germany": "https://www.adzuna.de",
    "France": "https://www.adzuna.fr",
}

CARD_SELECTORS = ["article", "div[data-type='job']"]

FIELDNAMES = [
    "job_title",
    "company",
    "location",
    "summary",
    "job_url",
    "country",
    "scraped_at",
    "source",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Adzuna job listings across multiple countries."
    )
    parser.add_argument(
        "--query",
        default="film industry",
        help="Search query for job titles and keywords.",
    )
    parser.add_argument(
        "--countries",
        default=",".join(ADZUNA_DOMAINS.keys()),
        help="Comma-separated list of countries to scrape.",
    )
    parser.add_argument(
        "--countries-file",
        help="Path to a text file with one country per line.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Number of search result pages to scrape per country.",
    )
    parser.add_argument(
        "--output",
        default="film_industry_jobs_worldwide.csv",
        help="Output CSV filename.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome in headless mode (disabled by default).",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=2.0,
        help="Minimum delay between page requests in seconds.",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=4.0,
        help="Maximum delay between page requests in seconds.",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="Custom user agent string for Chrome.",
    )
    parser.add_argument(
        "--page-load-timeout",
        type=int,
        default=30,
        help="Page load timeout in seconds.",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=12,
        help="Wait timeout for job cards in seconds.",
    )
    return parser.parse_args()


def normalize_text(value: str) -> str:
    return " ".join(value.split()) if value else ""


def resolve_countries(args: argparse.Namespace) -> list:
    values = []
    if args.countries_file:
        with open(args.countries_file, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    values.append(line)
    if args.countries:
        values.extend([value.strip() for value in args.countries.split(",") if value.strip()])
    deduped = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def build_driver(headless: bool, user_agent: str, page_load_timeout: int) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    if user_agent:
        options.add_argument(f"--user-agent={user_agent}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(page_load_timeout)
    return driver


def maybe_accept_cookies(driver: webdriver.Chrome) -> None:
    selectors = [
        "button#onetrust-accept-btn-handler",
        "button[aria-label='Accept cookies']",
        "button[data-testid='accept-cookie']",
    ]
    for selector in selectors:
        try:
            button = driver.find_element(By.CSS_SELECTOR, selector)
            button.click()
            return
        except NoSuchElementException:
            continue


def build_search_url(base_url: str, query: str, page: int) -> str:
    query_param = quote_plus(query)
    return f"{urljoin(base_url, '/search')}?q={query_param}&p={page}"


def get_text(parent, selectors) -> str:
    for selector in selectors:
        try:
            element = parent.find_element(By.CSS_SELECTOR, selector)
            text = normalize_text(element.text)
            if text:
                return text
        except NoSuchElementException:
            continue
    return ""


def get_job_cards(driver: webdriver.Chrome) -> list:
    for selector in CARD_SELECTORS:
        cards = driver.find_elements(By.CSS_SELECTOR, selector)
        if cards:
            return cards
    return []


def wait_for_job_cards(driver: webdriver.Chrome, timeout: int) -> list:
    try:
        WebDriverWait(driver, timeout).until(lambda d: bool(get_job_cards(d)))
    except TimeoutException:
        return []
    return get_job_cards(driver)


def extract_job(card, base_url: str, country: str) -> dict:
    title = get_text(card, ["h2 a", "h2", "a"])
    company = get_text(card, [".ui-company", ".company", ".job-card__company"])
    location = get_text(card, [".ui-location", ".location", ".job-card__location"])
    summary = get_text(card, [".ui-description", ".description", ".job-card__description", "p"])

    job_url = ""
    for selector in ["h2 a", "a"]:
        try:
            href = card.find_element(By.CSS_SELECTOR, selector).get_attribute("href")
            if href:
                job_url = urljoin(base_url, href)
                break
        except NoSuchElementException:
            continue

    return {
        "job_title": title,
        "company": company,
        "location": location,
        "summary": summary,
        "job_url": job_url,
        "country": country,
        "scraped_at": datetime.utcnow().isoformat(),
        "source": "Adzuna (HTML)",
    }


def scrape_country(
    driver: webdriver.Chrome,
    writer: csv.DictWriter,
    query: str,
    country: str,
    base_url: str,
    max_pages: int,
    delay_min: float,
    delay_max: float,
    wait_timeout: int,
) -> int:
    print(f"\nScraping {country}", flush=True)
    captured = 0

    for page in range(1, max_pages + 1):
        url = build_search_url(base_url, query, page)
        print(f"Loading: {url}", flush=True)
        driver.get(url)
        time.sleep(2)
        maybe_accept_cookies(driver)

        cards = wait_for_job_cards(driver, wait_timeout)
        if not cards:
            print("No jobs found.", flush=True)
            break

        for card in cards:
            job = extract_job(card, base_url, country)
            if not job["job_title"]:
                continue
            writer.writerow(job)
            captured += 1

        time.sleep(random.uniform(delay_min, delay_max))

    return captured


def main() -> int:
    args = parse_args()
    if args.max_pages < 1:
        print("max-pages must be >= 1", file=sys.stderr)
        return 2
    if args.page_load_timeout < 1:
        print("page-load-timeout must be >= 1", file=sys.stderr)
        return 2
    if args.wait_timeout < 1:
        print("wait-timeout must be >= 1", file=sys.stderr)
        return 2

    countries = resolve_countries(args)
    if not countries:
        print("No countries provided.", file=sys.stderr)
        return 2

    missing = [country for country in countries if country not in ADZUNA_DOMAINS]
    if missing:
        print(
            "Unsupported countries (skipped): " + ", ".join(missing),
            file=sys.stderr,
        )
    countries = [country for country in countries if country in ADZUNA_DOMAINS]
    if not countries:
        print("No supported countries provided.", file=sys.stderr)
        return 2

    driver = build_driver(args.headless, args.user_agent, args.page_load_timeout)
    try:
        with open(args.output, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()

            for country in countries:
                base_url = ADZUNA_DOMAINS[country]
                captured = scrape_country(
                    driver=driver,
                    writer=writer,
                    query=args.query,
                    country=country,
                    base_url=base_url,
                    max_pages=args.max_pages,
                    delay_min=args.delay_min,
                    delay_max=args.delay_max,
                    wait_timeout=args.wait_timeout,
                )
                print(f"Captured {captured} jobs for {country}", flush=True)
    finally:
        driver.quit()

    print(f"Done. Saved results to {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
