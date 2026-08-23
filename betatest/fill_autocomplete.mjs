// fill_autocomplete.mjs - fields identified ONLY by the HTML autocomplete
// attribute (no labels, generic names). Proves the strongest signal is read.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "autocomplete_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#q1").focus();
await sleep(5000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(4000);
const FILLED = { q1: "Mohammed", q2: "Al Omrani", q3: "test@example.com",
                 q4: "+44 7700 900000", q5: "Bristol", q6: "United Kingdom" };
let ok = true;
console.log("=== autocomplete-only result ===");
for (const [id, want] of Object.entries(FILLED)) {
  const got = await page.locator("#" + id).inputValue();
  const p = got === want; ok = ok && p;
  console.log(`${p?"PASS":"FAIL"}  #${id} (autocomplete): expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
}
const q7 = await page.locator("#q7").inputValue();
const p7 = q7 === ""; ok = ok && p7;
console.log(`${p7?"PASS":"FAIL"}  #q7 (not saved, declined): expected empty, got ${JSON.stringify(q7)}`);
await browser.close();
if (!ok) process.exit(1);
console.log("Fields identified by autocomplete alone were filled; unsaved one declined.");
