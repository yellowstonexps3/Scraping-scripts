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


# ---------------- SIMPLE SCRAPER ----------------
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

    # SIMPLE: Get ALL text from ALL spans on the page
    entries = []
    seen = set()

    try:
        # Get ALL spans
        all_spans = driver.find_elements(By.XPATH, "//span")
        
        for s in all_spans:
            t = s.text.strip()
            
            if t and len(t) > 2 and t not in seen:
                lower = t.lower()
                
                # Include if:
                # 1. Has comma (place name like "New York, NY")
                # 2. Has date keywords (like "Moved in 2016")
                # 3. Has status keywords (like "Current town/city", "Home town")
                
                is_place = "," in t and len(t) <= 60
                is_date = "moved in" in lower or any(year in t for year in ['199', '200', '201', '202'])
                is_status = "current town" in lower or "home town" in lower or "lives in" in lower
                
                if is_place or is_date or is_status:
                    # Skip headers
                    if lower not in ['places lived', 'places', 'about']:
                        entries.append(t)
                        seen.add(t)
        
    except Exception as ex:
        print(f"   ⚠ Error: {ex}")

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
