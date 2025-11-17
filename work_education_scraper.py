import csv
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ---------------- CONFIG ----------------
INPUT_FILE = "facebook_followers.csv"
OUTPUT_FILE = "facebook_work_education.csv"
TAB_PARAM = "about_work_and_education"

chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("detach", True)

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 10)

# ---------------- LOGIN ----------------
driver.get("https://www.facebook.com/")
print("🔐 Please log in to Facebook...")
input("👉 Press Enter after you have logged in: ")

# ---------------- READ INPUT ----------------
df = pd.read_csv(INPUT_FILE)
if "Profile Link" not in df.columns:
    raise Exception("⚠ CSV must contain a column named 'Profile Link'.")

profile_links = df["Profile Link"].dropna().unique().tolist()
print(f"✅ Loaded {len(profile_links)} profile URLs.\n")

# ---------------- PREPARE OUTPUT ----------------
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerow(["Profile URL", "Work Entries", "Education Entries"])


def build_about_url(url, tab_param):
    """Build the about URL with proper parameter"""
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}sk={tab_param}"


def click_section(section_label):
    """Try to click a section if it exists"""
    selectors = [
        f"//span[text()='{section_label}']",
        f"//div[text()='{section_label}']",
        f"//a[contains(text(),'{section_label}')]"
    ]
    for xp in selectors:
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
            return True
        except (TimeoutException, NoSuchElementException):
            continue
    return False


def scrape_work_and_education(url):
    """
    Scrape both work and education in ONE visit to avoid duplicate page loads
    """
    print(f"  ➡ Visiting Work & Education page...")
    
    try:
        driver.get(build_about_url(url, TAB_PARAM))
        time.sleep(4)
        
        # Try to expand the section if needed
        click_section("Work and education")
        time.sleep(2)
        
    except Exception as e:
        print(f"  ⚠ Error loading page: {e}")
        return "", ""

    # ============ SCRAPE WORK ============
    work_entries = []
    
    try:
        # Method 1: Look for work section with aria-label
        work_cards = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Work')]//div[@role='article' or contains(@class,'x1lliihq')]//span[@dir='auto']"
        )
        for card in work_cards:
            text = card.text.strip()
            if text and len(text) > 1:
                work_entries.append(text)
        
        # Method 2: Look for "Works at" or "Former" text
        work_fallback = driver.find_elements(
            By.XPATH,
            "//span[@dir='auto' and (contains(text(),'Works at') or contains(text(),'Former') or contains(text(),'worked at'))]"
        )
        for span in work_fallback:
            text = span.text.strip()
            if text and text not in work_entries:
                work_entries.append(text)
                
        # Method 3: Generic work section divs
        work_generic = driver.find_elements(
            By.XPATH,
            "//div[contains(text(),'Work')]//following::div[@dir='auto'][position() < 10]"
        )
        for div in work_generic:
            text = div.text.strip()
            if text and len(text) > 2 and text not in work_entries:
                work_entries.append(text)
                
    except Exception as e:
        print(f"  ⚠ Work scraping error: {e}")

    # ============ SCRAPE EDUCATION ============
    edu_entries = []
    
    try:
        # Method 1: University section
        uni_cards = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'University') or contains(@aria-label,'College')]//span[@dir='auto']"
        )
        for card in uni_cards:
            text = card.text.strip()
            if text and len(text) > 1:
                edu_entries.append(f"🎓 {text}")
        
        # Method 2: High School section
        hs_cards = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'High School') or contains(@aria-label,'Secondary')]//span[@dir='auto']"
        )
        for card in hs_cards:
            text = card.text.strip()
            if text and len(text) > 1:
                edu_entries.append(f"🏫 {text}")
        
        # Method 3: Fallback for "Studied at", "Went to"
        edu_fallback = driver.find_elements(
            By.XPATH,
            "//span[@dir='auto' and (contains(text(),'Studied at') or contains(text(),'Went to') or contains(text(),'Studies at'))]"
        )
        for span in edu_fallback:
            text = span.text.strip()
            if text and text not in [e.replace('🎓 ', '').replace('🏫 ', '') for e in edu_entries]:
                edu_entries.append(text)
                
    except Exception as e:
        print(f"  ⚠ Education scraping error: {e}")

    # Clean up duplicates while preserving order
    work_entries = list(dict.fromkeys(work_entries))
    edu_entries = list(dict.fromkeys(edu_entries))
    
    work_str = " | ".join(work_entries) if work_entries else ""
    edu_str = " | ".join(edu_entries) if edu_entries else ""
    
    print(f"  ✅ Work: {len(work_entries)} entries | Education: {len(edu_entries)} entries")
    
    return work_str, edu_str


# ---------------- MAIN LOOP ----------------
for idx, url in enumerate(profile_links, start=1):
    print(f"\n📄 [{idx}/{len(profile_links)}] Scraping → {url}")
    
    try:
        work_data, edu_data = scrape_work_and_education(url)
        
        with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([url, work_data, edu_data])
            
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        # Write empty row on failure
        with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([url, "", ""])
    
    time.sleep(2)

print(f"\n✅ DONE — Saved to: {OUTPUT_FILE}")
driver.quit()
