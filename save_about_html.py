import os
import time
import pandas as pd
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ---------------- CONFIG ----------------
INPUT_FILE = "facebook_followers.csv"
OUTPUT_FOLDER = "facebook_about_html"

# Create output folder
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
print(f"📁 HTML files will be saved to: {OUTPUT_FOLDER}\n")

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


# ---------------- HELPER FUNCTIONS ----------------
def sanitize_filename(name):
    """Clean name to make it safe for filename"""
    # Remove invalid filename characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    # Limit length
    return name[:100] if name else "unknown"


def extract_person_name(driver):
    """Extract person's name from Facebook page"""
    try:
        # Method 1: Try to get name from page title
        title = driver.title
        if title and '|' in title:
            name = title.split('|')[0].strip()
            if name and name != "Facebook":
                return name
        elif title and title != "Facebook":
            name = title.replace(" - About", "").replace(" | Facebook", "").strip()
            if name:
                return name
        
        # Method 2: Try to get from h1 or h2 heading
        try:
            name_elem = driver.find_element(By.XPATH, "//h1")
            name = name_elem.text.strip()
            if name:
                return name
        except:
            pass
        
        try:
            name_elem = driver.find_element(By.XPATH, "//h2")
            name = name_elem.text.strip()
            if name:
                return name
        except:
            pass
        
        # Method 3: Try to get from any prominent text element
        try:
            name_elem = driver.find_element(By.XPATH, "//span[@dir='auto' and string-length(text()) > 3]")
            name = name_elem.text.strip()
            if name and len(name) < 50:  # Reasonable name length
                return name
        except:
            pass
            
    except:
        pass
    
    return None


# ---------------- MAIN LOOP ----------------
name_counts = {}  # Track duplicate names

for i, url in enumerate(profile_links, start=1):
    print(f"\n📄 [{i}/{len(profile_links)}] {url}")
    
    # Go to about page
    if "?id=" in url:
        about_url = url + "&sk=about"
    else:
        about_url = url + "?sk=about"
    
    try:
        driver.get(about_url)
        time.sleep(5)
        
        # Extract person's name
        person_name = extract_person_name(driver)
        
        if person_name:
            clean_name = sanitize_filename(person_name)
            print(f"   👤 Name: {person_name}")
        else:
            # Fallback to URL-based name
            if "profile.php?id=" in url:
                profile_id = url.split("profile.php?id=")[1].split("&")[0]
                clean_name = f"profile_{profile_id}"
            else:
                parts = url.rstrip('/').split('/')
                clean_name = parts[-1].replace('?', '_').replace('&', '_')[:100]
            print(f"   ⚠ Could not extract name, using: {clean_name}")
        
        # Handle duplicate names by adding number
        if clean_name in name_counts:
            name_counts[clean_name] += 1
            filename = f"{clean_name}_{name_counts[clean_name]}.html"
        else:
            name_counts[clean_name] = 1
            filename = f"{clean_name}.html"
        
        # Get HTML
        html_content = driver.page_source
        
        # Save to file
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        file_size = len(html_content)
        print(f"   ✅ Saved: {filename} ({file_size:,} bytes)")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    time.sleep(2)

print(f"\n{'='*70}")
print(f"✅ DONE — {len(profile_links)} HTML files saved to:")
print(f"📂 {os.path.abspath(OUTPUT_FOLDER)}")
print(f"{'='*70}")

driver.quit()
