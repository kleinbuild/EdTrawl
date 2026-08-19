// search_edjoin.js
// Loads the saved session and scrapes job listings, then filters by your criteria.
//
// Because I don't have edjoin.org's exact DOM in front of me, this runs in two modes:
//   - DISCOVERY MODE (default on first run): dumps the search page's form fields and a
//     sample of result-row HTML to console + discovery.html, so you can confirm selectors.
//   - SCRAPE MODE: once selectors below are confirmed, extracts listings to results.csv.
//
// Edit the CONFIG block, then run `npm run search`.

import { chromium } from "playwright";
import fs from "fs";

// ============================ CONFIG ============================
const AUTH_FILE = "auth_state.json";

// Your search criteria. Leave a field as null/[] to ignore it.
// These are applied as a client-side filter over scraped rows, so they work
// even before you've wired up the site's own search form.
const CRITERIA = {
  keywords: [],          // e.g. ["math", "algebra"] — matches title/description (OR)
  excludeKeywords: [],   // e.g. ["substitute", "coach"] — drops rows containing any
  locations: [],         // e.g. ["Los Angeles", "Whittier"] — matches district/location (OR)
  postedWithinDays: null // e.g. 14 — only keep listings posted in the last N days
};

// The edjoin search results page. Adjust if you use a specific saved search or district.
const SEARCH_URL = "https://www.edjoin.org/Home/Jobs";

// Run headless once you trust it; keep false while confirming selectors.
const HEADLESS = false;

// Set to false once you've confirmed the selectors in the SELECTORS block below.
const DISCOVERY = true;

// Confirm these against discovery.html output before turning DISCOVERY off.
const SELECTORS = {
  resultRow: ".job-row, .search-result, [class*='JobResult']",
  title:     "a.job-title, h3 a, [class*='title'] a",
  link:      "a.job-title, h3 a, [class*='title'] a",
  location:  ".district, .location, [class*='district']",
  posted:    ".posted-date, .date, [class*='posted']"
};
// ================================================================

if (!fs.existsSync(AUTH_FILE)) {
  console.error(`No ${AUTH_FILE} found. Run \`npm run login\` first.`);
  process.exit(1);
}

const browser = await chromium.launch({ headless: HEADLESS });
const context = await browser.newContext({ storageState: AUTH_FILE });
const page = await context.newPage();

await page.goto(SEARCH_URL, { waitUntil: "networkidle" });

// Bail early if the session didn't take and we got bounced to a login page.
if (/login/i.test(page.url())) {
  console.error(`Got redirected to a login page (${page.url()}). The saved session may have expired — re-run \`npm run login\`.`);
  await browser.close();
  process.exit(1);
}

if (DISCOVERY) {
  const html = await page.content();
  fs.writeFileSync("discovery.html", html);

  const forms = await page.$$eval("input, select, textarea", (els) =>
    els.map((e) => ({
      tag: e.tagName.toLowerCase(),
      type: e.getAttribute("type"),
      name: e.getAttribute("name"),
      id: e.getAttribute("id"),
      placeholder: e.getAttribute("placeholder")
    }))
  );

  console.log("\n--- Form fields on the search page ---");
  console.log(JSON.stringify(forms, null, 2));
  console.log(`\nFull page HTML written to discovery.html`);
  console.log(`\nOpen discovery.html, find the repeating block for each job listing,`);
  console.log(`update the SELECTORS in this file, set DISCOVERY = false, and re-run.`);

  await browser.close();
  process.exit(0);
}

// -------- SCRAPE MODE --------
await page.waitForSelector(SELECTORS.resultRow, { timeout: 15000 }).catch(() => {
  console.error("No rows matched SELECTORS.resultRow. Re-run in DISCOVERY mode to fix selectors.");
});

const rows = await page.$$eval(
  SELECTORS.resultRow,
  (nodes, sel) =>
    nodes.map((n) => {
      const pick = (s) => {
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
    }),
  SELECTORS
);

// -------- CLIENT-SIDE FILTER --------
const now = Date.now();
const lc = (s) => (s || "").toLowerCase();

const matches = rows.filter((r) => {
  const hay = lc(r.title + " " + r.location);

  if (CRITERIA.keywords.length &&
      !CRITERIA.keywords.some((k) => hay.includes(lc(k)))) return false;

  if (CRITERIA.excludeKeywords.some((k) => hay.includes(lc(k)))) return false;

  if (CRITERIA.locations.length &&
      !CRITERIA.locations.some((l) => lc(r.location).includes(lc(l)))) return false;

  if (CRITERIA.postedWithinDays != null && r.posted) {
    const d = new Date(r.posted);
    if (!isNaN(d)) {
      const days = (now - d.getTime()) / 86400000;
      if (days > CRITERIA.postedWithinDays) return false;
    }
  }
  return true;
});

// -------- OUTPUT --------
const esc = (v) => `"${String(v).replace(/"/g, '""')}"`;
const csv = ["title,location,posted,url"]
  .concat(matches.map((r) => [r.title, r.location, r.posted, r.url].map(esc).join(",")))
  .join("\n");

fs.writeFileSync("results.csv", csv);

console.log(`Scraped ${rows.length} listings, ${matches.length} matched your criteria.`);
console.log(`Written to results.csv`);
console.table(matches.slice(0, 20));

await browser.close();
process.exit(0);
