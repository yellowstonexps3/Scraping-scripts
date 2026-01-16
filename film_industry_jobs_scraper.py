#!/usr/bin/env python3
"""
Selenium job scraper for film industry roles on Indeed.

Example:
  python film_industry_jobs_scraper.py \
    --query "film industry" \
    --locations "Worldwide,United States,United Kingdom" \
    --max-pages 3 \
    --output film_industry_jobs.csv

Requirements:
  pip install selenium webdriver-manager
  Google Chrome installed locally.
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
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

INDEED_BASE_URL = "https://www.indeed.com"
INDEED_SEARCH_URL = "https://www.indeed.com/jobs"

FIELDNAMES = [
    "search_query",
    "search_location",
    "job_title",
    "company",
    "location",
    "date_posted",
    "salary",
    "summary",
    "description",
    "job_url",
    "source",
    "scraped_at",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape film industry jobs worldwide using Selenium."
    )
    parser.add_argument(
        "--query",
        default="film industry",
        help="Search query for job titles and keywords.",
    )
    parser.add_argument(
        "--locations",
        default="Worldwide",
        help="Comma-separated list of locations to search.",
    )
    parser.add_argument(
        "--locations-file",
        help="Path to a text file with one location per line.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Number of search result pages to scrape per location.",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=0,
        help="Stop after this many jobs per location (0 = no limit).",
    )
    parser.add_argument(
        "--output",
        default="film_industry_jobs.csv",
        help="Output CSV filename.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome in headless mode (disabled by default).",
    )
    parser.add_argument(
        "--fetch-description",
        action="store_true",
        help="Open each job post and capture full description.",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=1.5,
        help="Minimum delay between page requests in seconds.",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=2.8,
        help="Maximum delay between page requests in seconds.",
    )
    return parser.parse_args()


def build_search_url(query: str, location: str, start: int) -> str:
    params = f"q={quote_plus(query)}&l={quote_plus(location)}&start={start}"
    return f"{INDEED_SEARCH_URL}?{params}"


def normalize_text(value: str) -> str:
    return " ".join(value.split()) if value else ""


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


def get_summary(parent) -> str:
    summary_selector = "div.job-snippet"
    try:
        snippet = parent.find_element(By.CSS_SELECTOR, summary_selector)
        return normalize_text(snippet.text)
    except NoSuchElementException:
        return ""


def maybe_accept_cookies(driver: webdriver.Chrome) -> None:
    selectors = [
        "button#onetrust-accept-btn-handler",
        "button[data-testid='accept-cookie']",
        "button[aria-label='Accept cookies']",
    ]
    for selector in selectors:
        try:
            button = driver.find_element(By.CSS_SELECTOR, selector)
            button.click()
            return
        except NoSuchElementException:
            continue


def fetch_description(driver: webdriver.Chrome, job_url: str) -> str:
    if not job_url:
        return ""

    original_window = driver.current_window_handle
    driver.execute_script("window.open(arguments[0], '_blank');", job_url)
    driver.switch_to.window(driver.window_handles[-1])
    description_text = ""
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#jobDescriptionText"))
        )
        description = driver.find_element(By.CSS_SELECTOR, "#jobDescriptionText")
        description_text = normalize_text(description.text)
    except TimeoutException:
        description_text = ""
    finally:
        driver.close()
        driver.switch_to.window(original_window)

    return description_text


def extract_job(card, query, location, fetch_full_description, driver) -> dict:
    job_title = get_text(card, ["h2.jobTitle span", "a[data-jk]"])
    company = get_text(card, ["span.companyName"])
    job_location = get_text(card, ["div.companyLocation"])
    date_posted = get_text(card, ["span.date", "span.datePosted"])
    salary = get_text(card, ["div.metadata.salary-snippet-container", "div.salary-snippet"])
    summary = get_summary(card)

    job_url = ""
    try:
        link = card.find_element(By.CSS_SELECTOR, "h2.jobTitle a")
        href = link.get_attribute("href")
        job_url = urljoin(INDEED_BASE_URL, href) if href else ""
    except NoSuchElementException:
        job_url = ""

    description = ""
    if fetch_full_description:
        description = fetch_description(driver, job_url)

    return {
        "search_query": query,
        "search_location": location,
        "job_title": job_title,
        "company": company,
        "location": job_location,
        "date_posted": date_posted,
        "salary": salary,
        "summary": summary,
        "description": description,
        "job_url": job_url,
        "source": "Indeed",
        "scraped_at": datetime.utcnow().isoformat(),
    }


def wait_for_job_cards(driver: webdriver.Chrome) -> list:
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.job_seen_beacon"))
        )
    except TimeoutException:
        return []
    return driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")


def scrape_location(
    driver: webdriver.Chrome,
    query: str,
    location: str,
    max_pages: int,
    max_jobs: int,
    fetch_full_description: bool,
    delay_min: float,
    delay_max: float,
    seen_urls: set,
) -> list:
    results = []
    for page in range(max_pages):
        start = page * 10
        search_url = build_search_url(query, location, start)
        print(f"Loading: {search_url}", flush=True)
        driver.get(search_url)
        time.sleep(2)
        maybe_accept_cookies(driver)
        cards = wait_for_job_cards(driver)
        if not cards:
            print("No job cards found. Stopping.", flush=True)
            break

        for card in cards:
            job_data = extract_job(
                card=card,
                query=query,
                location=location,
                fetch_full_description=fetch_full_description,
                driver=driver,
            )
            job_url = job_data.get("job_url")
            if job_url and job_url in seen_urls:
                continue
            if job_url:
                seen_urls.add(job_url)
            results.append(job_data)
            if max_jobs and len(results) >= max_jobs:
                return results

        sleep_for = random.uniform(delay_min, delay_max)
        time.sleep(sleep_for)

    return results


def resolve_locations(args: argparse.Namespace) -> list:
    locations = []
    if args.locations_file:
        with open(args.locations_file, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    locations.append(line)
    if args.locations:
        locations.extend([value.strip() for value in args.locations.split(",") if value.strip()])
    deduped = []
    for value in locations:
        if value not in deduped:
            deduped.append(value)
    return deduped


def build_driver(headless: bool) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def main() -> int:
    args = parse_args()
    if args.max_pages < 1:
        print("max-pages must be >= 1", file=sys.stderr)
        return 2

    locations = resolve_locations(args)
    if not locations:
        print("No locations provided.", file=sys.stderr)
        return 2

    print(f"Query: {args.query}", flush=True)
    print(f"Locations: {', '.join(locations)}", flush=True)
    print(f"Output: {args.output}", flush=True)

    seen_urls = set()
    driver = build_driver(args.headless)
    try:
        with open(args.output, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()

            for location in locations:
                print(f"Scraping location: {location}", flush=True)
                jobs = scrape_location(
                    driver=driver,
                    query=args.query,
                    location=location,
                    max_pages=args.max_pages,
                    max_jobs=args.max_jobs,
                    fetch_full_description=args.fetch_description,
                    delay_min=args.delay_min,
                    delay_max=args.delay_max,
                    seen_urls=seen_urls,
                )
                for job in jobs:
                    writer.writerow(job)
                print(f"Captured {len(jobs)} jobs for {location}", flush=True)
    finally:
        driver.quit()

    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
