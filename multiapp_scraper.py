# ----------------------
# Import Libraries
# ----------------------

# Selenium-related imports for browser automation
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

# HTML parsing library
from bs4 import BeautifulSoup

# Data manipulation and I/O
import pandas as pd
import time
from pathlib import Path

# Excel formatting with OpenPyXL
from openpyxl import load_workbook
from openpyxl.styles import numbers

# Multiprocessing and CLI utilities
from multiprocessing import Pool
import os
from tqdm import tqdm
import argparse

# ----------------------
# CLI Arguments
# ----------------------

parser = argparse.ArgumentParser(description="Scrape app data from a list of links using Selenium.")

# File input/output
parser.add_argument("--input", type=str, default="links.xlsx", help="Path to input Excel file with links")
parser.add_argument("--output", type=str, default="scraped_app_data.xlsx", help="Path to output Excel file")

# Link range selection
parser.add_argument("--start", type=int, default=1, help="Start index of links to process")
parser.add_argument("--end", type=int, default=None, help="End index (inclusive) of links to process. Use None for all.")

# Multiprocessing
parser.add_argument("--processes", type=int, default=1, help="Number of parallel Chrome processes to use")

# Optional flags
parser.add_argument("--retry", type=int, default=0, help="Number of retry attempts for failed links")
parser.add_argument("--save-failed", action="store_true", help="Save failed links to an Excel file for future retry")
parser.add_argument("--formatting-off", action="store_true", help="Disable Excel column formatting")
parser.add_argument("--headless-off", action="store_true", help="Disable headless mode for Chrome")

args = parser.parse_args()

# ----------------------
# Configuration and Chrome Options
# ----------------------

# Setup Chrome WebDriver options
options = Options()

# Use headless mode unless explicitly disabled via CLI
if not args.headless_off:
    options.add_argument('--headless')

options.add_argument('--disable-gpu')                  # Disable GPU acceleration
options.add_argument('--disable-extensions')           # Disable browser extensions
options.add_argument('--disable-dev-shm-usage')        # Avoid /dev/shm issues in Docker/Linux
options.add_argument('--no-sandbox')                   # Bypass OS security model (needed in some environments)

# Optimize performance: block image and CSS loading
prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.managed_default_content_settings.stylesheets": 2
}
options.add_experimental_option("prefs", prefs)

# Define input and output file paths
INPUT_FILE = Path(args.input)
OUTPUT_FILE = Path(args.output)

# Define path to the local ChromeDriver binary (update this path for your system)
CHROMEDRIVER_PATH = 'D:/data/utilities/chromedriver-win64/chromedriver.exe'
service = Service(CHROMEDRIVER_PATH)

# Load links from the Excel file (second column expected to contain URLs)
df_links = pd.read_excel(INPUT_FILE)
all_links = df_links.iloc[:, 1].dropna().tolist()

# Apply range slicing from CLI: --start is inclusive (1-based), --end is exclusive
links = all_links[args.start - 1 : args.end]

# ----------------------
# Scraping batch function for multiprocessing
# ----------------------

def scrape_batch(batch_links):
    # Each process initializes its own ChromeDriver instance
    local_driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=options)
    
    batch_data = []       # Stores the successful results
    failed_links = []     # Stores links that failed to scrape

    # Iterate over the assigned batch of links
    for idx, url in enumerate(tqdm(batch_links, desc=f"PID {os.getpid()} [{len(batch_links)} links]"), start=1):
        print(f"[PID {os.getpid()}] Scraping {idx}/{len(batch_links)}: {url}")
        try:
            # Load the URL in the headless browser
            local_driver.get(url)

            # Smart wait until "Estimated Downloads" data is non-empty
            WebDriverWait(local_driver, 15).until(
                lambda d: d.find_element(By.XPATH, "//span[contains(text(),'Estimated Downloads')]")
                .find_element(By.XPATH, "./ancestor::div[2]/following-sibling::div//div").text.strip() != ""
            )

            # Parse the loaded page with BeautifulSoup
            soup = BeautifulSoup(local_driver.page_source, 'html.parser')

            # Define the fields to extract: label text, tag to follow, and how many steps to move
            fields = {
                "App name": ("Full Profile →","div",1),
                "Downloads": ("Estimated Downloads", "div", 2),
                "Revenue": ("Estimated Net Revenue", "div", 2),
                "Monetization": ("Monetization", "div", 1),
                "Rating": ("Rating", "span", 1),
                "Release Date": ("Released", "span", 1),
                "Last Update": ("Last updated", "span", 1),
                "App ID": ("iOS App Store ID", "div", 1)
            }

            results = {key: "N/A" for key in fields}

            # Extract all requested fields
            for key, (label_text, next_tag, next_steps) in fields.items():
                label = soup.find(lambda tag: (tag.name == "span" or tag.name == "a") and label_text in tag.contents)
                if label:
                    target = label
                    
                    for _ in range(next_steps):
                        target = target.find_next(next_tag)
                        
                    if target:
                        if key == "Rating" or key == "App name":# Special case: "Rating" or "App name" uses a different HTML structure (sibling instead of nested)
                            target = target.find_next_sibling()
                        results[key] = target.get_text(strip=True).strip("$()")           
                        
            # Save the final result for the current app
            batch_data.append({**results, "App URL": url})

        except Exception as e:
            print(f"⚠️ Error scraping {url}: {e}")
            failed_links.append(url)

        # Politeness delay to reduce server load
        time.sleep(1)

    # Clean up ChromeDriver instance
    local_driver.quit()

    return batch_data, failed_links

# ----------------------
# Main Loop
# ----------------------
if __name__ == "__main__":

    # ----------------------
    # Divide into interleaved batches for better load balancing
    # ----------------------

    num_processes = args.processes  # Number of parallel processes to launch

    # Interleaved batching: Each process gets every N-th link (ensures fairer distribution)
    batches = [links[i::num_processes] for i in range(num_processes)]

    # Launch multiprocessing using a pool of ChromeDriver instances
    with Pool(num_processes) as pool:
        results = pool.map(scrape_batch, batches)  # Each batch is scraped in a separate process

    # ----------------------
    # Failed links management
    # ----------------------

    flattened_data = []  # List to collect all successfully scraped app data
    failed_all = []      # Master list of all failed URLs

    # Unpack results from all batches (initial run)
    for data, failed in results:
        flattened_data.extend(data)
        failed_all.extend(failed)

    # Retry failed links up to --retry times
    for attempt in range(1, args.retry + 1):
        if not failed_all:
            break
        print(f"\n🔁 Retry attempt {attempt} for {len(failed_all)} failed links...")

        # Recreate interleaved batches for retrying
        retry_batches = [failed_all[i::num_processes] for i in range(num_processes)]
        with Pool(num_processes) as pool:
            retry_results = pool.map(scrape_batch, retry_batches)

        # Reset and repopulate failed_all from retry
        failed_all = []
        for data, failed in retry_results:
            flattened_data.extend(data)
            failed_all.extend(failed)

    # Optionally save permanently failed links
    if args.save_failed and failed_all:
        # Save in same format as input file: numbered rows + links
        failed_df = pd.DataFrame({
            "No.": list(range(1, len(failed_all) + 1)),
            "App Link": failed_all
        })
        failed_df.to_excel("failed_links.xlsx", index=False)
        print(f"\n⚠️ Failed links saved to failed_links.xlsx ({len(failed_all)} entries)")

    # ----------------------
    # Save to Excel
    # ----------------------

    # Convert final scraped data into a DataFrame and write to Excel
    df_output = pd.DataFrame(flattened_data)
    df_output.to_excel(OUTPUT_FILE, index=False)

    # Optional Excel formatting
    if not args.formatting_off:
        # Load the newly created Excel file
        wb = load_workbook(OUTPUT_FILE)
        ws = wb.active

        # Adjust column widths based on the longest entry in each column
        for column_cells in ws.columns:
            max_length = 0
            col_letter = column_cells[0].column_letter
            for cell in column_cells:
                # Force format to text to preserve special characters like leading apostrophes
                cell.number_format = numbers.FORMAT_TEXT
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = max_length + 2
            ws.column_dimensions[col_letter].width = adjusted_width

        # Freeze the top row and apply auto-filter to all columns
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions

        # Save the updated Excel file with formatting
        wb.save(OUTPUT_FILE)
        print("\n✅ Excel formatting applied.")
    else:
        print("\n⚠️ Excel formatting skipped (fast mode).")

    # Final completion message
    print("\n✅ Scraping completed with multiprocessing. Data saved to:", OUTPUT_FILE)

