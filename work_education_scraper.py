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


# ---------------- SIMPLE SCRAPER (SAME AS PLACES) ----------------
def scrape_work_education(url):
    print(f"➡ Extracting Work & Education from: {url}")

    # Build about URL for work and education
    if "?id=" in url:
        about_url = url + "&sk=about_work_and_education"
    else:
        about_url = url + "?sk=about_work_and_education"

    driver.get(about_url)
    time.sleep(5)

    # Try clicking "Work and education"
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

    # SIMPLE: Get ALL text from ALL spans on the page (SAME AS PLACES)
    entries = []

    try:
        # Get ALL spans
        all_spans = driver.find_elements(By.XPATH, "//span")
        
        for s in all_spans:
            t = s.text.strip()
            
            if t and len(t) > 2:
                lower = t.lower()
                
                # Include if it has work/education keywords
                is_work = any(keyword in lower for keyword in 
                    ['works at', 'worked at', 'work at', 'former', 'founder', 'ceo', 'manager'])
                
                is_education = any(keyword in lower for keyword in 
                    ['studied at', 'studies at', 'went to', 'class of', 'graduated', 'attended'])
                
                is_company = any(keyword in t for keyword in 
                    [' at ', ' in ', 'Inc', 'LLC', 'Corp', 'Company', 'University', 'College', 'School'])
                
                # Also include text that doesn't have keywords but looks like company/school names
                # (length between 3-80 chars, on work/education page)
                is_potential = 5 < len(t) <= 80
                
                if is_work or is_education or (is_company and is_potential):
                    # Skip headers and common words
                    if lower not in ['work and education', 'work', 'education', 'professional skills', 
                                     'university', 'college', 'high school', 'about', 'overview']:
                        # Clean up newlines
                        cleaned = t.replace('\n', ' ').replace('  ', ' ').strip()
                        if cleaned:
                            entries.append(cleaned)
        
    except Exception as ex:
        print(f"   ⚠ Error: {ex}")
    
    # Remove consecutive duplicates only
    cleaned = []
    prev = None
    for entry in entries:
        if entry != prev:
            cleaned.append(entry)
            prev = entry
    entries = cleaned

    print(f"   ✓ Found {len(entries)} entries: {entries}")

    return " | ".join(entries)


# ---------------- MAIN LOOP ----------------
for i, url in enumerate(profile_links, start=1):
    print(f"\n📄 [{i}/{len(profile_links)}] Scraping {url}")
    work_edu = scrape_work_education(url)

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([url, work_edu])
        f.flush()

    time.sleep(2)

print(f"\n✅ DONE — Saved to: {OUTPUT_FILE}")
driver.quit()
