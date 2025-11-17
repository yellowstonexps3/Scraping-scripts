import os
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ---------------- CONFIG ----------------
INPUT_FILE = "facebook_followers.csv"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FOLDER = f"facebook_html_pages_{timestamp}"

# Create output folder
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
print(f"📁 HTML pages will be saved to: {OUTPUT_FOLDER}\n")

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
    # Extract profile name or ID from URL
    if "profile.php?id=" in url:
        profile_id = url.split("profile.php?id=")[1].split("&")[0]
        return f"profile_{profile_id}"
    else:
        # Extract username from URL
        parts = url.rstrip('/').split('/')
        username = parts[-1]
        # Remove special characters
        username = username.replace('?', '_').replace('&', '_').replace('=', '_')
        return username[:100]  # Limit length


def save_html_page(url, index):
    """Save the HTML of the about page"""
    print(f"➡ Collecting HTML from: {url}")

    # Build about URL
    if "?id=" in url:
        about_url = url + "&sk=about"
    else:
        about_url = url + "?sk=about"

    try:
        driver.get(about_url)
        time.sleep(5)

        # Try clicking "Work and education" to expand
        try:
            selectors = [
                "//span[text()='Work and education']",
                "//a[contains(text(),'Work and education')]",
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

        # Get page source (complete HTML)
        html_content = driver.page_source

        # Create filename
        filename = sanitize_filename(url)
        filepath = os.path.join(OUTPUT_FOLDER, f"{index:04d}_{filename}.html")

        # Save HTML to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        file_size = len(html_content)
        print(f"   ✅ Saved: {filepath} ({file_size:,} bytes)")
        
        return True, filepath

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, None


# ---------------- MAIN LOOP ----------------
print("=" * 70)
print("STARTING HTML COLLECTION...")
print("=" * 70)

success_count = 0
failed_count = 0
failed_urls = []

for i, url in enumerate(profile_links, start=1):
    print(f"\n📄 [{i}/{len(profile_links)}] Processing: {url}")
    
    success, filepath = save_html_page(url, i)
    
    if success:
        success_count += 1
    else:
        failed_count += 1
        failed_urls.append(url)
    
    time.sleep(2)

# ---------------- SUMMARY ----------------
print("\n" + "=" * 70)
print("✅ COLLECTION COMPLETE!")
print("=" * 70)
print(f"📊 Total profiles: {len(profile_links)}")
print(f"✅ Successfully collected: {success_count}")
print(f"❌ Failed: {failed_count}")
print(f"📁 HTML files saved to: {os.path.abspath(OUTPUT_FOLDER)}")

# Save failed URLs to file if any
if failed_urls:
    failed_file = os.path.join(OUTPUT_FOLDER, "failed_urls.txt")
    with open(failed_file, "w", encoding="utf-8") as f:
        for url in failed_urls:
            f.write(url + "\n")
    print(f"⚠️  Failed URLs saved to: {failed_file}")

print("=" * 70)

driver.quit()
