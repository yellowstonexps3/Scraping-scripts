from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import csv
import time
import re

# ---------------- CONFIG ----------------
INPUT_FILE = "facebook_followers.csv"   # Input CSV with column 'Profile Link'
OUTPUT_FILE = "facebook_places_with_dates.csv"  # Output file

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

    places_data = []

    # Method 1: Get places with dates from Places lived section using parent divs
    try:
        # Look for the main Places lived container
        place_cards = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Places lived')]//div[@role='article' or contains(@class,'x1lliihq')]"
        )
        
        for card in place_cards:
            try:
                # Get all text from this card
                full_text = card.text.strip()
                
                if full_text and len(full_text) > 2:
                    # Split by newlines to separate place from dates
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    
                    if len(lines) > 0:
                        place = lines[0]
                        dates = ""
                        
                        # Look for date patterns in remaining lines
                        for line in lines[1:]:
                            # Check if line contains year patterns (4 digits) or date keywords
                            if re.search(r'\d{4}|Present|Current|Moved|Lives|From', line):
                                dates = line
                                break
                        
                        # Format output
                        if dates:
                            places_data.append(f"{place} ({dates})")
                        else:
                            places_data.append(place)
            except:
                pass
    except:
        pass

    # Method 2: Alternative - Get ALL divs with location text
    if not places_data:
        try:
            elems = driver.find_elements(
                By.XPATH,
                "//div[contains(@aria-label,'Places lived')]//span[@dir='auto']"
            )
            
            all_text = []
            for e in elems:
                t = e.text.strip()
                if t and len(t) > 2 and t.lower() not in ['places lived', 'places', 'current city', 'hometown']:
                    all_text.append(t)
            
            # Try to pair places with dates
            current_place = None
            for text in all_text:
                # Check if this looks like a date
                if re.search(r'\d{4}|Present|Current|From|Moved to', text):
                    if current_place:
                        places_data.append(f"{current_place} ({text})")
                        current_place = None
                    else:
                        places_data.append(text)
                else:
                    # This is likely a place name
                    if current_place:
                        places_data.append(current_place)
                    current_place = text
            
            # Add last place if exists
            if current_place:
                places_data.append(current_place)
                
        except:
            pass

    # Method 3: Backup — Look for any location with comma (city, state, country)
    if not places_data:
        try:
            all_spans = driver.find_elements(By.XPATH, "//span[@dir='auto']")
            for s in all_spans:
                t = s.text.strip()
                if "," in t and len(t) <= 60:  # looks like a location
                    if t not in places_data:
                        places_data.append(t)
        except:
            pass

    # Remove duplicates while preserving order
    places_data = list(dict.fromkeys(places_data))

    print(f"   ✓ Found {len(places_data)} Places:")
    for place in places_data:
        print(f"      - {place}")

    return " | ".join(places_data)


# ---------------- MAIN LOOP ----------------
for i, url in enumerate(profile_links, start=1):
    print(f"\n📄 [{i}/{len(profile_links)}] Scraping {url}")
    places_dates = scrape_places_with_dates(url)

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([url, places_dates])

    time.sleep(2)

print(f"\n✅ DONE — Saved to: {OUTPUT_FILE}")
driver.quit()
