# search_edjoin.py
# Loads the saved session and scrapes job listings, then filters by your criteria.
#
# Because I don't have edjoin.org's exact DOM in front of me, this runs in two modes:
#   - DISCOVERY MODE (default on first run): dumps the search page's form fields and a
#     sample of result-row HTML to console + discovery.html, so you can confirm selectors.
#   - SCRAPE MODE: once selectors below are confirmed, extracts listings to results.csv.
#
# Edit the CONFIG block, then run: python search_edjoin.py

import csv
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

# ============================ CONFIG ============================
AUTH_FILE = "auth_state.json"

# Your search criteria. Leave a field as []/None to ignore it.
# These are applied as a client-side filter over scraped rows, so they work
# even before you've wired up the site's own search form.
CRITERIA = {
    "keywords": [],            # e.g. ["math", "algebra"] — matches title/description (OR)
    "exclude_keywords": [],    # e.g. ["substitute", "coach"] — drops rows containing any
    "locations": [],           # e.g. ["Los Angeles", "Whittier"] — matches district/location (OR)
    "posted_within_days": None # e.g. 14 — only keep listings posted in the last N days
}

# The edjoin search results page. Adjust if you use a specific saved search or district.
SEARCH_URL = "https://www.edjoin.org/Home/Jobs"

# Run headless once you trust it; keep False while confirming selectors.
HEADLESS = False

# Set to False once you've confirmed the selectors in the SELECTORS block below.
DISCOVERY = True

# Confirm these against discovery.html output before turning DISCOVERY off.
SELECTORS = {
    "result_row": ".job-row, .search-result, [class*='JobResult']",
    "title":      "a.job-title, h3 a, [class*='title'] a",
    "link":       "a.job-title, h3 a, [class*='title'] a",
    "location":   ".district, .location, [class*='district']",
    "posted":     ".posted-date, .date, [class*='posted']"
}
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

        # Bail early if the session didn't take and we got bounced to a login page.
        if re.search(r"login", page.url, re.IGNORECASE):
            print(f"Got redirected to a login page ({page.url}). "
                  "The saved session may have expired — re-run capture_login.py.")
            browser.close()
            sys.exit(1)

        if DISCOVERY:
            run_discovery(page)
            browser.close()
            return

        run_scrape(page)
        browser.close()


def run_discovery(page):
    html = page.content()
    Path("discovery.html").write_text(html, encoding="utf-8")

    forms = page.eval_on_selector_all(
        "input, select, textarea",
        """els => els.map(e => ({
            tag: e.tagName.toLowerCase(),
            type: e.getAttribute("type"),
            name: e.getAttribute("name"),
            id: e.getAttribute("id"),
            placeholder: e.getAttribute("placeholder")
        }))"""
    )

    print("\n--- Form fields on the search page ---")
    for field in forms:
        print(field)
    print(f"\nFull page HTML written to discovery.html")
    print(f"\nOpen discovery.html, find the repeating block for each job listing,")
    print(f"update the SELECTORS in this file, set DISCOVERY = False, and re-run.")


def run_scrape(page):
    try:
        page.wait_for_selector(SELECTORS["result_row"], timeout=15000)
    except Exception:
        print("No rows matched SELECTORS['result_row']. "
              "Re-run in DISCOVERY mode to fix selectors.")
        return

    rows = page.eval_on_selector_all(
        SELECTORS["result_row"],
        """(nodes, sel) => nodes.map(n => {
            const pick = s => {
                const el = n.querySelector(s);
                return el ? el.textContent.trim() : "";
            };
            const linkEl = n.querySelector(sel.link);
            return {
                title: pick(sel.title),
                location: pick(sel.location),
                posted: pick(sel.posted),
                url: linkEl ? linkEl.href : ""
            };
        })""",
        SELECTORS
    )

    # -------- CLIENT-SIDE FILTER --------
    matches = [r for r in rows if passes_filter(r)]

    # -------- OUTPUT --------
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
