import csv
import time
import pandas as pd
from datetime import datetime
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
# Try to create output file, add timestamp if file is locked
try:
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["Profile URL", "Work & Education"])
    print(f"📝 Output file: {OUTPUT_FILE}")
except PermissionError:
    # File is open in another program, create new file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_FILE = f"facebook_work_education_{timestamp}.csv"
    print(f"⚠ Original file is open! Creating new file: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["Profile URL", "Work & Education"])


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
    Scrape both work and education in ONE visit and combine into single output
    """
    print(f"  ➡ Visiting Work & Education page...")
    
    try:
        driver.get(build_about_url(url, TAB_PARAM))
        time.sleep(5)
        
        # Try to expand the section if needed
        click_section("Work and education")
        time.sleep(3)
        
    except Exception as e:
        print(f"  ⚠ Error loading page: {e}")
        return ""

    all_entries = []

    # ============ SCRAPE WORK - IMPROVED ============
    work_entries = []
    
    try:
        # Method 1: Get all text from Work section using aria-label
        work_section = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Work')]//span[@dir='auto' or @dir='ltr']"
        )
        for elem in work_section:
            text = elem.text.strip()
            if text and len(text) > 2 and 'Work' not in text:
                work_entries.append(text)
        
        # Method 2: Look for profile intro work info
        intro_work = driver.find_elements(
            By.XPATH,
            "//span[contains(text(),'Works at') or contains(text(),'Work at')]//parent::div//span[@dir='auto']"
        )
        for elem in intro_work:
            text = elem.text.strip()
            if text and 'Works at' not in text and 'Work at' not in text:
                work_entries.append(text)
        
        # Method 3: Direct "Works at" and "Former" patterns
        work_patterns = driver.find_elements(
            By.XPATH,
            "//div[contains(text(),'Works at') or contains(text(),'Former') or contains(text(),'Worked at')]"
        )
        for elem in work_patterns:
            full_text = elem.text.strip()
            # Extract company name after "Works at", "Former", etc.
            if 'Works at' in full_text:
                company = full_text.replace('Works at', '').strip()
                if company:
                    work_entries.append(f"💼 Works at: {company}")
            elif 'Worked at' in full_text:
                company = full_text.replace('Worked at', '').strip()
                if company:
                    work_entries.append(f"💼 Worked at: {company}")
            elif 'Former' in full_text:
                company = full_text.replace('Former', '').strip()
                if company:
                    work_entries.append(f"💼 Former: {company}")
        
        # Method 4: Look in about overview for work mentions
        overview_work = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'work_and_education')]//preceding::div[contains(text(),'at')]//span[@dir='auto']"
        )
        for elem in overview_work:
            text = elem.text.strip()
            if text and len(text) > 2:
                work_entries.append(text)
                
    except Exception as e:
        print(f"  ⚠ Work scraping error: {e}")

    # ============ SCRAPE EDUCATION - IMPROVED ============
    edu_entries = []
    
    try:
        # Method 1: University/College section
        uni_section = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'University') or contains(@aria-label,'College')]//span[@dir='auto']"
        )
        for elem in uni_section:
            text = elem.text.strip()
            if text and len(text) > 2 and 'University' not in text and 'College' not in text:
                edu_entries.append(f"🎓 University: {text}")
        
        # Method 2: High School section
        hs_section = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'High School')]//span[@dir='auto']"
        )
        for elem in hs_section:
            text = elem.text.strip()
            if text and len(text) > 2 and 'High School' not in text:
                edu_entries.append(f"🏫 High School: {text}")
        
        # Method 3: Profile intro education patterns
        edu_patterns = driver.find_elements(
            By.XPATH,
            "//div[contains(text(),'Studied at') or contains(text(),'Studies at') or contains(text(),'Went to')]"
        )
        for elem in edu_patterns:
            full_text = elem.text.strip()
            if 'Studied at' in full_text:
                school = full_text.replace('Studied at', '').strip()
                if school:
                    edu_entries.append(f"🎓 Studied at: {school}")
            elif 'Studies at' in full_text:
                school = full_text.replace('Studies at', '').strip()
                if school:
                    edu_entries.append(f"🎓 Studies at: {school}")
            elif 'Went to' in full_text:
                school = full_text.replace('Went to', '').strip()
                if school:
                    edu_entries.append(f"🏫 Went to: {school}")
                
    except Exception as e:
        print(f"  ⚠ Education scraping error: {e}")

    # Clean up duplicates while preserving order
    work_entries = list(dict.fromkeys(work_entries))
    edu_entries = list(dict.fromkeys(edu_entries))
    
    # Combine work and education into one list
    if work_entries:
        all_entries.extend(work_entries)
    if edu_entries:
        all_entries.extend(edu_entries)
    
    combined_str = " | ".join(all_entries) if all_entries else ""
    
    print(f"  ✅ Found: {len(work_entries)} work + {len(edu_entries)} education = {len(all_entries)} total entries")
    
    return combined_str


# ---------------- MAIN LOOP ----------------
for idx, url in enumerate(profile_links, start=1):
    print(f"\n📄 [{idx}/{len(profile_links)}] Scraping → {url}")
    
    try:
        combined_data = scrape_work_and_education(url)
        
        with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([url, combined_data])
            
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        # Write empty row on failure
        with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([url, ""])
    
    time.sleep(2)

print(f"\n✅ DONE — Saved to: {OUTPUT_FILE}")
driver.quit()
