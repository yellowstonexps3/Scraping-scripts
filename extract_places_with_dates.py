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

    places_data = []

    # Get ALL text from Places lived section - line by line
    try:
        # Get all spans from Places lived section
        all_spans = driver.find_elements(
            By.XPATH,
            "//div[contains(@aria-label,'Places lived')]//span[@dir='auto' or @dir='ltr']"
        )
        
        # Extract all text lines
        all_lines = []
        for span in all_spans:
            text = span.text.strip()
            if text and len(text) > 1:
                all_lines.append(text)
        
        # Process lines in pairs (place, then date/status)
        i = 0
        while i < len(all_lines):
            line = all_lines[i]
            
            # Skip header texts
            if line.lower() in ['places lived', 'places', 'current city', 'hometown']:
                i += 1
                continue
            
            # Check if this looks like a place (has comma or is substantial text)
            if ',' in line or len(line) > 3:
                place = line
                date_info = ""
                
                # Check next line for date/status info
                if i + 1 < len(all_lines):
                    next_line = all_lines[i + 1]
                    # Check if next line is a status/date (not another place)
                    if any(keyword in next_line.lower() for keyword in 
                           ['moved', 'current', 'home', 'town', 'city', '199', '200', '201', '202']):
                        date_info = next_line
                        i += 1  # Skip the date line in next iteration
                
                # Format output
                if date_info:
                    places_data.append(f"{place} ({date_info})")
                else:
                    places_data.append(place)
            
            i += 1
            
    except Exception as e:
        print(f"   ⚠ Error: {e}")
        pass

    # Fallback: Get all divs with text content
    if not places_data:
        try:
            divs = driver.find_elements(
                By.XPATH,
                "//div[contains(@aria-label,'Places lived')]//div[@dir='auto']"
            )
            for div in divs:
                text = div.text.strip()
                if text and len(text) > 2:
                    # Split by newlines
                    lines = text.split('\n')
                    if len(lines) >= 2:
                        place = lines[0].strip()
                        date = lines[1].strip()
                        places_data.append(f"{place} ({date})")
                    elif len(lines) == 1:
                        places_data.append(lines[0].strip())
        except:
            pass

    # Remove duplicates
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
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([url, places_dates])
        f.flush()

    time.sleep(2)

print(f"\n✅ DONE — Saved to: {OUTPUT_FILE}")
driver.quit()
