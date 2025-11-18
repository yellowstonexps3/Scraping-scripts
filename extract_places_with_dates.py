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

    # Collect ALL text entries - NO FILTERS
    entries = set()

    # Method 1: Get ALL spans from Places lived section (no attribute filter)
    try:
        elems = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Places lived')]//span"
        )
        for e in elems:
            t = e.text.strip()
            if t and len(t) > 1:
                entries.add(t)
        print(f"   [Method 1] Found {len(entries)} entries")
    except Exception as ex:
        print(f"   [Method 1] Error: {ex}")

    # Method 2: Get ALL divs from Places lived section
    try:
        elems = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Places lived')]//div"
        )
        for e in elems:
            t = e.text.strip()
            # Only add if it's a single line (not a parent div with multiple lines)
            if t and '\n' not in t and len(t) > 1 and len(t) < 100:
                entries.add(t)
        print(f"   [Method 2] Total entries now: {len(entries)}")
    except Exception as ex:
        print(f"   [Method 2] Error: {ex}")

    # Method 3: Get text from any element with specific keywords
    try:
        keywords = ['Moved in', 'Current town', 'Home town', 'Lives in', 'From', 'Born in']
        for keyword in keywords:
            elems = driver.find_elements(By.XPATH, f"//*[contains(text(),'{keyword}')]")
            for e in elems:
                t = e.text.strip()
                if t and len(t) < 100:
                    entries.add(t)
        print(f"   [Method 3] Total entries now: {len(entries)}")
    except Exception as ex:
        print(f"   [Method 3] Error: {ex}")

    # Filter out headers and long text
    filtered = []
    for entry in entries:
        lower = entry.lower()
        # Skip headers and long paragraphs
        if lower not in ['places lived', 'places', 'about'] and len(entry) < 100:
            filtered.append(entry)

    filtered = list(dict.fromkeys(filtered))  # Remove duplicates

    print(f"   ✓ Final Found: {filtered}")

    return " | ".join(filtered)


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
