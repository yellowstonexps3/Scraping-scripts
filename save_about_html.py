import os
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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


# ---------------- HELPER FUNCTION ----------------
def sanitize_filename(url):
    """Convert URL to safe filename"""
    if "profile.php?id=" in url:
        profile_id = url.split("profile.php?id=")[1].split("&")[0]
        return f"profile_{profile_id}"
    else:
        parts = url.rstrip('/').split('/')
        username = parts[-1].replace('?', '_').replace('&', '_')
        return username[:100]


# ---------------- MAIN LOOP ----------------
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
        
        # Get HTML
        html_content = driver.page_source
        
        # Save to file
        filename = sanitize_filename(url)
        filepath = os.path.join(OUTPUT_FOLDER, f"{i:04d}_{filename}.html")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"   ✅ Saved: {filename}.html")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    time.sleep(2)

print(f"\n✅ DONE — HTML files saved to: {os.path.abspath(OUTPUT_FOLDER)}")
driver.quit()
