==================================================
MultiApp Scraper (multiapp_scraper.py)
==================================================

📌 DESCRIPTION
--------------------------------------------------
This Python tool automates the extraction of app data from a list of URLs 
(Appfigures format) using Selenium and BeautifulSoup. It supports parallel 
processing with retry capabilities, optional formatting, and output to Excel.

✅ Data Points Extracted:
- App name
- Estimated Downloads
- Estimated Revenue
- Monetization method
- Rating (stars)
- Release Date
- Last Update
- iOS App Store ID

--------------------------------------------------
💻 USAGE
--------------------------------------------------
Run from terminal with customizable CLI options:

    python multiapp_scraper.py --input links.xlsx --output data.xlsx --processes 4 --retry 1

--------------------------------------------------
🛠️ OPTIONS
--------------------------------------------------
--input               Path to input Excel file (default: links.xlsx)
--output              Path to output Excel file (default: scraped_app_data.xlsx)
--start               Start row index (1-based, inclusive)
--end                 End row index (1-based, inclusive). Omit to use all.
--processes           Number of parallel Chrome instances (default: 1)
--retry               Number of retry attempts for failed links (default: 0)
--save-failed         Save failed links to a file ("failed_links.xlsx")
--formatting-off      Disable Excel column formatting (default: False)
--headless-off        Disable headless mode (for debugging)

--------------------------------------------------
📂 INPUT FORMAT
--------------------------------------------------
Excel file (XLSX) with at least two columns:
- Column 1: row numbers
- Column 2: app links (URLs to scrape)

--------------------------------------------------
📦 OUTPUT FORMAT
--------------------------------------------------
Excel file containing all extracted data and optional formatting:
- Autofit column widths
- Freeze header row
- Filterable columns

Optional: `failed_links.xlsx` for retrying incomplete runs

--------------------------------------------------
⚡ DEPENDENCIES
--------------------------------------------------
- Python 3.8+
- selenium
- beautifulsoup4
- pandas
- openpyxl
- tqdm

Install with:

    pip install selenium beautifulsoup4 pandas openpyxl tqdm

--------------------------------------------------
🔧 SETUP
--------------------------------------------------
1. Download ChromeDriver from https://chromedriver.chromium.org/
2. Update the path to your chromedriver executable in the script:
       CHROMEDRIVER_PATH = 'path/to/chromedriver.exe'
3. Run the script with your desired parameters.

--------------------------------------------------
👨‍💻 AUTHOR & LICENSE
--------------------------------------------------
Developed by [Your Name]
MIT License