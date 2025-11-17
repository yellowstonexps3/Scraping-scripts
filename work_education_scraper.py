import csv
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ---------------- CONFIG ----------------
INPUT_FILE = "facebook_followers.csv"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = f"facebook_work_education_{timestamp}.csv"

print(f"📝 Output will be saved to: {OUTPUT_FILE}\n")

chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("detach", True)

driver = webdriver.Chrome(options=chrome_options)

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
    writer = csv.writer(f)
    writer.writerow(["Profile URL", "Work & Education"])


# ---------------- SCRAPER FUNCTION ----------------
def scrape_work_education(url):
    print(f"➡ Extracting Work & Education from: {url}")

    # Build about URL
    if "?id=" in url:
        about_url = url + "&sk=about_work_and_education"
    else:
        about_url = url + "?sk=about_work_and_education"

    driver.get(about_url)
    time.sleep(5)

    # Try clicking "Work and education" section
    try:
        selectors = [
            "//span[text()='Work and education']",
            "//a[contains(text(),'Work and education')]",
            "//div[contains(text(),'Work and education')]"
        ]
        for s in selectors:
            try:
                btn = driver.find_element(By.XPATH, s)
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(3)
                break
            except:
                pass
    except:
        pass

    # Collect ALL work and education entries
    entries = set()

    # Method 1: Get ALL spans from Work section
    try:
        work_elems = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Work')]//span[@dir='auto']"
        )
        for e in work_elems:
            t = e.text.strip()
            if t and len(t) > 2 and t.lower() not in ['work', 'professional skills']:
                entries.add(f"💼 {t}")
    except:
        pass

    # Method 2: Get ALL spans from University/College section
    try:
        uni_elems = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'University') or contains(@aria-label,'College')]//span[@dir='auto']"
        )
        for e in uni_elems:
            t = e.text.strip()
            if t and len(t) > 2 and t.lower() not in ['university', 'college']:
                entries.add(f"🎓 {t}")
    except:
        pass

    # Method 3: Get ALL spans from High School section
    try:
        hs_elems = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'High School')]//span[@dir='auto']"
        )
        for e in hs_elems:
            t = e.text.strip()
            if t and len(t) > 2 and t.lower() not in ['high school', 'secondary school']:
                entries.add(f"🏫 {t}")
    except:
        pass

    # Method 4: Fallback - Look for common work/education patterns in ALL spans
    try:
        all_spans = driver.find_elements(By.XPATH, "//span[@dir='auto']")
        for s in all_spans:
            t = s.text.strip()
            # Filter for work/education keywords
            if any(keyword in t for keyword in ['Works at', 'Worked at', 'Former', 'Studied at', 'Studies at', 'Went to']):
                if len(t) <= 100:  # reasonable length
                    entries.add(t)
    except:
        pass

    entries = list(entries)
    
    print(f"   ✓ Found {len(entries)} entries: {entries}")

    return " | ".join(entries)


# ---------------- MAIN LOOP ----------------
for i, url in enumerate(profile_links, start=1):
    print(f"\n📄 [{i}/{len(profile_links)}] Scraping {url}")
    work_edu_data = scrape_work_education(url)

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([url, work_edu_data])

    time.sleep(2)

print(f"\n✅ DONE — Saved to: {OUTPUT_FILE}")
driver.quit()
