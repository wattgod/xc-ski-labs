// Real-browser check for #118: every cell of a /search/ race row opens that
// race, nothing outside the rows does, keyboard focus rings the row, and one
// click sends one race_result_click. Run by tests/test_search_row_links_browser.py.
//
// usage: node search_row_links.js <web dir>
// Prints one JSON line per engine; engines that cannot launch report "skip".
const fs = require("fs");
const path = require("path");

let pw;
try {
  pw = require("playwright");
} catch (e) {
  console.log(JSON.stringify({ engine: "all", status: "skip", reason: "playwright not installed" }));
  process.exit(0);
}

const WEB = process.argv[2];
const ORIGIN = "https://xcskilabs.com";
const RACES = Array.from({ length: 8 }, (_, i) => ({
  n: "Fixture Race " + i, dn: "Fixture Race " + i, s: "fixture-race-" + i,
  t: (i % 4) + 1, sc: 90 - i, co: "Norway", cc: "NO", d: 30 + i, di: "classic",
  st: "fixture race " + i,
}));

async function route(page) {
  await page.route("**/*", (r) => {
    const url = new URL(r.request().url());
    if (url.origin !== ORIGIN) return r.abort();
    if (url.pathname === "/search/") {
      return r.fulfill({ contentType: "text/html", body: fs.readFileSync(path.join(WEB, "nordic-lab-search.html"), "utf8") });
    }
    if (url.pathname === "/search/nordic-lab-search.js") {
      return r.fulfill({ contentType: "text/javascript", body: fs.readFileSync(path.join(WEB, "nordic-lab-search.js"), "utf8") });
    }
    if (url.pathname === "/search/race-index.json") {
      return r.fulfill({ contentType: "application/json", body: JSON.stringify({ races: RACES }) });
    }
    if (url.pathname.startsWith("/race/")) {
      return r.fulfill({ contentType: "text/html", body: "<title>race</title>" });
    }
    return r.fulfill({ status: 204, body: "" });
  });
}

async function check(name, width) {
  // XC_CHROMIUM_PATH points at a local Chromium when Playwright's own build
  // for this version isn't downloaded.
  const opts = name === "chromium" && process.env.XC_CHROMIUM_PATH ? { executablePath: process.env.XC_CHROMIUM_PATH } : {};
  const browser = await pw[name].launch(opts);
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  page.setDefaultTimeout(10000);
  page.setDefaultNavigationTimeout(10000);
  await route(page);
  let jsLoads = 0;
  page.on("request", (q) => { if (q.url().endsWith("/nordic-lab-search.js")) jsLoads++; });
  await page.goto(ORIGIN + "/search/");
  await page.waitForSelector(".race-table tbody tr a.race-name");

  const geo = await page.evaluate(() => {
    const out = { total: 0, hits: 0, misses: [], linksPerRow: [], cueFocusable: false };
    const rows = [...document.querySelectorAll(".race-table tbody tr")];
    for (const tr of rows) {
      const link = tr.querySelector("a.race-name");
      out.linksPerRow.push(tr.querySelectorAll("a").length);
      const cue = tr.querySelector(".rowlink");
      if (!cue || cue.tagName === "A" || cue.getAttribute("aria-hidden") !== "true") out.cueFocusable = true;
      for (const td of tr.cells) {
        const b = td.getBoundingClientRect();
        if (!b.width) continue;
        td.scrollIntoView({ block: "center" });
        const c = td.getBoundingClientRect();
        // 2px inside the top and bottom edges catches a neighbour row's overflow.
        for (const [fx, y] of [[0.5, c.top + c.height / 2], [0.1, c.top + 2], [0.9, c.bottom - 2]]) {
          out.total++;
          const el = document.elementFromPoint(c.left + c.width * fx, y);
          if (el && el.closest("a") === link) out.hits++;
          else out.misses.push(link.textContent + "/" + td.cellIndex + "->" + (el ? el.tagName : "null"));
        }
      }
    }
    const table = document.querySelector(".race-table");
    table.scrollIntoView({ block: "end" });
    const t = table.getBoundingClientRect();
    const below = document.elementFromPoint(t.left + t.width / 2, t.bottom + 4);
    out.belowIsLink = !!(below && below.closest("a.race-name"));
    out.hscroll = document.documentElement.scrollWidth > window.innerWidth;
    out.misses = out.misses.slice(0, 5);
    return out;
  });

  // Keyboard: Safari's Tab skips links unless Option is held.
  const TAB = name === "webkit" ? "Alt+Tab" : "Tab";
  await page.evaluate(() => { window.scrollTo(0, 0); document.getElementById("searchInput").focus(); });
  let reached = false;
  for (let i = 0; i < 40 && !reached; i++) {
    await page.keyboard.press(TAB);
    reached = await page.evaluate(() => document.activeElement.matches(".race-table tbody tr:first-child a.race-name"));
  }
  const ring = await page.evaluate(() => getComputedStyle(document.activeElement.closest("tr")).outlineStyle);
  await page.keyboard.press(TAB);
  const nextIsRow2 = await page.evaluate(() => document.activeElement.matches(".race-table tbody tr:nth-child(2) a.race-name"));

  // One click on a non-name cell sends exactly one race_result_click.
  await page.evaluate(() => {
    window.__events = [];
    window.gtag = function () { window.__events.push([...arguments]); };
    document.addEventListener("click", (e) => e.preventDefault());
  });
  const scoreCell = page.locator(".race-table tbody tr").nth(2).locator("td").nth(4);
  await scoreCell.scrollIntoViewIfNeeded();
  let box = await scoreCell.boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  const events = await page.evaluate(() => window.__events.filter((e) => e[1] === "race_result_click").map((e) => e[2].race_slug));

  const firstLoadJs = jsLoads;
  // And a real click navigates to that race.
  await page.goto(ORIGIN + "/search/");
  await page.waitForSelector(".race-table tbody tr a.race-name");
  const cell = page.locator(".race-table tbody tr").nth(3).locator("td").nth(4);
  await cell.scrollIntoViewIfNeeded();
  box = await cell.boundingBox();
  await Promise.all([page.waitForURL("**/race/fixture-race-3/", { timeout: 10000 }), page.mouse.click(box.x + box.width / 2, box.y + box.height / 2)]);

  await browser.close();
  return { ...geo, reached, ring, nextIsRow2, events, jsLoads: firstLoadJs, navigated: true };
}

(async () => {
  for (const name of ["chromium", "webkit", "firefox"]) {
    for (const width of [1440, 390]) {
      try {
        // A hung engine must not stall the suite: give each run 60s.
        const r = await Promise.race([
          check(name, width),
          new Promise((_, reject) => setTimeout(() => reject(new Error("timed out after 60s")), 60000)),
        ]);
        console.log(JSON.stringify({ engine: name, width, status: "ran", ...r }));
      } catch (e) {
        const msg = String(e && e.message || e);
        const missing = /Executable doesn't exist|browserType\.launch/.test(msg);
        console.log(JSON.stringify({ engine: name, width, status: missing ? "skip" : "error", reason: msg.split("\n")[0] }));
      }
    }
  }
  process.exit(0);
})();
