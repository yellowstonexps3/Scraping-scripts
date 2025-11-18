from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import csv
import time

# ---------------- CONFIG ----------------
INPUT_FILE = "facebook_followers.csv"
OUTPUT_FILE = "facebook_places_with_dates.csv"

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
    writer.writerow(["Profile URL", "All Places & Dates"])


# ---------------- SCRAPER FUNCTION ----------------
def scrape_places(url):
    print(f"➡ Extracting Places & Dates from: {url}")

    if "?id=" in url:
        about_url = url + "&sk=about_places"
    else:
        about_url = url + "?sk=about_places"

    driver.get(about_url)
    time.sleep(5)

    # Try clicking "Places lived"
    try:
        selectors = [
            "//span[text()='Places lived']",
            "//a[contains(text(),'Places lived')]",
            "//div[contains(text(),'Places lived')]"
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

    # Collect ALL possible entries
    entries = set()

    # Method 1: Look for spans inside Places lived section
    try:
        elems = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Places lived')]//span[@dir='auto']"
        )
        for e in elems:
            t = e.text.strip()
            if t and len(t) > 2 and t.lower() != "places lived":
                entries.add(t)
    except:
        pass

    # Method 2: Get ALL spans from the entire page that look relevant
    try:
        all_spans = driver.find_elements(By.XPATH, "//span[@dir='auto']")
        for s in all_spans:
            t = s.text.strip()
            if t and len(t) > 2:
                # Keep if: has comma OR has location/date keywords
                lower = t.lower()
                if ("," in t and len(t) <= 60) or \
                   "moved in" in lower or \
                   "current town" in lower or \
                   "home town" in lower or \
                   "lives in" in lower:
                    entries.add(t)
    except:
        pass

    # Method 3: Search for specific text patterns anywhere on page
    try:
        # Look for "Moved in XXXX"
        moved_elems = driver.find_elements(By.XPATH, "//*[contains(text(),'Moved in')]")
        for elem in moved_elems:
            t = elem.text.strip()
            if "Moved in" in t and len(t) < 30:
                entries.add(t)
        
        # Look for "Current town/city"
        current_elems = driver.find_elements(By.XPATH, "//*[contains(text(),'Current town')]")
        for elem in current_elems:
            t = elem.text.strip()
            if len(t) < 30:
                entries.add(t)
        
        # Look for "Home town"
        home_elems = driver.find_elements(By.XPATH, "//*[contains(text(),'Home town')]")
        for elem in home_elems:
            t = elem.text.strip()
            if len(t) < 30:
                entries.add(t)
    except:
        pass

    entries = list(entries)

    print(f"   ✓ Found {len(entries)} entries: {entries}")

    return " | ".join(entries)


# ---------------- MAIN LOOP ----------------
for i, url in enumerate(profile_links, start=1):
    print(f"\n📄 [{i}/{len(profile_links)}] Scraping {url}")
    all_places = scrape_places(url)

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([url, all_places])
        f.flush()

    time.sleep(2)

print(f"\n✅ DONE — Saved to: {OUTPUT_FILE}")
driver.quit()
