# capture_login.py
# Opens a real (headed) browser, lets YOU log in by hand, then saves the
# authenticated session (cookies + localStorage) to auth_state.json.
# Run this once; re-run whenever the saved session expires.

from playwright.sync_api import sync_playwright

AUTH_FILE = "auth_state.json"
START_URL = "https://www.edjoin.org/Home/Login"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto(START_URL, wait_until="domcontentloaded")

    print("""
============================================================
A browser window just opened.

1. Log into edjoin.org in that window (do it manually).
2. Get all the way to your logged-in dashboard / home page.
3. Come back HERE and press Enter to save the session.
============================================================
""")

    input()  # Wait for Enter

    context.storage_state(path=AUTH_FILE)
    print(f"\nSaved session to {AUTH_FILE}. You can close this any time.")

    browser.close()
