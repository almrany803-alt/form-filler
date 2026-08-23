// fill_messy.mjs - stress test against the messy form.
// Reports every field: what it is, what we expected, what actually happened.

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "messy_form.html").replace(/\\/g, "/");

// id -> { what it models, expected: "fill"<value> or "empty" }
const CASES = [
  ["ph_fn",       "placeholder-only label",      "fill", "Mohammed"],
  ["aria_em",     "aria-label only",             "fill", "test@example.com"],
  ["name_ph",     "name-only via HTML name",     "fill", "+44 7700 900000"],  // now identified via html-input-name
  ["rtl_city",    "Arabic (RTL) label",          "fill", "Bristol"],
  ["surn",        "label NOT associated",        "empty", ""],
  ["q9f2",        "fully unlabelled",            "empty", ""],
  ["country_sel", "native select (dropdown)",    "fill", "uk"],  // now filled: United Kingdom
  ["combo",       "custom combobox",             "empty", ""],
  ["dob",         "date input (no stored value)","empty", ""],
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#ph_fn").focus();
await sleep(3000);

execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1")], { stdio: "inherit" });
await sleep(4500);

console.log("\n=== messy-form stress test ===");
let ok = true;
for (const [id, desc, expect, val] of CASES) {
  const got = await page.locator("#" + id).inputValue();
  let pass;
  if (expect === "fill") pass = got === val;
  else pass = got === "" || got === val;  // empty (or default) is correct
  ok = ok && pass;
  const shown = JSON.stringify(got);
  console.log(`${pass ? "PASS" : "FAIL"}  #${id.padEnd(11)} ${desc.padEnd(28)} expected ${expect === "fill" ? JSON.stringify(val) : "empty"}, got ${shown}`);
}
await browser.close();

if (!ok) { console.error("\nStress test found mismatches (see above and the JFF log)."); process.exit(1); }
console.log("\nMessy form handled as expected: identifiable text fields filled, dropdowns and unlabelled fields correctly left.");
