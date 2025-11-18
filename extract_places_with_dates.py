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

    # Get ALL text from Places section
    all_text = []
    
    try:
        # Get all spans from Places lived section
        elems = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Places lived')]//span"
        )
        for e in elems:
            t = e.text.strip()
            if t and len(t) > 1:
                all_text.append(t)
    except:
        pass

    # Separate places (with comma) from dates/status
    places = []
    dates = []
    
    for text in all_text:
        # Skip headers
        if text.lower() in ['places lived', 'places', 'about']:
            continue
        
        # If it has a comma, it's likely a place
        if ',' in text:
            places.append(text)
        # If it has these keywords, it's a date/status
        elif any(keyword in text for keyword in 
                 ['Moved in', 'Current', 'Home', 'Lives in', 'From', 'Born', '19', '20']):
            dates.append(text)
        # Otherwise, could be either
        else:
            # If short, might be a date/status
            if len(text) < 30:
                dates.append(text)
            else:
                places.append(text)
    
    # Pair them together - match each place with its date
    result = []
    
    # Try to pair them in order
    for i in range(max(len(places), len(dates))):
        if i < len(places) and i < len(dates):
            # We have both place and date
            result.append(f"{places[i]} - {dates[i]}")
        elif i < len(places):
            # Only place, no date
            result.append(places[i])
        elif i < len(dates):
            # Only date, no place (shouldn't happen but just in case)
            result.append(dates[i])
    
    print(f"   ✓ Places found: {places}")
    print(f"   ✓ Dates found: {dates}")
    print(f"   ✓ Paired result: {result}")

    return " | ".join(result)


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
