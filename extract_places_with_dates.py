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
    writer.writerow(["Profile URL", "Places with Dates"])


# ---------------- SCRAPER FUNCTION ----------------
def scrape_places_with_dates(url):
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

    # Collect EVERYTHING - use multiple methods
    all_entries = []

    print("   [DEBUG] Trying multiple extraction methods...")

    # Method 1: ALL spans with dir=auto (like original allplaces)
    try:
        elems = driver.find_elements(By.XPATH, "//span[@dir='auto']")
        print(f"   [Method 1] Found {len(elems)} spans with dir=auto")
        for e in elems:
            t = e.text.strip()
            if t and len(t) > 1:
                all_entries.append(t)
    except Exception as ex:
        print(f"   [Method 1] Error: {ex}")

    # Method 2: ALL spans (no filter)
    try:
        elems = driver.find_elements(By.XPATH, "//span")
        print(f"   [Method 2] Found {len(elems)} total spans")
    except:
        pass

    # Method 3: Look for text containing comma (places)
    try:
        elems = driver.find_elements(By.XPATH, "//*[contains(text(),',')]")
        print(f"   [Method 3] Found {len(elems)} elements with comma")
        for e in elems:
            t = e.text.strip()
            if ',' in t and len(t) < 100:
                all_entries.append(t)
    except Exception as ex:
        print(f"   [Method 3] Error: {ex}")

    # Remove duplicates
    all_entries = list(dict.fromkeys(all_entries))
    
    # Filter to only places-related entries
    filtered = []
    for entry in all_entries:
        lower = entry.lower()
        # Keep if: has comma, or has date/location keywords
        if (',' in entry) or \
           any(keyword in lower for keyword in ['moved', 'current', 'home', 'town', 'city', '199', '200', '201', '202']):
            if lower not in ['places lived', 'places', 'about', 'overview']:
                filtered.append(entry)

    print(f"   ✓ Total entries found: {len(all_entries)}")
    print(f"   ✓ Filtered entries: {filtered}")

    return " | ".join(filtered)


# ---------------- MAIN LOOP ----------------
for i, url in enumerate(profile_links, start=1):
    print(f"\n📄 [{i}/{len(profile_links)}] Scraping {url}")
    places_dates = scrape_places_with_dates(url)

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([url, places_dates])
        f.flush()

    print(f"   💾 Saved: {places_dates}")

    time.sleep(2)

print(f"\n✅ DONE — Saved to: {OUTPUT_FILE}")
driver.quit()
