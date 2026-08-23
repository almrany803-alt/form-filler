// fill_multiselect_form.mjs - whole-form fill over text + native multi-select.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "multiselect_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#fn").focus();
await sleep(4000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(6000);
let ok = true;
const fn = await page.locator("#fn").inputValue();
const chosen = await page.locator("#nat").evaluate((el) => Array.from(el.selectedOptions).map((o) => o.text));
console.log("=== whole-form: text + multi-select ===");
for (const [name, got, want] of [["#fn", fn, "Mohammed"]]) {
  const p = got === want; ok = ok && p;
  console.log(`${p ? "PASS" : "FAIL"}  ${name}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
}
const msOk = chosen.includes("Saudi"); ok = ok && msOk;
console.log(`${msOk ? "PASS" : "FAIL"}  #nat: expected Saudi selected, got ${JSON.stringify(chosen)}`);
await browser.close();
if (!ok) process.exit(1);
console.log("Whole-form fill set text and the multi-select together.");
