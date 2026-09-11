# search_edjoin.py
# Loads the saved session and scrapes job listings, then filters by your criteria.
#
#
# Run: python search_edjoin.py

import csv
import re
import sys
from datetime import datetime
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright

# ============================ CONFIG ============================
AUTH_FILE = "auth_state.json"

CRITERIA = {
    "keywords": [],            # e.g. ["math", "algebra"] — matches title/description (OR)
    "exclude_keywords": [],    # e.g. ["substitute", "coach"] — drops rows containing any
    "locations": [],           # e.g. ["Los Angeles", "Whittier"] — matches district/location (OR)
    "posted_within_days": None # e.g. 14 — only keep listings posted in the last N days
}

SEARCH_URL = "https://edjoin.org/Home/Jobs?rows=10&page=1&sort=postingDate&order=DESC&keywords=Los%20Angeles&location=Los%20Angeles&searchType=&states=&regions=&jobTypes=&days=0&empType=&catID=0&onlineApps=null&recruitmentCenterID=0&stateID=0&regionID=0&districtID=0&countyID=0"

HEADLESS = False


# ================================================================

# API call - the new method for getting the job listings more directly 
# TODO: write interface and object/function to make the URL a usable API
# TODO: Use discovered Var option names  to write API documentation
url = 'https://edjoin.org/Home/LoadJobs?rows=10&page=1&sort=postingDate&sortVal=0&order=DESC&keywords=mild/moderate&location=Los%20Angeles&searchType=&regions=&jobTypes=&days=0&empType=&catID=0&onlineApps=null&recruitmentCenterID=0&stateID=0&regionID=0&districtID=0&searchID=0&_=1789076872184'
r = requests.get(url)
print("Status code:", r.status_code)
response_dict = r.json()

print(response_dict)

def run():
    if not Path(AUTH_FILE).exists():
        print(f"No {AUTH_FILE} found. Run capture_login.py first.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()

        page.goto(SEARCH_URL, wait_until="networkidle")

        if re.search(r"login", page.url, re.IGNORECASE):
            print(f"Redirected to login ({page.url}). "
                  "Session may have expired — re-run capture_login.py.")
            browser.close()
            sys.exit(1)

        else:
#We're holding off on more actions here until further process decision are complete. Playwright may still play some role for the data retrieval, if it is not completely replaced by `requests`
            browser.close()

# Why is run_scrape still here? in case we need to implement Playwright scraping or write it as a fallback chain
# ! def run_scrape(page):
#     # Wait for job listings to appear on the page.
#     page.locator(CARD_SELECTOR).first.wait_for(timeout=15000)
# * The following section will need to be removed or updated to correct locators and such if we use Playwright as fallback
#     rows = []
#     for card in page.locator(CARD_SELECTOR).all():
#         title    = card.locator(TITLE_SELECTOR).text_content() or ""
#         link     = card.locator(LINK_SELECTOR).get_attribute("href") or ""
#         location = card.locator(LOCATION_SELECTOR).text_content() or ""
#         posted   = card.locator(POSTED_SELECTOR).text_content() or ""
# * This section can be used with adjustments on our new API method
#         rows.append({
#             "title": title.strip(),
#             "location": location.strip(),
#             "posted": posted.strip(),
#             "url": link.strip(),
#         })

#     # Apply your keyword/location/date filters.
#     matches = [r for r in rows if passes_filter(r)]
# * This approach can still be used with API method
#     # Write results.
#     with open("results.csv", "w", newline="", encoding="utf-8") as f:
#         writer = csv.DictWriter(f, fieldnames=["title", "location", "posted", "url"])
#         writer.writeheader()
#         writer.writerows(matches)

# * This approach can still be used with API method

#     print(f"Scraped {len(rows)} listings, {len(matches)} matched your criteria.")
#     print("Written to results.csv")
#     for row in matches[:20]:
#         print(row)


# * This approach can still be used with API method. Can be used as a pre-filter prior to fuzzy matching school name search then the simple location filter. 

# def passes_filter(row):
#     hay = (row.get("title", "") + " " + row.get("location", "")).lower()

#     kw = CRITERIA["keywords"]
#     if kw and not any(k.lower() in hay for k in kw):
#         return False

#     if any(k.lower() in hay for k in CRITERIA["exclude_keywords"]):
#         return False

#     locs = CRITERIA["locations"]
#     if locs and not any(loc.lower() in row.get("location", "").lower() for loc in locs):
#         return False

#     days = CRITERIA["posted_within_days"]
#     if days is not None and row.get("posted"):
#         try:
#             posted_date = datetime.strptime(row["posted"], "%m/%d/%Y")
#             if (datetime.now() - posted_date).days > days:
#                 return False
#         except ValueError:
#             pass  # Unparseable date — keep the row

#     return True


if __name__ == "__main__":
    run()