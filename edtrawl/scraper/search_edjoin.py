# search_edjoin.py
# Loads the saved session and scrapes job listings, then filters by your criteria.
#
# Two modes:
#   - DISCOVERY MODE (default): dumps the search page HTML to discovery.html
#     so you can inspect the DOM and fill in the CSS selectors below.
#   - SCRAPE MODE: once selectors are filled in, extracts listings to results.csv.
#
# Run: python search_edjoin.py

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

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

# Set to False once you've inspected discovery.html and filled in the selectors.
DISCOVERY = True

# ===================== FILL THESE IN ============================
# After running in DISCOVERY mode, open discovery.html in your browser,
# right-click a job listing → Inspect, and find:
#   1. The repeating element that wraps ONE job listing (a div, tr, or li)
#   2. Inside that element: where the title, link, location, and date live
#
# Put the CSS class or selector for each one here.

CARD_SELECTOR     = ""   # the repeating wrapper for one job listing
TITLE_SELECTOR    = ""   # the element containing the job title text
LINK_SELECTOR     = ""   # the <a> tag whose href is the job detail URL
LOCATION_SELECTOR = ""   # the element containing district/location text
POSTED_SELECTOR   = ""   # the element containing the posted date
# ================================================================


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

        if DISCOVERY:
            run_discovery(page)
        else:
            run_scrape(page)

        browser.close()


def run_discovery(page):
    # Save full page HTML so you can inspect the DOM structure.
    html = page.content()
    Path("discovery.html").write_text(html, encoding="utf-8")

    # Print form fields to help understand the search interface.
    print("\n--- Form fields on the search page ---")
    for el in page.locator("input, select, textarea").all():
        print({
            "type": el.get_attribute("type"),
            "name": el.get_attribute("name"),
            "id": el.get_attribute("id"),
            "placeholder": el.get_attribute("placeholder"),
        })

    print(f"\nFull page HTML written to discovery.html")
    print(f"\nOpen discovery.html, right-click a job listing → Inspect.")
    print(f"Find the CSS selectors and fill them in at the top of this file.")
    print(f"Then set DISCOVERY = False and re-run.")


def run_scrape(page):
    # Wait for job listings to appear on the page.
    page.locator(CARD_SELECTOR).first.wait_for(timeout=15000)

    rows = []
    for card in page.locator(CARD_SELECTOR).all():
        title    = card.locator(TITLE_SELECTOR).text_content() or ""
        link     = card.locator(LINK_SELECTOR).get_attribute("href") or ""
        location = card.locator(LOCATION_SELECTOR).text_content() or ""
        posted   = card.locator(POSTED_SELECTOR).text_content() or ""

        rows.append({
            "title": title.strip(),
            "location": location.strip(),
            "posted": posted.strip(),
            "url": link.strip(),
        })

    # Apply your keyword/location/date filters.
    matches = [r for r in rows if passes_filter(r)]

    # Write results.
    with open("results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "location", "posted", "url"])
        writer.writeheader()
        writer.writerows(matches)

    print(f"Scraped {len(rows)} listings, {len(matches)} matched your criteria.")
    print("Written to results.csv")
    for row in matches[:20]:
        print(row)


def passes_filter(row):
    hay = (row.get("title", "") + " " + row.get("location", "")).lower()

    kw = CRITERIA["keywords"]
    if kw and not any(k.lower() in hay for k in kw):
        return False

    if any(k.lower() in hay for k in CRITERIA["exclude_keywords"]):
        return False

    locs = CRITERIA["locations"]
    if locs and not any(loc.lower() in row.get("location", "").lower() for loc in locs):
        return False

    days = CRITERIA["posted_within_days"]
    if days is not None and row.get("posted"):
        try:
            posted_date = datetime.strptime(row["posted"], "%m/%d/%Y")
            if (datetime.now() - posted_date).days > days:
                return False
        except ValueError:
            pass  # Unparseable date — keep the row

    return True


if __name__ == "__main__":
    run()