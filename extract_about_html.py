from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import os

# Setup Chrome
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_experimental_option("detach", True)

driver = webdriver.Chrome(options=chrome_options)

# Login
driver.get("https://www.facebook.com/")
print("Please log in to Facebook...")
input("Press Enter after login: ")

# Read profile links
df = pd.read_csv("facebook_followers.csv")
profile_links = df["Profile Link"].dropna().unique().tolist()

# Create folder for HTML files
os.makedirs("about_html", exist_ok=True)

# Extract HTML for each profile
for i, url in enumerate(profile_links, start=1):
    print(f"[{i}/{len(profile_links)}] {url}")
    
    # Go to about page
    about_url = url + "&sk=about" if "?id=" in url else url + "?sk=about"
    driver.get(about_url)
    time.sleep(5)
    
    # Save HTML
    html = driver.page_source
    filename = f"about_html/{i:04d}.html"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"  Saved: {filename}")
    time.sleep(2)

print("Done!")
driver.quit()
