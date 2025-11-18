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


# ---------------- SCRAPER FUNCTION (EXACTLY LIKE ALLPLACES - NO FILTERS) ----------------
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

    # Collect ALL - EXACTLY like allplaces does
    entries = set()

    # Method 1: Look for spans inside Places lived section (LIKE ALLPLACES)
    try:
        elems = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Places lived')]//span[@dir='auto']"
        )
        for e in elems:
            t = e.text.strip()
            # ONLY filter out the header "places lived"
            if t and len(t) > 2 and t.lower() != "places lived":
                entries.add(t)
    except:
        pass

    # Method 2: Backup — get ALL spans with dir=auto (LIKE ALLPLACES but NO comma filter)
    try:
        all_spans = driver.find_elements(By.XPATH, "//span[@dir='auto']")
        for s in all_spans:
            t = s.text.strip()
            # Accept ANYTHING that looks reasonable (place OR date)
            if t and 2 < len(t) <= 80:
                # Include if it has comma (place) OR date keywords
                if "," in t or any(keyword in t for keyword in 
                    ['Moved', 'Current', 'Home', 'town', 'city', '199', '200', '201', '202']):
                    entries.add(t)
    except:
        pass

    entries = list(entries)

    print(f"   ✓ Found: {entries}")

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
