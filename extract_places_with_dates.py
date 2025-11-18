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


# ---------------- SCRAPER FUNCTION (SIMPLE LIKE ALLPLACES) ----------------
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

    # Collect ALL text entries (EXACTLY like allplaces does)
    entries = set()

    # Method 1: Look for spans inside Places lived section
    try:
        elems = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Places lived')]//span[@dir='auto']"
        )
        for e in elems:
            t = e.text.strip()
            if t and len(t) > 1 and t.lower() not in ["places lived"]:
                entries.add(t)
    except:
        pass

    # Method 2: Backup — any span that looks like a location or date
    try:
        all_spans = driver.find_elements(By.XPATH, "//span[@dir='auto']")
        for s in all_spans:
            t = s.text.strip()
            # Get locations (with commas) OR date info
            if ("," in t and len(t) <= 60) or any(keyword in t for keyword in 
                ['Moved in', 'Current town', 'Home town', 'Lives in']):
                entries.add(t)
    except:
        pass

    entries = list(entries)

    print(f"   ✓ Found Entries: {entries}")

    return " | ".join(entries)


# ---------------- MAIN LOOP ----------------
for i, url in enumerate(profile_links, start=1):
    print(f"\n📄 [{i}/{len(profile_links)}] Scraping {url}")
    places_dates = scrape_places_with_dates(url)

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([url, places_dates])
        f.flush()

    time.sleep(2)

print(f"\n✅ DONE — Saved to: {OUTPUT_FILE}")
driver.quit()
