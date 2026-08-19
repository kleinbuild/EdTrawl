// capture_login.js
// Opens a real (headed) browser, lets YOU log in by hand, then saves the
// authenticated session (cookies + localStorage) to auth_state.json.
// Run this once; re-run whenever the saved session expires.

import { chromium } from "playwright";
import fs from "fs";

const AUTH_FILE = "auth_state.json";
const START_URL = "https://www.edjoin.org/Home/Login";

const browser = await chromium.launch({ headless: false });
const context = await browser.newContext();
const page = await context.newPage();

await page.goto(START_URL, { waitUntil: "domcontentloaded" });

console.log(`
============================================================
A browser window just opened.

1. Log into edjoin.org in that window (do it manually).
2. Get all the way to your logged-in dashboard / home page.
3. Come back HERE and press Enter to save the session.
============================================================
`);

// Wait for you to press Enter in the terminal.
await new Promise((resolve) => {
  process.stdin.resume();
  process.stdin.once("data", () => resolve());
});

await context.storageState({ path: AUTH_FILE });
console.log(`\nSaved session to ${AUTH_FILE}. You can close this any time.`);

await browser.close();
process.exit(0);
